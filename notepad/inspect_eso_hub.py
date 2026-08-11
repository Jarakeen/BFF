import requests
from bs4 import BeautifulSoup

url = "https://eso-hub.com/en/skills/weapon/destruction-staff/wall-of-elements"

response = requests.get(url, timeout=20)

print("STATUS:", response.status_code)
print("LENGTH:", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

target = "Champion Points that buff Wall of Elements"

hits = []

for text_node in soup.find_all(string=True):
    text = text_node.strip()

    if target in text:
        hits.append(text_node)

print("HITS:", len(hits))

for i, hit in enumerate(hits, 1):
    print()
    print("=" * 80)
    print("MATCH", i)
    print("=" * 80)

    parent = hit.parent

    if parent:
        print(parent.parent.prettify()[:15000])