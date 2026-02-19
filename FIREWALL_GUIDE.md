# Firewall Integration Guide

This guide explains how to use the firewall capabilities in the ConVerse benchmark system.

## Overview

The system supports two types of firewalls to protect against privacy and security attacks:

1. **Data Abstraction Firewall**: Filters sensitive information from environment responses before sharing with external agents
2. **Language Converter Firewall**: Converts external agent outputs into structured, controlled JSON format

## Prerequisites

Before using firewalls, you must generate domain-specific guidelines:

```bash
python generate_guidelines.py --config_file sample_config.yaml
```

This creates:
- `mitigation_guidelines/generated/{domain}/{domain}_data_abstraction_guidelines.txt`
- `mitigation_guidelines/generated/{domain}/{domain}_language_converter_template.json`

## Usage

### Enable Both Firewalls

```bash
python main.py \
  --use_case travel_planning \
  --persona_id 1 \
  --simulation_type privacy \
  --attack_name "related_and_useful_full_name" \
  --apply_data_firewall \
  --apply_language_converter_firewall \
  --llm_name gpt-4-turbo-2024-04-09
```

### Enable Only Data Abstraction Firewall

```bash
python main.py \
  --use_case travel_planning \
  --persona_id 1 \
  --simulation_type privacy \
  --attack_name "related_and_useful_full_name" \
  --apply_data_firewall \
  --llm_name gpt-4-turbo-2024-04-09
```

### Enable Only Language Converter Firewall

```bash
python main.py \
  --use_case travel_planning \
  --persona_id 1 \
  --simulation_type privacy \
  --attack_name "related_and_useful_full_name" \
  --apply_language_converter_firewall \
  --llm_name gpt-4-turbo-2024-04-09
```

## Command-Line Arguments

### Firewall Options

- `--apply_data_firewall`: Enable data abstraction firewall for environment agent
- `--apply_language_converter_firewall`: Enable language converter firewall for external agent

## How It Works

### Data Abstraction Firewall

1. **Location**: Applied in `UserEnvironmentAgent.simulate_env()`
2. **Purpose**: Filters PII and confidential data from environment responses
3. **Process**:
   - Environment generates response with full user data
   - Firewall applies confidentiality guidelines via LLM
   - Only filtered/abstracted data is shared with external agent
   - Original data preserved in environment's internal history

### Language Converter Firewall

1. **Location**: Applied in `External.process_agent_turn()`
2. **Purpose**: Converts external agent responses into structured, controlled JSON format
3. **Process**:
   - External agent generates free-form response
   - Firewall transforms response to JSON template via LLM
   - Validates compliance with template (types, required fields)
   - Replaces names with IDs (e.g., "Paris" → "destination_option1")
   - Assistant receives responses with IDs converted back to names

### ID Mapping

Language converter firewall maintains consistent name-to-ID mappings across conversation:
- First mention: "Paris" → "destination_option1"
- Subsequent mentions: "Paris" → "destination_option1" (same ID)
- Different location: "London" → "destination_option2"

This ensures:
- Structured data format for validation
- Consistency across multiple turns
- Human-readable names for assistant

## Architecture

```
firewalls/
├── __init__.py                      # Package exports
├── language_checker.py              # JSON validation and ID mapping
├── language_converter_firewall.py   # Language converter firewall class
└── data_abstraction_firewall.py    # Data abstraction firewall class
```

### Module Responsibilities

**language_checker.py**:
- `check_compliance()`: Validates JSON against template
- `process_final_dict()`: Replaces names with IDs
- Type checking for int, float, str, datetime, bool, lists

**language_converter_firewall.py**:
- `LanguageConverterFirewall` class with LLM-based transformation
- Retry logic (up to 10 attempts) for malformed JSON
- `update_ids_to_names()`: Converts IDs back to names

**data_abstraction_firewall.py**:
- `DataAbstractionFirewall` class with LLM-based filtering
- Uses domain-specific confidentiality guidelines
- Preserves utility while protecting privacy

## Example Output

### Without Firewalls
```
External: "I found a great hotel in Paris called Hotel Lumière on Rue de Rivoli for €150/night"
Assistant receives: [same unstructured text]
```

### With Language Converter Firewall
```
External: "I found a great hotel in Paris called Hotel Lumière on Rue de Rivoli for €150/night"
Language converter firewall transforms to:
{
  "destination_name": "destination_option1",
  "accommodation_name": "accommodation_option1",
  "address": "Rue de Rivoli",
  "price_per_night": 150.00
}
Assistant receives: "I found a great hotel in Paris called Hotel Lumière..."
(IDs converted back to names for readability)
```

### With Data Abstraction Firewall
```
Environment (internal): "User John Doe (SSN: 123-45-6789) prefers luxury hotels, budget €2000"
Data abstraction firewall filters to: "User prefers luxury hotels, budget range provided"
External agent receives: [filtered version only]
```

## Domain Support

Firewalls work with all three use cases:
- `travel_planning`
- `insurance`
- `real_estate`

Each domain has its own generated guidelines and templates.
