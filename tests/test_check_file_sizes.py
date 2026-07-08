import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_file_sizes.py"


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True
    )


def test_passes_under_limit(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "small.py").write_text("\n".join(f"x = {i}" for i in range(10)) + "\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    result = _run(tmp_path)

    assert result.returncode == 0


def test_fails_over_limit(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "big.py").write_text("\n".join(f"x = {i}" for i in range(401)) + "\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "big.py" in result.stdout
