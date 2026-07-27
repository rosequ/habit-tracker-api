import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive_plan.sh"


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=tmp_path, check=True)
    (tmp_path / "Plan.md").write_text("# Plan: Do the thing (issue #99)\n\nSome content.\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)


def _checkout(tmp_path: Path, branch: str) -> None:
    subprocess.run(["git", "checkout", "-q", "-b", branch, "main"], cwd=tmp_path, check=True)


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_issue_and_slug_from_branch_name(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _checkout(tmp_path, "agent/issue-42-add-widget")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    archived = tmp_path / "docs" / "plans" / "42-add-widget.md"
    assert archived.exists()
    assert "Do the thing" in archived.read_text()


def test_falls_back_to_date_and_branch_name_when_no_issue_number(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _checkout(tmp_path, "some-descriptive-branch")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    plans = list((tmp_path / "docs" / "plans").glob("*.md"))
    assert len(plans) == 1
    assert plans[0].name.endswith("-some-descriptive-branch.md")
    assert plans[0].name[:4].isdigit()  # YYYY- date prefix


def test_falls_back_to_plan_heading_when_branch_has_no_descriptive_part(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _checkout(tmp_path, "agent/issue-7")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    archived = tmp_path / "docs" / "plans" / "7-do-the-thing-issue-99.md"
    assert archived.exists()


def test_explicit_slug_argument_overrides_inference(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _checkout(tmp_path, "agent/issue-7")

    result = _run(tmp_path, "my-custom-slug")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "docs" / "plans" / "7-my-custom-slug.md").exists()


def test_includes_implement_md_when_present(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "Implement.md").write_text("# Implementation log\n\nDid stuff.\n")
    _checkout(tmp_path, "agent/issue-42-add-widget")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    content = (tmp_path / "docs" / "plans" / "42-add-widget.md").read_text()
    assert "Did stuff." in content


def test_fails_without_plan_md(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "Plan.md").unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "remove plan"], cwd=tmp_path, check=True)
    _checkout(tmp_path, "agent/issue-42-add-widget")

    result = _run(tmp_path)

    assert result.returncode != 0
    assert not (tmp_path / "docs" / "plans").exists()
