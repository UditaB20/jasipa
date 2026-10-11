"""Runs every JASIPA test suite and writes the executed test-case table.

    python scripts/run_all_tests.py

Suites: backend pytest (unit, API, agents, database), frontend Vitest (components, forms, formatting),
and Playwright end-to-end tests against the real backend + frontend + seeded database. Results are
taken from each runner's own output; nothing is marked passed unless it executed and passed.
Outputs: docs/test-results/TEST_CASES.md, docs/test-results/test_cases.csv, docs/test-results/summary.json
"""
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "test-results")
os.makedirs(OUT, exist_ok=True)


def run(cmd, cwd, env=None):
    print(f"$ {' '.join(cmd)}  (in {os.path.relpath(cwd, ROOT)})", flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
    print("   " + "\n   ".join(tail), flush=True)
    return proc.returncode


def parse_doc(doc):
    fields = {"feature": "", "input": "", "expected": ""}
    for line in (doc or "").splitlines():
        match = re.match(r"\s*(Feature|Input|Expected):\s*(.*)", line)
        if match:
            fields[match.group(1).lower()] = match.group(2).strip()
    return fields


def parse_title(title):
    match = re.match(r"(.*?) — input: (.*?) — expected: (.*)$", title)
    return {"feature": match.group(1), "input": match.group(2), "expected": match.group(3)} if match else {"feature": title, "input": "", "expected": ""}


def status_of(outcome):
    return {"passed": "Pass", "failed": "Fail", "error": "Fail", "timedOut": "Fail", "skipped": "Blocked", "interrupted": "Blocked"}.get(outcome, "Blocked")


def actual(outcome, message, duration_s):
    if outcome == "passed":
        return f"Behaved as expected; all assertions passed ({duration_s:.2f} s)."
    if outcome == "skipped":
        return f"Not executed: {message or 'skipped'}"
    return f"Observed: {message or 'assertion failed'}"


def backend():
    path = os.path.join(OUT, "backend-results.json")
    code = run([os.path.join(ROOT, "backend", ".venv", "bin", "python"), "-m", "pytest", "-q", "-p", "tests.catalog_plugin", "-p", "no:warnings", "tests"],
               os.path.join(ROOT, "backend"), {"JASIPA_CATALOG_OUT": path, "PYTHONPATH": "."})
    rows = []
    for r in json.load(open(path)):
        fields = parse_doc(r.get("doc"))
        if r.get("params"):
            fields["input"] = f"{fields['input']} [case: {r['params']}]"
        module = r["nodeid"].split("::")[0].replace("tests/", "").replace(".py", "")
        rows.append({"suite": "Backend (pytest)", "module": module, **fields, "status": status_of(r["outcome"]),
                     "actual": actual(r["outcome"], r.get("message"), r.get("duration", 0))})
    return code, rows


def frontend():
    path = os.path.join(OUT, "frontend-results.json")
    code = run(["npx", "vitest", "run", "--reporter=json", f"--outputFile={path}"], os.path.join(ROOT, "frontend"))
    rows = []
    for file in json.load(open(path))["testResults"]:
        module = os.path.relpath(file["name"], os.path.join(ROOT, "frontend"))
        for t in file["assertionResults"]:
            fields = parse_title(t["title"])
            message = (t.get("failureMessages") or [""])[0].splitlines()[0][:300] if t.get("failureMessages") else ""
            rows.append({"suite": "Frontend (Vitest)", "module": module, **fields, "status": status_of(t["status"]),
                         "actual": actual(t["status"], message, (t.get("duration") or 0) / 1000)})
    return code, rows


def e2e():
    path = os.path.join(OUT, "e2e-results.json")
    code = run(["npx", "playwright", "test"], os.path.join(ROOT, "frontend"))
    rows = []

    def walk(suite):
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                result = test["results"][-1] if test["results"] else {"status": "skipped", "duration": 0}
                message = (result.get("error") or {}).get("message", "").splitlines()[0][:300] if result.get("error") else ""
                rows.append({"suite": "End-to-end (Playwright)", "module": spec["file"], **parse_title(spec["title"]),
                             "status": status_of(result["status"]), "actual": actual(result["status"], message, result.get("duration", 0) / 1000)})
        for child in suite.get("suites", []):
            walk(child)

    for suite in json.load(open(path))["suites"]:
        walk(suite)
    return code, rows


def main():
    started = datetime.now(timezone.utc)
    suites = [backend(), frontend(), e2e()]
    prefix = {"Backend (pytest)": "BE", "Frontend (Vitest)": "FE", "End-to-end (Playwright)": "E2E"}
    rows, counters = [], {}
    for _, suite_rows in suites:
        for row in suite_rows:
            p = prefix[row["suite"]]
            counters[p] = counters.get(p, 0) + 1
            rows.append({"id": f"{p}-{counters[p]:03d}", **row})
    totals = {s: {"total": 0, "Pass": 0, "Fail": 0, "Blocked": 0} for s in prefix}
    for row in rows:
        totals[row["suite"]]["total"] += 1
        totals[row["suite"]][row["status"]] += 1
    summary = {"executed_at_utc": started.isoformat(timespec="seconds"), "python": sys.version.split()[0],
               "exit_codes": [code for code, _ in suites], "totals": totals,
               "overall": {k: sum(t[k] for t in totals.values()) for k in ("total", "Pass", "Fail", "Blocked")}}
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    with open(os.path.join(OUT, "test_cases.csv"), "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Test Case ID", "Suite", "Module", "Feature", "Test Input", "Expected Result", "Actual Result", "Status"])
        for r in rows:
            writer.writerow([r["id"], r["suite"], r["module"], r["feature"], r["input"], r["expected"], r["actual"], r["status"]])
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    lines = ["# JASIPA test cases and results", "",
             f"Executed {started.strftime('%Y-%m-%d %H:%M UTC')} by `python scripts/run_all_tests.py`. Every row comes from the runner's own result file; nothing is marked Pass without executing.", "",
             "| Suite | Total | Pass | Fail | Blocked |", "|---|---|---|---|---|"]
    for name, t in totals.items():
        lines.append(f"| {name} | {t['total']} | {t['Pass']} | {t['Fail']} | {t['Blocked']} |")
    o = summary["overall"]
    lines += [f"| **All** | **{o['total']}** | **{o['Pass']}** | **{o['Fail']}** | **{o['Blocked']}** |", "",
              "| Test Case ID | Feature | Test Input | Expected Result | Actual Result | Status |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {esc(r['feature'])} | {esc(r['input'])} | {esc(r['expected'])} | {esc(r['actual'])} | {r['status']} |")
    open(os.path.join(OUT, "TEST_CASES.md"), "w").write("\n".join(lines) + "\n")
    print(json.dumps(summary["overall"]))
    return 0 if o["Fail"] == 0 and o["Blocked"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
