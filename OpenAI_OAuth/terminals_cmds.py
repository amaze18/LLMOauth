import subprocess
import sys

def run_cmd(command, shell=True):
    print(f"\n[EXEC] {command}")
    subprocess.run(command, shell=shell, check=True)

def setup_openai_oauth():
    print("=== OpenAI Local Device OAuth Setup ===")
    
    try:
        # 1. Install the official OpenAI Codex CLI globally via npm
        print("\n--- Installing OpenAI Codex CLI ---")
        run_cmd("npm install -g @openai/codex")
        
        # 2. Trigger the Device Code login flow
        print("\n=== OAUTH AUTHENTICATION ===")
        print("The CLI will request a device code login.")
        print("1. Open the provided URL (e.g., https://auth.openai.com/codex/device) in your browser.")
        print("2. Enter the one-time code shown in the terminal.")
        print("3. Sign in with your ChatGPT Plus/Pro account.")
        
        # Using --device-auth forces the CLI to use the device code flow, 
        # avoiding issues with local browser callbacks in headless/WSL setups.
        run_cmd("codex login --device-auth")
        
        print("\n=== Setup Complete! ===")
        print("Tokens are securely saved in your system (typically ~/.codex/auth.json).")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_openai_oauth()
