# Quick Start Guide: Firewall Guideline Generation

## TL;DR - Most Common Use Cases

### 1. Generate guidelines from ALL personas (recommended for production)
```bash
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas all \
    --num_privacy_samples 10 \
    --num_security_samples 5 \
    --llm_name gpt-4
```

### 2. Quick test with single persona
```bash
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --firewall_type both \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas 1 \
    --num_privacy_samples 2 \
    --num_security_samples 1 \
    --llm_name gpt-4 \
    --verbose
```

### 3. Generate from specific personas with full attack coverage
```bash
python mitigation_guidelines/generate_guidelines.py \
    --domain real_estate \
    --firewall_type both \
    --model_folder_name claude \
    --mode baseline \
    --personas "1,2,3" \
    --llm_name claude-3-opus-20240229
```
*(No sampling = uses ALL attacks)*

## New vs Legacy Argument Styles

### NEW STYLE (Recommended)
**Advantages:**
- Process multiple personas in one command
- Auto-constructs paths
- Scales to all 12 personas with `--personas all`
- More flexible and powerful

```bash
--domain travel_planning \
--model_folder_name gpt_5_chat \
--mode baseline \
--personas "1,2,3"
```

### LEGACY STYLE (Still Supported)
**When to use:**
- Quick single persona testing
- Non-standard directory structures
- Backward compatibility

```bash
--domain travel_planning \
--persona_dir logs/travel_planning/gpt_5_chat/baseline/persona1
```

## Persona Specification Options

| Syntax | Meaning | Example |
|--------|---------|---------|
| `1` | Single persona | Persona 1 only |
| `1,2,3` | Specific list | Personas 1, 2, and 3 |
| `1-5` | Range | Personas 1, 2, 3, 4, 5 |
| `all` | All personas | All 12 personas |

## Sampling Strategy Recommendations

### Development/Testing
```bash
--num_privacy_samples 2 \
--num_security_samples 1
```
- Fast iteration
- ~3-6 LLM calls per persona

### Production (Balanced)
```bash
--num_privacy_samples 10 \
--num_security_samples 5
```
- Good coverage
- ~15 attacks per persona
- Reasonable cost

### Production (Comprehensive)
```bash
# Omit sampling arguments to use ALL attacks
```
- Full coverage
- ~50-80 attacks per persona
- Higher cost but best quality

## LLM Provider Examples

### OpenAI (Default)
```bash
--llm_name gpt-4 \
--provider openai
```
*(Requires: OPENAI_API_KEY environment variable)*

### Anthropic
```bash
--llm_name claude-3-opus-20240229 \
--provider anthropic
```
*(Requires: ANTHROPIC_API_KEY environment variable)*

### Azure OpenAI
```bash
--llm_name gpt-4 \
--provider azure \
--azure_endpoint https://your-endpoint.openai.azure.com/
```
*(Requires: AZURE_OPENAI_API_KEY or DefaultAzureCredential)*

### Google Gemini
```bash
--llm_name gemini-1.5-pro \
--provider google
```
*(Requires: GOOGLE_AI_API_KEY environment variable)*

## Output Files

Files are saved to `mitigation_guidelines/generated/` by default:

- **Data Abstraction:** `{domain}_data_abstraction_guidelines.txt`
- **Language Converter Firewall:** `{domain}_language_converter_template.json`

## Common Workflows

### Workflow 1: Initial Generation
```bash
# Step 1: Test with 2 personas, small sample
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas "1,2" \
    --num_privacy_samples 3 \
    --num_security_samples 2 \
    --firewall_type both \
    --llm_name gpt-4 \
    --verbose

# Step 2: Review output, then scale to all personas
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas all \
    --num_privacy_samples 10 \
    --num_security_samples 5 \
    --firewall_type both \
    --llm_name gpt-4
```

### Workflow 2: Iterative Refinement
```bash
# Step 1: Initial generation from personas 1-6
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas "1-6" \
    --firewall_type data_abstraction \
    --llm_name gpt-4 \
    --output_dir gen_v1

# Step 2: Refine with additional personas 7-12
python mitigation_guidelines/generate_guidelines.py \
    --domain travel_planning \
    --model_folder_name gpt_5_chat \
    --mode baseline \
    --personas "7-12" \
    --firewall_type data_abstraction \
    --llm_name gpt-4 \
    --previous_guidelines gen_v1/travel_planning_data_abstraction_guidelines.txt \
    --output_dir gen_v2
```

### Workflow 3: Cross-Domain Generation
```bash
# Generate for all 3 domains in sequence
for domain in travel_planning real_estate insurance; do
    python mitigation_guidelines/generate_guidelines.py \
        --domain $domain \
        --model_folder_name gpt_5_chat \
        --mode baseline \
        --personas all \
        --num_privacy_samples 10 \
        --num_security_samples 5 \
        --firewall_type both \
        --llm_name gpt-4
done
```

## Troubleshooting Quick Fixes

**Problem:** `Error: Either --persona_dir or --model_folder_name must be provided`
```bash
# Fix: Add both model_folder_name AND mode
--model_folder_name gpt_5_chat --mode baseline --personas 1
```

**Problem:** `Error: Persona directory not found`
```bash
# Fix: Check your logs folder structure
ls logs/travel_planning/
# Make sure model folder name matches exactly (case-sensitive)
```

**Problem:** `Warning: No guidelines extracted in iteration N`
```bash
# Fix: Use --verbose to see LLM output, check API credentials
--verbose
```

**Problem:** Too slow, too expensive
```bash
# Fix: Reduce sampling
--num_privacy_samples 2 --num_security_samples 1
# Or test with fewer personas first
--personas 1
```

## Environment Variables Needed

Depending on your LLM provider:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Azure OpenAI
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."

# Google Gemini
export GOOGLE_AI_API_KEY="..."

# Anthropic via Vertex AI
export GOOGLE_CLOUD_PROJECT_ID="..."
export GOOGLE_CLOUD_REGION="us-east5"
```

## Cost Estimation

Rough estimates for gpt-4:

| Personas | Sampling | Iterations | Est. Cost |
|----------|----------|------------|-----------|
| 1 | 2 privacy, 1 security | ~3-6 | $0.50 - $1 |
| 3 | 10 privacy, 5 security | ~15-20 | $3 - $5 |
| all (12) | 10 privacy, 5 security | ~50-80 | $10 - $20 |
| all (12) | ALL attacks | ~100-200 | $20 - $50 |

*(Actual costs vary by model, conversation length, and output size)*
