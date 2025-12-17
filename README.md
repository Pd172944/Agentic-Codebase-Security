
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

