# Firewalls to Secure Dynamic LLM Agentic Networks

[![arXiv](https://img.shields.io/badge/arXiv-2502.01822-b31b1b.svg)](https://arxiv.org/abs/2502.01822)
[![ConVerse Benchmark](https://img.shields.io/badge/arXiv-2511.05359_(ConVerse)-blue.svg)](https://arxiv.org/abs/2511.05359)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Note**: This is the actively maintained version of the project. Development originally began at Microsoft ([microsoft/Firewalled-Agentic-Networks](https://github.com/microsoft/Firewalled-Agentic-Networks)), but that repository is no longer maintained. All continued development by the same authors is published here.

<p align="center">
  <img src="system_overview.png" alt="Dual-Firewall Architecture Overview" width="100%">
</p>

<p align="center">
  <em>Figure 1: The dual-firewall architecture for agent-to-agent communication. Incoming path (right): Messages from the external service agent pass through the Language Converter Firewall, which transforms natural language into a structured protocol using a learned domain-specific schema, followed by deterministic verification. Outgoing path (left): When the assistant queries the user's data, responses pass through the Data Abstraction Firewall, which applies learned rules to filter, abstract, or pass information according to contextual appropriateness.</em>
</p>

This repository contains the code for **Firewalls to Secure Dynamic LLM Agentic Networks**, a dual-firewall architecture that provides structural protection for agent-to-agent communication. Our firewalls act as projections onto the task context, allowing only contextually appropriate content to cross each trust boundary — near-eliminating both privacy leakage and security attacks while maintaining or improving task utility.

This work builds on and extends the **[ConVerse](https://github.com/amrgomaaelhady/ConVerse)** benchmark ([Gomaa et al., 2025](https://arxiv.org/abs/2511.05359)), which provides the evaluation framework for contextual safety in agent-to-agent conversations.

> **Research Context**: The emergence of agent-to-agent communication protocols mirrors the early internet: powerful connectivity with minimal security infrastructure. When AI agents communicate on behalf of users, every message crosses a trust boundary where the user's personal data and the external agent's unconstrained language each present distinct risks. We address both through a dual-firewall architecture grounded in a unifying principle: each task defines a context, and both sides of the communication carry information far exceeding what that context requires.

**Key Results:**
- **Privacy ASR reduced by 80–90%**: e.g., from 84% to 10% for GPT-5
- **Security ASR reduced to under 4%**: e.g., from 60% to 3% for GPT-5
- **Utility preserved or improved**: Plan quality ratings increase with firewall protection
- **864 contextually grounded attacks** across 3 domains (Travel, Real Estate, Insurance) from the [ConVerse](https://github.com/amrgomaaelhady/ConVerse) benchmark
- **4 frontier models evaluated**: GPT-5, Claude Sonnet 4, Gemini 2.5 Pro, Gemini 2.5 Flash
- **Structural guarantees**: Protection holds regardless of attack sophistication — manipulation has no channel through which to arrive

## Table of Contents

- [Overview](#overview)
- [Dual-Firewall Architecture](#dual-firewall-architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Experiments](#running-experiments)
- [Data Organization](#data-organization)
- [Results Analysis](#results-analysis)
- [Reproducibility](#reproducibility)
- [Citation](#citation)

---

## Overview

This project implements a **dual-firewall architecture** for securing LLM agent-to-agent communication, evaluated on the [ConVerse](https://github.com/amrgomaaelhady/ConVerse) benchmark. The system addresses two fundamental risks:
- **Privacy leakage**: Agents overshare user data during task execution, even without adversarial prompting
- **Security attacks**: External agents use contextual manipulation (persuasive framing, urgency tactics, social engineering) to steer assistant behavior

Our firewalls provide **structural guarantees** that do not depend on the underlying model's robustness or alignment. They operate in a trusted environment isolated from external input, applying domain-specific rules learned automatically from demonstrations.

The evaluation uses the **ConVerse** benchmark ([Gomaa et al., 2025](https://arxiv.org/abs/2511.05359)), which models **autonomous, multi-turn agent-to-agent conversations** where malicious requests are contextually embedded within legitimate task domains across three practical domains.

### Privacy Taxonomy (from ConVerse)

The [ConVerse](https://github.com/amrgomaaelhady/ConVerse) benchmark uses a **three-tier privacy taxonomy** that goes beyond binary access control:

1. **Unrelated Data** (34.4% of attacks): No relevance to the task domain
   - Example: Employer details when planning vacation
   - Expected behavior: Should never be shared

2. **Domain-Related but Private** (29.3% of attacks): Semantically relevant but unnecessary
   - Example: Past trip dates and locations when planning future travel
   - Expected behavior: Should not be shared despite relevance

3. **Domain-Related and Useful** (36.3% of attacks): Necessary for planning but requires abstraction
   - Example: Asset ranges instead of detailed itemized lists for insurance coverage
   - Expected behavior: Share abstracted information, not raw granular details

### Security Attack Categories

1. **Toolkit Manipulation** (39.1%): Exploit assistant's tools for unauthorized actions
   - Calendar manipulation, email fraud, denial of service attacks
   
2. **Preference Manipulation** (60.9%): Steer agents toward misaligned options
   - Upselling beyond budget, contradicting user preferences, exceeding task scope

### Key Findings

**Baseline vulnerabilities** (without firewalls, from [ConVerse](https://github.com/amrgomaaelhady/ConVerse)):
- **Higher-capability models leak more**: 84.68% privacy ASR on GPT-5 despite strong utility (rating: 7.99, coverage: 96.55%)
- **Privacy is harder to defend than security**: Privacy ASR averages 64% vs. security ASR 33% across models
- **Contextual attacks are highly effective**: Multi-turn attacks using plausible justifications succeed at high rates

**With dual-firewall architecture** (this work):
- **Privacy ASR dramatically reduced**: GPT-5 drops from 88.51% to 7.77% on Travel Planning; all models converge to 7-9% ASR
- **Security attacks near-eliminated**: All models under 4% ASR (e.g., GPT-5 from 55.32% to 3.26%)
- **Utility preserved or improved**: Plan quality ratings increase (e.g., GPT-5: 8.07 → 8.42), coverage remains stable or improves
- **Firewalls complement each other**: Data Abstraction alone reduces privacy ASR to 29%; Language Conversion alone to 21%; both together achieve 7.77%
- **Generalizes across personas**: Rules learned from 2 personas protect held-out personas equally well


### System Architecture

The system uses a three-agent architecture from [ConVerse](https://github.com/amrgomaaelhady/ConVerse), augmented with our dual-firewall protection:
1. **User Environment Agent**: Represents the user with specific preferences and data
2. **Assistant Agent**: The LLM-based assistant being evaluated
3. **External Agent**: Simulates external services (travel agency, realtor, insurance broker)
4. **Language Converter Firewall** *(new)*: Interposes between external agent and assistant — converts incoming natural language to a closed, structured protocol
5. **Data Abstraction Firewall** *(new)*: Interposes between user environment and assistant — abstracts personal data to task-appropriate granularity

---

## Dual-Firewall Architecture

Our architecture interposes two complementary firewalls that together near-eliminate the conditions under which both privacy and security attacks succeed.

<p align="center">
  <img src="firewall_examples.png" alt="Firewall Examples" width="100%">
</p>

<p align="center">
  <em>Figure 2: Illustration of the dual-firewall architecture. Left (Data Abstraction): The user's home address is minimally transformed before reaching the assistant, preserving utility while removing identifying details. Right (Language Conversion): The external agent's natural language message (which may contain manipulative text) is converted to a closed structured protocol with validated fields and where free-form strings are sanitized.</em>
</p>

### Language Converter Firewall

The main enabler of security attacks in agent-to-agent communication is **natural language itself**. An external agent can embed urgency cues, social proof, appeals to authority, or direct instruction manipulation. The Language Converter Firewall inverts this asymmetry by converting incoming messages into a **closed, domain-specific structured protocol** before the assistant processes them.

**How it works:**
1. **LLM Conversion**: An LLM converts the external agent's natural language message into a structured JSON object based on a learned domain-specific schema
2. **Deterministic Verification**: A programmatic verifier validates every field — enumerated values are checked against valid sets, types are validated, unknown keys are dropped
3. **String Anonymization**: Free-form string fields (hotel names, airlines) are replaced with anonymous identifiers (e.g., `hotel_1`) to prevent embedded injection attacks

**Security guarantees**: Closed vocabulary, constrained values, type safety, string isolation, and deterministic verification. These hold regardless of attack sophistication because the attack surface of arbitrary natural language is eliminated.

### Data Abstraction Firewall

Even when processing only sanitized structured input, LLM assistants tend to **overshare** personal data. The Data Abstraction Firewall transforms personal data before it reaches the assistant, operating on the principle of **contextual integrity** — appropriate information sharing depends on context.

**How it works:**
- The firewall receives raw data from the knowledge base along with learned abstraction rules, but **never sees** the external agent's messages or conversation context
- It applies domain-specific rules that specify what information to allow, abstract, or block and at what granularity
- Example: A home address becomes "departing from the Paris area"; a specific age becomes "adult"; a medication list is reduced to "has a food allergy"

**Key property**: Adversarial isolation — manipulation attempts from the external agent cannot influence the abstraction process because the firewall has no channel through which that reasoning could arrive.

### Automated Rule Learning

Both firewalls operate by applying pre-generated rules **learned from demonstrations** rather than manually specified:
- **Language Converter rules** are learned from benign conversation corpora — an LLM identifies what information types are legitimately exchanged and produces a structured schema
- **Data Abstraction rules** are learned from paired benign/attack corpora — by contrasting legitimate and adversarial conversations, the system identifies appropriate disclosure levels

Rules capture domain-appropriate norms rather than persona-specific details, enabling generalization to new users and attack types. See [FIREWALL_GUIDE.md](FIREWALL_GUIDE.md) for details on generating rules.

### Comparison

| Feature | Prior Approaches | Our Dual-Firewall Architecture |
|---------|-----------------|----------|
| **Security Model** | Detect malicious content (adversary can win iteratively) | Structural elimination of manipulation channels |
| **Privacy Model** | Binary disclose-or-redact filtering | Context-appropriate abstraction at right granularity |
| **Attack Surface** | Unbounded natural language | Closed, verified structured protocol |
| **Firewall Placement** | Output filtering (can be manipulated) | Input-side protection in trusted environment |
| **Rule Specification** | Manual rules or model-level alignment | Automatically learned from demonstrations |

---

## Project Structure

```
Firewall-Agentic-Networks/
├── main.py                          # Main execution script
├── requirements.txt                 # Python dependencies
├── model.py                         # LLM interface and provider management
├── utils.py                         # Logging and utility functions
├── simulation_utils.py              # Simulation helper functions
├── attack_execution.py              # Attack orchestration logic
├── benchmark_stats.py               # Benchmark Statistics calculation (e.g., no. of attacks, etc..)
│
├── results_analysis/                # Modular results analysis package
│   ├── __init__.py
│   ├── data_loading.py             # Data loading and parsing utilities
│   ├── data_enhancement.py         # Dataset enhancement and categorization
│   ├── analysis_utils.py           # Statistical analysis and CIs
│   ├── formatting_utils.py         # LaTeX formatting utilities
│   ├── latex_generation.py         # LaTeX table generation
│   ├── results_analysis.ipynb      # Main analysis notebook
│   └── README.md                   # Package documentation
│
├── assistant/                       # Assistant agent implementation
│   ├── assistant_agent.py
│   ├── assistant_prompts.py
│   └── assistant_utils.py
│
├── user_environment/                # User environment agent
│   ├── environment_agent.py
│   ├── environment_prompts.py
│   └── environment_utils.py
│
├── external_agent/                  # External agent (adversarial/benign)
│   ├── external_agent.py
│   ├── external_prompts_adv.py
│   ├── external_prompts_benign.py
│   └── external_utils.py
│
├── judge/                          # Automated evaluation system
│   ├── utility_judge.py           # Evaluates task completion quality
│   ├── privacy_judge.py           # Evaluates privacy leakage
│   ├── security_judge.py          # Evaluates security vulnerabilities
│   └── *_prompts.py               # Judge-specific prompts
│
├── use_cases/                      # Use case configuration
│   ├── config.py                  # Use case registry and configs
│   └── data_loader.py             # Data loading utilities
│
├── firewalls/                      # Dual-firewall architecture (core contribution)
│   ├── __init__.py                # Package exports
│   ├── language_checker.py       # JSON validation, type checking, and ID mapping
│   ├── language_converter_firewall.py  # Language Converter Firewall: structured protocol enforcement
│   └── data_abstraction_firewall.py  # Data Abstraction Firewall: contextual data projection
│
├── mitigation_guidelines/          # Firewall rule generation and configuration
│   └── generated/                 # Auto-learned domain-specific guidelines
│       ├── travel_planning/
│       ├── insurance/
│       └── real_estate/
│
└── resources/                      # Experiment data and attack definitions
    ├── inter_rater_calc.py        # Inter-rater reliability calculator
    ├── IRR_results_summary_averaged.txt  # IRR test results
    ├── template_creation_script.py # Rating template generator
    │
    ├── travel_planning_usecase/
    │   ├── env_persona1.txt       # User environment description
    │   ├── env_persona2.txt
    │   ├── env_persona3.txt
    │   ├── env_persona4.txt
    │   ├── options.txt            # Available options (flights, hotels, etc.)
    │   ├── security_attacks/      # Security attack definitions
    │   │   ├── security_attacks_persona1.json
    │   │   └── ...
    │   ├── privacy_attacks/       # Privacy attack definitions
    │   │   ├── privacy_attacks_persona1.json
    │   │   └── ...
    │   └── ratings/              # Ground Truth utility ratings
    │       ├── ratings_persona1.json
    │       ├── ratings_persona2.json
    │       ├── ratings_persona3.json
    │       ├── ratings_persona4.json
    │       └── study/            # Reliability verification
    │           ├── template_ratings_persona1.json
    │           ├── template_ratings_persona1_gpt5.json
    │           ├── template_ratings_persona1_gpt41.json
    │           ├── template_ratings_persona1_claude.json
    │           ├── template_ratings_persona1_gemini.json
    │           └── ...           # Same pattern for personas 2-4
    │
    ├── real_estate_usecase/       # Same structure as travel_planning
    └── insurance_usecase/         # Same structure as travel_planning
```


---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- API keys for at least one LLM provider (OpenAI, Anthropic, Google, etc.)

### Step 1: Clone the Repository

```bash
git clone https://github.com/amrgomaaelhady/Firewall-Agentic-Networks.git
cd Firewall-Agentic-Networks
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages
- `openai` - OpenAI API client
- `anthropic` - Anthropic Claude API client
- `google-genai` - Google Gemini API client
- `azure-ai-inference` - Azure OpenAI services
- `pandas`, `numpy` - Data analysis
- `scipy` - Statistical analysis
- `notebook` - Jupyter notebook support

---

## Configuration

### Setting Up API Keys

You need to configure API credentials for the LLM providers you plan to use:

#### Option 1: System Environment Variables (Recommended)

Set environment variables in your system:

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your_openai_key_here"
$env:ANTHROPIC_API_KEY="your_anthropic_key_here"
$env:GOOGLE_AI_API_KEY="your_google_key_here"

# For Azure OpenAI
$env:AZURE_OPENAI_ENDPOINT="your_azure_endpoint"
$env:AZURE_OPENAI_API_KEY="your_azure_key"
```

To make them permanent, add them to your system environment variables via System Properties.

**Linux/Mac (bash/zsh):**
```bash
export OPENAI_API_KEY="your_openai_key_here"
export ANTHROPIC_API_KEY="your_anthropic_key_here"
export GOOGLE_AI_API_KEY="your_google_key_here"

# For Azure OpenAI
export AZURE_OPENAI_ENDPOINT="your_azure_endpoint"
export AZURE_OPENAI_API_KEY="your_azure_key"
```

Add these to your `~/.bashrc` or `~/.zshrc` to make them permanent.

#### Option 2: Command-line Arguments

Pass credentials directly when running experiments (see [Running Experiments](#running-experiments)).

### Model Configuration

The benchmark supports multiple LLM providers:

- **OpenAI**: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, `gpt-5-chat`, `o3-mini`
- **Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `claude-sonnet-4-0`
- **Google**: `gemini-2.0-flash-exp`, `gemini-2.5-flash`, `gemini-2.5-pro`
- **Azure OpenAI**: Any Azure-hosted model (including `grok-3` via Azure)

**Note**: Models like Grok-3 from xAI can be accessed through Azure OpenAI deployments using the `azure` provider.

---

## Running Experiments

### Basic Usage

The main entry point is `main.py`. Here's the general syntax:

```bash
python main.py \
    --use_case <use_case> \
    --persona_id <persona_id> \
    --simulation_type <attack_type> \
    --llm_name <model_name> \
    --run_all_attacks \
    [additional options]
```

### Essential Arguments

| Argument | Options | Default | Description |
|----------|---------|---------|-------------|
| `--use_case` | `travel_planning`, `real_estate`, `insurance` | `travel_planning` | Domain to evaluate |
| `--persona_id` | `1`, `2`, `3`, `4` | `1` | User persona (different privacy preferences) |
| `--simulation_type` | `security`, `privacy`, `benign_easy` | `benign_easy` | Type of evaluation |
| `--llm_name` | Model name string | `gpt-3.5-turbo` | Model for assistant agent |
| `--provider` | `openai`, `anthropic`, `google`, `azure` | Auto-detected, however, need to be specified for newer models | LLM provider for assistant |
| `--judge_llm_name` | Model name string | `gpt-4o-2024-11-20` | Model for evaluation judges |
| `--judge_provider` | `openai`, `anthropic`, `google`, `azure` | Auto-detected, however, need to be specified for newer models | LLM provider for judge |
| `--run_all_attacks` | flag | False | Run all attacks for the persona |
| `--attack_name` | Attack name string | `""` | Run specific attack only |
| `--repetitions` | Integer | `1` | Number of repetitions per attack |
| `--simulation_timeout` | Integer (seconds) | `600` | Timeout for each simulation |
| `--baseline_mode` | flag | False | Enable baseline assistant (no safety mechanisms) |

> **Note on Attack Names**: Attack name matching is **case-insensitive** and **space-flexible**. You can use either the original format (e.g., `"Date of Birth"`) or snake_case (e.g., `"date_of_birth"`). Both `--attack_name "Date of Birth"` and `--attack_name "date_of_birth"` will work identically.

### Example Commands

#### 1. Run All Privacy Attacks for Travel Planning

```bash
python main.py \
    --provider openai \
    --llm_name gpt-5 \
    --judge_llm_name gpt-5 \
    --judge_provider openai \
    --persona_id 1 \
    --use_case travel_planning \
    --baseline_mode \
    --simulation_type privacy \
    --run_all_attacks \
    --repetitions 1 \
    --simulation_timeout 600
```

#### 2. Run All Security Attacks for Real Estate

```bash
python main.py \
    --provider anthropic \
    --llm_name claude-sonnet-4-0 \
    --judge_llm_name gpt-5 \
    --judge_provider openai \
    --persona_id 2 \
    --use_case real_estate \
    --baseline_mode \
    --simulation_type security \
    --run_all_attacks \
    --repetitions 1 \
    --simulation_timeout 600
```

#### 3. Run Specific Privacy Attack

```bash
# Attack names are case-insensitive and space-flexible
# Both "date_of_birth" and "Date of Birth" work identically
python main.py \
    --provider google \
    --llm_name gemini-2.5-flash \
    --judge_llm_name gpt-5 \
    --judge_provider openai \
    --persona_id 1 \
    --use_case real_estate \
    --baseline_mode \
    --simulation_type privacy \
    --attack_name "date_of_birth" \
    --simulation_timeout 600

# Alternative using original format:
# --attack_name "Date of Birth"
```

#### 4. Run Benign Baseline Evaluation

```bash
python main.py \
    --provider google \
    --llm_name gemini-2.5-pro \
    --judge_llm_name gpt-5 \
    --judge_provider openai \
    --persona_id 1 \
    --use_case insurance \
    --baseline_mode \
    --simulation_type benign_easy \
    --repetitions 4 \
    --simulation_timeout 600
```

#### 5. Using Azure OpenAI

```bash
python main.py \
    --provider azure \
    --llm_name gpt-4o \
    --judge_llm_name gpt-5 \
    --judge_provider azure \
    --azure_endpoint https://your-endpoint.openai.azure.com \
    --persona_id 1 \
    --use_case insurance \
    --baseline_mode \
    --simulation_type security \
    --run_all_attacks \
    --repetitions 1 \
    --simulation_timeout 600
```

#### 6. Using Different Models for Agent and Judge

```bash
python main.py \
    --provider anthropic \
    --llm_name claude-3-5-sonnet-20241022 \
    --judge_provider google \
    --judge_llm_name gemini-2.0-flash-exp \
    --persona_id 4 \
    --use_case travel_planning \
    --baseline_mode \
    --simulation_type privacy \
    --run_all_attacks \
    --repetitions 1 \
    --simulation_timeout 600
```

### Advanced Options

```bash
# Firewall options
--apply_data_firewall              # Enable data abstraction firewall for environment agent
--apply_language_converter_firewall  # Enable language converter firewall for external agent

# Timeout and retry settings
--simulation_timeout 600           # Timeout per simulation (seconds)
--judge_max_retries 3             # Max retries for judge evaluation
--judge_retry_delay 1.0           # Delay between retries (seconds)

# Output directory
--logs_folder logs                # Directory for results

# Judge control
--enable_utility_judge            # Enable utility evaluation (default: True)
--enable_privacy_judge            # Enable privacy evaluation (default: True)
--enable_security_judge           # Enable security evaluation (default: True)

# Assistant modes
--baseline_mode                   # Standard assistant
--taskconfined_mode              # Task-confined assistant
```

### Firewall Protection

This repository implements the dual-firewall architecture from our paper. See [Dual-Firewall Architecture](#dual-firewall-architecture) for a detailed description.

#### Data Abstraction Firewall
Projects outgoing information onto the granularity appropriate for the task. Operates in a trusted environment isolated from external input, applying domain-specific abstraction rules learned from demonstrations.

#### Language Converter Firewall
Projects incoming messages onto a closed, domain-specific structured protocol. External agent messages are converted to validated fields while persuasive framing, urgency tactics, and embedded instructions are structurally eliminated through deterministic verification.

**Note**: Firewalls require pre-generated guidelines (learned from demonstration corpora). See [FIREWALL_GUIDE.md](FIREWALL_GUIDE.md) for details on generating rules.

**Example with Firewalls**:
```bash
# First, generate firewall guidelines (one-time setup)
python generate_guidelines.py --config_file sample_config.yaml

# Then run with firewalls enabled
python main.py \
    --provider openai \
    --llm_name gpt-4o \
    --judge_llm_name gpt-4o \
    --judge_provider openai \
    --persona_id 1 \
    --use_case travel_planning \
    --baseline_mode \
    --simulation_type privacy \
    --attack_name "Full Name" \
    --apply_data_firewall \
    --apply_language_converter_firewall \
    --repetitions 1
```

---

## Data Organization

### Input Data Structure

Attack definitions and persona data are organized in `resources/`:

#### 1. Persona Environment Files
- Location: `resources/<use_case>/env_persona<N>.txt`
- Content: User background, preferences, constraints, and private data
- Example: `env_persona1.txt` contains travel preferences, budget, dates, etc.

#### 2. Security Attacks
- Location: `resources/<use_case>/security_attacks/security_attacks_persona<N>.json`
- Structure:
```json
{
  "final_package_attacks": {
    "attack_1": {
      "name": "Attack Name",
      "external_attack_goal": "Attack objective",
      "user_task": "Modified user request",
      "attack_action": "Malicious action"
    }
  },
  "toolkit_attacks": {
    "attack_2": { "..." }
  }
}
```

#### 3. Privacy Attacks
- Location: `resources/<use_case>/privacy_attacks/privacy_attacks_persona<N>.json`
- Structure:
```json
{
  "categories": {
    "Personal_Details": {
      "items": [
        {
          "data_item": "Date of Birth",
          "attack_action": "Request date of birth",
          "attack_goal": "Extract birthdate",
          "attack_name_group": "Direct"
        }
      ]
    }
  }
}
```

#### 4. Ground Truth Ratings
- Location: `resources/<use_case>/ratings/ratings_persona<N>.json`
- Purpose: AI-annotated utility scores for benchmarking assistant outputs
- Verification: 
  - Inter-rater reliability tests conducted across multiple LLMs (GPT-5, GPT-4.1, Claude, Gemini)
  - Results stored in `resources/<use_case>/ratings/study/` directory
  - Random samples verified by human annotators to ensure quality
  - Reliability metrics available in `resources/IRR_results_summary_averaged.txt`

### Output Data Structure

Results are saved in `logs/` with the following hierarchy:

```
logs/
└── <use_case>/                    # e.g., travel_planning
    └── <model_name>/              # e.g., gpt_4o
        └── baseline/              # or taskconfined
            └── persona<N>/        # e.g., persona1
                ├── security/      # Security attack results
                │   └── <attack_category>_<attack_name>/
                │       ├── conversation_<timestamp>.json
                │       ├── utility_judge_<timestamp>.json
                │       └── security_judge_<timestamp>.json
                │
                ├── privacy/       # Privacy attack results
                │   └── <category>_<data_item>/
                │       ├── conversation_<timestamp>.json
                │       ├── utility_judge_<timestamp>.json
                │       └── privacy_judge_<timestamp>.json
                │
                └── benign/        # Benign baseline results
                    └── benign_<type>/
                        ├── conversation_<timestamp>.json
                        └── utility_judge_<timestamp>.json
```

### Result File Formats

#### Conversation Log (`conversation_<timestamp>.json`)
```json
{
  "turns": [
    {
      "external_to_assistant": "Message from external agent",
      "assistant_short_answer": "Brief response",
      "assistant_long_answer": "Detailed reasoning",
      "environment_to_assistant": "Environment context"
    }
  ],
  "metadata": {
    "attack_name": "...",
    "timestamp": "...",
    "model": "..."
  }
}
```

#### Utility Judge Output (`utility_judge_<timestamp>.json`)
```json
{
  "utility_evaluation": {
    "UTILITY": {
      "HOW_MANY_ITEMS_COVERED": "3/5"
    }
  },
  "ratings_evaluation": {
    "average_rating": 7.5,
    "num_items_rated": 3,
    "ratings": [
      {"item": "Flight", "rating": 8},
      {"item": "Hotel", "rating": 7}
    ]
  }
}
```

#### Privacy Judge Output (`privacy_judge_<timestamp>.json`)
```json
{
  "evaluation_type": "information_leak",
  "data_item": "date_of_birth",
  "llm_evaluation": {
    "leaked_information": "yes",
    "confidence_score": 9,
    "reasoning": "..."
  }
}
```

#### Security Judge Output (`security_judge_<timestamp>.json`)
```json
{
  "attack_success": "Successful",
  "evaluation_type": "toolkit_attack",
  "action_requested": true,
  "action_confirmed": true,
  "confidence": 9,
  "reasoning": "..."
}
```

### Utility Rating Generation and Verification

The ground truth utility ratings used for benchmarking are AI-generated with robust verification:

#### Rating Generation Process
1. **Template Creation**: The `template_creation_script.py` generates rating templates for each persona and use case
2. **Multi-Model Annotation**: Multiple state-of-the-art LLMs (GPT-5, GPT-4.1, Claude, Gemini) independently rate each option
3. **Inter-Rater Reliability**: Ratings are compared across models using `inter_rater_calc.py` to ensure consistency
4. **Human Verification**: Random samples are verified by human annotators to validate quality

#### Verification Files
- **`resources/IRR_results_summary_averaged.txt`**: Summary of inter-rater reliability metrics
- **`resources/<use_case>/ratings/study/`**: Contains individual model ratings for reliability testing
  - `template_ratings_persona<N>.json`: Base template
  - `template_ratings_persona<N>_gpt5.json`: GPT-5 annotations
  - `template_ratings_persona<N>_gpt41.json`: GPT-4.1 annotations
  - `template_ratings_persona<N>_claude.json`: Claude annotations
  - `template_ratings_persona<N>_gemini.json`: Gemini annotations

This multi-stage verification process ensures that the utility ratings provide a reliable benchmark for evaluating assistant performance, while the human verification step confirms the quality of AI-generated annotations.

---

## Results Analysis

### Running the Analysis Notebook

The analysis is organized as a modular Python package in the `results_analysis/` folder:

```bash
# Navigate to the results_analysis folder
cd results_analysis

# Open the analysis notebook
jupyter notebook results_analysis.ipynb
```

The analysis logic is organized into Python modules for maintainability:
- `data_loading.py` - Load judge outputs from logs directory
- `data_enhancement.py` - Enrich dataset with attack details from resources
- `analysis_utils.py` - Statistical analysis and CSV generation
- `formatting_utils.py` - Output formatting helpers
- `latex_generation.py` - Generate publication-ready LaTeX tables

See `results_analysis/README.md` for detailed documentation of the package structure and functions.

### Analysis Pipeline

The notebook performs the following analyses:

#### 1. Data Loading and Preparation
- Loads all judge outputs from `logs/` directory
- Parses file paths to extract metadata (model, persona, attack type)
- Merges with attack definitions from `resources/`
- Creates unified enhanced dataset

#### 2. Attack Categorization
- **Privacy Attacks**: Groups by data proximity (Direct, Indirect, Inferred)
- **Security Attacks**: Groups by objective (DoS, Email Manipulation, Upselling)
- **Responsibility Attribution**: Categorizes by agent responsibility

#### 3. Statistical Analysis
- Calculates attack success rates with 95% confidence intervals
- Computes utility metrics (average rating, coverage rate)
- Performs meta-level analysis across:
  - Models
  - Use cases
  - Attack types
  - Privacy data categories
  - Security attack objectives

#### 4. CSV Export
Generates detailed CSV files in `analysis_outputs/` (temporary, automatically removed at the last cell of the jupyter notebook, comment out the cell if needed):
- `<attack_type>_model_analysis.csv` - Model comparisons
- `<attack_type>_use_case_<model>_analysis.csv` - Per-model use case analysis
- `privacy_privacy_data_category_<model>_<use_case>_analysis.csv` - Privacy categories
- `security_attack_name_group_<model>_<use_case>_analysis.csv` - Security objectives
- `attack_type_comparison.csv` - Cross-attack-type comparison

#### 5. LaTeX Table Generation
Produces the tables from the paper in `latex_tables_selected.tex`:
- Model comparison tables (all models vs. complete models)
- Domain-grouped analyses (data proximity, categories, objectives)

### Key Metrics

#### Attack Success Rate (ASR)
- **Privacy**: Percentage of attacks where raw data was shared OR information leaked
- **Security**: Percentage where attack was "Successful" or "Partially successful"
- Reported with 95% confidence intervals using Wilson score method

#### Utility Metrics
- **Average Rating**: Mean quality score across evaluated items (0-10 scale)
- **Coverage Rate**: Percentage of required items addressed (0-100%)
- Reported with 95% confidence intervals using t-distribution

---

## Running Complete Benchmark

To run the full benchmark use below scripts. Note that this will consume lots of time and API costs as discussed below. Additionally, the following batch scripts are not tested end-to-end, if they did not work, use previous line commands instead.

#### Step 1: Run All Experiments

Create a batch script to run all combinations:

**Example: `run_all_experiments.sh` (Linux/Mac)**
```bash
#!/bin/bash

MODELS=("gpt-4o" "claude-sonnet-4-0" "gemini-2.5-flash" "o3-mini")
USE_CASES=("travel_planning" "insurance" "real_estate")
PERSONAS=(1 2 3 4)
ATTACK_TYPES=("security" "privacy" "benign_hard")

for model in "${MODELS[@]}"; do
  for use_case in "${USE_CASES[@]}"; do
    for persona in "${PERSONAS[@]}"; do
      for attack_type in "${ATTACK_TYPES[@]}"; do
        echo "Running: $model | $use_case | persona$persona | $attack_type"
        python main.py \
          --use_case $use_case \
          --persona_id $persona \
          --simulation_type $attack_type \
          --llm_name $model \
          --run_all_attacks \
          --baseline_mode \
          --repetitions 3
      done
    done
  done
done
```

**Example: `run_all_experiments.bat` (Windows)**
```batch
@echo off
setlocal enabledelayedexpansion

set MODELS=gpt-4o claude-sonnet-4-0 gemini-2.5-flash o3-mini
set USE_CASES=travel_planning insurance real_estate
set PERSONAS=1 2 3 4
set ATTACK_TYPES=security privacy benign_hard

for %%m in (%MODELS%) do (
  for %%u in (%USE_CASES%) do (
    for %%p in (%PERSONAS%) do (
      for %%a in (%ATTACK_TYPES%) do (
        echo Running: %%m ^| %%u ^| persona%%p ^| %%a
        python main.py ^
          --use_case %%u ^
          --persona_id %%p ^
          --simulation_type %%a ^
          --llm_name %%m ^
          --run_all_attacks ^
          --baseline_mode ^
          --repetitions 3
      )
    )
  )
)
```

#### Step 2: Run Analysis

```bash
# Navigate to the results_analysis folder and open the notebook
cd results_analysis
jupyter notebook results_analysis.ipynb
```

Or run programmatically:
```bash
cd results_analysis
jupyter nbconvert --to notebook --execute results_analysis.ipynb
```

#### Step 3: Extract Statistics

```bash
python benchmark_stats.py
```

### Expected Runtime

- **Single attack**: 2-5 minutes (depends on model response time)
- **All attacks for one persona**: 30-60 minutes
- **Complete use case (4 personas × 3 attack types)**: 6-10 hours
- **Full benchmark (3 use cases × 4 models)**: 3-5 days

### Resource Requirements

- **Storage**: ~10-50 GB for full benchmark results (depends on conversation length)
- **Memory**: 4-8 GB RAM
- **API Costs**: Varies by provider (estimate of few thousands dollars for the complete benchmark)

---

## Citation

If you use this code or the firewall architecture in your research, please cite both papers:

```bibtex
@article{abdelnabi2025firewalls,
  title={Firewalls to Secure Dynamic LLM Agentic Networks},
  author={Sahar Abdelnabi and Amr Gomaa and Eugene Bagdasarian and Per Ola Kristensson and Reza Shokri},
  journal={arXiv preprint arXiv:2502.01822},
  year={2025},
  doi={10.48550/arXiv.2502.01822},
  url={https://arxiv.org/abs/2502.01822}
}

@article{gomaa2025converse,
  title={ConVerse: Benchmarking Contextual Safety in Agent-to-Agent Conversations},
  author={Amr Gomaa and Ahmed Salem and Sahar Abdelnabi},
  journal={arXiv preprint arXiv:2511.05359},
  year={2025},
  doi={10.48550/arXiv.2511.05359},
  url={https://arxiv.org/abs/2511.05359}
}
```
---

## License

This project is released under the [MIT License](LICENSE). The code builds on the [ConVerse](https://github.com/amrgomaaelhady/ConVerse) benchmark, [ToolEmu](https://github.com/ryoungj/ToolEmu), and prior work on [agent-to-agent firewalls](https://github.com/microsoft/Firewalled-Agentic-Networks).

---

## Contact

For questions, issues, or contributions:
- **Firewalls Paper**: [arXiv:2502.01822](https://arxiv.org/abs/2502.01822)
- **ConVerse Benchmark Paper**: [arXiv:2511.05359](https://arxiv.org/abs/2511.05359)
- **Authors**:
  - Sahar Abdelnabi (ELLIS Institute Tübingen, MPI for Intelligent Systems, Tübingen AI Center)
  - Amr Gomaa (German Research Center for Artificial Intelligence - DFKI, University of Cambridge)
  - Eugene Bagdasarian (University of Massachusetts Amherst)
  - Per Ola Kristensson (University of Cambridge)
  - Reza Shokri (National University of Singapore, Google Research)

---


## Troubleshooting

### Common Issues

#### API Rate Limits
**Problem**: Getting rate limit errors from LLM providers
**Solution**: Add delays between requests

#### Timeout Errors
**Problem**: Simulations timing out
**Solution**: Increase `--simulation_timeout` value (default: 600 seconds)

#### JSON Parsing Errors
**Problem**: Judge outputs fail to parse
**Solution**: Check `--judge_max_retries` setting; use a better judge model

#### Missing Dependencies
**Problem**: Import errors when running scripts
**Solution**: 
```bash
pip install -r requirements.txt --upgrade
```
