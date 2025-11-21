# AI Agent Security Vulnerability Evaluation Framework

Evaluates GPT-4o, Claude Sonnet 4, and Gemini 2.0 Flash on fixing Python code vulnerabilities from the CyberNative dataset.

> **🟢 NEW: Green Agent Implementation!**  
> 👉 **[Quick Start Guide →](GREEN_AGENT_QUICKSTART.md)** | **[Run Now →](RUN_GREEN_AGENT.md)**  
> Green agent assessment system that evaluates your existing agents!

## Features

- **Real-time Web Interface** with live evaluation updates
- **A2A Protocol Integration** for standardized agent communication
- **Demo Mode** for testing without API keys
- **Python-focused** to ensure consistent comparisons
- **5-dimensional scoring** with LLM evaluation, static analysis, and execution testing

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

### Command-Line Interface

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Run evaluation
python src/main.py
```

## Documentation

- **[GREEN_AGENT_QUICKSTART.md](GREEN_AGENT_QUICKSTART.md)** - ⭐ NEW: Green agent quick start
- **[RUN_GREEN_AGENT.md](RUN_GREEN_AGENT.md)** - Step-by-step running guide
- **[WEBAPP_GUIDE.md](WEBAPP_GUIDE.md)** - Complete web app usage guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and structure
- **[USAGE.md](USAGE.md)** - CLI usage and configuration

## Evaluation Metrics

1. **Similarity Score (0-10)**: LLM-based comparison to reference fix
2. **Vulnerability Fixed**: Boolean assessment of security fix
3. **Static Analysis**: Bandit-based vulnerability detection (Python)
4. **Code Execution**: Syntax and compilation testing
5. **Performance**: Time, tokens, cost tracking

## A2A Protocol & AgentBeats

This framework implements the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/) for standardized AI agent communication. Agents can interoperate with other A2A-compliant systems.

### 🟢 Green Agent Assessment (NEW!)

We've implemented a **green agent** following the [AgentBeats "Agentify the Agent Assessment"](https://agentbeats.ai/blog/agentify-agent-assessment) blog post. The green agent assesses your existing agents' vulnerability fixing capabilities.

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

**Read More:** See [GREEN_AGENT_QUICKSTART.md](GREEN_AGENT_QUICKSTART.md) for complete details.

## Dataset

Uses the [CyberNative/Code_Vulnerability_Security_DPO](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO) dataset from HuggingFace:
- 4,660 total examples across 11 languages
- Filtered to Python-only for consistency
- Paired vulnerable/fixed code samples

## Results

Results are saved in `results/` directory:
- **CSV**: Detailed per-evaluation metrics
- **JSON**: Summary statistics by agent
