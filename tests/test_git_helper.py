# Copyright (c) 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from ai_changelog_msg.git_helper import GitRepository


def _make_subprocess_recorder() -> tuple[list, object]:
    """Return (calls, _run) where _run records positional subprocess.run args."""
    calls: list = []

    def _run(cmd, check, capture_output, text):
        calls.append(
            {
                "cmd": cmd,
                "check": check,
                "capture_output": capture_output,
                "text": text,
            }
        )
        return SimpleNamespace(returncode=0)

    return calls, _run


def _assert_single_subprocess_call(calls: list, expected_cmd: list[str]) -> None:
    """Assert a single successful subprocess.run call with the expected args."""
    assert len(calls) == 1
    assert calls[0]["check"] is True
    assert calls[0]["capture_output"] is True
    assert calls[0]["text"] is True
    assert calls[0]["cmd"] == expected_cmd


class _FakeGit:
    def __init__(
        self, *, diff_result=None, show_result=None, note_result=None, tag_result=""
    ):
        self.diff_result = diff_result
        self.show_result = show_result
        self.note_result = note_result
        self.tag_result = tag_result

    def diff(self, parent_hash, commit_hash):
        if isinstance(self.diff_result, Exception):
            raise self.diff_result
        return self.diff_result

    def show(self, commit_hash):
        if isinstance(self.show_result, Exception):
            raise self.show_result
        return self.show_result

    def notes(self, *args):
        if isinstance(self.note_result, Exception):
            raise self.note_result
        return self.note_result

    def tag(self, *args):
        return self.tag_result


def _make_repo(fake_git=None, tags=None, remote_url=None):
    repo = GitRepository.__new__(GitRepository)
    repo.repo_path = Path("/tmp/repo")
    repo.repo = SimpleNamespace(
        git=fake_git or _FakeGit(),
        iter_commits=lambda ref: [1, 2, 3],
        tags=tags or [],
        remotes=(
            SimpleNamespace(origin=SimpleNamespace(url=remote_url))
            if remote_url is not None
            else SimpleNamespace()
        ),
        head=SimpleNamespace(commit=object()),
    )
    return repo


def _make_repo_with_head_commit(remote_url: str) -> GitRepository:
    commit = SimpleNamespace(
        hexsha="abc12345",
        message="feat: add snapshot helper\n",
        author=SimpleNamespace(name="Alice"),
        committed_datetime=SimpleNamespace(isoformat=lambda: "2026-08-05T12:00:00"),
    )
    repo = _make_repo(remote_url=remote_url)
    repo.repo = SimpleNamespace(
        git=repo.repo.git,
        iter_commits=repo.repo.iter_commits,
        tags=repo.repo.tags,
        remotes=repo.repo.remotes,
        head=SimpleNamespace(commit=commit),
        active_branch=SimpleNamespace(name="main"),
    )
    return repo


def test_get_all_commits_honors_limit():
    repo = _make_repo()

    assert repo.get_all_commits(limit=2) == [1, 2]
    assert repo.get_all_commits(limit=None) == [1, 2, 3]


def test_get_commit_diff_uses_parent_when_present():
    fake_git = _FakeGit(diff_result="+added")
    repo = _make_repo(fake_git=fake_git)
    commit = SimpleNamespace(
        hexsha="abc12345", parents=[SimpleNamespace(hexsha="parent")]
    )

    assert repo.get_commit_diff(commit) == "+added"


def test_get_commit_diff_uses_show_for_root_commit_and_returns_error_on_failure():
    repo = _make_repo(fake_git=_FakeGit(show_result="root diff"))
    root_commit = SimpleNamespace(hexsha="abc12345", parents=[])
    assert repo.get_commit_diff(root_commit) == "root diff"

    failing_repo = _make_repo(fake_git=_FakeGit(diff_result=RuntimeError("bad diff")))
    commit = SimpleNamespace(
        hexsha="abc12345", parents=[SimpleNamespace(hexsha="parent")]
    )
    assert "[Error retrieving diff: bad diff]" == failing_repo.get_commit_diff(commit)


def test_get_note_returns_none_when_missing():
    repo = _make_repo(fake_git=_FakeGit(note_result=RuntimeError("missing")))

    assert repo.get_note("abc", "ai-changelog") is None


def test_get_note_returns_note_content_when_present():
    repo = _make_repo(fake_git=_FakeGit(note_result="existing note"))

    assert repo.get_note("abc", "ai-changelog") == "existing note"


def test_get_commit_diff_returns_placeholder_when_empty():
    repo = _make_repo(fake_git=_FakeGit(diff_result=""))
    commit = SimpleNamespace(
        hexsha="abc12345", parents=[SimpleNamespace(hexsha="parent")]
    )

    assert repo.get_commit_diff(commit) == "[No changes to display]"


def test_set_note_invokes_git_notes_add_with_force(monkeypatch):
    repo = _make_repo()
    calls, _run = _make_subprocess_recorder()
    monkeypatch.setattr(subprocess, "run", _run)

    repo.set_note("abc123", "hello world", "ai-changelog")

    _assert_single_subprocess_call(
        calls,
        [
            "git",
            "-C",
            "/tmp/repo",
            "notes",
            "--ref",
            "ai-changelog",
            "add",
            "-m",
            "hello world",
            "-f",
            "abc123",
        ],
    )


def test_set_note_raises_runtime_error_on_subprocess_failure(monkeypatch):
    repo = _make_repo()

    def _run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1,
            kwargs.get("args", args[0] if args else "git"),
            stderr="failure",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match="Failed to set git note"):
        repo.set_note("abc123", "hello world", "ai-changelog")


def test_clear_notes_returns_false_when_namespace_missing(monkeypatch):
    repo = _make_repo()
    calls = []

    def _run(cmd, check, capture_output, text):
        calls.append({"cmd": cmd, "check": check})
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(subprocess, "run", _run)

    assert repo.clear_notes("ai-changelog") is False
    assert len(calls) == 1
    assert calls[0]["check"] is False
    assert calls[0]["cmd"][-1] == "refs/notes/ai-changelog"


def test_clear_notes_deletes_existing_namespace(monkeypatch):
    repo = _make_repo()
    calls = []

    def _run(cmd, check, capture_output, text):
        calls.append({"cmd": cmd, "check": check})
        if "show-ref" in cmd:
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", _run)

    assert repo.clear_notes("ai-changelog") is True
    assert len(calls) == 2
    assert calls[0]["check"] is False
    assert calls[1]["check"] is True
    assert calls[1]["cmd"] == [
        "git",
        "-C",
        "/tmp/repo",
        "update-ref",
        "-d",
        "refs/notes/ai-changelog",
    ]


def test_clear_notes_raises_runtime_error_when_delete_fails(monkeypatch):
    repo = _make_repo()

    def _run(cmd, check, capture_output, text):
        if "show-ref" in cmd:
            return SimpleNamespace(returncode=0)
        raise subprocess.CalledProcessError(1, cmd, stderr="cannot delete")

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match="Failed to clear git notes namespace"):
        repo.clear_notes("ai-changelog")


def test_has_commits_false_when_head_commit_access_raises():
    repo = _make_repo()

    class _BrokenHead:
        @property
        def commit(self):
            raise RuntimeError("no commits")

    repo.repo = SimpleNamespace(head=_BrokenHead())
    assert repo.has_commits() is False


def test_create_tag_returns_false_when_tag_exists(monkeypatch):
    repo = _make_repo(fake_git=_FakeGit(tag_result="v1.0.0"))
    run_called = False

    def _run(*args, **kwargs):
        nonlocal run_called
        run_called = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", _run)

    assert repo.create_tag("v1.0.0", "abc123") is False
    assert run_called is False


def test_create_tag_invokes_git_tag_command(monkeypatch):
    repo = _make_repo(fake_git=_FakeGit(tag_result=""))
    calls, _run = _make_subprocess_recorder()
    monkeypatch.setattr(subprocess, "run", _run)

    assert repo.create_tag("v1.2.3", "abc123") is True
    _assert_single_subprocess_call(
        calls,
        [
            "git",
            "-C",
            "/tmp/repo",
            "tag",
            "v1.2.3",
            "abc123",
        ],
    )


def test_create_tag_raises_runtime_error_on_subprocess_failure(monkeypatch):
    repo = _make_repo(fake_git=_FakeGit(tag_result=""))

    def _run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0], stderr="cannot create")

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match="Failed to create tag"):
        repo.create_tag("v1.2.3", "abc123")


def test_get_semantic_version_tags_and_resolve_output_path():
    tags = [
        SimpleNamespace(name="v1.0.0", commit=SimpleNamespace(hexsha="a1")),
        SimpleNamespace(name="v1.0.1", commit=SimpleNamespace(hexsha="a1")),
    ]
    repo = _make_repo(tags=tags)

    assert repo.get_semantic_version_tags() == {"a1": ["v1.0.0", "v1.0.1"]}
    assert repo.resolve_output_path("CHANGELOG.md") == Path("/tmp/repo/CHANGELOG.md")
    assert repo.resolve_output_path("/tmp/custom.md") == Path("/tmp/custom.md")


@pytest.mark.parametrize(
    ("remote_url", "expected"),
    [
        ("https://host/org/repo.git", "https://host/org/repo"),
        ("git@host:org/repo.git", "https://host/org/repo"),
        ("ssh://git@host/org/repo.git", "https://host/org/repo"),
    ],
)
def test_get_repository_web_url_formats_supported_remotes(remote_url, expected):
    repo = _make_repo(remote_url=remote_url)

    assert repo.get_repository_web_url() == expected
    assert repo.get_commit_web_url("abc123") == f"{expected}/commit/abc123"


def test_get_repository_web_url_returns_none_without_remote():
    repo = _make_repo()

    assert repo.get_repository_web_url() is None
    assert repo.get_commit_web_url("abc123") is None


def test_get_repository_info_returns_best_effort_snapshot():
    repo = _make_repo_with_head_commit(remote_url="git@host:org/repo.git")

    info = repo.get_repository_info()

    assert info == {
        "path": "/tmp/repo",
        "branch": "main",
        "head_commit": {
            "hash": "abc12345",
            "message": "feat: add snapshot helper",
            "author": "Alice",
            "committed_at": "2026-08-05T12:00:00",
        },
        "remote_url": "git@host:org/repo.git",
        "repository_web_url": "https://host/org/repo",
        "semantic_version_tags": {},
    }


def test_get_repository_info_toon_uses_toon_format_encode(monkeypatch):
    repo = _make_repo_with_head_commit(remote_url="git@host:org/repo.git")

    toon_module = ModuleType("toon_format")
    calls: list[dict[str, object | None]] = []

    def _encode(value):
        calls.append(value)
        return "name: Alice"

    toon_module.encode = _encode  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "toon_format", toon_module)

    assert repo.get_repository_info_toon() == "name: Alice"
    assert calls == [repo.get_repository_info()]
