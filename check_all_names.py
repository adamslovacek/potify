import requests

resp = requests.get('http://127.0.0.1:5005')
html = resp.text

# Find all name attributes
import re
pattern = r'name="([^"]+)"'
matches = re.findall(pattern, html)
print("All input names found in HTML:")
for match in sorted(set(matches)):
    print(f"  {match}")
