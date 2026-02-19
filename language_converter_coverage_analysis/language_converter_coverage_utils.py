"""
Utility functions for language converter coverage analysis.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def extract_output_to_ai_assistant(text: str) -> str:
    """
    Extract content between <output_to_ai_assistant> tags.
    This is what the language converter firewall actually processes.
    
    Args:
        text: Full external agent response (may include scratchpad, etc.)
        
    Returns:
        Content between tags, or empty string if tags not found
    """
    delimiter = "output_to_ai_assistant"
    if f"<{delimiter}>" not in text or f"</{delimiter}>" not in text:
        return ""
    
    # Extract content between opening and closing tags
    try:
        content = text.split(f"<{delimiter}>")[-1].split(f"</{delimiter}>")[0]
        return content.strip()
    except (IndexError, AttributeError):
        return ""


def load_language_converter_template(use_case: str, templates_dir: str = "mitigation_guidelines/generated") -> Dict:
    """
    Load the language converter firewall template for a specific use case.
    
    Args:
        use_case: Name of use case (travel_planning, real_estate, insurance)
        templates_dir: Base directory containing generated templates
        
    Returns:
        Dictionary containing the language converter template
    """
    template_path = Path(templates_dir) / use_case / f"{use_case}_language_converter_template.json"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Language converter template not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_external_agent_messages(conversation: List[Dict]) -> List[Dict]:
    """
    Extract all messages from external agent to assistant.
    
    Args:
        conversation: List of conversation turns
        
    Returns:
        List of external agent messages
    """
    external_messages = []
    
    for turn in conversation:
        if turn.get("from") == "external_agent" and turn.get("to") == "assistant":
            external_messages.append({
                "short_answer": turn.get("short_answer", ""),
                "long_answer": turn.get("long_answer", "")
            })
    
    return external_messages


def format_external_messages_for_judge(messages: List[Dict]) -> str:
    """
    Format external agent messages for the judge prompt.
    Uses ONLY the content between <output_to_ai_assistant> tags from long_answer.
    This is what the language converter firewall LLM actually processes.
    
    Args:
        messages: List of external agent message dicts
        
    Returns:
        Formatted string representation
    """
    if not messages:
        return "No external agent messages in this conversation."
    
    formatted = []
    msg_count = 0
    for msg in messages:
        # Extract ONLY content between <output_to_ai_assistant> tags
        full_response = msg.get("long_answer", "")
        
        if full_response and full_response.strip():
            # Parse out the actual content sent to language converter firewall
            language_converter_input = extract_output_to_ai_assistant(full_response)
            
            if language_converter_input:
                msg_count += 1
                formatted.append(f"### Message {msg_count}")
                formatted.append("")
                formatted.append(language_converter_input)
                formatted.append("")
                formatted.append("---")
                formatted.append("")
    
    if not formatted:
        return "No external agent messages with output_to_ai_assistant content found."
    
    return "\n".join(formatted)


def parse_judge_response(judge_output: str) -> Dict:
    """
    Parse the judge's response to extract Q1 and Q2 answers.
    
    Args:
        judge_output: Raw judge output string
        
    Returns:
        Dictionary with parsed results
    """
    try:
        # Extract JSON from <final_evaluation> tags
        start_tag = "<final_evaluation>"
        end_tag = "</final_evaluation>"
        
        if start_tag in judge_output and end_tag in judge_output:
            json_str = judge_output.split(start_tag)[-1].split(end_tag)[0].strip()
            evaluation = json.loads(json_str)
            
            # Parse Q1 and Q2 answers (format: "NUMBER, [list]")
            q1_answer = evaluation["Q1"]["A"]
            q2_answer = evaluation["Q2"]["A"]
            
            def parse_answer(answer_str: str) -> Tuple[int, List[str]]:
                """Parse 'NUMBER, [item1, item2, ...]' format."""
                if ", [" in answer_str:
                    num_str, items_str = answer_str.split(", [", 1)
                    count = int(num_str.strip())
                    
                    # Remove trailing ] and parse list
                    items_str = items_str.rstrip("]").strip()
                    if items_str:
                        # Handle both single-quoted and double-quoted strings
                        items = [item.strip().strip("'\"") for item in items_str.split("', '")]
                        # Clean up if there are still quotes
                        items = [item.replace("', '", "").replace('", "', '') for item in items]
                    else:
                        items = []
                    
                    return count, items
                else:
                    # Fallback: just a number
                    return int(answer_str.strip()), []
            
            indescribable_count, indescribable_items = parse_answer(q1_answer)
            describable_count, describable_items = parse_answer(q2_answer)
            
            return {
                "judge_text": judge_output,
                "final_assessment": evaluation,
                "indescribable_count": indescribable_count,
                "indescribable_items": indescribable_items,
                "describable_count": describable_count,
                "describable_items": describable_items,
                "total_items": indescribable_count + describable_count,
                "coverage_percentage": (describable_count / (indescribable_count + describable_count) * 100) 
                                      if (indescribable_count + describable_count) > 0 else 100.0
            }
        else:
            raise ValueError("No <final_evaluation> tags found in judge output")
            
    except Exception as e:
        print(f"Error parsing judge response: {e}")
        print(f"Judge output: {judge_output[:500]}...")
        return {
            "judge_text": judge_output,
            "error": str(e),
            "indescribable_count": 0,
            "indescribable_items": [],
            "describable_count": 0,
            "describable_items": [],
            "total_items": 0,
            "coverage_percentage": 0.0
        }


def find_conversation_files(logs_dir: str, mode: str, use_cases: Optional[List[str]] = None) -> List[Path]:
    """
    Find all conversation files (output_*.json) for the specified mode.
    
    Args:
        logs_dir: Base logs directory
        mode: Mode to filter by (e.g., firewalls_data_abstraction_language_converter)
        use_cases: List of use cases to include (None = all)
        
    Returns:
        List of Path objects to conversation files
    """
    logs_path = Path(logs_dir)
    conversation_files = []
    
    # Pattern: logs/{use_case}/{model}/{mode}/persona{N}/{attack_type}/{attack_name}/output_*.json
    for use_case_dir in logs_path.iterdir():
        if not use_case_dir.is_dir():
            continue
        
        # Filter by use case if specified
        if use_cases and use_case_dir.name not in use_cases:
            continue
        
        # Traverse model directories
        for model_dir in use_case_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            # Check if mode directory exists
            mode_dir = model_dir / mode
            if not mode_dir.exists():
                continue
            
            # Find all output_*.json files
            for output_file in mode_dir.rglob("output_*.json"):
                conversation_files.append(output_file)
    
    return sorted(conversation_files)


def parse_conversation_path(file_path: Path, logs_dir: str) -> Dict[str, str]:
    """
    Extract metadata from conversation file path.
    
    Args:
        file_path: Path to conversation file
        logs_dir: Base logs directory
        
    Returns:
        Dictionary with use_case, model, mode, persona, attack_type, attack_name, repetition
    """
    # Structure: logs/{use_case}/{model}/{mode}/persona{N}/{attack_type}/{attack_name}/output_{timestamp}_rep{X}.json
    parts = file_path.relative_to(logs_dir).parts
    
    if len(parts) < 7:
        raise ValueError(f"Unexpected path structure: {file_path}")
    
    use_case = parts[0]
    model = parts[1]
    mode = parts[2]
    persona = parts[3].replace("persona", "")
    attack_type = parts[4]
    attack_name = parts[5]
    
    # Extract repetition from filename
    filename = file_path.stem  # output_20260117_141920_rep1
    if "_rep" in filename:
        repetition = filename.split("_rep")[-1]
    else:
        repetition = "1"
    
    return {
        "use_case": use_case,
        "model": model,
        "mode": mode,
        "persona": persona,
        "attack_type": attack_type,
        "attack_name": attack_name,
        "repetition": repetition,
        "file_path": str(file_path)
    }


def save_coverage_result(result: Dict, output_dir: str, metadata: Dict):
    """
    Save language converter coverage result to JSON file.
    
    Args:
        result: Coverage evaluation result
        output_dir: Output directory for results
        metadata: Metadata from parse_conversation_path
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Filename: {use_case}_{model}_{mode}_{persona}_{attack_name}_rep{X}.json
    filename = (
        f"{metadata['use_case']}_{metadata['model']}_{metadata['mode']}_"
        f"persona{metadata['persona']}_{metadata['attack_name']}_rep{metadata['repetition']}.json"
    )
    
    # Combine metadata and result
    output_data = {
        **metadata,
        **result
    }
    
    output_file = output_path / filename
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    return output_file
