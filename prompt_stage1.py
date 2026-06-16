def get_stage1_problem_statement(plot_boundary, setback_vertical=5, setback_horizontal=15, custom_sbc_rules=""):
    boundary_str = ", ".join([f"({x}, {y})" for x, y in plot_boundary])
    
    # Dynamically analyze each edge
    edges_analysis = []
    for i in range(len(plot_boundary) - 1):
        p1 = plot_boundary[i]
        p2 = plot_boundary[i + 1]
        if p1[0] == p2[0]:
            edge_type = "VERTICAL"
            setback = setback_vertical
        elif p1[1] == p2[1]:
            edge_type = "HORIZONTAL"
            setback = setback_horizontal
        else:
            edge_type = "DIAGONAL"
            setback = setback_vertical
        edges_analysis.append(f"   Edge {i+1}: ({p1[0]},{p1[1]}) -> ({p2[0]},{p2[1]}) = {edge_type} => {setback}ft buffer")
    
    edges_str = "\n".join(edges_analysis)
    
    # Compute bounding box
    xs = [p[0] for p in plot_boundary]
    ys = [p[1] for p in plot_boundary]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    prompt = f"""
You are Agent 1 (Formulation Agent). Your task is to write a Python script using the `shapely` library to calculate the maximum buildable house footprint.

=== PLOT BOUNDARY (DYNAMIC INPUT) ===
The raw plot boundary has the following vertices in order:
{boundary_str}

Bounding box: X in [{min_x}, {max_x}], Y in [{min_y}, {max_y}]

=== DYNAMIC SETBACK RULES ===
The exact polygon erosion logic involves eroding different edges by different amounts based on their orientation.
{edges_str}

=== CUSTOM BUILDING CODE CONSTRAINTS ===
{custom_sbc_rules if custom_sbc_rules.strip() else "None specified by the user."}

=== THE ORTHOGONAL ERASER ALGORITHM (MANDATORY) ===
Because the plot has complex conditional notches, you must use Boolean geometric subtraction to carve the final shape. Follow these exact steps:

1. Create the `base_poly` representing the entire raw plot:
   `base_poly = Polygon([{boundary_str}])`

2. Create standard erasers using the pre-calculated `edges` list. 
   HOWEVER, you must apply the Custom SBC Constraints. If a Custom SBC rule overrides an edge (e.g. "0ft setback" or "do not erode"), you must SKIP eroding that edge or modify its buffer.
   
   Here is the python code for the default edges. You must include this in your script:
   ```python
   from shapely.geometry import Polygon, LineString, box
   edges = [
"""
    for i in range(len(plot_boundary) - 1):
        p1 = plot_boundary[i]
        p2 = plot_boundary[i + 1]
        if p1[0] == p2[0]:
            setback = setback_vertical
        elif p1[1] == p2[1]:
            setback = setback_horizontal
        else:
            setback = setback_vertical
        prompt += f"       (({p1[0]}, {p1[1]}), ({p2[0]}, {p2[1]}), {setback}),\n"
    prompt += f"""   ]
   
   final_polygon = base_poly
   
   # 1. Erode the standard edges
   for p1, p2, buf in edges:
       # Modify or skip buffer based on Custom SBC (e.g. if an edge matches the SBC, change `buf` or `continue`)
       # [INJECT SBC LOGIC HERE]
       
       eraser = LineString([p1, p2]).buffer(buf, cap_style=2)
       final_polygon = final_polygon.difference(eraser)

   # 2. Add extra erasers for custom zones (like Protected Trees)
   # final_polygon = final_polygon.difference(box(X_MIN, Y_MIN, X_MAX, Y_MAX))
   # [INJECT ADDITIONAL SBC ERASERS HERE]
   ```

3. The resulting `final_polygon` is the house footprint.

[OUTPUT FORMAT]
Provide the Python code inside a markdown block. Do not add conversational filler.
Your Python code MUST end with exactly this code so the orchestrator can parse it safely even if the setbacks split the plot:
import json
if final_polygon.geom_type in ['MultiPolygon', 'GeometryCollection']:
    polys = [g for g in final_polygon.geoms if g.geom_type == 'Polygon']
    final_polygon = max(polys, key=lambda p: p.area) if polys else final_polygon
print(json.dumps({{"coordinates": list(final_polygon.exterior.coords)}}))
"""
    return prompt
