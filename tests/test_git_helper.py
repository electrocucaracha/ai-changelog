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

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from git.exc import GitCommandError

from ai_changelog_msg.git_helper import GitRepository


class _FakeGit:
    def __init__(
        self,
        *,
        diff_result=None,
        show_result=None,
        note_result=None,
        update_ref_result=None,
    ):
        self.diff_result = diff_result
        self.show_result = show_result
        self.note_result = note_result
        self.update_ref_result = update_ref_result
        self.notes_calls: list[tuple] = []
        self.update_ref_calls: list[tuple] = []

    def diff(self, parent_hash, commit_hash):
        if isinstance(self.diff_result, Exception):
            raise self.diff_result
        return self.diff_result

    def show(self, commit_hash):
        if isinstance(self.show_result, Exception):
            raise self.show_result
        return self.show_result

    def notes(self, *args):
        self.notes_calls.append(args)
        if isinstance(self.note_result, Exception):
            raise self.note_result
        return self.note_result

    def update_ref(self, *args):
        self.update_ref_calls.append(args)
        if isinstance(self.update_ref_result, Exception):
            raise self.update_ref_result
        return self.update_ref_result


def _make_repo(
    fake_git=None, tags=None, remote_url=None, refs=None, create_tag=None
) -> GitRepository:
    repo = GitRepository.__new__(GitRepository)
    repo.repo_path = Path("/tmp/repo")
    repo.repo = SimpleNamespace(  # type: ignore[assignment]
        git=fake_git or _FakeGit(),
        iter_commits=lambda ref: [1, 2, 3],
        tags=tags or [],
        refs=refs or [],
        create_tag=create_tag or (lambda name, ref: None),
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
    repo.repo = SimpleNamespace(  # type: ignore[assignment]
        git=repo.repo.git,
        iter_commits=repo.repo.iter_commits,
        tags=repo.repo.tags,
        refs=repo.repo.refs,
        create_tag=repo.repo.create_tag,
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


def test_get_commit_diff_passes_parent_and_commit_hash_in_order():
    calls: list[tuple[str, str]] = []

    class _TrackingGit(_FakeGit):
        def diff(self, parent_hash, commit_hash):
            calls.append((parent_hash, commit_hash))
            return "+delta"

    repo = _make_repo(fake_git=_TrackingGit())
    commit = SimpleNamespace(
        hexsha="childhash",
        parents=[SimpleNamespace(hexsha="parenthash")],
    )

    assert repo.get_commit_diff(commit) == "+delta"
    assert calls == [("parenthash", "childhash")]


def test_get_commit_diff_uses_show_for_root_commit_and_returns_error_on_failure():
    repo = _make_repo(fake_git=_FakeGit(show_result="root diff"))
    root_commit = SimpleNamespace(hexsha="abc12345", parents=[])
    assert repo.get_commit_diff(root_commit) == "root diff"

    failing_repo = _make_repo(fake_git=_FakeGit(diff_result=RuntimeError("bad diff")))
    commit = SimpleNamespace(
        hexsha="abc12345", parents=[SimpleNamespace(hexsha="parent")]
    )
    assert "[Error retrieving diff: bad diff]" == failing_repo.get_commit_diff(commit)


def test_get_commit_diff_logs_fetching_with_8char_hexsha(caplog):
    import logging

    fake_git = _FakeGit(diff_result="+added")
    repo = _make_repo(fake_git=fake_git)
    commit = SimpleNamespace(
        hexsha="abc12345longerhash", parents=[SimpleNamespace(hexsha="parent")]
    )

    with caplog.at_level(logging.DEBUG, logger="ai_changelog_msg.git_helper"):
        repo.get_commit_diff(commit)

    assert "Fetching diff for commit abc12345" in caplog.text
    assert "abc12345l" not in caplog.text


def test_get_commit_diff_logs_warning_with_expected_capitalization(caplog):
    caplog.set_level("WARNING")
    failing_repo = _make_repo(fake_git=_FakeGit(diff_result=RuntimeError("bad diff")))
    commit = SimpleNamespace(
        hexsha="abc12345", parents=[SimpleNamespace(hexsha="parent")]
    )

    _ = failing_repo.get_commit_diff(commit)

    assert any(
        record.getMessage().startswith("Could not retrieve diff for abc12345")
        for record in caplog.records
    )


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


def test_set_note_invokes_git_notes_add_with_force():
    fake_git = _FakeGit()
    repo = _make_repo(fake_git=fake_git)

    repo.set_note("abc123", "hello world", "ai-changelog")

    assert fake_git.notes_calls == [
        (
            "--ref",
            "ai-changelog",
            "add",
            "-m",
            "hello world",
            "-f",
            "abc123",
        )
    ]


def test_set_note_raises_runtime_error_on_git_command_failure():
    error = GitCommandError(
        ["git", "notes", "add"],
        1,
        stderr="failure",
    )
    repo = _make_repo(fake_git=_FakeGit(note_result=error))

    with pytest.raises(RuntimeError, match="Failed to set git note"):
        repo.set_note("abc123", "hello world", "ai-changelog")


def test_clear_notes_returns_false_when_namespace_missing():
    repo = _make_repo()

    assert repo.clear_notes("ai-changelog") is False


def test_clear_notes_logs_namespace_name_when_missing(caplog):
    import logging

    repo = _make_repo()

    with caplog.at_level(logging.DEBUG, logger="ai_changelog_msg.git_helper"):
        repo.clear_notes("ai-changelog")

    assert "ai-changelog" in caplog.text
    assert "Notes namespace" in caplog.text
    assert "does not exist" in caplog.text


def test_clear_notes_deletes_existing_namespace():
    ref_name = "refs/notes/ai-changelog"
    fake_git = _FakeGit()
    repo = _make_repo(
        fake_git=fake_git,
        refs=[SimpleNamespace(path=ref_name)],
    )

    assert repo.clear_notes("ai-changelog") is True
    assert fake_git.update_ref_calls == [("-d", "refs/notes/ai-changelog")]


def test_clear_notes_logs_deletion_message(caplog):
    import logging

    ref_name = "refs/notes/ai-changelog"
    repo = _make_repo(
        refs=[SimpleNamespace(path=ref_name)],
    )

    with caplog.at_level(logging.INFO, logger="ai_changelog_msg.git_helper"):
        repo.clear_notes("ai-changelog")

    assert "Deleted git notes namespace" in caplog.text
    assert "ai-changelog" in caplog.text


def test_clear_notes_raises_runtime_error_when_delete_fails():
    ref_name = "refs/notes/ai-changelog"
    error = GitCommandError(
        ["git", "update-ref", "-d", ref_name], 1, stderr="cannot delete"
    )
    repo = _make_repo(
        fake_git=_FakeGit(update_ref_result=error),
        refs=[SimpleNamespace(path=ref_name)],
    )

    with pytest.raises(RuntimeError, match="Failed to clear git notes namespace"):
        repo.clear_notes("ai-changelog")


def test_clear_notes_requires_exact_namespace_match():
    fake_git = _FakeGit()
    repo = _make_repo(
        fake_git=fake_git,
        refs=[SimpleNamespace(path="refs/notes/ai-changelog-other")],
    )

    assert repo.clear_notes("ai-changelog") is False
    assert fake_git.update_ref_calls == []


def test_has_commits_false_when_head_commit_access_raises():
    repo = _make_repo()

    class _BrokenHead:
        @property
        def commit(self):
            raise RuntimeError("no commits")

    repo.repo = SimpleNamespace(head=_BrokenHead())
    assert repo.has_commits() is False


def test_create_tag_returns_false_when_tag_exists():
    repo = _make_repo(tags=[SimpleNamespace(name="v1.0.0")])

    assert repo.create_tag("v1.0.0", "abc123") is False


def test_create_tag_invokes_gitpython_create_tag():
    calls: list[tuple[str, str]] = []

    def _create_tag(name: str, ref: str):
        calls.append((name, ref))

    repo = _make_repo(create_tag=_create_tag)

    assert repo.create_tag("v1.2.3", "abc123") is True
    assert calls == [("v1.2.3", "abc123")]


def test_create_tag_logs_created_message(caplog):
    import logging

    repo = _make_repo()

    with caplog.at_level(logging.INFO, logger="ai_changelog_msg.git_helper"):
        repo.create_tag("v1.2.3", "abc12345longerhash")

    assert "Created tag 'v1.2.3' at abc12345" in caplog.text


def test_create_tag_logs_skipped_message_when_exists(caplog):
    import logging

    repo = _make_repo(tags=[SimpleNamespace(name="v1.0.0")])

    with caplog.at_level(logging.DEBUG, logger="ai_changelog_msg.git_helper"):
        repo.create_tag("v1.0.0", "abc12345")

    assert "already exists" in caplog.text
    assert "v1.0.0" in caplog.text


def _make_tag_spy() -> tuple[list[tuple[str, str]], object]:
    """Return a (calls, create_tag) pair for recording tag creation calls."""
    calls: list[tuple[str, str]] = []

    def _create_tag(name: str, ref: str) -> None:
        calls.append((name, ref))

    return calls, _create_tag


def test_create_tag_does_not_skip_when_only_other_tags_exist():
    calls, _create_tag = _make_tag_spy()

    repo = _make_repo(
        tags=[SimpleNamespace(name="v9.9.9")],
        create_tag=_create_tag,
    )

    assert repo.create_tag("v1.0.0", "abc123") is True
    assert calls == [("v1.0.0", "abc123")]


def test_create_tag_raises_runtime_error_on_git_command_failure():
    def _create_tag(name: str, ref: str):
        raise GitCommandError(["git", "tag", name, ref], 1, stderr="cannot create")

    repo = _make_repo(create_tag=_create_tag)

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


# ---------------------------------------------------------------------------
# Tests for edge cases targeting specific surviving mutations
# ---------------------------------------------------------------------------


def test_get_repository_info_head_commit_is_none_when_access_raises():
    """head_commit must be None (not '') when accessing head.commit raises."""

    class _BrokenHead:
        @property
        def commit(self):
            raise RuntimeError("detached HEAD")

    repo = _make_repo()
    repo.repo = SimpleNamespace(
        head=_BrokenHead(),
        active_branch=SimpleNamespace(name="main"),
        remotes=SimpleNamespace(),
        tags=[],
    )

    info = repo.get_repository_info()

    assert info["head_commit"] is None
    assert not isinstance(info["head_commit"], str)


def test_get_repository_info_branch_is_none_when_active_branch_raises():
    """branch must be None (not '') when active_branch.name raises."""

    class _BrokenBranch:
        @property
        def name(self) -> str:
            raise RuntimeError("detached HEAD")

    head_commit = SimpleNamespace(
        hexsha="abc12345",
        message="msg\n",
        author=SimpleNamespace(name="Alice"),
        committed_datetime=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00"),
    )
    repo = _make_repo()
    repo.repo = SimpleNamespace(
        head=SimpleNamespace(commit=head_commit),
        active_branch=_BrokenBranch(),
        remotes=SimpleNamespace(),
        tags=[],
    )

    info = repo.get_repository_info()

    assert info["branch"] is None
    assert not isinstance(info["branch"], str)


def test_get_note_uses_ref_argument():
    """get_note must pass '--ref' (lowercase) to git notes."""
    fake_git = _FakeGit(note_result="my note")
    repo = _make_repo(fake_git=fake_git)

    result = repo.get_note("abc123", "ai-changelog")

    assert result == "my note"
    # Verify the exact argument used
    assert len(fake_git.notes_calls) == 1
    call_args = fake_git.notes_calls[0]
    assert call_args[0] == "--ref"
    assert call_args == ("--ref", "ai-changelog", "show", "abc123")


def test_create_tag_does_not_call_backend_when_exact_tag_exists():
    calls, _create_tag = _make_tag_spy()

    repo = _make_repo(
        tags=[SimpleNamespace(name="v1.0.0")],
        create_tag=_create_tag,
    )

    assert repo.create_tag("v1.0.0", "abc123") is False
    assert calls == []


def test_create_tag_error_message_includes_stderr():
    """RuntimeError for failed tag creation must include stderr detail."""

    def _create_tag(name: str, ref: str):
        raise GitCommandError(["git", "tag"], 1, stderr="already exists")

    repo = _make_repo(create_tag=_create_tag)

    with pytest.raises(RuntimeError, match="already exists"):
        repo.create_tag("v1.0.0", "abc123")


def test_has_commits_returns_true_when_commits_exist():
    """has_commits must return True (not False) when commits exist.

    Kills xǁGitRepositoryǁhas_commits__mutmut_2:
    return False replaces return True.
    """
    from tempfile import TemporaryDirectory

    from git import Repo

    with TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        # Add a commit
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("initial")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        from ai_changelog_msg.git_helper import GitRepository

        git_repo = GitRepository(tmpdir)

        # should return True when commits exist
        assert git_repo.has_commits() is True
