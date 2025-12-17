
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

### Command-Line Interface specific for Green Agent run in Agentbeats

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the env
source venv/bin/activate

# Install dependencies, when you run there may be others based on needs of agentbeats (ie Earthshaker, Python versioning, etc.)
pip install -r requirements.txt

# Configure API keys, only need one but can put up to 3
cp .env.example .env
# Edit .env with your API keys

# Run evaluation - for cloudflared see below
python src/main.py


# Cloudflared to config on agentbeats
cloudflared tunnel --url http://localhost:8010

#in separate terminal run
export CLOUDRUN_HOST=<cloudflared url from other terminal> export HTTPS_ENABLED=true export AGENT_PORT=8010 export PORT=8010 venv/bin/agentbeats run_ctrl


```



