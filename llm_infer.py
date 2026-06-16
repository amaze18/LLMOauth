import os
import anthropic
from dotenv import load_dotenv

# Load the OAuth token from the .env file into the environment
load_dotenv()

# Check if the token was properly set
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Error: ANTHROPIC_API_KEY not found.")
    print("Please run terminal_cmds.py first and paste your OAuth token into a .env file.")
    exit(1)

# Initialize the Anthropic client
# It automatically reads the ANTHROPIC_API_KEY from the environment
client = anthropic.Anthropic()

def call_claude(model_name, system_prompt, user_prompt, max_tokens=1024):
    """Generic function to handle calls to different Claude models."""
    print(f"\n--- Routing request to {model_name} ---")
    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        print(f"Response:\n{response.content[0].text}\n")
        return response.content[0].text
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    print("Testing Anthropic Inference via OAuth Token...")

    # Call 1: Claude 3.5 Haiku (Best for fast, lightweight tasks)
    call_claude(
        model_name="claude-3-5-haiku-20241022",
        system_prompt="You are a strict data formatter. Output only JSON.",
        user_prompt="Extract the name, location, and role: Alice is a Data Scientist living in Seattle."
    )

    # Call 2: Claude 3.5 Sonnet (Best for standard coding and complex tasks)
    call_claude(
        model_name="claude-3-5-sonnet-20241022",
        system_prompt="You are an expert Python engineer.",
        user_prompt="Write a one-line Python dictionary comprehension to square the numbers from 1 to 5."
    )
    
    # Call 3: Claude 3 Opus (Best for heavy reasoning and strategy)
    call_claude(
        model_name="claude-3-opus-20240229",
        system_prompt="You are a senior tech lead.",
        user_prompt="In two short sentences, why is it dangerous to commit a .env file to GitHub?"
    )
