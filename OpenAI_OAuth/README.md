# OpenAI Local OAuth & Inference Demo (2026)

This repository provides an automated setup for authenticating with OpenAI's official **Codex CLI** using your existing ChatGPT Plus or Pro subscription. This utilizes the local OAuth device flow, bypassing the need for pay-per-token API keys (`sk-proj-...`).

## Repository Structure

## Repository contains:

*   `terminal_cmds.py`: Automated environment setup script for the Codex CLI.
*   `llm_infer.py`: Python wrapper script to execute programmatic inferences via the CLI.
*   `requirements.txt`: Empty (relies strictly on Node.js/CLI).
*   `README.md`: Setup and execution guide.

---

## Prerequisites
You must have **Node.js (v20+)** installed on your system. 

## Step 1: Environment Setup & Authentication

Run the setup script to install the Codex CLI globally and initiate the Device Code authentication flow. 

```bash
python terminal_cmds.py

```

## Authentication Steps

1. The terminal will provide a URL (e.g., `https://auth.openai.com/codex/device`) and a short device code.

2. Open the URL in your browser and enter the code.

3. Sign in with your ChatGPT account to authorize the CLI.

4. The CLI will automatically save the session tokens locally (`~/.codex/auth.json`).

> ⚠️ **Note:** Unlike standard API keys, you do not need to manually configure a `.env` file for this implementation. The Codex CLI manages token storage automatically.

## Step 2: Run Inference Calls

Once authenticated, execute the Python wrapper script. This script passes natural language prompts directly to the CLI execution engine.

```bash
python llm_infer.py
```
