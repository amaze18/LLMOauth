import math
from shapely.geometry import Polygon, LineString

def run_footprint_verification(footprint_coords, plot_boundary, setback_vertical=5, setback_horizontal=15, custom_sbc_rules=""):
    print("\n" + "="*60)
    print("[STEP 2] Math Cop — Verifying Footprint Setbacks")
    print("="*60)

    try:
        footprint_poly = Polygon(footprint_coords)
        if not footprint_poly.is_valid:
            return False, "Generated footprint is not a valid polygon."

        plot_poly = Polygon(plot_boundary)
        
        if custom_sbc_rules.strip():
            print("  [INFO] Custom SBC rules active. Skipping strict mathematical setback validation, relying on AI geometry.")
            # Just ensure the footprint is generally within the bounding box of the plot (or exact plot)
            if footprint_poly.area <= 0:
                return False, "Footprint area is zero or negative."
            if not footprint_poly.within(plot_poly.buffer(1.0)): # Allow 1ft floating point leniency
                return False, "Footprint extends outside the main plot boundary!"
            return True, "PASSED (Custom SBC Override)"

        # Check setbacks for every edge of the plot boundary
        for i in range(len(plot_boundary) - 1):
            p1 = plot_boundary[i]
            p2 = plot_boundary[i+1]
            line = LineString([p1, p2])
            
            # Determine required setback
            if p1[0] == p2[0]:
                required_setback = float(setback_vertical)  # Vertical
            elif p1[1] == p2[1]:
                required_setback = float(setback_horizontal) # Horizontal
            else:
                required_setback = float(setback_vertical)  # Diagonal
                
            distance = footprint_poly.distance(line)
            
            # Account for floating point inaccuracies
            if distance < required_setback - 0.01:
                return False, f"Footprint breaches setback! Edge ({p1[0]},{p1[1]}) to ({p2[0]},{p2[1]}) requires {required_setback}ft setback, but distance is {distance:.2f}ft."

        area = footprint_poly.area
        if area <= 0:
            return False, "Footprint area is zero or negative."

        print(f"  [OK] Math Cop Verified: All footprint setbacks passed! Area: {int(area)} sqft")
        return True, "PASSED"
    except Exception as e:
        return False, f"Verification crashed: {e}"
