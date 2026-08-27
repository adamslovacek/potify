import requests
import re

resp = requests.get('http://127.0.0.1:5001', timeout=10)
resp.raise_for_status()
html = resp.text

# Find all name attributes
pattern = r'name="([^"]+)"'
matches = re.findall(pattern, html)
print("All input names found in HTML:")
for match in sorted(set(matches)):
    print(f"  {match}")
