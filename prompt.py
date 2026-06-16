def get_problem_statement(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, custom_vastu_rules=""):
    SW_x, SW_y = footprint_corners["SW"]
    SE_x, SE_y = footprint_corners["SE"]
    NE_x, NE_y = footprint_corners["NE"]
    NW_x, NW_y = footprint_corners["NW"]

    exclusion_list_str = "\n".join(f"- Rectangle from X={r[0]} to {r[2]}, Y={r[1]} to {r[3]}" for r in exclusion_rects)

    if custom_vastu_rules and custom_vastu_rules.strip():
        rooms_section = f"""
=== CUSTOM ROOMS AND VASTU CONSTRAINTS (CRITICAL) ===
The user has provided a custom list of rooms, minimum dimensions, and relative Vastu constraints:
{custom_vastu_rules}

Instructions for Custom Rooms:
- Extract the room names from the user's custom instructions above.
- Define Z3 Int variables for EACH room exactly as requested.
- Create Z3 variables `x1, y1, x2, y2` for each room representing left, bottom, right, top edges.
- Enforce the minimum dimensions specified by the user.
- Enforce the specific layout constraints (e.g., Southeast, Northwest, adjacency) specified by the user by translating them into Z3 coordinate comparisons (e.g., `center_x`, `center_y`).
"""
    else:
        rooms_section = """
=== REQUIRED ROOMS AND CONSTRAINTS ===
Define Z3 Int variables for the 10 rooms: "Living Room", "Dining Area", "Kitchen", "Master Bedroom", "Bedroom 2", "Bedroom 3", "Bathroom 1", "Bathroom 2", "Corridor", and "Staircase".
Each room has coordinates: [x1, y1, x2, y2] representing its left, bottom, right, and top edges respectively. Ensure you generate UNIQUE string names for the Z3 Int variables for each room (e.g. use `z3.Int(f"{name}_x1")`).

Add the following mathematical constraints to your solver (`solver = z3.Solver()`):
2. Vastu Relative Positioning (CRITICAL):
   - Master Bedroom is South-West: Its center X must be strictly less than the Kitchen's center X. Its center Y must be strictly less than the Living Room's center Y.
   - Kitchen is South-East: Its center X must be strictly greater than Master Bedroom's center X. Its center Y must be strictly less than the Living Room's center Y.
   - Living Room is North-East: Its center Y must be strictly greater than both Master Bedroom and Kitchen's center Y.
   - Implement this by comparing the centers: e.g. `solver.add((rooms["Master Bedroom"][0] + rooms["Master Bedroom"][2]) < (rooms["Kitchen"][0] + rooms["Kitchen"][2]))`
2. Minimum Room Sizes (Width x Height):
   - Living Room: >= 15 x 15
   - Dining Area: >= 10 x 10
   - Kitchen: >= 10 x 10
   - Master Bedroom: >= 12 x 12
   - Bedroom 2: >= 10 x 10
   - Bedroom 3: >= 10 x 10
   - Bathroom 1 & 2: >= 6 x 6 (and must also be <= 10 x 10)
   - Corridor: width >= 4, height >= 4
   - Staircase: >= 8 x 8 (and must touch Corridor)
3. Zones (Relative):
   - Bathrooms 1 & 2 must be West of the Kitchen: Their center X must be less than the Kitchen's center X.
   - Bathrooms 1 & 2 must be North of the Master Bedroom: Their center Y must be greater than the Master Bedroom's center Y.
4. Adjacencies:
   - Living Room must touch Dining Area.
   - Dining Area must touch Kitchen.
   - Dining Area must touch Corridor.
   - Corridor must touch: Master Bedroom, Bedroom 2, Bedroom 3, Bathroom 1, and Bathroom 2.
   - Bathroom 1 and Bathroom 2 must touch.
5. Privacy (Negative Edges):
   - Bathroom 1 must NEVER touch Master Bedroom, Bedroom 2, or Bedroom 3.
   - Bathroom 2 must NEVER touch Kitchen.
   - Kitchen must NEVER touch Bathroom 1.
"""

    prompt = f"""
You are Agent 1 (Formulation Agent). Your task is to write a Python script using the `z3-solver` library to perfectly pack rectangular rooms inside a Vastu-compliant house footprint with NO empty space (zero-waste packing).

=== HOUSE AND PLOT BOUNDARIES ===
The house footprint resides within the bounding box limits:
- X in [{XMIN}, {XMAX}]
- Y in [{YMIN}, {YMAX}]

=== EXCLUSION ZONES (CRITICAL) ===
The bounding box includes empty/cut-out regions that you MUST NOT build in. 
We have pre-calculated the rectangular exclusion zones inside this bounding box:
{exclusion_list_str if exclusion_rects else "- None (simple rectangular plot)"}

For EVERY room `[rx1, ry1, rx2, ry2]`, you must add a constraint that it does not overlap with any of the exclusion zones listed above.
Specifically, for each exclusion zone `[ex1, ey1, ex2, ey2]`, add:
`solver.add(z3.Or(rx2 <= ex1, rx1 >= ex2, ry2 <= ey1, ry1 >= ey2))`

{rooms_section}

=== VASTU & GEOMETRY TRANSLATION TIPS ===
When translating the text-based Vastu constraints into Z3 constraints:
- "West" means smaller X. "East" means larger X. "South" means smaller Y. "North" means larger Y.
- If a room must be "on the West side" or "West wall", force `x1 == 0`.
- If a room must be "on the South side", force `y1 == 0`.
- If a room must be "on the East side", force `x2 == {XMAX}`.
- If a room must be "on the North side", force `y2 == {YMAX}`.

=== UNIVERSAL MATHEMATICAL CONSTRAINTS ===
1. Room Boundaries:
   - For all rooms: x1 < x2 and y1 < y2.
2. House Boundaries:
   - All rooms must fit entirely within the house footprint bounding box: 
     x1 >= {XMIN}, x2 <= {XMAX}, y1 >= {YMIN}, y2 <= {YMAX}
   - Ensure you do NOT force the sum of room areas to equal the total valid area. Rooms just need to fit inside the bounding box and respect exclusion zones.
3. Non-overlapping:
   - No two rooms can overlap. For any pair of rooms, they must be separated horizontally or vertically.
4. Adjacency Connections:
   - Enforce that two rooms touch (share a wall segment of >0 length) using this helper function:
     def touch(r1, r2):
         x1_a, y1_a, x2_a, y2_a = r1
         x1_b, y1_b, x2_b, y2_b = r2
         return z3.Or(
             z3.And(z3.Or(x2_a == x1_b, x2_b == x1_a), y1_a < y2_b, y1_b < y2_a),
             z3.And(z3.Or(y2_a == y1_b, y2_b == y1_a), x1_a < x2_b, x1_b < x2_a)
         )

   - Enforce non-overlapping constraints using this helper function:
     def non_overlap(r1, r2):
         x1_a, y1_a, x2_a, y2_a = r1
         x1_b, y1_b, x2_b, y2_b = r2
         return z3.Or(x2_a <= x1_b, x2_b <= x1_a, y2_a <= y1_b, y2_b <= y1_a)

         
=== CODE STRATEGY ===
Write a python script that:
1. Imports `z3` and `json`.
2. DEFINES the `touch(r1, r2)` and `non_overlap(r1, r2)` helper functions EXACTLY as provided above, at the top of your script.
3. Encapsulates all logic inside a function `solve_for_fraction(fraction)`:
   - Initialize a fresh solver: `solver = z3.Solver()` and set a timeout: `solver.set("timeout", 5000)`.
   - Define the variables, boundary, exclusion zone, Vastu, size, zone, non_overlap, and adjacency touch constraints.
   - NEVER use division (`/` or `//`) on Z3 variables, as it makes the solver extremely slow or crash. To compare centers or add tolerances, ALWAYS use sums (e.g. `(x1 + x2) < (gx1 + gx2)`) and multiply out any fractions!
   - If `fraction > 0.0`, add the area constraint: `solver.add(sum((rooms[r][2] - rooms[r][0]) * (rooms[r][3] - rooms[r][1]) for r in rooms) >= int(fraction * {target_area}))`.
   - Call `solver.check()`. If `sat`, evaluate the model using `model.eval(var).as_long()` for all coordinates, and return the rooms dictionary with python integer arrays: `[x1, y1, x2, y2]`. Using `.as_long()` is CRITICAL to avoid JSON serialization errors!
   - If `unsat` or an exception occurs, return `None`.
4. Loop through the coverage fractions `[1.0, 0.95, 0.90, 0.85, 0.80, 0.0]`. For each fraction:
   - Call `res = solve_for_fraction(fraction)`.
   - If it returns a valid dictionary, print the JSON `print(json.dumps({{"rooms": res}}))` and `break`.
5. If the loop finishes with no result, print `{{"rooms": {{}}}}`. Do NOT embed pre-calculated coordinates.

=== EXPECTED OUTPUT FORMAT ===
Your entire response MUST be valid Python code. Do not wrap it in markdown block quotes. Just pure code.
Make sure you include the full Z3 logic, `solver.check()`.
If a solution is found, print it EXACTLY as:
`print(json.dumps({{"rooms": {{"Living Area": [x1, y1, x2, y2], ...}}}}))`
If no solution is found (unsat), you MUST print an empty rooms dictionary:
`print(json.dumps({{"rooms": {{}}}}))`

Write the code.
"""
    return prompt
