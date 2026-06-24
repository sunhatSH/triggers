"""Tests for user vs project root discovery."""
from pathlib import Path

from triggerctl.roots import Root, all_roots, project_root, user_root


def test_project_prefers_repo_triggers_over_claude_triggers(tmp_path, monkeypatch):
    """When repo has both triggers/ and .claude/triggers (user symlink), pick triggers/."""
    repo = tmp_path / "repo"
    user_trig = repo / ".claude" / "triggers"
    proj_trig = repo / "triggers"
    user_trig.mkdir(parents=True)
    proj_trig.mkdir(parents=True)

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    # Simulate user root == repo/.claude/triggers (shared-disk layout)
    user_link = fake_home / ".claude" / "triggers"
    user_link.parent.mkdir(parents=True, exist_ok=True)
    user_link.symlink_to(user_trig, target_is_directory=True)

    pr = project_root(repo)
    assert pr.path.resolve() == proj_trig.resolve()
    assert pr.kind == "project"


def test_all_roots_includes_both_user_and_project(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    proj_trig = repo / "triggers"
    proj_trig.mkdir(parents=True)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    user_trig = fake_home / ".claude" / "triggers"
    user_trig.mkdir(parents=True)
    (user_trig / "system-triggers").mkdir()
    (user_trig / "system-triggers" / "x.md").write_text(
        "---\nname: x\nenabled: true\nwhen: test\n---\n\nbody\n", encoding="utf-8"
    )

    roots = all_roots(repo)
    kinds = {r.kind for r in roots}
    assert kinds == {"user", "project"}


def test_project_claude_md_at_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    trig = repo / "triggers"
    trig.mkdir()
    root = Root("project", trig)
    assert root.claude_md == repo / "CLAUDE.md"
    assert root.base == repo


def test_find_prefers_project_over_user(tmp_path, monkeypatch):
    from triggerctl.model import find

    repo = tmp_path / "repo"
    proj_trig = repo / "triggers"
    proj_trig.mkdir(parents=True)
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    user_trig = fake_home / ".claude" / "triggers"
    user_trig.mkdir(parents=True)

    for root_path, val in ((proj_trig, "project-val"), (user_trig, "user-val")):
        p = root_path / "t-triggers" / "dup.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            f"---\nname: dup\nenabled: true\nwhen: w\n---\n\n{val}\n",
            encoding="utf-8",
        )

    ur = user_root()
    pr = project_root(repo)
    t = find([ur, pr], "dup")
    assert t is not None and t.body.strip() == "project-val"
