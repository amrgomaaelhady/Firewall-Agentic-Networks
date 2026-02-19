"""
Language Converter Firewall for structuring external agent outputs into predefined JSON format.
Uses LLM to transform free-form responses and validates compliance with template.
"""

import json
from typing import Dict, Optional
from model import LLM
from .language_checker import check_compliance, process_final_dict


def has_nested_arrays(obj, depth=0, max_depth=100):
    """
    Recursively check if a data structure contains nested arrays (arrays within arrays).
    
    Args:
        obj: Dictionary, list, or primitive value to check
        depth: Current recursion depth (internal use)
        max_depth: Maximum allowed recursion depth to prevent stack overflow
        
    Returns:
        True if nested arrays are found, False otherwise
    """
    if depth > max_depth:
        print(f"[Language Converter Firewall Warning] Max recursion depth ({max_depth}) reached in has_nested_arrays")
        return False
        
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, list):
                return True
            if isinstance(item, dict):
                if has_nested_arrays(item, depth + 1, max_depth):
                    return True
    elif isinstance(obj, dict):
        for value in obj.values():
            if has_nested_arrays(value, depth + 1, max_depth):
                return True
    return False


def flatten_nested_arrays(obj):
    """
    Iteratively flatten nested arrays in a data structure.
    Converts [["a"], ["b"], ["c"]] to ["a", "b", "c"].
    Also handles nested objects within arrays.
    Uses iteration instead of recursion to avoid stack overflow.
    
    Args:
        obj: Dictionary, list, or primitive value to flatten
        
    Returns:
        Flattened version of the data structure
    """
    # Use a stack for iterative processing to avoid recursion limits
    def flatten_list(lst):
        """Flatten a list iteratively."""
        result = []
        stack = list(reversed(lst))  # Process in order
        
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                # Push list items back onto stack in reverse order
                stack.extend(reversed(item))
            elif isinstance(item, dict):
                # Flatten dict and add to result
                result.append(flatten_dict(item))
            else:
                # Primitive value
                result.append(item)
        return result
    
    def flatten_dict(d):
        """Flatten a dictionary iteratively."""
        result = {}
        stack = [(k, v) for k, v in d.items()]
        
        while stack:
            key, value = stack.pop()
            if isinstance(value, list):
                result[key] = flatten_list(value)
            elif isinstance(value, dict):
                result[key] = flatten_dict(value)
            else:
                result[key] = value
        return result
    
    # Start processing based on type
    if isinstance(obj, list):
        return flatten_list(obj)
    elif isinstance(obj, dict):
        return flatten_dict(obj)
    else:
        return obj


# Domain-agnostic prompts for language converter firewall
LANGUAGE_CONVERTER_INTRO = """You are tasked with translating the external agent's response into a structured JSON format according to the provided Language template.

**Instructions:**
1. Extract relevant information from the external agent's response.
2. Structure the extracted information according to the Language template provided.
3. Follow these type rules strictly:
   - **Type:str**: Must be a string value (e.g., "Paris", "Hotel Name")
   - **Type:float**: Must be a decimal number (e.g., 500.00, 1200.50)
   - **Type:bool**: Must be true or false
   - **Type:datetime**: Must be in ISO format (YYYY-MM-DD)
   - **Patterns**: Follow exact patterns like "Type:float to Type:float" means "100.00 to 500.00"
   - **Lists**: For multiple choice fields, use ONLY a flat array of primitive values (strings, numbers, bools)
   - **CRITICAL**: NEVER create nested arrays (arrays within arrays) like [["item1"], ["item2"]]
   - **CRITICAL**: Each list item must be a primitive value (string/number/bool), NOT another array or object
   - **Example Valid**: ["option1", "option2", "option3"]
   - **Example INVALID**: [["option1"], ["option2"]] or [{"key": "value"}]
4. Only include information that is explicitly provided in the external agent's response.
5. Use the previous_names mapping to ensure consistency when referring to the same entities across turns.
6. Return ONLY valid JSON without any additional text or explanation.

**Output Format:**
```json
{
  "key": "value according to template type"
}
```
"""

LANGUAGE_CONVERTER_TURN_TEMPLATE = """**Language Template:**
```json
{Language}
```

**Previous Names Mapping:**
{previous_names}

**External Agent Response:**
{current_input}

**Your Task:**
Translate the external agent's response into the structured JSON format following the Language template. Return only the JSON, no explanations.
"""


class LanguageConverterFirewall:
    """
    Language Converter Firewall that enforces structured JSON output from external agent.
    Uses LLM to transform responses and validates against predefined template.
    """

    def __init__(
        self,
        template_json: Dict,
        llm_instance: LLM,
        max_retries: int = 10
    ):
        """
        Initialize language converter firewall.
        
        Args:
            template_json: Dictionary containing the language converter template structure
            llm_instance: LLM instance to use for response transformation
            max_retries: Maximum number of retry attempts for invalid JSON
        """
        self.template_json = template_json
        self.template_str = json.dumps(template_json, indent=2)
        self.llm_instance = llm_instance
        self.max_retries = max_retries
        self.names_lookup: Dict = {}

    def get_previous_names(self) -> str:
        """
        Format the names_lookup dictionary for prompt inclusion.
        Shows mappings like 'destination: Paris -> destination_option1'.
        """
        if not self.names_lookup:
            return "None yet"
        
        lines = []
        for key_type, name_mapping in self.names_lookup.items():
            for name, option_id in name_mapping.items():
                lines.append(f"  {key_type}: {name} -> {option_id}")
        
        return "\n".join(lines) if lines else "None yet"

    def apply_firewall(self, response_text: str) -> Optional[Dict]:
        """
        Apply language converter firewall to external agent response.
        Transforms free-form text into structured JSON with validation and retries.
        
        Args:
            response_text: Free-form response from external agent
            
        Returns:
            Validated and structured dictionary with ID mappings, or None if all retries failed
        """
        # Build the firewall prompt
        turn_prompt = LANGUAGE_CONVERTER_TURN_TEMPLATE.format(
            Language=self.template_str,
            previous_names=self.get_previous_names(),
            current_input=response_text
        )
        
        # Debug: Verify template is being passed correctly
        print("\n[Language Converter Firewall Debug] Template being sent to LLM (first 500 chars):")
        print(self.template_str[:500])
        print("...")
        
        messages = [
            {"role": "system", "content": LANGUAGE_CONVERTER_INTRO},
            {"role": "user", "content": turn_prompt}
        ]
        
        # Retry loop for JSON validation
        for attempt in range(self.max_retries):
            try:
                # Get LLM transformation
                transformed_response = self.llm_instance.call_model(messages)
                
                if not transformed_response:
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: LLM call failed")
                    continue
                
                # Validate compliance with template
                filtered_dict = check_compliance(self.template_str, transformed_response)
                
                if not filtered_dict:
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: No compliant data found")
                    continue
                
                # Check if nested arrays exist (gpt-5 often generates these despite instructions)
                if has_nested_arrays(filtered_dict):
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: Nested arrays detected, flattening...")
                    try:
                        filtered_dict = flatten_nested_arrays(filtered_dict)
                        print(f"[Language Converter Firewall] Attempt {attempt + 1}: Arrays flattened successfully")
                    except Exception as flatten_error:
                        print(f"[Language Converter Firewall] Attempt {attempt + 1}: Flattening failed - {str(flatten_error)}")
                        continue
                else:
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: JSON validated (no nested arrays)")
                
                # Process names to IDs
                try:
                    final_dict, self.names_lookup = process_final_dict(
                        filtered_dict, self.names_lookup
                    )
                except Exception as process_error:
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: Name processing failed - {str(process_error)}")
                    continue
                
                # Verify the result is JSON serializable (catches circular references)
                try:
                    json.dumps(final_dict)
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: Successfully validated final JSON")
                    return final_dict
                except (TypeError, ValueError) as json_error:
                    print(f"[Language Converter Firewall] Attempt {attempt + 1}: JSON serialization failed - {str(json_error)}")
                    continue
                
            except Exception as e:
                print(f"[Language Converter Firewall] Attempt {attempt + 1} failed: {str(e)}")
                continue
        
        print(f"[Language Converter Firewall] All {self.max_retries} attempts failed")
        return None

    def update_ids_to_names(self, response_text: str) -> str:
        """
        Replace option IDs with actual names in text for assistant consumption.
        Converts 'destination_option1' back to 'Paris'.
        
        Args:
            response_text: Text containing option IDs
            
        Returns:
            Text with IDs replaced by actual names
        """
        updated_text = response_text
        
        for key_type, name_mapping in self.names_lookup.items():
            for name, option_id in name_mapping.items():
                updated_text = updated_text.replace(option_id, name)
        
        return updated_text

    def reset(self):
        """Reset the names lookup for a new conversation."""
        self.names_lookup = {}
