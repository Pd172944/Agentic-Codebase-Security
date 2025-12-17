
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
## Instructions to reproduce evaluation results
Due to very limited resources for us, including financial strain for token purchases, we were only able to run on 100 samples once with a different CoT reasoning structure that was iterated upon. Our report (irrelevant for those browsing this repo for fun) hinges on the availability of tokens to run 100 samples many times so that you can average out the results and look at differing CoT structures. If we had more API credits available, we would have also run ablation studies to verify the results on 100 samples. As for now, the results presented in our report are accurate from a prior run on 100 samples.

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



