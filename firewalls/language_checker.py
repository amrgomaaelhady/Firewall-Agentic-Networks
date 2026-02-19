"""
JSON validation and compliance checking for language converter firewall.
Validates external agent responses against the predefined language converter template.
"""

import json
import datetime
import builtins
import re


def process_final_dict(filtered_dict, names_lookup={}):
    """
    Replace names with IDs and update the lookup table.
    For fields ending in '_name', creates option IDs like 'destination_option1'.
    Uses iterative approach to avoid recursion limits.
    """
    def replace_names_with_ids(filtered_dict):
        # Use a stack for iterative traversal
        stack = [(filtered_dict, None, None)]  # (dict_obj, parent_dict, parent_key)
        
        while stack:
            current, parent, parent_key = stack.pop()
            
            if isinstance(current, dict):
                for key, value in current.items():
                    if isinstance(value, dict):
                        stack.append((value, current, key))
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                stack.append((item, current, key))
                    else:
                        if "_name" in key:
                            key_type = key.split("_name")[0]
                            if not key_type in names_lookup:
                                names_lookup[key_type] = {value: key_type + "_option1"}
                                current[key] = key_type + "_option1"
                            elif not value in names_lookup[key_type]:
                                num_options = len(names_lookup[key_type])
                                names_lookup[key_type][value] = key_type + f"_option{num_options+1}"
                                current[key] = key_type + f"_option{num_options+1}"
                            else:
                                current[key] = names_lookup[key_type][value]

    replace_names_with_ids(filtered_dict)
    return filtered_dict, names_lookup


def is_valid_type(type_str):
    """Check if a type string represents a valid Python type."""
    if "datetime" in type_str:
        return True
    return hasattr(builtins, type_str) and isinstance(getattr(builtins, type_str), type)


def handle_datetime(string_to_check):
    """Validate datetime string format."""
    try:
        datetime.date.fromisoformat(string_to_check)
        return True
    except:
        return False


def remove_indices(text):
    """Remove array indices from flattened keys (e.g., 'dates[0]' -> 'dates')."""
    return re.sub(r"\[\d+\]", "", text)


def find_index(text):
    """Extract array index from flattened key."""
    match = re.search(r"\[(\d+)\]", text)
    if match:
        return int(match.group(1))
    return None


def check_compliance_to_type(response_value, supported_type):
    """Verify that a response value matches the expected type."""
    if supported_type == "int":
        supported_types = ["int", "float"]
    elif supported_type == "float":
        supported_types = ["int", "float"]
    else:
        supported_types = [supported_type]

    comply = False
    if response_value == None:
        return True
    
    for supported_type in supported_types:
        if "datetime" in supported_type:
            return handle_datetime(response_value)
        elif eval(supported_type) == str:
            return True
        elif isinstance(response_value, str):
            comply = comply or isinstance(eval(response_value), eval(supported_type))
        else:
            comply = comply or isinstance(response_value, eval(supported_type))
    return comply


def get_key_values_language(language_dict):
    """Flatten the language template to 'parent.parent: value' format using iteration."""
    items = {}

    def flatten_dict(d, parent_key="", sep="."):
        # Use a stack for iterative traversal
        stack = [(d, parent_key)]
        
        while stack:
            current_dict, current_parent = stack.pop()
            
            for k, v in current_dict.items():
                new_key = f"{current_parent}{sep}{k}" if current_parent else k
                if isinstance(v, dict):
                    stack.append((v, new_key))
                else:
                    items[new_key] = v

    flatten_dict(language_dict)
    return items


def get_key_values_response(response_dict):
    """
    Flatten the response to 'parent.parent: value' format using iteration.
    Lists become 'parent[index].parent: value'.
    """
    items = []

    def flatten_dict(d, parent_key="", sep="."):
        # Use a stack for iterative traversal: (dict, parent_key)
        stack = [(d, parent_key)]
        
        while stack:
            current_dict, current_parent = stack.pop()
            
            for k, v in current_dict.items():
                new_key = f"{current_parent}{sep}{k}" if current_parent else k
                if isinstance(v, dict):
                    stack.append((v, new_key))
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            stack.append((item, f"{new_key}[{i}]"))
                        else:
                            if v:
                                items.append((new_key, v))
                                break  # Only add the list once
                else:
                    if v:
                        items.append((new_key, v))

    flatten_dict(response_dict)
    return items


def compare_keys(supported_language, response):
    """Filter response to only include keys that exist in the language template."""
    correct_key_value_pairs = []
    for item in response:
        if remove_indices(item[0]) in supported_language:
            correct_key_value_pairs.append(item)
    return correct_key_value_pairs


def compare_values(key_value_pair_response, predefined_language_flattened):
    """Verify that response values match the expected types/choices in the template."""
    try:
        key_response, value_response = key_value_pair_response
        key_response = remove_indices(key_response)
        language_supported_value = predefined_language_flattened[key_response]

        new_list_responses = []

        # Check multiple choice values
        if isinstance(language_supported_value, list):
            if isinstance(value_response, list):
                for response in value_response:
                    if response in language_supported_value:
                        new_list_responses.append(response)
            else:
                if not value_response in language_supported_value:
                    return False, new_list_responses

        # Check typed values (Type:str, Type:int, etc.)
        else:
            language_supported_value = (
                language_supported_value.replace("{", "")
                .replace("}", "")
                .replace("Type:", "")
            )
            # Handle pattern values like "Type:float to Type:float"
            supported_parts = [i.strip() for i in language_supported_value.split(" ")]
            if len(supported_parts) > 1:
                value_response = [i.strip() for i in value_response.split(" ")]
                if not len(value_response) == len(supported_parts):
                    return False, new_list_responses
            else:
                value_response = [value_response]

            for i in range(len(supported_parts)):
                if is_valid_type(supported_parts[i].strip()):
                    if not check_compliance_to_type(value_response[i], supported_parts[i].strip()):
                        return False, new_list_responses
                elif not value_response[i].strip() == supported_parts[i].strip():
                    return False, new_list_responses
        return True, new_list_responses
    except:
        return False, []


def combine_keys_with_indices(flattened_data):
    """Recombine array elements that were flattened with indices."""
    indexed_dict = {}
    other_data = []

    for key, value in flattened_data:
        if "[" in key:
            base_key = key.split("[")[0]
            index = int(key.split("[")[1].split("]")[0])
            sub_key = key.split(".", 1)[1]
            if base_key not in indexed_dict:
                indexed_dict[base_key] = {}
            if index not in indexed_dict[base_key]:
                indexed_dict[base_key][index] = {}
            indexed_dict[base_key][index][sub_key] = value
        else:
            other_data.append((key, value))

    combined_data = [
        (base_key, [indexed_dict[base_key][i] for i in sorted(indexed_dict[base_key])])
        for base_key in indexed_dict
    ]
    return combined_data + other_data


def unflatten_json(flattened_data):
    """Convert flattened key-value pairs back to nested dictionary."""
    unflattened_data = {}

    for key, value in flattened_data:
        keys = key.split(".")
        d = unflattened_data
        for k in keys[:-1]:
            if "[" in k:
                k = k.split("[")[0]
                if k not in d:
                    d[k] = []
                index = int(keys[keys.index(k) + 1].split("[")[1].split("]")[0])
                while len(d[k]) <= index:
                    d[k].append({})
                d = d[k][index]
            else:
                if k not in d:
                    d[k] = {}
                d = d[k]
        if keys[-1] not in d:
            d[keys[-1]] = value
        else:
            if isinstance(d[keys[-1]], list):
                d[keys[-1]].append(value)
            else:
                d[keys[-1]] = [d[keys[-1]], value]

    return unflattened_data


def check_compliance(predefined_language: str, response: str):
    """
    Validate external agent response against the language converter template.
    Returns only compliant key-value pairs, filtering out non-compliant data.
    
    Args:
        predefined_language: JSON string of the language converter template
        response: JSON string of the external agent's response
        
    Returns:
        Dictionary with only validated and compliant data
    """
    predefined_language = json.loads(predefined_language)
    response = json.loads(response.split("```json")[-1].split("```")[0].strip())

    # Flatten both structures for comparison
    predefined_language_flattened = get_key_values_language(predefined_language)
    response_flattened = get_key_values_response(response)

    # Filter to only keys that exist in template
    correct_keys_items = compare_keys(predefined_language_flattened, response_flattened)

    # Validate values match expected types/choices
    correct_value_items = []
    for key_value_response in correct_keys_items:
        complies, new_list = compare_values(key_value_response, predefined_language_flattened)
        if new_list:
            correct_value_items.append((key_value_response[0], new_list))
        elif complies:
            correct_value_items.append(key_value_response)

    # Reconstruct nested structure
    combined_data = combine_keys_with_indices(correct_value_items)
    unflattened_data = unflatten_json(combined_data)

    return unflattened_data
