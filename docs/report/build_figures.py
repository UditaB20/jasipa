"""Compiles each TikZ figure to PDF (for LaTeX) and PNG (for slides and poster). Requires tectonic and PyMuPDF."""
import os
import subprocess
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "images", "generated")
os.makedirs(OUT, exist_ok=True)
STYLES = open(os.path.join(SRC, "styles.tex")).read()

for name in sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".tex") and f != "styles.tex"):
    body = open(os.path.join(SRC, f"{name}.tex")).read()
    doc = ("\\documentclass[border=6pt]{standalone}\n\\usepackage{tikz}\n\\usepackage[T1]{fontenc}\n\\usepackage{helvet}\n"
           f"{STYLES}\n\\begin{{document}}\n{body}\n\\end{{document}}\n")
    path = os.path.join(OUT, f"{name}.tex")
    open(path, "w").write(doc)
    proc = subprocess.run(["tectonic", "-X", "compile", f"{name}.tex"], cwd=OUT, capture_output=True, text=True)
    if proc.returncode:
        print(name, "FAILED\n", proc.stderr[-1500:])
        continue
    pdf = fitz.open(os.path.join(OUT, f"{name}.pdf"))
    pdf[0].get_pixmap(matrix=fitz.Matrix(4, 4)).save(os.path.join(OUT, f"{name}.png"))
    os.remove(path)
    print(name, "ok")
