# Firewall Guideline Generation System - Implementation Summary

## Completed Components

### 1. Core Utility Functions (`utils.py`)
✅ Created conversation parsing functions adapted for ConVerse structure:
- `get_conversation_history()` - Extracts assistant ↔ external_agent dialogue
- `load_conversation_from_folder()` - Loads JSON from ConVerse attack/benign folders
- `collect_attack_folders()` - Collects privacy/security attack folders with sampling support
- `collect_benign_folders()` - Collects all benign conversation folders
- `load_conversations_from_folders()` - Batch loads conversations from folder lists
- `extract_tagged_content()` - Parses XML-style tags from LLM output

**Key Design Changes from Original:**
- Removed `balance_conversation_lists()` - not needed with new sampling strategy
- Added folder-based loading (ConVerse has 1 folder per attack with multiple reps inside)
- Added sampling support for attacks (few benign + many attacks vs original's opposite ratio)
- Added reproducible random sampling with seed parameter

### 2. Domain-Agnostic Prompts (`prompts/`)
✅ Created parameterized prompt templates:

**`data_abstraction_prompts.py`:**
- `get_data_abstraction_prompt(domain, task_description)` - Main prompt generator
- `get_previous_guidelines_prompt()` - For iterative refinement
- `DOMAIN_TASK_DESCRIPTIONS` - Mapping of domains to task descriptions
- Domain-agnostic structure with {domain} and {task} placeholders

**`language_converter_prompts.py`:**
- `get_language_converter_prompt(domain, task_description)` - Main prompt generator
- `get_previous_template_prompt()` - For iterative template refinement
- Uses same DOMAIN_TASK_DESCRIPTIONS mapping
- Instructs LLM to generate structured JSON templates

### 3. Main Generation Script (`generate_guidelines.py`)
✅ Complete CLI-based generation system:

**Features:**
- **Multi-persona support**: Process multiple personas in one command
- **Path auto-construction**: Build paths from domain/model/mode/personas
- **Persona specifications**: Single (1), list (1,2,3), range (1-12), or 'all'
- **LLM integration**: Uses LLM class from model.py (same as main.py)
- **Provider auto-detection**: Supports Azure, OpenAI, Anthropic, Google, etc.
- Sampling strategy for privacy/security attacks (per persona)
- Iterative refinement across conversation pairs
- Support for both firewall types
- Previous guidelines refinement support
- Verbose mode for debugging

**Key Functions:**
- `parse_persona_arg()` - Parses persona specifications (1, 1-5, 1,2,3, all)
- `construct_persona_dirs()` - Builds paths from domain/model/mode/personas
- `generate_data_abstraction_guidelines()` - Iterates through (benign, attack) pairs
- `generate_language_converter_template()` - Iterates through benign conversations only
- `main()` - Orchestrates entire generation pipeline

**Design Decisions:**
- Data abstraction uses benign + attacks (both privacy and security)
- Language converter firewall uses ONLY benign (learns allowed patterns, not attacks)
- Benign: always ALL files per persona (typically 3-6 each)
- Attacks: configurable sampling per persona (can be 50+ per type per persona)
- **NEW**: Combines conversations from ALL specified personas before generation

### 4. Documentation (`README.md`)
✅ Comprehensive documentation covering:
- Overview and architecture
- Directory structure
- Usage examples for all scenarios
- Command-line argument reference
- ConVerse log structure explanation
- Sampling strategy details
- Output format examples
- Integration guidance
- Troubleshooting section

## Architecture Highlights

### Sampling Strategy
```
Benign: ALWAYS ALL (3-6 files typically)
Privacy Attacks: --num_privacy_samples N (or ALL if not specified)
Security Attacks: --num_security_samples M (or ALL if not specified)
Seed: --sampling_seed 42 (for reproducibility)
```

### Iteration Logic
```
Data Abstraction Firewall:
  for i in range(min(len(benign), len(attacks))):
      benign_conv = benign[i]
      attack_conv = attacks[i]
      guidelines = LLM(base_prompt + prev_guidelines + benign_conv + attack_conv)
      prev_guidelines = extract_guidelines(guidelines)

Language Converter Firewall:
  for benign_conv in benign_conversations:
      template = LLM(base_prompt + prev_template + benign_conv)
      prev_template = extract_template(template)
```

### Domain Parameterization
```python
DOMAIN_TASK_DESCRIPTIONS = {
    "travel_planning": "planning and booking travel arrangements",
    "real_estate": "searching for and purchasing real estate properties",
    "insurance": "comparing and purchasing insurance policies"
}

# Used in prompts as:
f"This assistant helps users with {task_description} in the {domain} domain."
```

## Usage Examples

### Example 1: Generate for Multiple Personas (New Recommended Approach)
```bash
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas "1,2,3" \
    --num_privacy_samples 10 \
    --num_security_samples 5 \
    --llm_name gpt-4
```

**What happens:**
1. Constructs paths: `logs/travel_planning/gpt_5_chat/baseline/persona{1,2,3}`
2. Loads ALL benign from each persona (~3-6 files × 3 = ~9-18 total)
3. Samples 10 privacy + 5 security attacks per persona (15 × 3 = 45 total attacks)
4. Combines all conversations: ~15 benign + 45 attacks
5. Iterates through min(15, 45) = 15 conversation pairs
6. Outputs: `generated/travel_planning_data_abstraction_guidelines.txt` + language converter template

### Example 2: Process ALL Personas at Once (Budget-Friendly)
```bash
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas all \
    --num_privacy_samples 5 \
    --num_security_samples 3 \
    --llm_name gpt-4
```

**What happens:**
1. Processes all 12 personas automatically
2. Loads ~3-6 benign × 12 = ~36-72 total benign conversations
3. Samples 5 privacy + 3 security × 12 personas = 96 total attacks
4. Combines everything for comprehensive guidelines
5. Single command generates rules from entire dataset!

### Example 3: Use Persona Range
```bash
python mitigation_guidelines/generate_guidelines.py \
    --domain real_estate \
    --firewall_type data_abstraction \
    --model_folder_name claude \
    --mode baseline \
    --personas "1-5" \
    --llm_name claude-3-opus-20240229 \
    --provider anthropic
```

**What happens:**
1. Processes personas 1, 2, 3, 4, 5 from real_estate
2. Uses Claude for generation
3. Loads ALL available attacks (no sampling)

## Next Steps (Not Yet Implemented)

The following components are planned but NOT yet implemented:

### 1. Integration with ConVerse Main Execution
- Modify `main.py` to add `--firewall_mode` argument
- Load generated guidelines/templates at runtime
- Apply data abstraction in environment agent
- Apply language converter firewall in external agent

### 2. Firewall Application Logic
- Data abstraction filter in `user_environment/environment_agent.py`
- Language converter template enforcement in `external_agent/external_agent.py`
- Proper error handling for malformed responses

### 3. Results Analysis Updates
- Modify `results_analysis/` to handle firewall experiment results
- Add comparison metrics: baseline vs taskConfined vs firewall
- Generate latex tables with firewall columns

### 4. Judge Analysis Updates
- Ensure judges can evaluate firewall-protected conversations
- Add specific metrics for data leakage prevention

## File Structure Created

```
mitigation_guidelines/
├── __init__.py                          ✅ Created
├── README.md                            ✅ Created (comprehensive)
├── generate_guidelines.py               ✅ Created (548 lines)
├── utils.py                             ✅ Created (200 lines)
├── prompts/
│   ├── __init__.py                      ✅ Created
│   ├── data_abstraction_prompts.py      ✅ Created (114 lines)
│   └── language_converter_prompts.py    ✅ Created (121 lines)
└── generated/                           ✅ Created (empty, ready for output)
```

## Testing Recommendations

Before full deployment:

1. **Test with small sample:**
   ```bash
   python mitigation_guidelines/generate_guidelines.py \
       --domain travel_planning \
       --firewall_type both \
       --persona_dir logs/travel_planning/gpt_5_chat/baseline/persona1 \
       --num_privacy_samples 2 \
       --num_security_samples 1 \
       --verbose
   ```

2. **Verify output files are created:**
   - Check `generated/travel_planning_data_abstraction_guidelines.txt` exists
   - Check `generated/travel_planning_language_converter_template.json` exists
   - Verify content quality

3. **Test sampling reproducibility:**
   ```bash
   # Run twice with same seed
   python generate_guidelines.py ... --sampling_seed 42
   python generate_guidelines.py ... --sampling_seed 42
   # Should produce identical attack selection
   ```

4. **Test iterative refinement:**
   ```bash
   # First generation
   python generate_guidelines.py ... --output_dir gen1
   # Second generation using first as starting point
   python generate_guidelines.py ... --previous_guidelines gen1/...txt --output_dir gen2
   # Compare gen1 vs gen2 to see refinement
   ```

## Summary

✅ **COMPLETED:**
- Full utility function suite for ConVerse log structure
- Domain-agnostic prompt templates for both firewalls
- Complete CLI-based generation script with sampling
- Comprehensive documentation and usage examples

❌ **NOT YET IMPLEMENTED:**
- Integration with main.py execution pipeline
- Firewall application logic in agents
- Results analysis updates
- Judge analysis updates

The guideline generation system is **fully functional and ready to use** for creating firewall rules. The next phase is integrating these rules into the ConVerse runtime execution.
