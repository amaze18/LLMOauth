# Claude API Authentication & Inference Demo (2026)

This repository provides a streamlined setup for authenticating with Anthropic's Claude API using an **OAuth Token (`sk-ant-oat01-`)** derived from an active Claude.ai Pro or Max subscription. It includes script automation for Linux/WSL and clear manual steps for native Windows environments to handle system packages, node dependencies, and multi-model LLM inferences.

## Repository Structure

As shown in the project workspace:

* `terminal_cmds.py`: Automated environment setup script (optimized for Linux/WSL).
* `llm_infer.py`: Python script demonstrating inference calls to multiple Claude models.
* `requirements.txt`: Python package dependencies.
* `README.md`: Setup and execution guide.

---

## Getting Started

### 1. Clone the Repository (Common Step) 

Open your terminal (WSL, Bash, PowerShell, or CMD) based on which Operating System you are using and clone this repository:

```bash
git clone <your-repository-url>
cd <repository-folder-name>
```

## 2. Environment Setup & Authentication ( Option A or B ) 

Choose the section below that matches your operating system.

### Option A: Linux or Windows Subsystem for Linux (WSL)

If you are using Linux or WSL, the setup is entirely automated. Run the script to install Node.js, Python packages, the Claude CLI, and launch the browser authentication:

```bash
python terminal_cmds.py
```

### Option B: Native Windows (PowerShell or CMD)

Because native Windows uses different package managers, follow these quick manual steps.

#### Install Node.js

Download and install Node.js (v20+) from the official website:

https://nodejs.org

#### Install Python Dependencies

```powershell
pip install -r requirements.txt
```

#### Install the Claude Code CLI Globally

```powershell
npm install -g @anthropic-ai/claude-code
```

#### Trigger the OAuth Flow

```powershell
claude setup-token
```

## 3. Complete the OAuth Authentication (All Platforms) (Common Step ) 

The terminal will trigger a browser window or generate an authentication link.

1. Sign in using the Claude.ai account tied to your Pro or Max subscription.
2. Complete the authorization flow.
3. Once authorized, the terminal will output your unique personal OAuth token beginning with:

```text
sk-ant-oat01-...
```

## 4. Configure Your Environment Variables  (Common Step ) 

Create a file named `.env` in the root directory of this project.

### Linux / WSL

```bash
touch .env
```

### Windows (PowerShell)

```powershell
New-Item .env
```

Open the `.env` file in your preferred text editor and paste your token exactly like this:

```env
ANTHROPIC_API_KEY=sk-ant-oat01-your-actual-oauth-token-here
```

> ⚠️ **Security Warning:** Never commit the `.env` file to version control. It contains access credentials to your personal subscription account.

---

# 5. Running Inference Calls  (Common Step ) 

Once your `.env` file is configured, you can run the multi-model inference script to test the setup.

The script sequentially routes targeted prompts across multiple Claude models.

```bash
python llm_infer.py
```

## Models Demonstrated

### Claude 3.5 Haiku

Utilized for lightweight data extraction and fast structural formatting (JSON).

### Claude 3.5 Sonnet

Executed for complex programming logic and code generation.

### Claude 3 Opus

Deployed for high-level technical reasoning and architectural strategy questions.
