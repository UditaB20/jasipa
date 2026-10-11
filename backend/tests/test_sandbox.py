"""Sandboxed code execution: correctness, error handling, limits and isolation."""
import os

import pytest

from app.agents.question_banks import CODING_BANK
from app.services.code_sandbox import candidate_view, outputs_match, run_python_tests

TESTS = [{"args": [[1, 2, 3]], "expected": 6}, {"args": [[]], "expected": 0, "hidden": True}]


def run(code):
    return run_python_tests(code, "total", TESTS)


def test_correct_solution_passes_all_tests():
    """Feature: Code sandbox – correct solution
    Input: def total(xs): return sum(xs) against 1 visible + 1 hidden test
    Expected: status OK, 2/2 tests passed"""
    result = run("def total(xs):\n    return sum(xs)")
    assert result["status"] == "OK" and result["passed"] == 2 and result["total"] == 2


def test_wrong_answer_is_reported_per_test():
    """Feature: Code sandbox – wrong answer
    Input: function that always returns 1
    Expected: 0/2 passed, each test reports 'Wrong answer'"""
    result = run("def total(xs):\n    return 1")
    assert result["passed"] == 0
    assert all(t["error"] == "Wrong answer" for t in result["tests"])


def test_compile_error_is_reported():
    """Feature: Code sandbox – compilation error
    Input: syntactically invalid Python
    Expected: status COMPILE_ERROR with line number"""
    result = run("def total(xs) return 0")
    assert result["status"] == "COMPILE_ERROR" and "line 1" in result["compile_error"]


def test_runtime_error_and_missing_function():
    """Feature: Code sandbox – runtime error / missing function
    Input: division by zero; module without the required function
    Expected: ZeroDivisionError reported per test; FUNCTION_NOT_FOUND status"""
    assert run("def total(xs):\n    return 1 / 0")["tests"][0]["error"].startswith("ZeroDivisionError")
    assert run("x = 1")["status"] == "FUNCTION_NOT_FOUND"


def test_infinite_loop_hits_time_limit():
    """Feature: Code sandbox – execution time limit (boundary)
    Input: while True loop
    Expected: no test passes; time limit reported"""
    result = run("def total(xs):\n    while True:\n        pass")
    assert result["passed"] == 0
    assert result["status"] in ("OK", "TIMEOUT")
    if result["status"] == "OK":
        assert all(t["error"] == "Time limit exceeded" for t in result["tests"])


def test_empty_and_oversized_submissions_are_rejected():
    """Feature: Code sandbox – input validation (boundary)
    Input: empty code; code longer than the configured maximum
    Expected: NO_CODE and REJECTED statuses without starting a process"""
    assert run("   ")["status"] == "NO_CODE"
    assert run("x = 1\n" * 5000)["status"] == "REJECTED"


@pytest.mark.parametrize("code", [
    "import os\ndef total(xs): return 0",
    "import socket\ndef total(xs): return 0",
    "import subprocess\ndef total(xs): return 0",
])
def test_dangerous_imports_are_refused(code):
    """Feature: Code sandbox – import restrictions (negative)
    Input: import of os / socket / subprocess
    Expected: ImportError 'not available in the sandbox', nothing passes"""
    result = run(code)
    assert result["passed"] == 0 and "not available in the sandbox" in (result.get("error") or "")


@pytest.mark.parametrize("payload", [
    "posix.system('touch /tmp/jasipa_sandbox_escape')",
    "posix.kill(posix.getppid(), 9)",
    "posix.open('/tmp/jasipa_sandbox_escape', posix.O_WRONLY | posix.O_CREAT)",
    "posix.listdir('/')",
    "collections._sys.modules['builtins'].open('/etc/hosts').read()",
])
def test_escape_attempts_through_preloaded_modules_are_blocked(payload):
    """Feature: Code sandbox – isolation (security, negative)
    Input: shell command, killing the parent, file write, directory listing, reading /etc/hosts via preloaded modules
    Expected: PermissionError from the audit hook; no file created on the host"""
    code = f"import collections\nposix = collections._sys.modules['posix']\ndef total(xs):\n    return {payload}"
    result = run(code)
    assert result["passed"] == 0
    assert all("PermissionError" in (t.get("error") or "") for t in result["tests"])
    assert not os.path.exists("/tmp/jasipa_sandbox_escape")


def test_environment_secrets_are_not_visible(monkeypatch):
    """Feature: Code sandbox – secret isolation (security)
    Input: GEMINI_API_KEY set in the API process; candidate code prints the environment
    Expected: the secret value never appears in the result"""
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-value")
    code = "import collections\ndef total(xs):\n    return str(collections._sys.modules['posix'].environ)"
    assert "super-secret-value" not in str(run(code))


def test_forged_result_line_cannot_fake_hidden_tests():
    """Feature: Code sandbox – result integrity (security)
    Input: code that writes a forged result line claiming outputs, then exits
    Expected: hidden test still fails because expected outputs are judged outside the sandbox"""
    code = ("import collections\nsys = collections._sys\n"
            "sys.__stdout__.write('__JASIPA_SANDBOX_RESULT__{\"status\":\"OK\",\"results\":[{\"index\":0,\"actual\":6},{\"index\":1,\"actual\":123}]}\\n')\n"
            "sys.__stdout__.flush()\nsys.modules['posix']._exit(0)\ndef total(xs): return 0")
    assert run(code)["passed"] < 2


def test_candidate_view_hides_hidden_test_data():
    """Feature: Code sandbox – candidate feedback
    Input: failing run viewed through candidate_view
    Expected: hidden test omits args/expected; visible test shows them"""
    view = candidate_view(run("def total(xs):\n    return 5"), TESTS)
    hidden = [t for t in view["tests"] if t["hidden"]][0]
    assert "expected" not in hidden and "args" not in hidden
    assert "expected" in [t for t in view["tests"] if not t["hidden"]][0]


def test_output_comparison_rules():
    """Feature: Code sandbox – output comparison
    Input: float rounding, unordered lists, bool vs int, nested dicts
    Expected: tolerant float compare, unordered flag respected, True != 1"""
    assert outputs_match(0.1 + 0.2, 0.3)
    assert outputs_match([3, 1, 2], [1, 2, 3], unordered=True)
    assert not outputs_match([3, 1, 2], [1, 2, 3])
    assert not outputs_match(1, True)
    assert outputs_match({"a": [1.0]}, {"a": [1]})


@pytest.mark.parametrize("challenge", CODING_BANK, ids=[c["key"] for c in CODING_BANK])
def test_every_bank_reference_solution_passes_its_tests(challenge):
    """Feature: Question bank – coding challenge validity
    Input: each bank challenge's reference solution
    Expected: all of its visible and hidden tests pass in the sandbox"""
    result = run_python_tests(challenge["reference_solution"], challenge["function_name"], challenge["tests"])
    assert result["status"] == "OK" and result["passed"] == result["total"], result
