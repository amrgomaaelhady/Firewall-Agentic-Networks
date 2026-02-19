"""
Language Converter Coverage Judge - Evaluates how well the language converter template covers external agent communications.
"""

import json
from typing import Dict, List
from language_converter_coverage_prompts import format_language_converter_coverage_prompt
from language_converter_coverage_utils import (
    load_language_converter_template,
    extract_external_agent_messages,
    format_external_messages_for_judge,
    parse_judge_response
)

# Import from main codebase
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from model import LLM


class LanguageConverterCoverageJudge:
    """
    Judge that evaluates language converter firewall template coverage.
    """
    
    def __init__(self, llm_name: str, provider: str = None, use_azure_credentials: bool = False, debug: bool = False, **llm_kwargs):
        """
        Initialize the language converter coverage judge.
        
        Args:
            llm_name: Name of LLM to use for judging
            provider: LLM provider (azure, openai, anthropic, etc.)
            use_azure_credentials: Use Azure DefaultAzureCredential instead of API key
            debug: Enable debug output
            **llm_kwargs: Additional arguments for LLM initialization
        """
        self.llm_name = llm_name
        self.provider = provider
        self.debug = debug
        
        # Initialize LLM instance
        config = {
            "llm_name": llm_name,
            "provider": provider,
            "use_azure_credentials": use_azure_credentials,
            **llm_kwargs
        }
        self.llm = LLM(llm_name=llm_name, config=config)
        
    def evaluate_conversation(
        self, 
        conversation: List[Dict], 
        language_converter_template: Dict,
        max_retries: int = 3
    ) -> Dict:
        """
        Evaluate a single conversation for language converter coverage.
        
        Args:
            conversation: List of conversation turns
            language_converter_template: Language converter firewall template (dict)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with evaluation results
        """
        # Extract external agent messages
        external_messages = extract_external_agent_messages(conversation)
        
        if not external_messages:
            return {
                "indescribable_count": 0,
                "indescribable_items": [],
                "describable_count": 0,
                "describable_items": [],
                "total_items": 0,
                "coverage_percentage": 100.0,
                "note": "No external agent messages in conversation"
            }
        
        # Format messages for judge
        formatted_messages = format_external_messages_for_judge(external_messages)
        
        # Format language converter template as pretty JSON string
        template_str = json.dumps(language_converter_template, indent=2)
        
        # Create judge prompt
        messages = format_language_converter_coverage_prompt(template_str, formatted_messages)
        
        # DEBUG OUTPUT - Write to file if enabled
        if self.debug:
            debug_file = "language_converter_coverage_analysis/debug_judge_input.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("DEBUG: WHAT'S BEING SENT TO JUDGE LLM\n")
                f.write("=" * 80 + "\n")
                f.write(f"\n1. LANGUAGE CONVERTER TEMPLATE (length: {len(template_str)} chars):\n")
                f.write("-" * 80 + "\n")
                f.write(template_str + "\n")
                f.write(f"\n2. FORMATTED EXTERNAL MESSAGES (length: {len(formatted_messages)} chars):\n")
                f.write("-" * 80 + "\n")
                f.write(formatted_messages + "\n")
                f.write("\n3. FULL MESSAGES ARRAY SENT TO LLM:\n")
                f.write("-" * 80 + "\n")
                for i, msg in enumerate(messages):
                    f.write(f"\nMessage {i+1} (role={msg['role']}):\n")
                    f.write(f"Content length: {len(msg['content'])} chars\n")
                    f.write("Content:\n")
                    f.write(msg['content'] + "\n")
                f.write("\n" + "=" * 80 + "\n")
                f.write("END DEBUG OUTPUT\n")
                f.write("=" * 80 + "\n")
            print(f"   🐛 Debug info written to {debug_file}")
        
        # Call LLM judge with retries
        for attempt in range(max_retries):
            try:
                judge_output = self.llm.call_model(messages)
                
                # Parse response
                result = parse_judge_response(judge_output)
                
                if "error" not in result:
                    return result
                else:
                    print(f"Attempt {attempt + 1}/{max_retries}: Parsing error - {result['error']}")
                    if attempt == max_retries - 1:
                        return result
                    
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries}: LLM call failed - {e}")
                if attempt == max_retries - 1:
                    return {
                        "error": str(e),
                        "indescribable_count": 0,
                        "indescribable_items": [],
                        "describable_count": 0,
                        "describable_items": [],
                        "total_items": 0,
                        "coverage_percentage": 0.0
                    }
        
        return {
            "error": "Max retries exceeded",
            "indescribable_count": 0,
            "indescribable_items": [],
            "describable_count": 0,
            "describable_items": [],
            "total_items": 0,
            "coverage_percentage": 0.0
        }


def evaluate_single_file(
    conversation_file: str,
    use_case: str,
    judge: LanguageConverterCoverageJudge,
    templates_dir: str = "mitigation_guidelines/generated"
) -> Dict:
    """
    Evaluate a single conversation file.
    
    Args:
        conversation_file: Path to conversation JSON file
        use_case: Use case name (for loading correct template)
        judge: LanguageConverterCoverageJudge instance
        templates_dir: Directory containing language converter templates
        
    Returns:
        Evaluation results dictionary
    """
    # Load conversation
    with open(conversation_file, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    # Load language converter template
    language_converter_template = load_language_converter_template(use_case, templates_dir)
    
    # Evaluate
    result = judge.evaluate_conversation(conversation, language_converter_template)
    
    return result
