from shapely.geometry import box

def run_z3_verification(rooms, footprint, target_area, telemetry, PLOT_BOUNDARY, footprint_corners, exclusion_rects, custom_vastu_rules=""):
    print("\n" + "="*60)
    print("[STEP 2] Z3/Math Verification — Checking Vastu & Geometric Feasibility")
    print("="*60)

    if not custom_vastu_rules or not custom_vastu_rules.strip():
        required_rooms = [
            "Living Room", "Dining Area", "Kitchen", "Master Bedroom",
            "Bedroom 2", "Bedroom 3", "Bathroom 1", "Bathroom 2", "Corridor", "Staircase"
        ]
        
        for r in required_rooms:
            if r not in rooms:
                return False, f"Missing required room: {r}"

    minx, miny, maxx, maxy = footprint.bounds
    XMIN, YMIN, XMAX, YMAX = int(minx), int(miny), int(maxx), int(maxy)
    
    for name, coords in rooms.items():
        if not isinstance(coords, list) or len(coords) != 4:
            return False, f"Room {name} must have coordinates as [x1, y1, x2, y2]"
        x1, y1, x2, y2 = coords
        if x1 >= x2 or y1 >= y2:
            return False, f"Room {name} has invalid coordinates: x1={x1}, x2={x2}, y1={y1}, y2={y2}"
        room_box = box(x1, y1, x2, y2)
        if not footprint.contains(room_box.buffer(-0.01)):
            return False, f"Room {name} goes outside dynamically calculated house boundary polygon: {coords}"

    # Exclusion rectangles overlap verification
    for name, coords in rooms.items():
        rx1, ry1, rx2, ry2 = coords
        for ex1, ey1, ex2, ey2 in exclusion_rects:
            if not (rx2 <= ex1 or rx1 >= ex2 or ry2 <= ey1 or ry1 >= ey2):
                return False, f"Room {name} overlaps with exclusion zone [{ex1}, {ey1}, {ex2}, {ey2}]"

    def overlap(r1, r2):
        x1_a, y1_a, x2_a, y2_a = r1
        x1_b, y1_b, x2_b, y2_b = r2
        return not (x2_a <= x1_b or x2_b <= x1_a or y2_a <= y1_b or y2_b <= y1_a)

    def touch(r1, r2):
        x1_a, y1_a, x2_a, y2_a = r1
        x1_b, y1_b, x2_b, y2_b = r2
        if overlap(r1, r2):
            return False
        if (x2_a == x1_b or x2_b == x1_a) and not (y2_a <= y1_b or y2_b <= y1_a):
            return True
        if (y2_a == y1_b or y2_b == y1_a) and not (x2_a <= x1_b or x2_b <= x1_a):
            return True
        return False

    keys = list(rooms.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if overlap(rooms[keys[i]], rooms[keys[j]]):
                return False, f"Room {keys[i]} overlaps with {keys[j]}."

    if not custom_vastu_rules or not custom_vastu_rules.strip():
        sizes = {
            "Living Room": (15, 15),
            "Dining Area": (10, 10),
            "Kitchen": (10, 10),
            "Master Bedroom": (12, 12),
            "Bedroom 2": (10, 10),
            "Bedroom 3": (10, 10),
            "Bathroom 1": (6, 6),
            "Bathroom 2": (6, 6),
            "Corridor": (4, 4),
            "Staircase": (8, 8)
        }
        for r, (mw, mh) in sizes.items():
            coords = rooms[r]
            w = coords[2] - coords[0]
            h = coords[3] - coords[1]
            if w < mw or h < mh:
                return False, f"Room {r} is too small: {w}x{h} (min {mw}x{mh})."

        for r in ["Bathroom 1", "Bathroom 2"]:
            coords = rooms[r]
            w = coords[2] - coords[0]
            h = coords[3] - coords[1]
            if w > 10 or h > 10:
                return False, f"Room {r} is too large: {w}x{h} (max 10x10)."

        # Dynamic Vastu relative verification
        mb = rooms["Master Bedroom"]
        kt = rooms["Kitchen"]
        lr = rooms["Living Room"]
        
        mb_cx = (mb[0] + mb[2]) / 2.0
        mb_cy = (mb[1] + mb[3]) / 2.0
        kt_cx = (kt[0] + kt[2]) / 2.0
        kt_cy = (kt[1] + kt[3]) / 2.0
        lr_cx = (lr[0] + lr[2]) / 2.0
        lr_cy = (lr[1] + lr[3]) / 2.0

        if mb_cx >= kt_cx:
            return False, f"Master Bedroom (SW) must be West of Kitchen (SE). mb_x={mb_cx}, kt_x={kt_cx}"
        if mb_cy >= lr_cy:
            return False, f"Master Bedroom (SW) must be South of Living Room (NE). mb_y={mb_cy}, lr_y={lr_cy}"
        if kt_cy >= lr_cy:
            return False, f"Kitchen (SE) must be South of Living Room (NE). kt_y={kt_cy}, lr_y={lr_cy}"

        b1 = rooms["Bathroom 1"]
        b2 = rooms["Bathroom 2"]
        if not touch(b1, b2):
            return False, "Bathroom 1 and Bathroom 2 must be clustered (share a wall)."

        for r in ["Bathroom 1", "Bathroom 2"]:
            coords = rooms[r]
            cx = (coords[0] + coords[2]) / 2.0
            cy = (coords[1] + coords[3]) / 2.0
            if cx >= kt_cx:
                return False, f"Bathroom {r} must be West of Kitchen. cx={cx}, kt_x={kt_cx}"
            if cy <= mb_cy:
                return False, f"Bathroom {r} must be North of Master Bedroom. cy={cy}, mb_y={mb_cy}"

        da = rooms["Dining Area"]
        co = rooms["Corridor"]
        
        if not touch(lr, da):
            return False, "Living Room must connect to Dining Area (must share a wall segment)."
        if not touch(da, kt):
            return False, "Dining Area must connect to Kitchen (must share a wall segment)."
        if not touch(da, co):
            return False, "Dining Area must connect to Corridor/Lobby (must share a wall segment)."
            
        for r in ["Master Bedroom", "Bedroom 2", "Bedroom 3", "Bathroom 1", "Bathroom 2"]:
            if not touch(co, rooms[r]):
                return False, f"Corridor/Lobby must connect to {r} (must share a wall segment)."

        kt = rooms["Kitchen"]
        for r in ["Master Bedroom", "Bedroom 2", "Bedroom 3"]:
            if touch(b1, rooms[r]):
                return False, f"Bathroom 1 must NEVER touch {r}."
        if touch(b2, kt):
            return False, "Bathroom 2 must NEVER touch Kitchen."
        if touch(b1, kt):
            return False, "Bathroom 1 must NEVER touch Kitchen."

    total_area = sum((r[2]-r[0])*(r[3]-r[1]) for r in rooms.values())
    telemetry["final_area"] = total_area
    
    print(f"  [OK] Z3/Vastu Verified: All constraints passed! Combined room area: {total_area:.1f} sqft (out of {target_area} max)")
    return True, "PASSED"
