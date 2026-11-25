"""Guard: no code path prints, logs or writes an environment variable's value (API keys live there)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ["src", "eval", "scripts", "infra", "app.py"]
OUTPUT_CALL = re.compile(r"\b(print|pprint|write|writelines|\w*log\w*\.\w+|logging\.\w+|st\.\w+)\s*\(")
ENV_READ = re.compile(r"os\.environ|os\.getenv|getenv\(|dotenv_values")


def offending_lines(paths: list[Path]) -> list[str]:
    hits = []
    for p in paths:
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if OUTPUT_CALL.search(line) and ENV_READ.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{n}: {line.strip()}")
    return hits


def python_files() -> list[Path]:
    files = []
    for s in SCANNED:
        p = ROOT / s
        files += [p] if p.is_file() else sorted(p.rglob("*.py"))
    return [f for f in files if ".venv" not in f.parts]


def test_detector_flags_env_values_in_output(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('import os\nprint(os.environ["GROQ_API_KEY"])\nlogger.info(os.getenv("X"))\n')
    ok = tmp_path / "ok.py"
    ok.write_text('import os\nkey = os.getenv("X")\nprint("key set:", bool(key))\n')
    global ROOT
    old, ROOT = ROOT, tmp_path
    try:
        assert len(offending_lines([bad])) == 2
        assert offending_lines([ok]) == []
    finally:
        ROOT = old


def test_repo_never_outputs_env_values():
    assert offending_lines(python_files()) == []
