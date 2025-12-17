
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


# same steps for virtual environment, see branch green
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Run evaluation for cloudflared see below
python src/main.py



# Cloudflared to config on agentbeats
cloudflared tunnel --url http://localhost:8020

#in separate terminal run
export CLOUDRUN_HOST=<cloudflared url from other terminal> export HTTPS_ENABLED=true export AGENT_PORT=8020 export PORT=8020 venv/bin/agentbeats run_ctrl
```



## Dataset

Uses the [CyberNative/Code_Vulnerability_Security_DPO](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO) dataset from HuggingFace:
- 4,660 total examples across 11 languages
- Filtered to Python-only for consistency
- Paired vulnerable/fixed code samples

