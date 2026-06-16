import requests
import sys
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
AGENT_2_MODEL = "llama-3.3-70b-versatile"
USE_MLFLOW = os.getenv("USE_MLFLOW", "False").lower() == "true"

if USE_MLFLOW:
    import mlflow
    from openai import OpenAI
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("Vastu_Layout_Pipeline")
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY
    )

def call_agent_2_generic(prompt, telemetry, error_msg, step_name="unknown", iteration=0):
    prompt += "\n\nCRITICAL INSTRUCTION: Provide concise feedback. Do NOT suggest assigning markdown strings to variables. Do not suggest importing `markdown`. Focus purely on fixing the Z3 logic constraints and mathematical rules."
    trace_id = telemetry.get("trace_id", None)
    
    if USE_MLFLOW:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with mlflow.start_span(name=f"Agent 2 - {step_name}") as span:
                    span.set_attributes({
                        "agent_name": "Agent 2 (Mentor)",
                        "step": step_name,
                        "iteration": str(iteration),
                        "trace_id": str(trace_id)
                    })
                    
                    messages = [
                        {"role": "system", "content": "You are a senior technical mentor."},
                        {"role": "user", "content": prompt}
                    ]
                    span.set_inputs({"messages": messages})
                    
                    response = client.chat.completions.create(
                        model=AGENT_2_MODEL,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=8000
                    )
                    
                    text = response.choices[0].message.content.strip()
                    span.set_outputs({"response": text})
                    telemetry["agent2_tokens"] += response.usage.total_tokens
                    
                    enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
                    if enc == 'utf-8' and hasattr(sys, '__stdout__') and sys.__stdout__:
                        enc = getattr(sys.__stdout__, 'encoding', None) or 'utf-8'
                    safe_text = text.encode(enc, errors='replace').decode(enc)
                    print(f">>> Agent 2 Feedback:\n{safe_text}\n")
                    time.sleep(30) # Bleed TPM bucket
                    return text
            except Exception as e:
                print(f"\n  [ERROR] MLflow/OpenAI API Failed for Agent 2 (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return error_msg
        return error_msg
    else:
        payload = {
            "model": AGENT_2_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4
        }
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload, timeout=30)
                if r.status_code == 429:
                    print(f"\n  [ERROR] Rate Limit (429) for Agent 2. Waiting 35s to clear bucket...")
                    time.sleep(35)
                    continue
                r.raise_for_status()
                data = r.json()
                
                telemetry["agent2_tokens"] += data.get("usage", {}).get("total_tokens", 0)
                
                text = data["choices"][0]["message"]["content"].strip()
                enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
                if enc == 'utf-8' and hasattr(sys, '__stdout__') and sys.__stdout__:
                    enc = getattr(sys.__stdout__, 'encoding', None) or 'utf-8'
                safe_text = text.encode(enc, errors='replace').decode(enc)
                print(f">>> Agent 2 Feedback:\n{safe_text}\n")
                return text
            except Exception as e:
                print(f"\n  [ERROR] Groq API Failed for Agent 2 (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = 10
                    print(f"  [RETRY] Waiting {sleep_time}s before retrying...")
                    time.sleep(sleep_time)
                else:
                    return error_msg
        return error_msg

def call_agent_2_mentor(z3_error, agent_1_code, telemetry, iteration=0):
    print("\n" + "="*60)
    print(f"[STAGE 2] Agent 2 (Mentor) — Generating Feedback ({AGENT_2_MODEL})")
    print("="*60)
    
    prompt = f"""
    Agent 1 attempted to write a Z3 script to layout a Vastu-compliant house floor plan inside an L-shaped boundary, but it failed verification.
    
    ERROR: {z3_error}

    FAILED CODE:
    ```python
    {agent_1_code}
    ```
    
    Analyze the Z3 constraints. Tell Agent 1 exactly how to fix their solver logic or constraints to resolve this error. Do not write the full code, just explain the correction.
    """
    return call_agent_2_generic(prompt, telemetry, f"Fix your Z3 layout solver. Z3 error: {z3_error}", step_name="room_packing_feedback", iteration=iteration)

def call_agent_2_mentor_footprint(math_error, agent_1_code, telemetry, iteration=0):
    print("\n" + "="*60)
    print(f"[STAGE 1] Agent 2 (Mentor) — Generating Feedback ({AGENT_2_MODEL})")
    print("="*60)
    
    prompt = f"""
    Agent 1 attempted to write a Shapely Python script to calculate a footprint from a plot boundary, but it failed geometry verification.
    
    ERROR: {math_error}

    FAILED CODE:
    ```python
    {agent_1_code}
    ```
    
    Analyze the Shapely erosion logic. Tell Agent 1 exactly how to fix their geometry script to resolve this setback error. Do not write the full code, just explain the correction.
    """
    return call_agent_2_generic(prompt, telemetry, f"Fix your Shapely logic. Math error: {math_error}", step_name="calculate_footprint_feedback", iteration=iteration)

def call_agent_2_mentor_stage3(z3_error, agent_1_code, telemetry, iteration=0):
    print("\n" + "="*60)
    print(f"[STAGE 3] Agent 2 (Mentor) — Generating Feedback ({AGENT_2_MODEL})")
    print("="*60)
    
    prompt = f"""
    Agent 1 attempted to write a Z3 script to layout a Stage 3 Upper Floor house plan, but it failed verification.
    
    ERROR: {z3_error}

    FAILED CODE:
    ```python
    {agent_1_code}
    ```
    
    Analyze the Z3 constraints. Tell Agent 1 exactly how to fix their solver logic or constraints to resolve this error. Do not write the full code, just explain the correction.
    """
    return call_agent_2_generic(prompt, telemetry, f"Fix your Z3 layout solver. Z3 error: {z3_error}", step_name="room_packing_stage3_feedback", iteration=iteration)
