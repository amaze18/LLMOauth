import os
import sys
import json
import re
import time
import contextlib
import io
import builtins
import queue
import json
import ast
import uuid
from shapely.geometry import Polygon, LineString, box, Point

from agent1 import call_agent_1
from agent2 import call_agent_2_mentor
from z3_verifier import run_z3_verification

DEFAULT_PLOT_BOUNDARY = [(0, 8), (0, 84), (75, 84), (75, 88), (80, 88), (80, 8), (75, 8), (75, 0), (35, 0), (35, 8), (0, 8)]

telemetry = {
    "start_time": time.time(),
    "agent1_tokens": 0,
    "agent2_tokens": 0,
    "iterations": 0,
    "final_area": 0
}

def print(*args, **kwargs):
    sep = kwargs.get('sep', ' ')
    msg = sep.join(str(arg) for arg in args)
    try:
        builtins.print(msg, **kwargs)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or 'utf-8'
        safe_msg = msg.encode(encoding, errors='replace').decode(encoding)
        builtins.print(safe_msg, **kwargs)

def calculate_house_footprint(plot_boundary, setback_vertical=5, setback_horizontal=15):
    base_poly = Polygon(plot_boundary)
    for i in range(len(plot_boundary)):
        p1 = plot_boundary[i]
        p2 = plot_boundary[(i + 1) % len(plot_boundary)]
        line = LineString([p1, p2])
        if p1[0] == p2[0]:
            # Vertical segment
            eraser = line.buffer(setback_vertical, cap_style=2)
        elif p1[1] == p2[1]:
            # Horizontal segment
            eraser = line.buffer(setback_horizontal, cap_style=2)
        else:
            eraser = line.buffer(setback_vertical, cap_style=2)
        base_poly = base_poly.difference(eraser)
    return base_poly

def get_exclusion_rectangles(footprint, XMIN, YMIN, XMAX, YMAX):
    # Unique rounded coordinates of exterior points
    x_coords = sorted(list(set([XMIN, XMAX] + [int(round(pt[0])) for pt in footprint.exterior.coords])))
    y_coords = sorted(list(set([YMIN, YMAX] + [int(round(pt[1])) for pt in footprint.exterior.coords])))
    
    exclusions = []
    for i in range(len(x_coords) - 1):
        for j in range(len(y_coords) - 1):
            x1, x2 = x_coords[i], x_coords[i+1]
            y1, y2 = y_coords[j], y_coords[j+1]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            pt = Point(cx, cy)
            if not footprint.contains(pt):
                exclusions.append((x1, y1, x2, y2))
    return exclusions

def get_footprint_corners(footprint):
    coords = list(footprint.exterior.coords)
    sw = min(coords, key=lambda p: (p[0], p[1]))
    se = max(coords, key=lambda p: (p[0], -p[1]))
    ne = max(coords, key=lambda p: (p[0], p[1]))
    nw = min(coords, key=lambda p: (p[0], -p[1]))
    return {
        "SW": (int(round(sw[0])), int(round(sw[1]))),
        "SE": (int(round(se[0])), int(round(se[1]))),
        "NE": (int(round(ne[0])), int(round(ne[1]))),
        "NW": (int(round(nw[0])), int(round(nw[1])))
    }

def extract_and_execute_code(raw_text):
    import re
    raw_text_clean = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    code_match = re.search(r'```(?:python)?(.*?)```', raw_text_clean, re.DOTALL | re.IGNORECASE)
    if not code_match:
        return None, "No python code block found in response", ""
    python_code = code_match.group(1).strip()
    
    stdout = io.StringIO()
    try:
        import z3
        import shapely.geometry
        from shapely.geometry import Polygon, LineString, box
        import json
        with contextlib.redirect_stdout(stdout):
            local_vars = {
                "__name__": "__main__",
                "shapely": shapely,
                "Polygon": Polygon,
                "LineString": LineString,
                "box": box,
                "json": json
            }
            exec(python_code, local_vars)
            
        output_str = stdout.getvalue().strip()
        json_match = re.search(r'\{.*\}', output_str, re.DOTALL)
        dict_str = json_match.group(0) if json_match else output_str
        
        try:
            data = json.loads(dict_str)
        except Exception as json_err:
            # Fallback: if the agent printed a python dict instead of valid JSON (single quotes)
            try:
                data = ast.literal_eval(dict_str)
            except Exception as ast_err:
                raise ValueError(f"Failed to parse as JSON ({json_err}) and failed python eval ({ast_err}). Output was: {dict_str}")
            
        if "coordinates" in data:
            return data["coordinates"], "SUCCESS", python_code
        elif "rooms" in data:
            return data["rooms"], "SUCCESS", python_code
        elif "solution" in data and data["solution"] and "rooms" in data["solution"]:
            return data["solution"]["rooms"], "SUCCESS", python_code
        else:
            raise ValueError("JSON output does not contain 'rooms' or 'coordinates' key.")
            
    except Exception as e:
        return None, f"Execution failed: {e}", python_code



def generate_rich_dxf(rooms, plot_boundary, footprint_poly=None, rooms_stage3=None):
    print("\n" + "="*60)
    print("[FINAL] Generating Output DXF File")
    print("="*60)
    try:
        import ezdxf
        from ezdxf.enums import TextEntityAlignment
        
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        doc.layers.add("PLOT_BOUNDARY", color=1)
        msp.add_lwpolyline(plot_boundary, dxfattribs={"layer": "PLOT_BOUNDARY", "closed": True, "const_width": 0.5})
        
        doc.layers.add("HOUSE_FOOTPRINT", color=4)
        if footprint_poly is None:
            footprint_poly = calculate_house_footprint(plot_boundary)
        
        if footprint_poly.geom_type in ['MultiPolygon', 'GeometryCollection']:
            polygons = [geom for geom in footprint_poly.geoms if geom.geom_type == 'Polygon']
            if polygons:
                footprint_poly = max(polygons, key=lambda a: a.area)
                
        house_footprint_coords = list(footprint_poly.exterior.coords)
        msp.add_lwpolyline(house_footprint_coords, dxfattribs={"layer": "HOUSE_FOOTPRINT", "closed": True, "const_width": 0.3})
        
        def annotate_boundary(coords, layer_name, color):
            for i in range(len(coords) - 1):
                p1 = coords[i]
                p2 = coords[i+1]
                txt_v = msp.add_text(f"({int(p1[0])}, {int(p1[1])})", dxfattribs={"layer": layer_name, "height": 1.2, "color": color})
                txt_v.set_placement((p1[0] + 0.5, p1[1] + 0.5))
                length = ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)**0.5
                mid_x = (p1[0] + p2[0]) / 2.0
                mid_y = (p1[1] + p2[1]) / 2.0
                txt_l = msp.add_text(f"{int(round(length))}'", dxfattribs={"layer": layer_name, "height": 1.5, "color": color})
                txt_l.set_placement((mid_x, mid_y), align=TextEntityAlignment.CENTER)
                
        annotate_boundary(plot_boundary, "PLOT_BOUNDARY", 1)
        annotate_boundary(house_footprint_coords, "HOUSE_FOOTPRINT", 4)
        
        room_colors = {
            "Living Room": 2,     
            "Dining Area": 3,     
            "Kitchen": 5,         
            "Master Bedroom": 6,  
            "Bedroom 2": 30,      
            "Bedroom 3": 40,      
            "Bathroom 1": 150,    
            "Bathroom 2": 150,    
            "Corridor": 8         
        }
        
        def draw_rooms(room_dict, prefix=""):
            for name, coords in room_dict.items():
                layer_name = f"{prefix}{name.replace(' ', '_').upper()}"
                color = room_colors.get(name, 7)
                if prefix == "FF_": color = 40  # Different color for First Floor to stand out
                
                doc.layers.add(layer_name, color=color)
                
                # coords is a flat list [x1, y1, x2, y2]
                x1, y1, x2, y2 = coords
                room_pts = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
                msp.add_lwpolyline(room_pts, dxfattribs={"layer": layer_name, "closed": True, "const_width": 0.8})
                
                from shapely.geometry import Polygon
                poly = Polygon(room_pts)
                cx, cy = poly.centroid.x, poly.centroid.y
                
                txt_entity = msp.add_text(
                    f"{prefix}{name}", 
                    dxfattribs={
                        "layer": layer_name, 
                        "height": 1.5,
                        "color": color
                    }
                )
                txt_entity.set_placement((cx, cy), align=TextEntityAlignment.CENTER)
                
                sqft = int(poly.area)
                size_str = f"{sqft} sqft"
                txt_size = msp.add_text(
                    size_str,
                    dxfattribs={
                        "layer": layer_name,
                        "height": 1.0,
                        "color": 8
                    }
                )
                txt_size.set_placement((cx, cy - 1.8), align=TextEntityAlignment.CENTER)
                
                coord_str = f"{len(room_pts)} vertices"
                txt_coord = msp.add_text(
                    coord_str,
                    dxfattribs={
                        "layer": layer_name,
                        "height": 0.8,
                        "color": 8
                    }
                )
                txt_coord.set_placement((cx, cy - 3.2), align=TextEntityAlignment.CENTER)
                
        if rooms:
            draw_rooms(rooms, "GF_")
        if rooms_stage3:
            draw_rooms(rooms_stage3, "FF_")
            
        import tempfile
        dxf_dir = os.path.join(tempfile.gettempdir(), "dxf_outputs")
        os.makedirs(dxf_dir, exist_ok=True)
        filename = os.path.join(dxf_dir, f"vastu_house_layout_{int(time.time())}.dxf")
        doc.saveas(filename)
        
        print(f"\n[DXF GENERATED SUCCESSFULLY]")
        print(f"  File Name:    {filename}")
        return filename
    except Exception as e:
        print(f"\n[ERROR] Failed to generate DXF: {e}")
        return ""

def run_pipeline(plot_boundary, max_iterations=5, callback=None, feedback_queue=None, setbacks=None, custom_sbc_rules="", custom_vastu_rules="", custom_vastu_rules_stage3=""):
    if plot_boundary is None:
        plot_boundary = DEFAULT_PLOT_BOUNDARY
    if setbacks is None:
        setbacks = {"vertical": 5, "horizontal": 15}
    
    sv = setbacks["vertical"]
    sh = setbacks["horizontal"]

    print("="*65)
    print(f"  Vastu-Compliant House Layout — Autonomous Agent Pipeline (DYNAMIC)")
    print("="*65)

    telemetry['start_time'] = time.time()
    telemetry['agent1_tokens'] = 0
    telemetry['agent2_tokens'] = 0
    telemetry['iterations'] = 0
    telemetry['final_area'] = 0
    telemetry['history'] = []
    telemetry['trace_id'] = str(uuid.uuid4())

    from agent1 import call_agent_1, call_agent_1_footprint
    from agent2 import call_agent_2_mentor, call_agent_2_mentor_footprint
    from z3_verifier_stage1 import run_footprint_verification
    
    feedback = ""
    footprint = None
    target_area = 0
    success = False
    dxf_filename = ""
    
    def pause_for_feedback(turn_index, stage=1):
        nonlocal feedback
        has_override = False
        if feedback_queue and callback:
            callback({"type": "wait_for_feedback", "iteration": turn_index, "stage": stage})
            print(f"  [PAUSED] Waiting for human feedback for Iteration {turn_index}...", flush=True)
            try:
                human_msg = feedback_queue.get(timeout=600) # 10 minute timeout
                if human_msg and str(human_msg).strip():
                    feedback = f"{feedback}\n\n=== HUMAN ARCHITECT OVERRIDE ===\n{str(human_msg).strip()}"
                    print(f"  [HUMAN OVERRIDE RECEIVED] {human_msg}", flush=True)
                    has_override = True
            except queue.Empty:
                print("  [WARN] Human feedback timed out after 10 minutes.", flush=True)
        return has_override

    # ==========================================
    # STAGE 1: Calculate Footprint (AI Pipeline)
    # ==========================================
    start_time_stage1 = time.time()
    for turn in range(1, 4):
        telemetry['iterations'] = turn
        print(f"\n\n{'#'*65}\n  STAGE 1: FOOTPRINT - ITERATION {turn} / 3\n{'#'*65}")

        raw_code = call_agent_1_footprint(plot_boundary, telemetry, feedback, sv, sh, custom_sbc_rules, iteration=turn)
        
        if not raw_code:
            # Groq rate limit or network error — fall back to deterministic
            print("  [WARN] Agent 1 returned no data. Falling back to deterministic footprint.")
            footprint = calculate_house_footprint(plot_boundary, sv, sh)
            target_area = int(footprint.area)
            footprint_coords = list(footprint.exterior.coords)
            footprint_coords_rounded = [[round(c[0], 2), round(c[1], 2)] for c in footprint_coords]
            
            # Generate DXF
            dxf_filename = generate_rich_dxf({}, plot_boundary, footprint_poly=footprint)
            import os
            
            step_data = {
                "iteration": 0, "agent1_code": "# Fallback: deterministic calculate_house_footprint()", 
                "z3_status": "SUCCESS", "rooms": {},
                "verification_passed": True, 
                "verification_report": f"Footprint calculated via fallback. Area: {target_area} sqft.",
                "mentor_feedback": "Proceeding to interior room packing.",
                "footprint": footprint_coords_rounded,
                "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None
            }
            if callback: callback(step_data)
            pause_for_feedback(0)
            break
            
        print(f"\n--- AGENT 1 (FOOTPRINT) CODE OUTPUT ---\n{raw_code}\n---------------------------")
            
        coords, status, python_code = extract_and_execute_code(raw_code)

        if not coords or status != "SUCCESS":
            error_msg = f"Python execution failed: {status}" if status != "SUCCESS" else "Z3 returned unsat (no overlapping solution found). Please relax constraints."
            feedback = call_agent_2_mentor_footprint(error_msg, python_code, telemetry, iteration=turn)
            step_data = {
                "iteration": 0, "agent1_code": python_code, "z3_status": status, "rooms": {},
                "verification_passed": False, "verification_report": error_msg, "mentor_feedback": feedback
            }
            if callback: callback(step_data)
            time.sleep(2) # Auto-continue without pausing if no layout
            continue

        ok_z3, report_z3 = run_footprint_verification(coords, plot_boundary, sv, sh, custom_sbc_rules)
        
        import os
        if ok_z3:
            footprint = Polygon(coords)
            target_area = int(footprint.area)
            dxf_filename = generate_rich_dxf({}, plot_boundary, footprint_poly=footprint)
            step_data = {
                "iteration": 0, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms": {},
                "verification_passed": True, "verification_report": f"House footprint calculated autonomously! Area: {target_area} sqft.", "mentor_feedback": "Proceeding to interior room packing.",
                "footprint": coords,
                "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None
            }
            if callback: callback(step_data)
            has_override = pause_for_feedback(0, stage=1)
            if has_override:
                continue
            break
        
        if turn == 3:
            # All 3 iterations failed — fall back to deterministic
            print("  [WARN] Stage 1 failed after 3 iterations. Falling back to deterministic footprint.")
            footprint = calculate_house_footprint(plot_boundary, sv, sh)
            target_area = int(footprint.area)
            footprint_coords = list(footprint.exterior.coords)
            footprint_coords_rounded = [[round(c[0], 2), round(c[1], 2)] for c in footprint_coords]
            
            # Generate DXF for fallback
            dxf_filename = generate_rich_dxf({}, plot_boundary, footprint_poly=footprint)
            
            step_data = {
                "iteration": 0, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms": {},
                "verification_passed": True, 
                "verification_report": f"Footprint via deterministic fallback after AI failed. Area: {target_area} sqft.",
                "mentor_feedback": "AI footprint did not converge. Using deterministic calculation.",
                "footprint": footprint_coords_rounded,
                "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None
            }
            if callback: callback(step_data)
            pause_for_feedback(0)
            break
        
        feedback = call_agent_2_mentor_footprint(report_z3, python_code, telemetry, iteration=turn)
        step_data = {
            "iteration": 0, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms": {},
            "verification_passed": False, "verification_report": report_z3, "mentor_feedback": feedback
        }
        if callback: callback(step_data)
        time.sleep(5)

    end_time_stage1 = time.time()
    telemetry["time_stage1"] = round(end_time_stage1 - start_time_stage1, 2)

    # ==========================================
    # STAGE 2: Room Packing
    # ==========================================
    start_time_stage2 = time.time()
    minx, miny, maxx, maxy = footprint.bounds
    XMIN, YMIN, XMAX, YMAX = int(minx), int(miny), int(maxx), int(maxy)
    footprint_corners = get_footprint_corners(footprint)
    exclusion_rects = get_exclusion_rectangles(footprint, XMIN, YMIN, XMAX, YMAX)

    feedback = ""
    rooms = {}

    for iteration in range(1, max_iterations + 1):
        telemetry['iterations'] += 1
        print(f"\n\n#################################################################")
        print(f"  STAGE 2: ROOM PACKING & VASTU - ITERATION {iteration} / {max_iterations}")
        print(f"#################################################################")
        
        # 3. Call Agent 1 (Coder)
        raw_code = call_agent_1(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, telemetry, feedback=feedback, custom_vastu_rules=custom_vastu_rules, iteration=iteration)
        
        if not raw_code:
            break
        
        print(f"\n--- AGENT 1 (ROOMS) CODE OUTPUT ---\n{raw_code}\n---------------------------")
            
        coords, status, python_code = extract_and_execute_code(raw_code)

        if not coords or status != "SUCCESS":
            error_msg = f"Python execution failed: {status}" if status != "SUCCESS" else "Z3 returned unsat (no overlapping solution found). Please relax constraints."
            feedback = call_agent_2_mentor(error_msg, python_code, telemetry, iteration=iteration)
            step_data = {
                "stage": 2, "iteration": iteration, "agent1_code": python_code, "z3_status": status, "rooms": {},
                "verification_passed": False, "verification_report": error_msg, "mentor_feedback": feedback
            }
            if callback: callback(step_data)
            time.sleep(2) # Auto-continue without pausing if no layout
            continue

        from z3_verifier import run_z3_verification
        ok_z3, report_z3 = run_z3_verification(coords, footprint, target_area, telemetry, DEFAULT_PLOT_BOUNDARY, footprint_corners, exclusion_rects, custom_vastu_rules)

        dxf_filename = generate_rich_dxf(coords, plot_boundary, footprint_poly=footprint)
        import os

        if ok_z3:
            rooms = coords
            success = True
            telemetry['final_area'] = sum((c[2]-c[0])*(c[3]-c[1]) for c in coords.values() if len(c)==4)
            step_data = {
                "stage": 2, "iteration": iteration, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms": rooms,
                "verification_passed": True, "verification_report": "All Vastu and Geometric constraints verified successfully!", "mentor_feedback": "",
                "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None
            }
            if callback: callback(step_data)
            has_override = pause_for_feedback(iteration, stage=2)
            if has_override:
                continue
            break
            
        if iteration == max_iterations:
            step_data = {
                "stage": 2, "iteration": iteration, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms": coords,
                "verification_passed": False, "verification_report": report_z3, "mentor_feedback": "Final iteration failed to converge.",
                "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None
            }
            if callback: callback(step_data)
            pause_for_feedback(iteration, stage=2)
            break
        
        feedback = call_agent_2_mentor(report_z3, python_code, telemetry, iteration=iteration)
        step_data = {
            "stage": 2, "iteration": iteration, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms": coords,
            "verification_passed": False, "verification_report": report_z3, "mentor_feedback": feedback,
            "dxf_filename": os.path.basename(dxf_filename) if dxf_filename else None
        }
        if callback: callback(step_data)
        pause_for_feedback(iteration, stage=2)
        time.sleep(5)

    end_time_stage2 = time.time()
    telemetry["time_stage2"] = round(end_time_stage2 - start_time_stage2, 2)

    # ==========================================
    # STAGE 3: Upper Level Design
    # ==========================================
    from agent1 import call_agent_1_stage3
    from agent2 import call_agent_2_mentor_stage3
    from z3_verifier_stage3 import run_z3_verification_stage3

    start_time_stage3 = time.time()
    rooms_stage3 = {}
    success_stage3 = False
    feedback = ""

    # Calculate the bounding box of Ground Floor rooms to serve as the footprint for Stage 3
    stage3_xmin, stage3_ymin, stage3_xmax, stage3_ymax = XMIN, YMIN, XMAX, YMAX
    exclusion_rects_stage3 = exclusion_rects
    
    if rooms:
        stage3_xmin = min(c[0] for c in rooms.values() if len(c) == 4)
        stage3_xmax = max(c[2] for c in rooms.values() if len(c) == 4)
        stage3_ymin = min(c[1] for c in rooms.values() if len(c) == 4)
        stage3_ymax = max(c[3] for c in rooms.values() if len(c) == 4)



    for iteration in range(1, max_iterations + 1):
        telemetry['iterations'] += 1
        print(f"\n\n#################################################################")
        print(f"  STAGE 3: UPPER LEVEL DESIGN - ITERATION {iteration} / {max_iterations}")
        print(f"#################################################################")
        
        raw_code = call_agent_1_stage3(target_area, stage3_xmin, stage3_ymin, stage3_xmax, stage3_ymax, footprint_corners, exclusion_rects_stage3, rooms, telemetry, feedback=feedback, custom_vastu_rules=custom_vastu_rules_stage3, iteration=iteration)
        
        if not raw_code:
            break
        
        print(f"\n--- AGENT 1 (STAGE 3) CODE OUTPUT ---\n{raw_code}\n---------------------------")
            
        coords, status, python_code = extract_and_execute_code(raw_code)

        if not coords or status != "SUCCESS":
            error_msg = f"Python execution failed: {status}" if status != "SUCCESS" else "Z3 returned unsat (no overlapping solution found). Please relax constraints."
            feedback = call_agent_2_mentor_stage3(error_msg, python_code, telemetry, iteration=iteration)
            step_data = {
                "stage": 3, "iteration": iteration, "agent1_code": python_code, "z3_status": status, "rooms": coords,
                "verification_passed": False, "verification_report": error_msg, "mentor_feedback": feedback,
                "dxf_filename": None
            }
            if callback: callback(step_data)
            has_override = pause_for_feedback(iteration, stage=3)
            if has_override:
                continue
            continue
            
        ok_z3, report_z3 = run_z3_verification_stage3(coords, footprint, target_area, telemetry, plot_boundary, footprint_corners, exclusion_rects_stage3, rooms, custom_vastu_rules_stage3)

        # For stage 3, generate a single DXF file with both ground floor and upper floor rooms on different layers
        dxf_filename_stage3 = generate_rich_dxf(rooms, plot_boundary, footprint_poly=footprint, rooms_stage3=coords)
        import os

        if ok_z3:
            rooms_stage3 = coords
            success_stage3 = True
            step_data = {
                "stage": 3, "iteration": iteration, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms_stage3": rooms_stage3,
                "verification_passed": True, "verification_report": "All Upper Level constraints verified successfully!", "mentor_feedback": "",
                "dxf_filename": os.path.basename(dxf_filename_stage3) if dxf_filename_stage3 else None
            }
            if callback: callback(step_data)
            has_override = pause_for_feedback(iteration, stage=3)
            if has_override:
                continue
            break
            
        if iteration == max_iterations:
            step_data = {
                "stage": 3, "iteration": iteration, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms_stage3": coords,
                "verification_passed": False, "verification_report": report_z3, "mentor_feedback": "Final iteration failed to converge.",
                "dxf_filename": os.path.basename(dxf_filename_stage3) if dxf_filename_stage3 else None
            }
            if callback: callback(step_data)
            pause_for_feedback(iteration, stage=3)
            break
        
        feedback = call_agent_2_mentor_stage3(report_z3, python_code, telemetry, iteration=iteration)
        step_data = {
            "stage": 3, "iteration": iteration, "agent1_code": python_code, "z3_status": "SUCCESS", "rooms_stage3": coords,
            "verification_passed": False, "verification_report": report_z3, "mentor_feedback": feedback,
            "dxf_filename": os.path.basename(dxf_filename_stage3) if dxf_filename_stage3 else None
        }
        if callback: callback(step_data)
        pause_for_feedback(iteration, stage=3)
        time.sleep(5)

    end_time_stage3 = time.time()

    print("\n" + "="*65)
    print("  [TELEMETRY] SYSTEM TELEMETRY (FINAL REPORT)")
    print("="*65)
    print(f"  Total Runtime:   {time.time() - telemetry['start_time']:.2f} seconds")
    print(f"  Iterations:      {telemetry['iterations']}")
    print(f"  A1 Tokens:       {telemetry['agent1_tokens']}")
    print(f"  A2 Tokens:       {telemetry['agent2_tokens']}")
    print(f"  Max Room Area:   {telemetry['final_area']} sq ft")
    print("="*65)

    return success, rooms, rooms_stage3, footprint, dxf_filename, telemetry

if __name__ == "__main__":
    main()
