# AI Agent Security Vulnerability Evaluation Framework

Evaluates GPT-4o, Claude Sonnet 4, and Gemini 2.0 Flash on fixing Python code vulnerabilities from insecure codebases
## Features

- **Real-time Web Interface** with live evaluation updates
- **A2A Protocol Integration** for standardized agent communication
- **Demo Mode** for testing without API keys
- **Python-focused** to ensure consistent comparisons
- **5-dimensional scoring** with LLM evaluation, static analysis, and execution testing


## DEMO (Green Agent)
Our demo shows a dry run of the system, demonstrating how PRs are auto-generated, plots of security fixes and performance, cost, time to execute, and the interface of the platform.


https://github.com/user-attachments/assets/c2a8df79-8191-43aa-86d1-43bcb1c5a037




## Quick Start

### Web Application (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Run web app
python run_webapp.py

# Open http://localhost:8000 in your browser
# Click "Start Demo" to see it in action (no API keys needed!)
```

### Command-Line Interface for agentbeats

```bash
# Install dependencies in both terminals, create a virtual environment
pip install -r requirements.txt

# in terminal 1 run cloudflated tunnel command with flag --8010

# in terminal 2 run cloudflated tunnel command with flag --8020

# in terminal 3, 4 export CLOUDRUN_HOST, HTTPS_ENABLED, PORT, AGENT_PORT and then venv/bin/agentbeats run_ctrl


# Configure API keys
cp .env.example .env
# Edit .env with your API keys using vim or other editor

# Run evaluation
python src/main.py
```

## Documentation

## Evaluation Metrics

1. **Similarity Score (0-10)**: LLM-based comparison to reference fix
2. **Vulnerability Fixed**: Boolean assessment of security fix
3. **Static Analysis**: Bandit-based vulnerability detection (Python)
4. **Code Execution**: Syntax and compilation testing
5. **Performance**: Time, tokens, cost tracking

## Instructions to reproduce evaluation results
Due to very limited resources for us, including financial strain for token purchases, we were only able to run on 100 samples once with a different CoT reasoning structure that was iterated upon. Our report (irrelevant for those browsing this repo for fun) hinges on the availability of tokens to run 100 samples many times so that you can average out the results and look at differing CoT structures. If we had more API credits available, we would have also run ablation studies to verify the results on 100 samples. As for now, the results presented in our report are accurate from a prior run on 100 samples.



**Quick Start:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY="sk-..."

# Run assessment
python src/launcher.py --agent gpt --samples 3
```

**What's the Green Agent?**
- ✅ **Assessment Manager**: Coordinates vulnerability testing
- ✅ **Uses Existing Agents**: Tests GPTAgent, ClaudeAgent, GeminiAgent directly
- ✅ **Comprehensive Metrics**: Similarity, security, execution testing
- ✅ **Simple to Run**: One command execution


## Dataset

Uses the [CyberNative/Code_Vulnerability_Security_DPO](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO) dataset from HuggingFace:
- 4,660 total examples across 11 languages
- Filtered to Python-only for consistency
- Paired vulnerable/fixed code samples
