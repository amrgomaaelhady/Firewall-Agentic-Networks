"""
Generate firewall mitigation guidelines from ConVerse conversation logs.

This script generates domain-specific firewall rules for:
1. Data Abstraction Firewall - filters sensitive user data
2. Language Converter Firewall - controls external agent input language

Enhanced features:
- Auto-construct paths from domain/model/mode/personas
- Support multiple personas in one run (1,2,3 or 1-12 or 'all')
- Use LLM class same as main.py
- Iterate across all specified personas

Usage:
    # Single persona
    python generate_guidelines.py --domain travel_planning \\
        --firewall_type both \\
        --persona_dir logs/travel_planning/gpt_5_chat/baseline/persona1 \\
        --llm_name gpt-4 --provider openai

    # Multiple personas
    python generate_guidelines.py --domain travel_planning \\
        --firewall_type both \\
        --model_folder_name gpt_5_chat \\
        --mode baseline \\
        --personas "1,2,3" \\
        --num_privacy_samples 10 \\
        --num_security_samples 5 \\
        --llm_name gpt-4

    # All personas at once
    python generate_guidelines.py --domain travel_planning \\
        --firewall_type both \\
        --model_folder_name gpt_5_chat \\
        --mode baseline \\
        --personas all \\
        --llm_name gpt-4
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from model import LLM
from mitigation_guidelines.utils import (
    get_conversation_history,
    collect_attack_folders,
    collect_benign_folders,
    load_conversations_from_folders,
    extract_tagged_content,
    GUIDELINES_TAG,
    LANGUAGE_TAG,
)
from mitigation_guidelines.prompts.data_abstraction_prompts import (
    get_data_abstraction_prompt,
    get_previous_guidelines_prompt,
    DOMAIN_TASK_DESCRIPTIONS,
)
from mitigation_guidelines.prompts.language_converter_prompts import (
    get_language_converter_prompt,
    get_previous_template_prompt,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate firewall mitigation guidelines from ConVerse logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Required arguments
    parser.add_argument(
        "--domain",
        type=str,
        required=True,
        choices=["travel_planning", "real_estate", "insurance"],
        help="Domain for guideline generation"
    )
    parser.add_argument(
        "--firewall_type",
        type=str,
        required=True,
        choices=["data_abstraction", "language_converter", "both"],
        help="Type of firewall to generate"
    )
    
    # Path construction arguments (new approach)
    parser.add_argument(
        "--model_folder_name",
        type=str,
        help="Model folder name in logs (e.g., 'gpt_5_chat', 'claude', 'gemini')"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["baseline", "taskConfined"],
        help="Simulation mode folder (baseline or taskConfined)"
    )
    parser.add_argument(
        "--personas",
        type=str,
        help="Persona numbers: single (1), list (1,2,3), range (1-12), or 'all' for all personas"
    )
    parser.add_argument(
        "--logs_folder",
        type=str,
        default="logs",
        help="Base logs directory (default: logs)"
    )
    
    # Legacy argument (for backward compatibility)
    parser.add_argument(
        "--persona_dir",
        type=str,
        help="Direct path to persona directory (legacy, overrides constructed path)"
    )
    
    # Attack sampling arguments
    parser.add_argument(
        "--num_privacy_samples",
        type=int,
        default=None,
        help="Number of privacy attacks to sample per persona (None = all)"
    )
    parser.add_argument(
        "--num_security_samples",
        type=int,
        default=None,
        help="Number of security attacks to sample per persona (None = all)"
    )
    parser.add_argument(
        "--sampling_seed",
        type=int,
        default=42,
        help="Random seed for attack sampling (default: 42)"
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default=None,
        help="Path to config file with predefined personas and attacks (overrides --personas and sampling)"
    )
    
    # LLM configuration (matching main.py pattern)
    parser.add_argument(
        "--llm_name",
        type=str,
        default="gpt-4.1-2025-04-14",
        help="LLM model name for generating guidelines"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["azure", "openai", "anthropic", "anthropic_vertex", "google", "huggingface"],
        help="LLM provider (auto-detected if not specified)"
    )
    parser.add_argument(
        "--azure_endpoint",
        type=str,
        help="Azure endpoint URL (overrides environment variable)"
    )
    parser.add_argument(
        "--use_azure_credentials",
        action="store_true",
        default=True,
        help="Use DefaultAzureCredential for Azure (recommended)"
    )
    
    # Output configuration
    parser.add_argument(
        "--output_dir",
        type=str,
        default="mitigation_guidelines/generated",
        help="Output directory for generated guidelines"
    )
    parser.add_argument(
        "--previous_guidelines",
        type=str,
        default=None,
        help="Path to previous guidelines file for refinement"
    )
    
    # Optional flags
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information"
    )
    parser.add_argument(
        "--max_new_tokens",
        type=int,
        default=4000,
        help="Maximum tokens for LLM generation (increase if JSON gets truncated)"
    )
    
    return parser.parse_args()


def load_config_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a sample config file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Dictionary with 'personas', 'privacy_attacks', 'security_attacks'
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines()]
    
    config = {
        'personas': [],
        'privacy_attacks': [],
        'security_attacks': []
    }
    
    current_section = None
    for line in lines:
        if not line:
            continue
        if line == "PERSONAS":
            current_section = "personas"
        elif line == "PRIVACY_ATTACKS":
            current_section = "privacy_attacks"
        elif line == "SECURITY_ATTACKS":
            current_section = "security_attacks"
        elif current_section == "personas":
            config['personas'] = [int(p) for p in line.split(',')]
        elif current_section == "privacy_attacks":
            config['privacy_attacks'].append(line)
        elif current_section == "security_attacks":
            config['security_attacks'].append(line)
    
    return config


def parse_persona_arg(personas_str: str) -> List[int]:
    """
    Parse persona argument into list of persona IDs.
    
    Args:
        personas_str: String specifying personas (e.g., '1', '1,2,3', '1-12', 'all')
        
    Returns:
        List of persona IDs
        
    Examples:
        '1' -> [1]
        '1,2,3' -> [1, 2, 3]
        '1-5' -> [1, 2, 3, 4, 5]
        'all' -> [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    """
    if not personas_str:
        return [1]  # default
    
    personas_str = personas_str.strip().lower()
    
    # Handle 'all'
    if personas_str == 'all':
        return list(range(1, 13))  # ConVerse has 12 personas
    
    # Handle range (e.g., '1-5')
    if '-' in personas_str:
        parts = personas_str.split('-')
        if len(parts) == 2:
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                return list(range(start, end + 1))
            except ValueError:
                raise ValueError(f"Invalid persona range: {personas_str}")
    
    # Handle comma-separated list (e.g., '1,2,3')
    if ',' in personas_str:
        try:
            return [int(p.strip()) for p in personas_str.split(',')]
        except ValueError:
            raise ValueError(f"Invalid persona list: {personas_str}")
    
    # Handle single number
    try:
        return [int(personas_str)]
    except ValueError:
        raise ValueError(f"Invalid persona specification: {personas_str}")


def construct_persona_dirs(args) -> List[str]:
    """
    Construct persona directory paths from domain/model/mode/personas arguments.
    
    Args:
        args: Command line arguments
        
    Returns:
        List of persona directory paths
    """
    # If legacy persona_dir is provided, use it directly
    if args.persona_dir:
        return [args.persona_dir]
    
    # Validate required arguments for path construction
    if not args.model_folder_name:
        raise ValueError("Either --persona_dir or --model_folder_name must be provided")
    if not args.mode:
        raise ValueError("Either --persona_dir or --mode must be provided")
    
    # Parse personas
    persona_ids = parse_persona_arg(args.personas)
    
    # Construct paths
    persona_dirs = []
    for persona_id in persona_ids:
        path = os.path.join(
            args.logs_folder,
            args.domain,
            args.model_folder_name,
            args.mode,
            f"persona{persona_id}"
        )
        persona_dirs.append(path)
    
    return persona_dirs


def generate_data_abstraction_guidelines(
    args,
    llm_instance: LLM,
    paired_conversations: list,
    prev_guidelines: str = "",
    output_file: str = None
) -> str:
    """
    Generate data abstraction firewall guidelines.
    
    Args:
        args: Command line arguments
        llm_instance: LLM instance for generation
        paired_conversations: List of dicts with 'persona', 'benign', 'attack' keys
        prev_guidelines: Previous guidelines for iterative refinement
        output_file: Path to save guidelines after each iteration (optional)
        
    Returns:
        Generated guidelines text
    """
    print("\n" + "="*80)
    print("GENERATING DATA ABSTRACTION FIREWALL GUIDELINES")
    print("="*80)
    
    # Get domain-specific task description
    domain_task_desc = DOMAIN_TASK_DESCRIPTIONS.get(
        args.domain,
        DOMAIN_TASK_DESCRIPTIONS["travel_planning"]  # fallback
    )
    
    # Get base prompt
    base_prompt = get_data_abstraction_prompt(args.domain, domain_task_desc)
    
    # Iterate through all paired conversations
    num_iterations = len(paired_conversations)
    
    for i, pair in enumerate(paired_conversations):
        if args.verbose:
            print(f"\n--- Iteration {i+1}/{num_iterations} ({pair['persona']}) ---")
        
        benign_history = get_conversation_history(pair['benign'])
        attack_history = get_conversation_history(pair['attack'])
        
        # Build prompt
        prompt = base_prompt
        
        # Add previous guidelines if available
        if prev_guidelines:
            prompt += "\n\n" + get_previous_guidelines_prompt(prev_guidelines)
        
        # Add conversation examples
        prompt += f"""

### Conversation Examples

**Benign Conversation:**
{benign_history}

**Attack Conversation (contains privacy/security breach attempt):**
{attack_history}

### Your Task

Based on the above conversations, generate or refine data abstraction guidelines that:
1. Allow necessary information flow for the benign conversation
2. Block sensitive data exposure from the attack conversation
3. Are generalizable to similar scenarios in {args.domain}

Provide your guidelines in the following format:

<{GUIDELINES_TAG}>
[Your data abstraction guidelines here]
</{GUIDELINES_TAG}>
"""
        
        # Call LLM
        messages = [{"role": "system", "content": prompt}]
        
        # Save prompt to file for debugging (append mode to see all iterations)
        mode = "w" if i == 0 else "a"
        with open("debug_data_abstraction_prompt.txt", mode, encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"ITERATION {i+1}/{num_iterations}\n")
            f.write(f"{'='*80}\n")
            f.write(prompt)
        print(f"DEBUG: Prompt iteration {i+1} saved (length: {len(prompt)} chars)")
        
        response = llm_instance.call_model(messages)
        
        print(f"DEBUG: Response length: {len(response) if response else 0}")
        print(f"DEBUG: Response type: {type(response)}")
        print(f"DEBUG: Response repr: {repr(response[:500] if response else response)}")
        
        if args.verbose:
            print(f"LLM Response:\n{response}\n")
        
        # Extract guidelines
        prev_guidelines = extract_tagged_content(response, GUIDELINES_TAG)
        
        if not prev_guidelines:
            print(f"Warning: No guidelines extracted in iteration {i+1}")
        else:
            # Save after each iteration if output file is specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(prev_guidelines)
                print(f"  ✓ Guidelines saved to: {output_file} (iteration {i+1}/{num_iterations})")
        
        print(f"Iteration {i+1}/{num_iterations} complete")
    
    return prev_guidelines


def generate_language_converter_template(
    args,
    llm_instance: LLM,
    benign_conversations: list,
    prev_template: str = "",
    output_file: str = None
) -> str:
    """
    Generate language converter firewall controlled language template.
    
    NOTE: Language converter firewall only uses BENIGN conversations (no attacks).
    
    Args:
        args: Command line arguments
        llm_instance: LLM instance for generation
        benign_conversations: List of benign conversation data
        prev_template: Previous template for iterative refinement
        output_file: Path to save template after each iteration (optional)
        
    Returns:
        Generated template text (JSON format)
    """
    print("\n" + "="*80)
    print("GENERATING LANGUAGE CONVERTER FIREWALL LANGUAGE TEMPLATE")
    print("="*80)
    
    # Get domain-specific task description
    domain_task_desc = DOMAIN_TASK_DESCRIPTIONS.get(
        args.domain,
        DOMAIN_TASK_DESCRIPTIONS["travel_planning"]  # fallback
    )
    
    # Get base prompt
    base_prompt = get_language_converter_prompt(args.domain, domain_task_desc)
    
    # Iterate through benign conversations only
    for i, benign_conv in enumerate(benign_conversations):
        if args.verbose:
            print(f"\n--- Iteration {i+1}/{len(benign_conversations)} ---")
        
        benign_history = get_conversation_history(benign_conv)
        
        # Build prompt
        prompt = base_prompt
        
        # Add previous template if available
        if prev_template:
            prompt += "\n\n" + get_previous_template_prompt(prev_template)
        
        # Add conversation example
        prompt += f"""

### Benign Conversation Example

{benign_history}

### Your Task

Based on the above benign conversation, generate or refine a JSON template that:
1. Captures all necessary communication patterns for {args.domain} tasks
2. Restricts external agent responses to structured key-value pairs
3. Prevents free-form text that could contain social engineering attempts

Provide your template in the following format:

<{LANGUAGE_TAG}>
{{
  "key1": "description of allowed values",
  "key2": "description of allowed values",
  ...
}}
</{LANGUAGE_TAG}>
"""
        
        # Call LLM
        messages = [{"role": "system", "content": prompt}]
        
        # Save prompt to file for debugging (append mode to see all iterations)
        mode = "w" if i == 0 else "a"
        with open("debug_language_converter_prompt.txt", mode, encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"ITERATION {i+1}/{len(benign_conversations)}\n")
            f.write(f"{'='*80}\n")
            f.write(prompt)
        print(f"DEBUG: Language converter prompt iteration {i+1} saved (length: {len(prompt)} chars)")
        
        response = llm_instance.call_model(messages)
        
        # Save response for debugging
        mode_resp = "w" if i == 0 else "a"
        with open("debug_language_converter_response.txt", mode_resp, encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"ITERATION {i+1} RESPONSE\n")
            f.write(f"{'='*80}\n")
            f.write(response)
        
        print(f"DEBUG: Language converter response length: {len(response) if response else 0}")
        print(f"DEBUG: Language converter response preview: {repr(response[:300] if response else response)}")
        
        if args.verbose:
            print(f"LLM Response:\n{response}\n")
        
        # Extract template - try tagged content first, then fallback to JSON extraction
        prev_template = extract_tagged_content(response, LANGUAGE_TAG)
        
        if not prev_template and response:
            # Fallback: try to extract JSON directly (LLM might not use tags)
            import re
            
            # Look for JSON starting with { - match balanced braces
            # First, try to find where JSON actually starts (after any preamble text)
            lines = response.split('\n')
            json_start_idx = -1
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('{'):
                    json_start_idx = idx
                    break
            
            if json_start_idx >= 0:
                # Join from the JSON start onwards
                potential_json = '\n'.join(lines[json_start_idx:])
                # Find the matching closing brace
                brace_count = 0
                json_end = -1
                for char_idx, char in enumerate(potential_json):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = char_idx + 1
                            break
                
                if json_end > 0:
                    prev_template = potential_json[:json_end]
                    print(f"Info: Extracted JSON without tags in iteration {i+1}")
                else:
                    print(f"Warning: Could not find complete JSON in iteration {i+1}")
            else:
                print(f"Warning: No template extracted in iteration {i+1}")
        elif not prev_template:
            print(f"Warning: No template extracted in iteration {i+1}")
        else:
            # Save after each iteration if output file is specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(prev_template)
                print(f"  ✓ Template saved to: {output_file} (iteration {i+1}/{len(benign_conversations)})")
        
        print(f"Iteration {i+1}/{len(benign_conversations)} complete")
    
    return prev_template


def validate_and_fix_json_with_llm(json_str: str, llm_instance: LLM) -> tuple[bool, str, str]:
    """
    Validate JSON and use LLM to fix if invalid.
    
    Returns:
        (is_valid, fixed_json, error_message)
    """
    import json
    
    # Try parsing as-is first
    try:
        json.loads(json_str)
        return True, json_str, ""
    except json.JSONDecodeError as e:
        original_error = str(e)
    
    # Ask LLM to fix the JSON
    print(f"\nJSON validation failed: {original_error}")
    print("Asking LLM to fix the JSON...")
    
    fix_prompt = f"""The following JSON has syntax errors:

{json_str}

Error message: {original_error}

Please fix the JSON and return ONLY valid JSON (no explanations, no markdown, just the fixed JSON).
Common issues to fix:
- Comments with // are not valid in JSON - remove them
- Unquoted values like Type:bool should be "Type:bool"
- Ensure all property names are in double quotes
- Remove trailing commas before }} or ]

Return the corrected JSON:"""
    
    try:
        messages = [{"role": "user", "content": fix_prompt}]
        fixed_json = llm_instance.call_model(messages)
        
        # Try to extract JSON if LLM added explanations
        if not fixed_json.strip().startswith('{'):
            # Find the JSON object
            lines = fixed_json.split('\n')
            for idx, line in enumerate(lines):
                if line.strip().startswith('{'):
                    fixed_json = '\n'.join(lines[idx:])
                    break
        
        # Validate the fixed version
        json.loads(fixed_json)
        return True, fixed_json, f"Fixed by LLM (original error: {original_error})"
    except Exception as e:
        return False, json_str, f"LLM fix failed: {str(e)}"


def main():
    """Main execution function."""
    args = parse_args()
    
    print("="*80)
    print("CONVERSE FIREWALL GUIDELINE GENERATOR")
    print("="*80)
    print(f"Domain: {args.domain}")
    print(f"Firewall Type: {args.firewall_type}")
    
    # Load config file if provided
    config = None
    if args.config_file:
        print(f"Loading configuration from: {args.config_file}")
        config = load_config_file(args.config_file)
        print(f"Config loaded: {len(config['personas'])} personas, {len(config['privacy_attacks'])} privacy attacks, {len(config['security_attacks'])} security attacks")
        # Override personas argument with config personas
        args.personas = ",".join(map(str, config['personas']))
    
    # Construct persona directories
    try:
        persona_dirs = construct_persona_dirs(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    print(f"Personas to process: {len(persona_dirs)}")
    for pdir in persona_dirs:
        print(f"  - {pdir}")
    
    if config:
        print(f"Privacy Attacks: {len(config['privacy_attacks'])} (from config)")
        print(f"Security Attacks: {len(config['security_attacks'])} (from config)")
    else:
        print(f"Privacy Samples per persona: {args.num_privacy_samples or 'ALL'}")
        print(f"Security Samples per persona: {args.num_security_samples or 'ALL'}")
    print(f"LLM: {args.llm_name}")
    
    # Validate all persona directories exist
    for persona_dir in persona_dirs:
        if not os.path.exists(persona_dir):
            print(f"Error: Persona directory not found: {persona_dir}")
            sys.exit(1)
    
    # Create output directory with domain subfolder
    domain_output_dir = os.path.join(args.output_dir, args.domain)
    os.makedirs(domain_output_dir, exist_ok=True)
    
    # Initialize LLM using the same pattern as main.py
    llm_instance = LLM(llm_name=args.llm_name, config=args)
    
    # Determine and print the actual provider being used
    provider = llm_instance._determine_provider() if hasattr(llm_instance, '_determine_provider') else getattr(args, 'provider', 'auto-detected')
    print(f"Provider: {provider}")
    if provider == "anthropic_vertex":
        print(f"  → Using Anthropic Claude via Google Cloud Vertex AI (Region: {os.getenv('GOOGLE_CLOUD_REGION', 'us-east5')})")
    elif provider == "anthropic":
        print(f"  → Using Anthropic Claude via direct API")
    elif provider == "google":
        print(f"  → Using Google Gemini API")
    print("="*80)
    
    # Load previous guidelines if specified
    prev_content = ""
    if args.previous_guidelines and os.path.exists(args.previous_guidelines):
        with open(args.previous_guidelines, 'r', encoding='utf-8') as f:
            prev_content = f.read()
        print(f"Loaded previous guidelines from: {args.previous_guidelines}")
    
    # Collect conversations from ALL personas
    # Structure: dict[persona_id] = {'benign': [...], 'attacks': [...]}
    persona_conversations = {}
    
    # If using config file, load attacks directly with persona tracking
    if config and args.firewall_type in ["data_abstraction", "both"]:
        print(f"\n{'='*60}")
        print("Loading attacks from config file")
        print(f"{'='*60}")
        
        base_logs_dir = os.path.join("logs", args.domain, args.model_folder_name, args.mode)
        
        for attack_file in config['privacy_attacks'] + config['security_attacks']:
            attack_path = os.path.join(base_logs_dir, attack_file)
            if os.path.exists(attack_path):
                # Extract persona number from path (e.g., "persona1/privacy/...")
                persona_id = attack_file.split('/')[0]  # e.g., "persona1"
                
                with open(attack_path, 'r', encoding='utf-8') as f:
                    conversation = json.load(f)
                
                if persona_id not in persona_conversations:
                    persona_conversations[persona_id] = {'benign': [], 'attacks': []}
                persona_conversations[persona_id]['attacks'].append(conversation)
            else:
                print(f"Warning: Attack file not found: {attack_path}")
        
        total_attacks = sum(len(p['attacks']) for p in persona_conversations.values())
        print(f"Loaded {total_attacks} attack conversations from config")
    
    for persona_dir in persona_dirs:
        persona_name = os.path.basename(persona_dir)
        print(f"\n{'='*60}")
        print(f"Processing {persona_name}")
        print(f"{'='*60}")
        
        # Initialize if not already done
        if persona_name not in persona_conversations:
            persona_conversations[persona_name] = {'benign': [], 'attacks': []}
        
        # Collect benign conversations (ALWAYS ALL)
        print("Collecting benign conversations...")
        benign_folders = collect_benign_folders(persona_dir)
        if args.verbose:
            print(f"  Benign folders found: {benign_folders}")
        benign_conversations = load_conversations_from_folders(benign_folders)
        print(f"Loaded {len(benign_conversations)} benign conversations from {persona_name} ({len(benign_folders)} folders)")
        persona_conversations[persona_name]['benign'] = benign_conversations
        
        # Collect attack conversations if needed for data abstraction (and NOT using config file)
        if args.firewall_type in ["data_abstraction", "both"] and not config:
            print("Collecting attack conversations for data abstraction firewall...")
            
            privacy_folders = collect_attack_folders(
                persona_dir,
                "privacy",
                args.num_privacy_samples,
                args.sampling_seed
            )
            security_folders = collect_attack_folders(
                persona_dir,
                "security",
                args.num_security_samples,
                args.sampling_seed
            )
            
            # Combine privacy and security attacks
            attack_folders = privacy_folders + security_folders
            attack_conversations = load_conversations_from_folders(attack_folders)
            
            print(f"Loaded {len(attack_conversations)} attack conversations from {persona_name} " +
                  f"({len(privacy_folders)} privacy, {len(security_folders)} security)")
            persona_conversations[persona_name]['attacks'] = attack_conversations
    
    # Create persona-aware pairs for data abstraction
    paired_conversations = []
    total_benign = 0
    total_attacks = 0
    
    for persona_name, convos in persona_conversations.items():
        benign_list = convos['benign']
        attack_list = convos['attacks']
        
        total_benign += len(benign_list)
        total_attacks += len(attack_list)
        
        # Pair each attack with a benign from same persona (cycle benign if needed)
        for i, attack_conv in enumerate(attack_list):
            benign_conv = benign_list[i % len(benign_list)] if benign_list else None
            if benign_conv:
                paired_conversations.append({
                    'persona': persona_name,
                    'benign': benign_conv,
                    'attack': attack_conv
                })
    
    # Summary of collected data
    print(f"\n{'='*80}")
    print("COLLECTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total benign conversations: {total_benign}")
    if args.firewall_type in ["data_abstraction", "both"]:
        print(f"Total attack conversations: {total_attacks}")
        print(f"Persona-aware pairs created: {len(paired_conversations)}")
    print(f"{'='*80}")
    
    # Generate guidelines based on firewall type
    if args.firewall_type in ["data_abstraction", "both"]:
        # Prepare output file path
        output_file = os.path.join(
            domain_output_dir,
            f"{args.domain}_data_abstraction_guidelines.txt"
        )
        
        # Generate data abstraction guidelines using persona-aware pairs
        # Guidelines will be saved after each iteration
        data_guidelines = generate_data_abstraction_guidelines(
            args,
            llm_instance,
            paired_conversations,
            prev_content,
            output_file=output_file
        )
        
        print(f"\n✓ Data abstraction guidelines generation complete: {output_file}")
        print(f"  Final version saved after {len(paired_conversations)} iterations")
    
    if args.firewall_type in ["language_converter", "both"]:
        # Language converter firewall uses ONLY benign conversations (collect all from persona_conversations)
        all_benign_for_language_converter = []
        for persona_name, convos in persona_conversations.items():
            all_benign_for_language_converter.extend(convos['benign'])
        
        # Prepare output file path
        output_file = os.path.join(
            domain_output_dir,
            f"{args.domain}_language_converter_template.json"
        )
        
        language_converter_template = generate_language_converter_template(
            args,
            llm_instance,
            all_benign_for_language_converter,
            prev_content if args.firewall_type == "language_converter" else "",
            output_file=output_file
        )
        
        # Check if we actually got a template
        if not language_converter_template or len(language_converter_template.strip()) < 10:
            print(f"\n⚠ Warning: Language converter template generation failed or returned empty result")
            print("This might be due to:")
            print("  1. Max tokens too low (try --max_new_tokens 4000)")
            print("  2. LLM not following the format")
            print("Skipping validation...")
            is_valid = False
        else:
            # Validate and fix JSON using LLM
            is_valid, fixed_template, message = validate_and_fix_json_with_llm(language_converter_template, llm_instance)
            
            if is_valid:
                if message:
                    print(f"\n✓ JSON validated and fixed: {message}")
                else:
                    print(f"\n✓ JSON is valid")
                language_converter_template = fixed_template
                # Save the validated version
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(language_converter_template)
                print(f"  ✓ Final validated template saved to: {output_file}")
            else:
                print(f"\n⚠ Warning: JSON validation failed: {message}")
                print("Original template saved - manual correction may be needed")
        
        print(f"\n✓ Language Converter Firewall template generation complete: {output_file}")
        print(f"  Final version saved after {len(all_benign_for_language_converter)} iterations")
    
    print("\n" + "="*80)
    print("GENERATION COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
