"""
Create reproducible sample configurations for guideline generation.
Randomly selects a subset of personas and attacks for each domain.
"""

import random
import json
from pathlib import Path

# ==================== CONFIGURATION ====================
SEED = 42
NUM_PERSONAS = 2
PRIVACY_ATTACK_PERCENTAGE = 20  # 20% per persona (doubled from 10%)
SECURITY_ATTACK_PERCENTAGE = 40  # 40% per persona (doubled from 20%)
DOMAINS = ["travel_planning", "insurance", "real_estate"]
MODEL_FOLDER_NAME = "claude_sonnet_4_0"
MODE = "baseline"
# =======================================================


def get_all_personas(domain, model_folder_name, mode):
    """Find all available personas for a domain."""
    logs_dir = Path(__file__).parent.parent / "logs" / domain / model_folder_name / mode
    
    if not logs_dir.exists():
        return []
    
    personas = []
    for persona_dir in sorted(logs_dir.iterdir()):
        if persona_dir.is_dir() and persona_dir.name.startswith("persona"):
            persona_num = persona_dir.name.replace("persona", "")
            if persona_num.isdigit():
                personas.append(int(persona_num))
    
    return sorted(personas)


def get_attack_files(domain, model_folder_name, mode, persona, attack_type):
    """Get all attack files for a specific persona and attack type."""
    persona_dir = Path(__file__).parent.parent / "logs" / domain / model_folder_name / mode / f"persona{persona}"
    attack_dir = persona_dir / attack_type
    
    if not attack_dir.exists():
        return []
    
    attack_files = []
    # Recursively search for output_*.json files in subdirectories
    for file in sorted(attack_dir.rglob("output_*.json")):
        # Store relative path from logs/domain/model/mode
        rel_path = file.relative_to(persona_dir.parent)
        attack_files.append(str(rel_path).replace("\\", "/"))
    
    return attack_files


def create_sample_config(domain, model_folder_name, mode):
    """Create a sample configuration file for a domain."""
    random.seed(SEED)
    
    # Get all available personas
    all_personas = get_all_personas(domain, model_folder_name, mode)
    
    if not all_personas:
        print(f"⚠️  No personas found for {domain}")
        return None
    
    # Randomly select personas
    num_to_select = min(NUM_PERSONAS, len(all_personas))
    selected_personas = sorted(random.sample(all_personas, num_to_select))
    
    # Sample attacks PER PERSONA to maintain balance
    sampled_privacy = []
    sampled_security = []
    total_privacy = 0
    total_security = 0
    
    for persona in selected_personas:
        # Get attacks for this persona
        privacy_files = get_attack_files(domain, model_folder_name, mode, persona, "privacy")
        security_files = get_attack_files(domain, model_folder_name, mode, persona, "security")
        
        total_privacy += len(privacy_files)
        total_security += len(security_files)
        
        # Sample percentage from each persona
        num_privacy = max(1, int(len(privacy_files) * PRIVACY_ATTACK_PERCENTAGE / 100))
        num_security = max(1, int(len(security_files) * SECURITY_ATTACK_PERCENTAGE / 100))
        
        persona_privacy = random.sample(privacy_files, min(num_privacy, len(privacy_files)))
        persona_security = random.sample(security_files, min(num_security, len(security_files)))
        
        sampled_privacy.extend(persona_privacy)
        sampled_security.extend(persona_security)
    
    # Sort for consistent ordering
    sampled_privacy = sorted(sampled_privacy)
    sampled_security = sorted(sampled_security)
    
    # Create config content
    config_lines = []
    config_lines.append("PERSONAS")
    config_lines.append(",".join(map(str, selected_personas)))
    config_lines.append("")
    config_lines.append("PRIVACY_ATTACKS")
    config_lines.extend(sampled_privacy)
    config_lines.append("")
    config_lines.append("SECURITY_ATTACKS")
    config_lines.extend(sampled_security)
    
    return {
        "personas": selected_personas,
        "privacy_count": len(sampled_privacy),
        "security_count": len(sampled_security),
        "total_privacy": total_privacy,
        "total_security": total_security,
        "content": "\n".join(config_lines)
    }


def main():
    print("="*70)
    print("CREATING SAMPLE CONFIGURATIONS")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Seed: {SEED}")
    print(f"  Personas to select: {NUM_PERSONAS}")
    print(f"  Privacy attack percentage: {PRIVACY_ATTACK_PERCENTAGE}%")
    print(f"  Security attack percentage: {SECURITY_ATTACK_PERCENTAGE}%")
    print(f"  Model folder: {MODEL_FOLDER_NAME}")
    print(f"  Mode: {MODE}")
    print(f"  Domains: {', '.join(DOMAINS)}")
    print()
    
    output_dir = Path(__file__).parent
    configs_created = []
    
    for domain in DOMAINS:
        print(f"Processing {domain}...")
        
        result = create_sample_config(domain, MODEL_FOLDER_NAME, MODE)
        
        if result is None:
            continue
        
        # Save config file
        config_filename = f"sample_config_{domain}.txt"
        config_path = output_dir / config_filename
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        
        print(f"  ✅ Created {config_filename}")
        print(f"     Personas: {result['personas']}")
        print(f"     Privacy attacks: {result['privacy_count']}/{result['total_privacy']} ({PRIVACY_ATTACK_PERCENTAGE}%)")
        print(f"     Security attacks: {result['security_count']}/{result['total_security']} ({SECURITY_ATTACK_PERCENTAGE}%)")
        print()
        
        configs_created.append(config_filename)
    
    if configs_created:
        print("="*70)
        print(f"✅ Created {len(configs_created)} config file(s)")
        print("\nUsage example:")
        print(f"  python mitigation_guidelines/generate_guidelines.py \\")
        print(f"      --domain travel_planning \\")
        print(f"      --model_folder_name {MODEL_FOLDER_NAME} \\")
        print(f"      --mode {MODE} \\")
        print(f"      --config_file mitigation_guidelines/sample_config_travel_planning.txt \\")
        print(f"      --firewall_type both \\")
        print(f"      --llm_name gpt-4.1-2025-04-14 \\")
        print(f"      --provider openai")
    else:
        print("⚠️  No config files created. Check if logs directory exists.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
