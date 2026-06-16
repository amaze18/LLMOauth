import json
import math
import os
import threading
import queue
import uuid
from flask import Flask, render_template, request, Response, jsonify, send_from_directory

from main import run_pipeline, calculate_house_footprint

DEFAULT_SETBACKS = {"vertical": 5, "horizontal": 15}

app = Flask(__name__)

# Global dictionary to hold feedback queues for active pipeline sessions
pipeline_sessions = {}

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/validate_plot', methods=['POST'])
def validate_plot():
    try:
        data = request.get_json()
        raw_coords = data.get('coords', [])
        sv = data.get('setback_vertical', DEFAULT_SETBACKS['vertical'])
        sh = data.get('setback_horizontal', DEFAULT_SETBACKS['horizontal'])
        
        if len(raw_coords) < 3:
            return jsonify({'error': 'Please specify at least 3 coordinates.'}), 400
            
        closed_coords = raw_coords + [raw_coords[0]]
        footprint = calculate_house_footprint(closed_coords, sv, sh)
        net_area = int(footprint.area)
        
        # Extract coordinates from the calculated footprint
        fx, fy = footprint.exterior.xy
        footprint_coords = list(zip(fx, fy))
        
        return jsonify({
            'success': True,
            'net_area': net_area,
            'footprint_coords': footprint_coords
        })
    except Exception as e:
        return jsonify({'error': f"Invalid polygon shape: {str(e)}"}), 400

@app.route('/api/submit_feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    session_id = data.get('session_id')
    feedback = data.get('feedback', '')
    
    if not session_id or session_id not in pipeline_sessions:
        return jsonify({'error': 'Invalid or expired session'}), 400
        
    # Put the feedback into the queue to resume the backend thread
    pipeline_sessions[session_id].put(feedback)
    return jsonify({'success': True})

@app.route('/api/run_pipeline')
def stream_pipeline():
    coords_param = request.args.get('coords')
    if not coords_param:
        return jsonify({'error': 'No coordinates provided'}), 400
        
    try:
        raw_coords = json.loads(coords_param)
        closed_coords = raw_coords + [raw_coords[0]]
    except Exception as e:
        return jsonify({'error': 'Invalid coordinates format'}), 400

    sv = int(request.args.get('sv', DEFAULT_SETBACKS['vertical']))
    sh = int(request.args.get('sh', DEFAULT_SETBACKS['horizontal']))
    sbc_rules = request.args.get('sbc', '')
    vastu_rules = request.args.get('vastu', '')
    vastu_rules_stage3 = request.args.get('vastu_stage3', '')
    setbacks = {"vertical": sv, "horizontal": sh}

    q = queue.Queue()
    feedback_queue = queue.Queue()
    session_id = str(uuid.uuid4())
    pipeline_sessions[session_id] = feedback_queue

    def step_callback(step_data):
        if "type" in step_data and step_data["type"] == "wait_for_feedback":
            q.put(step_data)
        else:
            q.put({"type": "step", "data": step_data})

    def run_thread():
        try:
            success, rooms, rooms_stage3, footprint, dxf_filename, telemetry = run_pipeline(closed_coords, callback=step_callback, feedback_queue=feedback_queue, setbacks=setbacks, custom_sbc_rules=sbc_rules, custom_vastu_rules=vastu_rules, custom_vastu_rules_stage3=vastu_rules_stage3)
            
            # Send final completion message
            final_data = {
                "success": success,
                "rooms": rooms,
                "rooms_stage3": rooms_stage3,
                "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None,
                "telemetry": telemetry
            }
            q.put({"type": "complete", "data": final_data})
        except Exception as e:
            import traceback
            error_msg = f"{e}\n{traceback.format_exc()}"
            print("PIPELINE EXCEPTION:", error_msg, flush=True)
            q.put({"type": "error", "message": error_msg})
        finally:
            q.put(None) # Signal termination
            if session_id in pipeline_sessions:
                del pipeline_sessions[session_id]

    threading.Thread(target=run_thread, daemon=True).start()

    def generate():
        # Send initial session ID
        yield f"data: {json.dumps({'type': 'session_init', 'session_id': session_id})}\n\n"
        
        while True:
            msg = q.get()
            if msg is None:
                break
            # Format as Server-Sent Event
            yield f"data: {json.dumps(msg)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/download/<filename>')
def download_dxf(filename):
    import tempfile
    dxf_dir = os.path.join(tempfile.gettempdir(), "dxf_outputs")
    return send_from_directory(dxf_dir, filename, as_attachment=True)

@app.route('/api/debug_env')
def debug_env():
    import os
    key = os.getenv("GROQ_API_KEY", "")
    return jsonify({
        "has_key": bool(key),
        "key_prefix": key[:4] if key else "",
        "key_length": len(key)
    })

@app.route('/api/test_groq')
def test_groq():
    import os, requests
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        return jsonify({"error": "No key"})
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.2
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=10)
        return jsonify({
            "status_code": r.status_code,
            "response": r.json() if r.status_code == 200 else r.text
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, threaded=True)
