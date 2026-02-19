# Language Converter Firewall Coverage Analysis

Evaluates how completely the language converter firewall template can represent external agent communications. This analysis identifies which requests/offers can be described by the template (allowed through) versus which cannot (filtered/blocked).

## Overview

The language converter firewall transforms external agent communications into a fixed JSON schema. This analysis measures its **effectiveness** by counting:

1. **Describable items**: Communications that CAN be represented in the template
2. **Indescribable items**: Communications that CANNOT be represented (blocked by firewall)

**Expected behavior**:
- **Benign cases**: Most items describable (~0.5 indescribable) → Firewall doesn't block legitimate requests
- **Attack cases**: Many items indescribable (1-5) → Firewall successfully blocks malicious requests

## Files

- `run_coverage_analysis.py` - Main script to evaluate existing conversation logs
- `language_converter_coverage_judge.py` - LLM judge that performs coverage evaluation
- `language_converter_coverage_prompts.py` - Prompts for the coverage judge
- `language_converter_coverage_utils.py` - Helper functions (file loading, parsing, etc.)
- `generate_coverage_tables.py` - Aggregates results and generates tables
- `results/` - Stores individual coverage evaluation results (JSON)

## Usage

### Step 1: Run Coverage Analysis

Evaluate language converter coverage for existing experiment logs:

```bash
python language_converter_coverage_analysis/run_coverage_analysis.py \
  --logs_dir logs \
  --mode firewalls_data_abstraction_language_converter \
  --use_cases travel_planning,real_estate,insurance \
  --judge_llm_name gpt-5-chat-latest \
  --judge_provider openai
```

**Parameters**:
- `--logs_dir`: Directory containing experiment logs (default: `logs`)
- `--mode`: Mode to analyze (e.g., `firewalls_data_abstraction_language_converter`, `firewalls_language_converter`)
- `--use_cases`: Comma-separated list of use cases (optional, defaults to all)
- `--models`: Comma-separated list of models to analyze (optional filter)
- `--judge_llm_name`: LLM to use for coverage evaluation
- `--judge_provider`: Provider for judge LLM (azure, openai, anthropic, etc.)
- `--skip_existing`: Skip files that already have coverage results
- `--max_files`: Limit number of files to process (for testing)

**Output**:
- Individual result files saved to `language_converter_coverage_analysis/results/`
- Format: `{use_case}_{model}_{mode}_persona{N}_{attack_name}_rep{X}.json`

### Step 2: Generate Tables

Aggregate results and create analysis tables:

```bash
python language_converter_coverage_analysis/generate_coverage_tables.py \
  --results_dir language_converter_coverage_analysis/results \
  --output_format both
```

**Parameters**:
- `--results_dir`: Directory containing coverage result JSON files
- `--output_dir`: Directory to save output tables (default: `language_converter_coverage_analysis`)
- `--output_format`: Output format - `csv`, `latex`, or `both`

**Output**:
- `language_converter_coverage_summary.csv` - Summary table with statistics per attack type
- `language_converter_coverage_table.tex` - LaTeX table (Table 13 style)

## Output Format

### Individual Result File

Each evaluated conversation produces a JSON file with:

```json
{
  "use_case": "travel_planning",
  "model": "gpt_5_chat",
  "mode": "firewalls_data_abstraction_language_converter",
  "persona": "1",
  "attack_type": "privacy",
  "attack_name": "related_and_useful_full_name",
  "repetition": "1",
  "file_path": "logs/.../output_20260117_141920_rep1.json",
  
  "indescribable_count": 3,
  "indescribable_items": [
    "Requesting user's full legal name",
    "Asking for passport details",
    "Emergency contact information request"
  ],
  "describable_count": 12,
  "describable_items": [
    "Flight options with prices",
    "Hotel recommendations",
    "Activity suggestions",
    ...
  ],
  "total_items": 15,
  "coverage_percentage": 80.0,
  "judge_text": "Full judge output..."
}
```

### Summary Table (CSV) (Example numbers not real ones)

| Attack Type | Count | Avg Indescribable | Avg Describable | Coverage % | Example Indescribable Items |
|-------------|-------|-------------------|-----------------|------------|----------------------------|
| Benign      | 48    | 0.53              | 11.2            | 95.5       | ['Confirmation numbers', ...] |
| Privacy     | 144   | 3.72              | 8.4             | 69.3       | ['Past trips', 'Calendar', ...] |
| Security    | 96    | 2.15              | 9.1             | 80.9       | ['Delete calendar', ...] |

### LaTeX Table

Generates publication-ready LaTeX table matching Table 13 format from the paper.

## How It Works

1. **Load Conversation**: Reads `output_*.json` files from experiment logs
2. **Extract External Messages**: Identifies all messages from external agent to assistant
3. **Load Language Converter Template**: Loads use-case-specific template from `mitigation_guidelines/generated/{use_case}/`
4. **Judge Evaluation**: LLM judge compares external messages against template schema
5. **Parse Results**: Extracts counts and example items from judge response
6. **Save Results**: Individual JSON files for each conversation
7. **Aggregate**: Group by attack type and calculate statistics
8. **Generate Tables**: Create CSV and LaTeX outputs

## Examples

### Quick Test Run

Test on a small subset:

```bash
python language_converter_coverage_analysis/run_coverage_analysis.py \
  --logs_dir logs \
  --mode firewalls_data_abstraction_language_converter \
  --use_cases travel_planning \
  --judge_llm_name gpt-5-chat-latest \
  --judge_provider openai \
  --max_files 10
```

### Full Analysis

Run complete analysis for all use cases:

```bash
# Step 1: Evaluate all conversations
python language_converter_coverage_analysis/run_coverage_analysis.py \
  --logs_dir logs \
  --mode firewalls_data_abstraction_language_converter \
  --use_cases travel_planning,real_estate,insurance \
  --judge_llm_name gpt-5-chat-latest \
  --judge_provider openai \
  --skip_existing

# Step 2: Generate tables
python language_converter_coverage_analysis/generate_coverage_tables.py \
  --results_dir language_converter_coverage_analysis/results \
  --output_format both
```

### Compare Multiple Modes

Analyze different firewall modes separately:

```bash
# Language converter only
python language_converter_coverage_analysis/run_coverage_analysis.py \
  --mode firewalls_language_converter \
  --output_dir language_converter_coverage_analysis/results_language_converter \
  ...

# Data abstraction + Language converter
python language_converter_coverage_analysis/run_coverage_analysis.py \
  --mode firewalls_data_abstraction_language_converter \
  --output_dir language_converter_coverage_analysis/results_both \
  ...
```

## Troubleshooting

**No files found**:
- Verify `--mode` matches directory names in `logs/`
- Check that language converter firewall experiments have been run

**Parsing errors**:
- Judge LLM may not follow format strictly
- Increase `--judge_max_retries`
- Try different judge model

**High error rate**:
- Check that conversation files contain external agent messages
- Verify language converter template exists for use cases

