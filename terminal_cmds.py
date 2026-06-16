import os
import subprocess
import sys

def run_cmd(command, shell=True):
    print(f"\n[EXEC] {command}")
    subprocess.run(command, shell=shell, check=True)

def setup_environment():
    print("=== Starting Environment Setup ===")
    try:
        # 1. Install Python requirements
        print("\n--- Installing Python Dependencies ---")
        run_cmd("pip install -r requirements.txt")
        
        # 2. Install Node.js (Assumes Debian/Ubuntu/WSL/EC2)
        print("\n--- Checking Node.js Installation ---")
        node_check = subprocess.run("command -v node", shell=True, capture_output=True)
        if node_check.returncode != 0:
            print("Node.js not found. Installing via NodeSource...")
            run_cmd("curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -")
            run_cmd("sudo apt-get install -y nodejs")
        else:
            print("Node.js is already installed.")

        # 3. Install Claude Code CLI globally
        print("\n--- Installing Claude CLI ---")
        run_cmd("sudo npm install -g @anthropic-ai/claude-code")

        # 4. Initiate the OAuth Flow
        print("\n=== OAUTH AUTHENTICATION ===")
        print("The browser will now open (or provide a link) for Claude.ai authentication.")
        print("Once authenticated, copy the token starting with 'sk-ant-oat01-'")
        print("Create a file named '.env' in this folder and add: ANTHROPIC_API_KEY=your_token_here\n")
        
        # This will pause the script while the user interacts with the browser
        run_cmd("claude setup-token")

        print("\n=== Setup Complete! ===")
        print("Don't forget to paste your token into the .env file before running llm_infer.py")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_environment()
