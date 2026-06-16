def get_stage3_problem_statement(target_area, XMIN, YMIN, XMAX, YMAX, footprint_corners, exclusion_rects, ground_floor_rooms, custom_vastu_rules=""):
    exclusion_list_str = "\n".join(f"- Rectangle from X={r[0]} to {r[2]}, Y={r[1]} to {r[3]}" for r in exclusion_rects)
    
    staircase_coords = ground_floor_rooms.get("Staircase", [0,0,10,10])
    sx1, sy1, sx2, sy2 = staircase_coords
    
    kitchen_coords = ground_floor_rooms.get("Kitchen", [0,0,10,10])
    kx1, ky1, kx2, ky2 = kitchen_coords

    ground_rooms_str = "\n".join(f"    - {name}: [{c[0]}, {c[1]}, {c[2]}, {c[3]}]" for name, c in ground_floor_rooms.items() if len(c) == 4)

    rooms_section = f"""
=== REQUIRED ROOMS AND CONSTRAINTS FOR STAGE 3 (UPPER LEVEL) ===
{custom_vastu_rules if custom_vastu_rules else 'Define Z3 Int variables for the 6 rooms: "Upper Hallway", "Primary Suite", "Primary Bath", "Bedroom 4", "Bedroom 5", and "Shared Bath".'}

Add the following mathematical constraints to your solver (`solver = z3.Solver()`):
1. STAIRCASE IMMUTABILITY (CRITICAL):
   - The Stage 2 staircase is a fixed shaft from X=[{sx1}, {sx2}] and Y=[{sy1}, {sy2}].
   - NO Stage 3 room may overlap with the interior of the staircase:
     `solver.add(z3.Or(rx2 <= {sx1}, rx1 >= {sx2}, ry2 <= {sy1}, ry1 >= {sy2}))` for ALL rooms.
   - The "Upper Hallway" MUST exactly touch the Staircase landing edge to ensure circulation.
     Since the hallway must connect, enforce that it touches the staircase bounding box using the `touch()` function:
     `solver.add(touch([rx1, ry1, rx2, ry2], [{sx1}, {sy1}, {sx2}, {sy2}]))` where r is the Upper Hallway.





=== VASTU & GEOMETRY TRANSLATION TIPS ===
When translating the text-based Vastu constraints into Z3 constraints:
- "West" means smaller X. "East" means larger X. "South" means smaller Y. "North" means larger Y.
- If a room must be "on the West side", force `x1 == 0`.
- If a room must be "on the South side", force `y1 == 0`.
- If a room must be "on the East side", force `x2 == {XMAX}`.
- If a room must be "on the North side", force `y2 == {YMAX}`.
- NEVER use Python's built-in `abs()` function on Z3 variables, as it will crash the execution. If you need to add a tolerance (e.g. within 5 units), use two inequalities instead: `solver.add(diff <= 5)`, `solver.add(diff >= -5)`.
"""

    prompt = f"""
You are Agent 1 (Formulation Agent). Your task is to write a Python script using the `z3-solver` library to perfectly pack rectangular rooms inside a Vastu-compliant UPPER FLOOR footprint with NO empty space (zero-waste packing).

=== HOUSE AND PLOT BOUNDARIES ===
The house footprint resides within the bounding box limits:
- X in [{XMIN}, {XMAX}]
- Y in [{YMIN}, {YMAX}]

=== EXCLUSION ZONES (CRITICAL) ===
The bounding box includes empty/cut-out regions that you MUST NOT build in (such as the Balcony Zone). 
We have pre-calculated the rectangular exclusion zones inside this bounding box:
{exclusion_list_str if exclusion_rects else "- None (simple rectangular plot)"}

For EVERY room `[rx1, ry1, rx2, ry2]`, you must add a constraint that it does not overlap with any of the exclusion zones listed above.
Specifically, for each exclusion zone `[ex1, ey1, ex2, ey2]`, add:
`solver.add(z3.Or(rx2 <= ex1, rx1 >= ex2, ry2 <= ey1, ry1 >= ey2))`

{rooms_section}

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
   - YOU MUST COPY THE FOLLOWING HELPER FUNCTIONS EXACTLY INTO YOUR SCRIPT BEFORE USING THEM:

     def touch(r1, r2):
         x1_a, y1_a, x2_a, y2_a = r1
         x1_b, y1_b, x2_b, y2_b = r2
         return z3.Or(
             z3.And(z3.Or(x2_a == x1_b, x2_b == x1_a), y1_a < y2_b, y1_b < y2_a),
             z3.And(z3.Or(y2_a == y1_b, y2_b == y1_a), x1_a < x2_b, x1_b < x2_a)
         )

     def non_overlap(r1, r2):
         x1_a, y1_a, x2_a, y2_a = r1
         x1_b, y1_b, x2_b, y2_b = r2
         return z3.Or(x2_a <= x1_b, x2_b <= x1_a, y2_a <= y1_b, y2_b <= y1_a)

     def overlap(r1, r2):
         return z3.Not(non_overlap(r1, r2))

=== CODE STRATEGY ===
Write a python script that:
1. Imports `z3` and `json`.
2. DEFINES the `touch(r1, r2)`, `non_overlap(r1, r2)`, and `overlap(r1, r2)` helper functions EXACTLY as provided above, at the top of your script.
3. Encapsulates all logic inside a function `solve_for_fraction(fraction)`:
   - Initialize a fresh solver: `solver = z3.Solver()` and set a timeout: `solver.set("timeout", 15000)`.
   - Define the variables, boundary, exclusion zone, Vastu, size, zone, non_overlap, and adjacency touch constraints.
   - If `fraction > 0.0`, add the area constraint: `solver.add(sum((rooms[r][2] - rooms[r][0]) * (rooms[r][3] - rooms[r][1]) for r in rooms) >= int(fraction * {target_area}))`.
   - Call `solver.check()`. If `sat`, evaluate the model using `model.eval(var).as_long()` for all coordinates, and return the rooms dictionary with python integer arrays: `[x1, y1, x2, y2]`. Using `.as_long()` is CRITICAL to avoid JSON serialization errors!
   - If `unsat` or an exception occurs, return `None`.
4. Loop through the coverage fractions `[1.0, 0.95, 0.90, 0.85, 0.80, 0.0]`. For each fraction:
   - Call `res = solve_for_fraction(fraction)`.
   - If it returns a valid dictionary, print the JSON `print(json.dumps({{"rooms": res}}))` and `break`.
5. If the loop finishes with no result, print `{{"rooms": {{}}}}`. Do NOT embed pre-calculated coordinates.

=== EXPECTED OUTPUT FORMAT ===
Your entire response MUST be valid Python code. Do not wrap it in markdown block quotes. Just pure code.
Your python code must end with printing exactly a JSON matching this structure:
print(json.dumps({{
  "rooms": {{
    "Upper Hallway": [x1, y1, x2, y2],
    ...
  }}
}}))
"""
    return prompt
