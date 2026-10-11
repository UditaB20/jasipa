"""pytest plugin: records each test's documentation docstring and real outcome to a JSON file."""
import json
import os

_RESULTS = {}
_DOCS = {}


def pytest_collection_modifyitems(items):
    for item in items:
        doc = getattr(getattr(item, "function", None), "__doc__", None) or ""
        params = getattr(getattr(item, "callspec", None), "id", None)
        _DOCS[item.nodeid] = {"doc": doc, "params": params}


def pytest_runtest_logreport(report):
    entry = _RESULTS.setdefault(report.nodeid, {"outcome": "passed", "duration": 0.0, "message": ""})
    entry["duration"] += report.duration
    if report.failed:
        entry["outcome"] = "failed" if report.when == "call" else "error"
        entry["message"] = str(report.longrepr).strip().splitlines()[-1][:300] if report.longrepr else ""
    elif report.skipped:
        entry["outcome"] = "skipped"
        entry["message"] = str(report.longrepr)[:300]


def pytest_sessionfinish(session):
    path = os.environ.get("JASIPA_CATALOG_OUT")
    if not path:
        return
    rows = [{"nodeid": nid, **_DOCS.get(nid, {}), **res} for nid, res in _RESULTS.items()]
    with open(path, "w") as handle:
        json.dump(rows, handle, indent=1)
