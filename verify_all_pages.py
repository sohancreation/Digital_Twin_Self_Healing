import sys
sys.stdout.reconfigure(encoding='utf-8')
import fitz

doc = fitz.open("test_page6_fit2.pdf")
print("Total pages:", len(doc))

elements = [
    "Fig. 1", "Fig. 2", "Fig. 3", "Fig. 4", "Fig. 5", "Fig. 6", "Fig. 7",
    "TABLE I", "TABLE II", "TABLE III", "TABLE IV",
    "Algorithm 1",
    "Theorem 1", "Theorem 2",
    "Proposition 1", "Proposition 2", "Proposition 3",
    "Threats to Validity", "REFERENCES"
]

found_map = {e: [] for e in elements}

for pno, page in enumerate(doc):
    txt = page.get_text()
    for e in elements:
        if e.lower() in txt.lower():
            found_map[e].append(pno + 1)

print("\n--- Element Page Locations ---")
for e, pages in found_map.items():
    print(f"  {e:20s}: Page(s) {pages}")

# Verify no undefined references in pdf text
text_all = ""
for page in doc:
    text_all += page.get_text()

import re
undef = re.findall(r"\?\?", text_all)
print("\nUndefined '??' count:", len(undef))
if undef:
    print("WARNING: Undefined references found!")
