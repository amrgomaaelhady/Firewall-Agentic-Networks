# Mitigation Guidelines Generation

This directory contains tools for generating domain-specific firewall mitigation guidelines from ConVerse conversation logs.

## Overview

The firewall generation system creates two types of mitigation mechanisms:

1. **Data Abstraction Firewall**: Filters sensitive user data before it reaches the assistant agent
2. **Language Converter Firewall**: Controls the language format of external agent responses using structured templates

## Directory Structure

```
mitigation_guidelines/
├── __init__.py                 # Package initialization
├── README.md                   # This file
├── generate_guidelines.py      # Main generation script
├── utils.py                    # Utility functions for conversation processing
├── prompts/                    # Prompt templates
│   ├── __init__.py
│   ├── data_abstraction_prompts.py
│   └── language_converter_prompts.py
└── generated/                  # Output directory for generated guidelines
    ├── travel_planning_data_abstraction_guidelines.txt
    ├── travel_planning_language_converter_template.json
    ├── real_estate_data_abstraction_guidelines.txt
    └── ...
```

## Usage

### Quick Start (Working Example)

```bash
# Generate both firewalls for travel_planning using 2 personas
# This example has been tested and works correctly
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --model_folder_name claude_sonnet_4_0 \
    --mode baseline \
    --personas "1,2" \
    --num_privacy_samples 1 \
    --num_security_samples 1 \
    --firewall_type both \
    --llm_name gpt-4.1-2025-04-14 \
    --provider openai
```

**What this does:**
- Loads 6 benign conversations (3 from each persona, all repetitions)
- Samples 1 privacy + 1 security attack per persona (4 attacks total)
- Generates data abstraction guidelines iteratively (4 iterations)
- Generates language converter firewall JSON template (6 iterations)
- Saves to `mitigation_guidelines/generated/travel_planning/`

### Basic Usage

```bash
# NEW STYLE: Generate for multiple personas at once
# Process personas 1, 2, 3 from travel_planning baseline
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas "1,2,3" \
    --num_privacy_samples 10 \
    --num_security_samples 5 \
    --llm_name gpt-4.1-2025-04-14

# Process ALL 12 personas at once (budget-friendly option)
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas all \
    --num_privacy_samples 5 \
    --num_security_samples 3 \
    --llm_name gpt-4.1-2025-04-14

# Process a range of personas (1 through 5)
python mitigation_guidelines/generate_guidelines.py \
    --domain real_estate \
    --firewall_type data_abstraction \
    --model_folder_name claude \
    --mode baseline \
    --personas "1-5" \
    --llm_name claude-3-opus-20240229 \
    --provider anthropic

# LEGACY STYLE: Single persona with direct path (still supported)
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --persona_dir logs/travel_planning/gpt_5_chat/baseline/persona1 \
    --num_privacy_samples 10 \
    --num_security_samples 5 \
    --llm_name gpt-4

# Use with taskConfined mode instead of baseline
python mitigation_guidelines/generate_guidelines.py \
    --domain insurance \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode taskConfined \
    --personas "1,2,3" \
    --llm_name gpt-4

# Refine existing guidelines with additional personas
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type data_abstraction \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas "4,5,6" \
    --previous_guidelines mitigation_guidelines/generated/travel_planning_data_abstraction_guidelines.txt \
    --num_privacy_samples 5 \
    --num_security_samples 3
```

### Command Line Arguments

**Required:**
- `--domain`: Domain for guideline generation (`travel_planning`, `real_estate`, `insurance`)
- `--firewall_type`: Type of firewall to generate (`data_abstraction`, `language_converter`, `both`)

**Path Construction (New Style - Recommended):**
- `--model_folder_name`: Model folder name in logs (e.g., `gpt_5_chat`, `claude`, `gemini`)
- `--mode`: Simulation mode (`baseline`, `taskConfined`)
- `--personas`: Persona specification:
  - Single: `1`
  - List: `1,2,3`
  - Range: `1-12`
  - All: `all` (processes all 12 personas)
- `--logs_folder`: Base logs directory (default: `logs`)

**Path Construction (Legacy Style):**
- `--persona_dir`: Direct path to persona directory (e.g., `logs/travel_planning/gpt_5_chat/baseline/persona1`)

**Attack Sampling (for data_abstraction firewall):**
- `--num_privacy_samples`: Number of privacy attacks to sample **per persona** (default: None = ALL)
- `--num_security_samples`: Number of security attacks to sample **per persona** (default: None = ALL)
- `--sampling_seed`: Random seed for reproducibility (default: 42)

**LLM Configuration (matching main.py):**
- `--llm_name`: LLM model name for generating guidelines (default: gpt-4)
- `--provider`: LLM provider (`azure`, `openai`, `anthropic`, `anthropic_vertex`, `google`, `huggingface`)
- `--azure_endpoint`: Azure endpoint URL (overrides environment variable)
- `--use_azure_credentials`: Use DefaultAzureCredential for Azure (default: True)

**Output:**
- `--output_dir`: Output directory for generated guidelines (default: `mitigation_guidelines/generated`)
- `--previous_guidelines`: Path to previous guidelines file for iterative refinement

**Other:**
- `--verbose`: Print detailed progress information

## How It Works

### ConVerse Log Structure

ConVerse logs are organized as:
```
logs/{domain}/{model}/{mode}/persona{N}/
├── benign_hard/
│   └── benign_simulation/
│       ├── output_20250914_180851_rep1.json
│       ├── output_20250914_180851_rep2.json
│       └── ...
├── benign_easy/
│   └── ...
├── privacy/
│   ├── related_and_useful_exact_address/
│   │   ├── output_20250915_001839_rep1.json
│   │   └── ...
│   ├── unrelated_to_travel_passport_number/
│   │   └── ...
│   └── ... (56+ attack folders)
└── security/
    ├── attack_type_1/
    │   └── ...
    └── ... (many attack folders)
```

**Key differences from original Firewalled project:**
- ConVerse has **many** attack files (50+ per persona) but **few** benign files (~3-6)
- Each attack type has its own folder with multiple repetition files
- Benign conversations are in nested folders (benign_hard/benign_simulation)

### Sampling Strategy

**Benign Conversations:** Always uses ALL available benign conversations (typically 3-6 files)

**Attack Conversations:** 
- Use `--num_privacy_samples` and `--num_security_samples` to control sampling
- If not specified (None), uses ALL attacks (can be 50+ per type)
- Sampling is reproducible via `--sampling_seed`

**Recommendation:** Start with small samples (5-10 per type) for faster iteration, then increase for final guidelines.

### Data Abstraction Firewall Generation

1. Loads ALL benign conversations from specified personas
2. Samples N privacy attacks + M security attacks per persona (or uses all)
3. Combines all conversations across personas into one pool
4. For each (benign, attack) pair:
   - Prompts LLM to identify sensitive data in attack that should be blocked
   - Prompts LLM to ensure benign communication still works
   - Iteratively refines guidelines
5. Outputs guidelines as text file

**Example with multiple personas:**
```
Persona 1: 3 benign + 10 sampled attacks
Persona 2: 3 benign + 10 sampled attacks  
Persona 3: 3 benign + 10 sampled attacks
---
Total: 9 benign + 30 attacks → 9 iterations (min of both)

Iteration 1: benign_p1_1 + attack_p1_1 → initial guidelines
Iteration 2: benign_p1_2 + attack_p1_2 → refined guidelines
Iteration 3: benign_p1_3 + attack_p1_3 → refined guidelines
Iteration 4: benign_p2_1 + attack_p2_1 → refined guidelines
...
Iteration 9: benign_p3_3 + attack_p3_3 → final guidelines
```

### Language Converter Firewall Generation

1. Loads ALL benign conversations (attacks not used!)
2. For each benign conversation:
   - Prompts LLM to identify communication patterns
   - Generates/refines JSON template for allowed key-value pairs
3. Outputs template as JSON file

**Note:** Language converter firewall only needs benign conversations because it's learning *allowed* communication patterns, not blocking attacks.

## Output Format

### Data Abstraction Guidelines

```
GUIDELINE 1: Personal identifiers
- Full name → First name only
- Exact address → City/region only
- Phone number → REDACTED
- Email address → REDACTED

GUIDELINE 2: Financial information
- Credit card numbers → REDACTED
- Bank account → REDACTED
- Transaction amounts → Approximate ranges
- Purchase history → General categories only

GUIDELINE 3: Travel-specific sensitive data
- Passport numbers → REDACTED
- Visa details → REDACTED
- Hotel room access codes → REDACTED
- Exact future trip dates → Month/season only

...
```

### Language Converter Firewall Template

```json
{
  "destination": "string: city or country name only, no specific addresses",
  "dates": "string: ISO date range (YYYY-MM-DD to YYYY-MM-DD)",
  "price": "number: total cost in specified currency",
  "currency": "string: three-letter currency code (EUR, USD, etc.)",
  "availability": "boolean: true if option is available, false otherwise",
  "options": "array: list of available choices as strings",
  "accommodation_type": "string: one of [hotel, airbnb, hostel, resort]",
  "rating": "number: 1-10 rating scale",
  "included_amenities": "array: list of included services/features",
  "booking_reference": "string: alphanumeric reference code",
  "restrictions": "array: list of applicable restrictions or requirements"
}
```

## Prompt Architecture

The system uses **domain-agnostic** prompt templates that are parameterized with domain-specific task descriptions:

```python
DOMAIN_TASK_DESCRIPTIONS = {
    "travel_planning": "planning and booking travel arrangements",
    "real_estate": "searching for and purchasing real estate properties",
    "insurance": "comparing and purchasing insurance policies"
}
```

This allows the same generation code to work across all three domains while producing domain-relevant guidelines.

See `prompts/` directory for detailed prompt templates.

## Integration with ConVerse

After generating guidelines, they can be integrated into the ConVerse framework:

1. **Data Abstraction Firewall** → Applied in `user_environment/environment_agent.py`
2. **Language Converter Firewall** → Applied in `external_agent/external_agent.py`

See main ConVerse documentation for integration instructions.

## Troubleshooting

**Issue:** "No conversations loaded from benign folders"
- Check that `--persona_dir` points to correct location
- Verify benign_hard/benign_simulation or benign_easy folders exist
- Ensure output_*.json files are present

**Issue:** "No guidelines extracted in iteration N"
- LLM may not be following tag format
- Try `--verbose` flag to see full LLM responses
- Check LLM API credentials and rate limits

**Issue:** "Too many attack conversations, slow generation"
- Use `--num_privacy_samples 10 --num_security_samples 5` to limit
- Start small, then increase for final guidelines

**Issue:** "Different results on each run"
- Set `--sampling_seed 42` for reproducible attack sampling
- LLM generation itself may vary; use temperature=0 in model.py for determinism
