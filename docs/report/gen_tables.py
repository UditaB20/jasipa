"""Builds chapters/test_table.tex (full executed test-case table) from docs/test-results/test_cases.csv."""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "test-results")


def tex(s):
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
                 ("≥", r"$\geq$"), ("≤", r"$\leq$"), ("→", r"$\rightarrow$"), ("×", r"$\times$"), ("–", "--"), ("—", "---"),
                 ("…", "..."), ("’", "'"), ("“", "``"), ("”", "''"), ("·", r"$\cdot$"), ("√", "sqrt"), ("⁄", "/")]:
        s = s.replace(a, b)
    return s.replace(r"\_", r"\_\allowbreak ").replace("/", r"/\allowbreak ")


rows = list(csv.DictReader(open(os.path.join(RESULTS, "test_cases.csv"))))
summary = json.load(open(os.path.join(RESULTS, "summary.json")))
out = [r"\begingroup\scriptsize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.15}",
       r"\begin{longtable}{|>{\raggedright\arraybackslash}p{1.15cm}|>{\raggedright\arraybackslash}p{2.6cm}|>{\raggedright\arraybackslash}p{3.3cm}|>{\raggedright\arraybackslash}p{3.3cm}|>{\raggedright\arraybackslash}p{3.0cm}|>{\raggedright\arraybackslash}p{0.85cm}|}",
       r"\caption{Executed test cases (generated from the test runners' result files)}\label{tab:alltests}\\ \hline",
       r"\textbf{ID} & \textbf{Feature} & \textbf{Test input} & \textbf{Expected result} & \textbf{Actual result} & \textbf{Status}\\ \hline\endfirsthead",
       r"\hline \textbf{ID} & \textbf{Feature} & \textbf{Test input} & \textbf{Expected result} & \textbf{Actual result} & \textbf{Status}\\ \hline\endhead"]
for r in rows:
    out.append(" & ".join(tex(r[k]) for k in ["Test Case ID", "Feature", "Test Input", "Expected Result", "Actual Result", "Status"]) + r"\\ \hline")
out += [r"\end{longtable}\endgroup"]
open(os.path.join(HERE, "chapters", "test_table.tex"), "w").write("\n".join(out) + "\n")
t = summary["totals"]
lines = [r"\begin{table}[H]\centering\small\caption{Test execution summary}\label{tab:testsummary}",
         r"\begin{tabular}{|l|r|r|r|r|}\hline \textbf{Suite} & \textbf{Total} & \textbf{Pass} & \textbf{Fail} & \textbf{Blocked}\\ \hline"]
for name, v in t.items():
    lines.append(f"{tex(name)} & {v['total']} & {v['Pass']} & {v['Fail']} & {v['Blocked']}\\\\ \\hline")
o = summary["overall"]
lines += [f"\\textbf{{All}} & \\textbf{{{o['total']}}} & \\textbf{{{o['Pass']}}} & \\textbf{{{o['Fail']}}} & \\textbf{{{o['Blocked']}}}\\\\ \\hline",
          r"\end{tabular}\end{table}"]
open(os.path.join(HERE, "chapters", "test_summary.tex"), "w").write("\n".join(lines) + "\n")
print(len(rows), "rows;", o)
