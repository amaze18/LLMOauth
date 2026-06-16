from shapely.geometry import box

def run_z3_verification_stage3(rooms, footprint, target_area, telemetry, PLOT_BOUNDARY, footprint_corners, exclusion_rects, ground_floor_rooms, custom_vastu_rules=""):
    print("\n" + "="*60)
    print("[STAGE 3] Z3/Math Verification — Upper Floor Geometry")
    print("="*60)

    required_rooms = [
        "Upper Hallway", "Primary Suite", "Primary Bath", "Bedroom 4", "Bedroom 5", "Shared Bath"
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

    # Staircase overlap verification
    staircase_coords = ground_floor_rooms.get("Staircase")
    if staircase_coords:
        sx1, sy1, sx2, sy2 = staircase_coords
        for name, coords in rooms.items():
            rx1, ry1, rx2, ry2 = coords
            # Allow edges to touch, but interior cannot overlap
            if not (rx2 <= sx1 or rx1 >= sx2 or ry2 <= sy1 or ry1 >= sy2):
                return False, f"Room {name} overlaps with the immutable STAIRCASE shaft {staircase_coords}"

    def overlap(r1, r2):
        x1_a, y1_a, x2_a, y2_a = r1
        x1_b, y1_b, x2_b, y2_b = r2
        return not (x2_a <= x1_b or x2_b <= x1_a or y2_a <= y1_b or y2_b <= y1_a)

    keys = list(rooms.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if overlap(rooms[keys[i]], rooms[keys[j]]):
                return False, f"Room {keys[i]} overlaps with {keys[j]}."

    sizes = {
        "Primary Suite": (14, 14),
        "Primary Bath": (8, 8),
        "Bedroom 4": (12, 12),
        "Bedroom 5": (12, 12),
        "Shared Bath": (8, 8),
        "Upper Hallway": (4, 4)
    }
    for r, (mw, mh) in sizes.items():
        coords = rooms[r]
        w = coords[2] - coords[0]
        h = coords[3] - coords[1]
        if w < mw or h < mh:
            return False, f"Room {r} is too small: {w}x{h} (min {mw}x{mh})."

    return True, "All Upper Level constraints verified successfully!"
