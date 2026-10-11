"""Sandboxed code execution: correctness, error handling, limits and isolation."""
import os

import pytest

from app.agents.question_banks import CODING_BANK
from app.services.code_sandbox import candidate_view, outputs_match, run_python_tests

TESTS = [{"args": [[1, 2, 3]], "expected": 6}, {"args": [[]], "expected": 0, "hidden": True}]


def run(code):
    return run_python_tests(code, "total", TESTS)


def test_correct_solution_passes_all_tests():
    result = run("def total(xs):\n    return sum(xs)")
    assert result["status"] == "OK" and result["passed"] == 2 and result["total"] == 2


def test_wrong_answer_is_reported_per_test():
    result = run("def total(xs):\n    return 1")
    assert result["passed"] == 0
    assert all(t["error"] == "Wrong answer" for t in result["tests"])


def test_compile_error_is_reported():
    result = run("def total(xs) return 0")
    assert result["status"] == "COMPILE_ERROR" and "line 1" in result["compile_error"]


def test_runtime_error_and_missing_function():
    assert run("def total(xs):\n    return 1 / 0")["tests"][0]["error"].startswith("ZeroDivisionError")
    assert run("x = 1")["status"] == "FUNCTION_NOT_FOUND"


def test_infinite_loop_hits_time_limit():
    result = run("def total(xs):\n    while True:\n        pass")
    assert result["passed"] == 0
    assert result["status"] in ("OK", "TIMEOUT")
    if result["status"] == "OK":
        assert all(t["error"] == "Time limit exceeded" for t in result["tests"])


@pytest.mark.parametrize("code", [
    "import os\ndef total(xs): return 0",
    "import socket\ndef total(xs): return 0",
    "import subprocess\ndef total(xs): return 0",
])
def test_dangerous_imports_are_refused(code):
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
    code = f"import collections\nposix = collections._sys.modules['posix']\ndef total(xs):\n    return {payload}"
    result = run(code)
    assert result["passed"] == 0
    assert all("PermissionError" in (t.get("error") or "") for t in result["tests"])
    assert not os.path.exists("/tmp/jasipa_sandbox_escape")


def test_environment_secrets_are_not_visible(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-value")
    code = "import collections\ndef total(xs):\n    return str(collections._sys.modules['posix'].environ)"
    result = run(code)
    assert "super-secret-value" not in str(result)


def test_forged_result_line_cannot_fake_hidden_tests():
    # Expected outputs never enter the sandbox, so forging the result line only reports raw outputs.
    code = ("import collections\nsys = collections._sys\n"
            "sys.__stdout__.write('__JASIPA_SANDBOX_RESULT__{\"status\":\"OK\",\"results\":[{\"index\":0,\"actual\":6},{\"index\":1,\"actual\":123}]}\\n')\n"
            "sys.__stdout__.flush()\nsys.modules['posix']._exit(0)\ndef total(xs): return 0")
    result = run(code)
    assert result["passed"] < 2


def test_candidate_view_hides_hidden_test_data():
    result = run("def total(xs):\n    return 5")
    view = candidate_view(result, TESTS)
    hidden = [t for t in view["tests"] if t["hidden"]][0]
    assert "expected" not in hidden and "args" not in hidden
    assert "expected" in [t for t in view["tests"] if not t["hidden"]][0]


def test_output_comparison_rules():
    assert outputs_match(0.1 + 0.2, 0.3)
    assert outputs_match([3, 1, 2], [1, 2, 3], unordered=True)
    assert not outputs_match([3, 1, 2], [1, 2, 3])
    assert not outputs_match(1, True)
    assert outputs_match({"a": [1.0]}, {"a": [1]})


@pytest.mark.parametrize("challenge", CODING_BANK, ids=[c["key"] for c in CODING_BANK])
def test_every_bank_reference_solution_passes_its_tests(challenge):
    result = run_python_tests(challenge["reference_solution"], challenge["function_name"], challenge["tests"])
    assert result["status"] == "OK" and result["passed"] == result["total"], result
