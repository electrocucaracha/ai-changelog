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

from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_changelog_msg.git_helper import GitRepository


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
