"""Sandboxed execution of candidate code against test cases.

Candidate code never runs inside the API process. Each run starts a fresh Python interpreter with:

* an empty temporary working directory and a cleared environment (no API keys or DB URLs),
* resource limits: CPU seconds, address space, zero-byte file writes, no child processes,
* a CPython audit hook, installed before candidate code is compiled and impossible to remove from
  Python code, that blocks sockets, subprocesses, os.system/exec/fork, file writes, deletions,
  ctypes and opening files outside the Python standard library,
* a restricted ``__import__`` that refuses modules such as os, socket, subprocess and signal,
* a per-test timer plus a wall-clock kill from the parent process.

``SANDBOX_BACKEND=docker`` additionally runs the interpreter in a throwaway container with no
network, a read-only root filesystem, a pids limit and a memory cap. The subprocess backend is
defense in depth for local and demo use; production deployments should prefer the docker backend.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

from app.config import settings

RESULT_MARKER = "__JASIPA_SANDBOX_RESULT__"

HARNESS = r'''
import builtins, io, json, signal, sys, time

RESULT_MARKER = "__JASIPA_SANDBOX_RESULT__"
payload = json.loads(sys.stdin.read())
real_stdout = sys.stdout
STDLIB_DIRS = tuple(p for p in sys.path if p and ("python3" in p or "lib-dynload" in p or p.endswith(".zip")))
BLOCKED_EVENT_PREFIXES = (
    "socket.", "subprocess.", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty",
    "os.kill", "os.killpg", "os.remove", "os.unlink", "os.rename", "os.rmdir", "os.mkdir", "os.chmod",
    "os.chown", "os.symlink", "os.link", "os.truncate", "os.putenv", "os.unsetenv", "os.chdir", "os.startfile",
    "os.listdir", "os.scandir", "os.listxattr", "os.getxattr", "os.setxattr", "os.utime", "glob.glob",
    "shutil.", "ctypes.", "winreg.", "urllib.", "http.", "ftplib.", "smtplib.", "webbrowser.", "pty.",
    "sys._getframe", "sys.setprofile", "sys.settrace", "sys.addaudithook", "code.", "cpython.run_",
    "pickle.find_class", "marshal.load", "builtins.input",
)

def audit(event, args):
    if event.startswith(BLOCKED_EVENT_PREFIXES):
        raise PermissionError(f"Operation not permitted in sandbox: {event}")
    if event == "open":
        path, mode = args[0], (args[1] if len(args) > 1 else "r")
        writing = any(flag in mode for flag in "wax+") if isinstance(mode, str) else bool(isinstance(mode, int) and mode & 0o3)
        if writing or not isinstance(path, str) or not path.startswith(STDLIB_DIRS):
            raise PermissionError("File access is not permitted in sandbox")

DENIED_MODULES = frozenset({
    "os", "posix", "nt", "sys", "socket", "_socket", "subprocess", "multiprocessing", "ctypes", "_ctypes",
    "signal", "resource", "shutil", "pathlib", "importlib", "io", "_io", "builtins", "urllib", "http", "ftplib",
    "smtplib", "ssl", "select", "selectors", "asyncio", "threading", "_thread", "pty", "fcntl", "mmap", "gc",
    "inspect", "code", "codeop", "pickle", "marshal", "tempfile", "glob", "webbrowser", "sqlite3", "zipimport",
    "pkgutil", "runpy", "__main__", "unittest"})
real_import = builtins.__import__

def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level == 0 and name.split(".")[0] in DENIED_MODULES:
        raise ImportError(f"Module '{name}' is not available in the sandbox")
    return real_import(name, globals, locals, fromlist, level)

def normalise(value):
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError, RecursionError):
        return {"__unserialisable__": type(value).__name__}

def emit(result):
    sys.stdout = real_stdout
    real_stdout.write(RESULT_MARKER + json.dumps(result) + "\n")
    real_stdout.flush()

class TestTimeout(Exception):
    pass

def on_alarm(signum, frame):
    raise TestTimeout()

signal.signal(signal.SIGALRM, on_alarm)
per_test = float(payload.get("per_test_seconds", 1.0))
sys.addaudithook(audit)  # From here on every blocked operation raises, and the hook cannot be removed.

try:
    compiled = compile(payload["code"], "<candidate>", "exec")
except SyntaxError as exc:
    emit({"status": "COMPILE_ERROR", "compile_error": f"{exc.msg} (line {exc.lineno})", "results": []})
    raise SystemExit(0)

safe_builtins = dict(vars(builtins))
safe_builtins["__import__"] = safe_import
for name in ("open", "exec", "eval", "compile", "input", "breakpoint", "help", "exit", "quit", "globals", "vars"):
    safe_builtins.pop(name, None)
namespace = {"__builtins__": safe_builtins, "__name__": "candidate_solution"}
captured = io.StringIO()
sys.stdout = captured
try:
    signal.setitimer(signal.ITIMER_REAL, max(per_test, 1.0))
    exec(compiled, namespace)
    signal.setitimer(signal.ITIMER_REAL, 0)
except TestTimeout:
    emit({"status": "TIMEOUT", "error": "Module-level code exceeded the time limit.", "results": []})
    raise SystemExit(0)
except BaseException as exc:
    signal.setitimer(signal.ITIMER_REAL, 0)
    emit({"status": "RUNTIME_ERROR", "error": f"{type(exc).__name__}: {str(exc)[:300]}", "results": []})
    raise SystemExit(0)

func = namespace.get(payload["function_name"])
if not callable(func):
    emit({"status": "FUNCTION_NOT_FOUND", "error": f"Define a function named '{payload['function_name']}'.", "results": []})
    raise SystemExit(0)

results = []
for index, args in enumerate(payload["inputs"]):
    entry = {"index": index}
    started = time.perf_counter()
    try:
        signal.setitimer(signal.ITIMER_REAL, per_test)
        actual = func(*args)
        signal.setitimer(signal.ITIMER_REAL, 0)
        entry["actual"] = normalise(actual)
    except TestTimeout:
        entry["error"] = "Time limit exceeded"
    except RecursionError:
        signal.setitimer(signal.ITIMER_REAL, 0)
        entry["error"] = "RecursionError: maximum recursion depth exceeded"
    except MemoryError:
        signal.setitimer(signal.ITIMER_REAL, 0)
        entry["error"] = "Memory limit exceeded"
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        entry["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    entry["runtime_ms"] = round((time.perf_counter() - started) * 1000, 2)
    results.append(entry)

emit({"status": "OK", "results": results, "stdout": captured.getvalue()[:2000]})
'''


def _limit_resources():  # pragma: no cover - runs in the child process
    import resource
    cpu = int(settings.SANDBOX_TIMEOUT_SECONDS) + 1
    memory = settings.SANDBOX_MEMORY_MB * 1024 * 1024
    limits = [
        (resource.RLIMIT_CPU, (cpu, cpu)),
        (resource.RLIMIT_FSIZE, (0, 0)),
        (resource.RLIMIT_CORE, (0, 0)),
    ]
    if hasattr(resource, "RLIMIT_NPROC"):
        limits.append((resource.RLIMIT_NPROC, (0, 0)))
    if sys.platform.startswith("linux"):
        limits.append((resource.RLIMIT_AS, (memory, memory)))
    else:
        limits.append((resource.RLIMIT_DATA, (memory, memory)))
    for kind, value in limits:
        try:
            resource.setrlimit(kind, value)
        except (ValueError, OSError):
            pass
    os.setsid()


def _command() -> List[str]:
    if settings.SANDBOX_BACKEND == "docker" and shutil.which("docker"):
        return ["docker", "run", "--rm", "-i", "--network", "none", "--read-only", "--tmpfs", "/tmp:size=8m",
                "--memory", f"{settings.SANDBOX_MEMORY_MB}m", "--memory-swap", f"{settings.SANDBOX_MEMORY_MB}m",
                "--cpus", "0.5", "--pids-limit", "32", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--user", "65534:65534", settings.SANDBOX_DOCKER_IMAGE, "python", "-I", "-c", HARNESS]
    return [sys.executable, "-I", "-S", "-c", HARNESS]


def run_python_tests(code: str, function_name: str, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Runs ``code`` against ``tests`` ([{args, expected, hidden?, unordered?}]) and reports per-test results."""
    started = time.perf_counter()
    base = {"language": "python", "function_name": function_name, "total": len(tests), "passed": 0,
            "backend": settings.SANDBOX_BACKEND}
    if not code or not code.strip():
        return {**base, "status": "NO_CODE", "error": "No code was submitted.", "tests": [], "duration_ms": 0}
    if len(code) > settings.SANDBOX_MAX_CODE_CHARS:
        return {**base, "status": "REJECTED", "error": f"Submission exceeds {settings.SANDBOX_MAX_CODE_CHARS} characters.",
                "tests": [], "duration_ms": 0}
    if not tests:
        return {**base, "status": "NO_TESTS", "error": "This question has no test cases.", "tests": [], "duration_ms": 0}

    per_test = max(0.2, min(1.0, settings.SANDBOX_TIMEOUT_SECONDS / max(1, len(tests))))
    # Expected outputs never enter the sandbox: the child only reports what the code returned.
    payload = json.dumps({"code": code, "function_name": function_name, "per_test_seconds": per_test,
                          "inputs": [list(test.get("args", [])) for test in tests]})
    use_docker = settings.SANDBOX_BACKEND == "docker" and shutil.which("docker")
    workdir = tempfile.mkdtemp(prefix="jasipa-sandbox-")
    try:
        proc = subprocess.run(
            _command(), input=payload, capture_output=True, text=True, cwd=workdir,
            timeout=settings.SANDBOX_TIMEOUT_SECONDS + (8 if use_docker else 2),
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"},
            preexec_fn=None if use_docker else _limit_resources,
        )
    except subprocess.TimeoutExpired:
        return {**base, "status": "TIMEOUT", "error": "Execution exceeded the time limit.", "tests": [],
                "duration_ms": _ms(started)}
    except OSError as exc:
        return {**base, "status": "SANDBOX_ERROR", "error": f"Sandbox could not start: {type(exc).__name__}",
                "tests": [], "duration_ms": _ms(started)}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    line = next((l for l in reversed(proc.stdout.splitlines()) if l.startswith(RESULT_MARKER)), None)
    if line is None:
        stderr = (proc.stderr or "").strip().splitlines()
        if proc.returncode in (-9, -24, 137) or "MemoryError" in (proc.stderr or ""):
            status, error = "RESOURCE_LIMIT", "Execution exceeded the memory or CPU limit."
        else:
            status, error = "RUNTIME_ERROR", (stderr[-1][:300] if stderr else "The program terminated unexpectedly.")
        return {**base, "status": status, "error": error, "tests": [], "duration_ms": _ms(started)}

    try:
        raw = json.loads(line[len(RESULT_MARKER):])
    except ValueError:
        return {**base, "status": "RUNTIME_ERROR", "error": "The program produced unreadable output.", "tests": [],
                "duration_ms": _ms(started)}
    status = raw.get("status", "RUNTIME_ERROR")
    by_index = {item.get("index"): item for item in raw.get("results", []) if isinstance(item, dict)}
    judged = []
    if status == "OK":
        for index, test in enumerate(tests):
            item = by_index.get(index, {"error": "No result reported"})
            entry = {"index": index, "hidden": bool(test.get("hidden")), "runtime_ms": item.get("runtime_ms")}
            if "error" in item:
                entry.update(passed=False, error=str(item["error"])[:300])
            else:
                actual = item.get("actual")
                entry["passed"] = outputs_match(actual, test.get("expected"), bool(test.get("unordered")))
                entry["actual"] = actual if len(json.dumps(actual)) <= 500 else json.dumps(actual)[:500]
                if not entry["passed"]:
                    entry["error"] = "Wrong answer"
            judged.append(entry)
    passed = sum(1 for test in judged if test["passed"])
    result = {**base, "status": status, "tests": judged, "passed": passed, "duration_ms": _ms(started)}
    for key in ("error", "compile_error", "stdout"):
        if raw.get(key):
            result[key] = str(raw[key])[:2000]
    return result


def outputs_match(actual: Any, expected: Any, unordered: bool = False) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected or actual == expected and type(actual) is type(expected)
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-6, abs_tol=1e-9)
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return False
        if unordered:
            key = lambda value: json.dumps(value, sort_keys=True)
            return sorted(map(key, actual)) == sorted(map(key, expected))
        return all(outputs_match(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, dict) and isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(outputs_match(actual[k], expected[k]) for k in expected)
    return actual == expected


def candidate_view(result: Dict[str, Any], tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execution feedback safe for candidates: hidden test inputs/outputs are withheld."""
    visible = []
    for test in result.get("tests", []):
        case = tests[test["index"]] if test["index"] < len(tests) else {}
        item = {"index": test["index"], "hidden": test.get("hidden", False), "passed": test.get("passed", False),
                "error": test.get("error"), "runtime_ms": test.get("runtime_ms")}
        if not test.get("hidden"):
            item.update(args=case.get("args"), expected=case.get("expected"), actual=test.get("actual"))
        visible.append(item)
    keep = {"status", "error", "compile_error", "passed", "total", "stdout", "duration_ms"}
    return {**{k: v for k, v in result.items() if k in keep}, "tests": visible}


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
