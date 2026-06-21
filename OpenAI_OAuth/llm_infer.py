import subprocess

def call_codex_cli(prompt):
    """Passes a prompt to the OpenAI Codex CLI using the local OAuth session."""
    print(f"--- Sending request to ChatGPT/Codex ---")
    try:
        # The 'codex exec' command allows for non-interactive execution
        result = subprocess.run(
            ["codex", "exec", prompt],
            capture_output=True,
            text=True,
            check=True
        )
        print("Response:\n", result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing Codex CLI: {e.stderr}")

if __name__ == "__main__":
    print("Testing OpenAI Inference via Local OAuth...")
    
    # Task 1: Data Extraction
    call_codex_cli("Extract the name, location, and role: Alice is a Data Scientist living in Seattle. Output JSON only.")
    
    # Task 2: Code Generation
    call_codex_cli("Write a Python dictionary comprehension to square numbers from 1 to 5. Output only the code.")
