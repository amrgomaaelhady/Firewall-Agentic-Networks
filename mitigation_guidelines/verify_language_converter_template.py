"""Verify that all language converter firewall template JSONs are valid and loadable."""

import json
from pathlib import Path


def verify_json_file(json_path):
    """Verify that a JSON file is valid and loadable."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data
    except json.JSONDecodeError as e:
        return False, f"JSON parsing error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    script_dir = Path(__file__).parent
    generated_dir = script_dir / "generated"
    
    if not generated_dir.exists():
        print("No generated/ directory found")
        return 1
    
    # Find all JSON files in generated subfolders
    json_files = list(generated_dir.glob("*/*.json"))
    
    if not json_files:
        print("No JSON files found in generated/ subfolders")
        return 1
    
    print(f"Found {len(json_files)} JSON file(s) to verify:\n")
    
    failed = []
    for json_path in sorted(json_files):
        relative_path = json_path.relative_to(generated_dir)
        is_valid, result = verify_json_file(json_path)
        
        if not is_valid:
            print(f"❌ {relative_path}: {result}")
            failed.append(relative_path)
        else:
            print(f"✅ {relative_path}: {len(result)} fields")
    
    print(f"\n{len(json_files) - len(failed)}/{len(json_files)} files valid")
    
    return 1 if failed else 0


if __name__ == "__main__":
    exit(main())
