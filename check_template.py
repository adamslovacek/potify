import sys
sys.path.insert(0, 'src')
from planter_generator.web import create_app

app = create_app()

# Get the defaults that would be passed to template
response = app.test_client().get('/')
print("Status:", response.status_code)

# Check if defaults are rendered
html = response.get_data(as_text=True)
fields_to_check = [
    'include_bottom', 'shape_type', 'star_inner_ratio',
    'middle_inbound_turns', 'z_rotation'
]

print("\nFields in rendered HTML:")
for field in fields_to_check:
    if f'name="{field}"' in html:
        print(f"  ✓ {field}")
    else:
        print(f"  ✗ {field} MISSING")
