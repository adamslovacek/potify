import requests
import re

# Test with all required form fields
data = {
    'pot_diameter': '140',
    'clearance': '1.2',
    'height': '135',
    'wall': '3.0',
    'base': '4.0',
    'include_bottom': 'on',
    'taper': '1.5',
    'rim_lip': '1.2',
    'texture_type': 'none',
    'texture_strength': '0.7',
    'texture_scale': '2.0',
    'texture_rotation': '0',
    'middle_inbound_turns': '0',
    'z_rotation': '0',
    'shape_type': 'polygon',
    'star_inner_ratio': '0.5',
    'sections': '256',
    'format': 'stl'
}

print("Testing polygon shape...")
resp = requests.post('http://127.0.0.1:5005/generate', data=data)
print(f"Status: {resp.status_code}")

# Extract error from HTML if present
if resp.status_code != 200:
    match = re.search(r'<div class="error">([^<]+)</div>', resp.text)
    if match:
        print(f"Error message: {match.group(1)}")
    else:
        print("Response (first 300 chars):")
        print(resp.text[:300])
else:
    print("✓ Polygon export successful!")

# Now test star shape
print("\nTesting star shape...")
data['shape_type'] = 'star'
data['star_inner_ratio'] = '0.4'
resp2 = requests.post('http://127.0.0.1:5005/generate', data=data)
print(f"Status: {resp2.status_code}")

if resp2.status_code != 200:
    match = re.search(r'<div class="error">([^<]+)</div>', resp2.text)
    if match:
        print(f"Error message: {match.group(1)}")
else:
    print("✓ Star export successful!")
