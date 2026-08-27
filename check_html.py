import requests

resp = requests.get('http://127.0.0.1:5001', timeout=10)
resp.raise_for_status()
html = resp.text

# Check for required input fields
required_fields = [
    'pot_diameter', 'clearance', 'height', 'wall', 'base', 
    'include_bottom', 'taper', 'rim_lip', 'shape_type', 'star_inner_ratio',
    'texture_type', 'texture_strength', 'texture_scale', 'texture_rotation',
    'middle_inbound_turns', 'z_rotation', 'material_type', 'sections',
    'drainage_pattern', 'drainage_hole_count', 'drainage_spacing',
    'print_profile', 'nozzle_diameter', 'layer_height', 'auto_repair',
    'text_content', 'text_mode', 'text_height', 'text_depth'
]

print("Checking HTML for required input fields:")
for field in required_fields:
    pattern = f'name="{field}"'
    if pattern in html:
        print(f"  ✓ {field}")
    else:
        print(f"  ✗ {field} MISSING!")

# Check for canvas
if 'id="preview-canvas"' in html:
    print("\n  ✓ Canvas element found")
else:
    print("\n  ✗ Canvas element MISSING!")

# Check for Three.js import
if '/static/vendor/three/three.module.js' in html:
    print("  ✓ Three.js import found")
else:
    print("  ✗ Three.js import MISSING!")
