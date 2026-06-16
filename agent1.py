import requests
import time
from prompt import get_problem_statement
import os
import json
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
AGENT_1_MODEL = "llama-3.3-70b-versatile"
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

def call_agent_1_generic(user_msg, telemetry, feedback="", model_override=None, step_name="unknown", iteration=0):
    user_msg += "\n\nCRITICAL INSTRUCTION: Output ONLY valid python code. Do not assign markdown strings to variables. Do not include random python imports like `import markdown`. Write pure, executable Z3 python code."
    if feedback:
        user_msg += f"\n\n=== FEEDBACK FROM REVIEWERS (MENTOR / HUMAN ARCHITECT) ===\n{feedback}"

    model = model_override if model_override else AGENT_1_MODEL
    trace_id = telemetry.get("trace_id", None)
    
    if USE_MLFLOW:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with mlflow.start_span(name=f"Agent 1 - {step_name}") as span:
                    span.set_attributes({
                        "agent_name": "Agent 1 (Coder)",
                        "step": step_name,
                        "iteration": str(iteration),
                        "trace_id": str(trace_id)
                    })
                    
                    messages = [{"role": "user", "content": user_msg}]
                    span.set_inputs({"messages": messages})
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=8000
                    )
                    
                    output_text = response.choices[0].message.content.strip()
                    span.set_outputs({"response": output_text})
                    
                    telemetry["agent1_tokens"] += response.usage.total_tokens
                    time.sleep(30) # Bleed TPM bucket
                    return output_text
            except Exception as e:
                print(f"\n  [ERROR] MLflow/OpenAI API failed for Agent 1 (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return ""
        return ""
    else:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_msg}],
            "temperature": 0.2 
        }
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload, timeout=30)
                if r.status_code == 429:
                    print(f"\n  [ERROR] Rate Limit (429) for Agent 1. Waiting 35s to clear bucket...")
                    time.sleep(35)
                    continue
                r.raise_for_status()
                data = r.json()
                
                telemetry["agent1_tokens"] += data.get("usage", {}).get("total_tokens", 0)
                    
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"\n  [ERROR] Groq API failed for Agent 1 (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = 10
                    print(f"  [RETRY] Waiting {sleep_time}s before retrying...")
                    time.sleep(sleep_time)
                else:
                    return ""
        return ""

def call_agent_1(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, telemetry, feedback="", custom_vastu_rules="", iteration=0):
    print("\n" + "="*60)
    print(f"[STEP 1] Agent 1 (Coder) — Translating Vastu Constraints ({AGENT_1_MODEL})")
    print("="*60)

    user_msg = get_problem_statement(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, custom_vastu_rules)
    return call_agent_1_generic(user_msg, telemetry, feedback, step_name="room_packing", iteration=iteration)

def call_agent_1_footprint(plot_boundary, telemetry, feedback="", setback_vertical=5, setback_horizontal=15, custom_sbc_rules="", iteration=0):
    from prompt_stage1 import get_stage1_problem_statement
    print("\n" + "="*60)
    print(f"[STAGE 1] Agent 1 (Coder) — Calculating House Footprint ({AGENT_1_MODEL})")
    print("="*60)

    user_msg = get_stage1_problem_statement(plot_boundary, setback_vertical, setback_horizontal, custom_sbc_rules)
    return call_agent_1_generic(user_msg, telemetry, feedback, step_name="calculate_footprint", iteration=iteration)

def call_agent_1_stage3(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, ground_floor_rooms, telemetry, feedback="", custom_vastu_rules="", iteration=0):
    from prompt_stage3 import get_stage3_problem_statement
    print("\n" + "="*60)
    print(f"[STAGE 3] Agent 1 (Coder) — Upper Level Design ({AGENT_1_MODEL})")
    print("="*60)

    user_msg = get_stage3_problem_statement(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, ground_floor_rooms, custom_vastu_rules)
    return call_agent_1_generic(user_msg, telemetry, feedback, step_name="room_packing_stage3", iteration=iteration)
