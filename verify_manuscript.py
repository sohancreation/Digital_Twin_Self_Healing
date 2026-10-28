import subprocess
import fitz # PyMuPDF
import re

print("Running pass 1...")
r1 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "manuscript_6pages.tex"], capture_output=True, text=True)
print("Pass 1 returncode:", r1.returncode)

print("Running pass 2...")
r2 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "manuscript_6pages.tex"], capture_output=True, text=True)
print("Pass 2 returncode:", r2.returncode)

# Check for undefined references
undef = re.findall(r"LaTeX Warning: Reference `(.*?)' on page \d+ undefined", r2.stdout)
cit_undef = re.findall(r"LaTeX Warning: Citation `(.*?)' on page \d+ undefined", r2.stdout)
print("Undefined references:", undef)
print("Undefined citations:", cit_undef)

# Check page count
doc = fitz.open("manuscript_6pages.pdf")
print("Total pages:", len(doc))
for i, page in enumerate(doc):
    text = page.get_text()
    first_line = text.split("\n")[0] if text else ""
    last_line = text.split("\n")[-2] if len(text.split("\n")) > 1 else ""
    print(f"Page {i+1}: text length = {len(text)}, first line: {first_line[:50]}..., last line: {last_line[:50]}...")
