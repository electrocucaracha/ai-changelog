"""Git repository helper for reading commits, diffs, and git notes."""

from __future__ import annotations

import logging
import re
from importlib import import_module
from pathlib import Path

from git import Commit, Repo
from git.exc import GitCommandError

logger = logging.getLogger(__name__)


class GitRepository:
    """Wrapper around a local git repository for reading commits and git notes.

    Uses :mod:`gitpython` for repository introspection and git note/tag
    operations.

    Args:
        repo_path: Filesystem path to the root of a git repository.  The
            directory must exist and contain a ``.git`` sub-directory.

    Raises:
        ValueError: If *repo_path* does not exist or is not a git repository.

    Examples:
        A non-existent path raises an error immediately:

        >>> GitRepository("/nonexistent/path")
        Traceback (most recent call last):
            ...
        ValueError: Repository path does not exist: /nonexistent/path
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path)
        logger.debug("Validating repository path: %s", repo_path)

        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")

        self.repo = Repo(self.repo_path)
        logger.debug("Repository opened: %s", self.repo_path)

    def get_all_commits(self, limit: int | None = None) -> list[Commit]:
        """Return commits reachable from ``HEAD``, newest first.

        Args:
            limit: When given and greater than zero, only the *limit* most
                recent commits are returned.  ``None`` or ``0`` returns the
                full history.

        Returns:
            Ordered list of :class:`git.Commit` objects.
        """
        commits = list(self.repo.iter_commits("HEAD"))
        if limit and limit > 0:
            commits = commits[:limit]
        return commits

    def get_commit_diff(self, commit: Commit) -> str:
        """Return the unified diff for *commit* as a plain string.

        For commits with at least one parent the diff is computed against the
        first parent.  For the initial (root) commit ``git show`` is used so
        that all added files are visible in the output.

        Args:
            commit: The commit whose diff should be fetched.

        Returns:
            Unified diff text, the sentinel ``"[No changes to display]"``
            when the diff is empty, or ``"[Error retrieving diff: ...]"``
            when the git command fails.
        """
        logger.debug("Fetching diff for commit %s", commit.hexsha[:8])
        try:
            if commit.parents:
                diff_output = self.repo.git.diff(
                    commit.parents[0].hexsha, commit.hexsha
                )
            else:
                diff_output = self.repo.git.show(commit.hexsha)
            logger.debug(
                "Diff size for %s: %d chars", commit.hexsha[:8], len(diff_output or "")
            )
            return diff_output if diff_output else "[No changes to display]"
        except Exception as error:  # noqa: BLE001
            logger.warning(
                "Could not retrieve diff for %s: %s", commit.hexsha[:8], error
            )
            return f"[Error retrieving diff: {error}]"

    def get_note(self, commit_hash: str, namespace: str) -> str | None:
        """Retrieve an existing git note attached to *commit_hash*.

        Args:
            commit_hash: Full or abbreviated commit SHA.
            namespace: The ``--ref`` namespace to look up.

        Returns:
            Note content as a string, or ``None`` when no note exists for
            the given commit and namespace.
        """
        try:
            result = self.repo.git.notes("--ref", namespace, "show", commit_hash)
            return result if result else None
        except Exception:  # noqa: BLE001
            return None

    def set_note(self, commit_hash: str, content: str, namespace: str) -> None:
        """Write *content* as a git note attached to *commit_hash*.

        Uses ``git notes add -f`` so that any existing note in *namespace* is
        overwritten silently.

        Args:
            commit_hash: Full commit SHA to annotate.
            content: Note body text to store.
            namespace: The ``--ref`` namespace to write into.

        Raises:
            RuntimeError: If setting the git note fails.
        """
        logger.debug(
            "Writing git note for %s in namespace '%s'", commit_hash[:8], namespace
        )
        try:
            self.repo.git.notes(
                "--ref",
                namespace,
                "add",
                "-m",
                content,
                "-f",
                commit_hash,
            )
            logger.debug("Note saved for %s", commit_hash[:8])
        except GitCommandError as error:
            raise RuntimeError(
                f"Failed to set git note for {commit_hash}: "
                f"{getattr(error, 'stderr', str(error))}"
            ) from error

    def clear_notes(self, namespace: str) -> bool:
        """Remove all git notes stored under *namespace*.

        Args:
            namespace: The git-notes ``--ref`` namespace to delete.

        Returns:
            ``True`` when the namespace existed and was removed, ``False`` when
            no notes ref existed for the namespace.

        Raises:
            RuntimeError: If deleting the notes ref fails.
        """
        ref_name = f"refs/notes/{namespace}"
        try:
            if not any(getattr(ref, "path", "") == ref_name for ref in self.repo.refs):
                logger.debug("Notes namespace '%s' does not exist", namespace)
                return False

            self.repo.git.update_ref("-d", ref_name)
            logger.info("Deleted git notes namespace '%s'", namespace)
            return True
        except GitCommandError as error:
            raise RuntimeError(
                f"Failed to clear git notes namespace {namespace}: "
                f"{getattr(error, 'stderr', str(error))}"
            ) from error

    def has_commits(self) -> bool:
        """Return ``True`` if the repository contains at least one commit.

        Returns:
            ``True`` when ``HEAD`` resolves to a commit object, ``False``
            for a freshly initialised repository with no commits.
        """
        try:
            _ = self.repo.head.commit
            return True
        except Exception:  # noqa: BLE001
            return False

    def get_semantic_version_tags(self) -> dict[str, list[str]]:
        """Return semantic-version tag names grouped by target commit hash.

        Tags are returned as a mapping of ``commit.hexsha`` to a list of tag
        names such as ``v1.2.3`` or ``1.2.3``. Non-semantic-version tags are
        filtered out by the caller.
        """
        tags_by_commit: dict[str, list[str]] = {}
        for tag in self.repo.tags:
            commit_hash = tag.commit.hexsha
            tags_by_commit.setdefault(commit_hash, []).append(tag.name)
        return tags_by_commit

    def create_tag(self, tag_name: str, commit_hash: str) -> bool:
        """Create a lightweight git tag at *commit_hash*.

        Args:
            tag_name: Tag name to create (for example ``v1.2.3``).
            commit_hash: Commit SHA the tag should point to.

        Returns:
            ``True`` when the tag was created, ``False`` when a tag with the
            same name already exists.

        Raises:
            RuntimeError: If creating the tag fails.
        """
        try:
            if any(tag.name == tag_name for tag in self.repo.tags):
                logger.debug("Tag '%s' already exists; skipping", tag_name)
                return False

            self.repo.create_tag(tag_name, ref=commit_hash)
            logger.info("Created tag '%s' at %s", tag_name, commit_hash[:8])
            return True
        except GitCommandError as error:
            raise RuntimeError(
                f"Failed to create tag {tag_name}: "
                f"{getattr(error, 'stderr', str(error))}"
            ) from error

    def resolve_output_path(self, file_path: str) -> Path:
        """Resolve *file_path* relative to the repository root.

        Absolute paths are returned unchanged. Relative paths are interpreted
        from the repository root directory.
        """
        path = Path(file_path)
        return path if path.is_absolute() else self.repo_path / path

    def get_repository_web_url(self) -> str | None:
        """Return the best-effort web URL for the repository origin remote.

        Supports common remote URL forms such as:
        - ``https://host/org/repo.git``
        - ``git@host:org/repo.git``
        - ``ssh://git@host/org/repo.git``

        Returns:
            Repository base URL (without trailing ``.git``) or ``None`` when
            the URL cannot be resolved.
        """
        try:
            remote_url = self.repo.remotes.origin.url
        except Exception:  # noqa: BLE001
            return None

        if not remote_url:
            return None

        http_match = re.match(r"^(https?://[^/]+/.+?)(?:\.git)?$", remote_url)
        if http_match:
            return http_match.group(1)

        scp_match = re.match(r"^git@([^:]+):(.+?)(?:\.git)?$", remote_url)
        if scp_match:
            host, path = scp_match.groups()
            return f"https://{host}/{path}"

        ssh_match = re.match(r"^ssh://git@([^/]+)/(.+?)(?:\.git)?$", remote_url)
        if ssh_match:
            host, path = ssh_match.groups()
            return f"https://{host}/{path}"

        return None

    def get_commit_web_url(self, commit_hash: str) -> str | None:
        """Return the web URL to view *commit_hash* in the origin repository.

        Args:
            commit_hash: Full commit SHA.

        Returns:
            Commit page URL or ``None`` when the origin web URL is not known.
        """
        base_url = self.get_repository_web_url()
        if not base_url:
            return None
        return f"{base_url}/commit/{commit_hash}"

    def get_repository_info(self) -> dict[str, object | None]:
        """Return a best-effort snapshot of repository metadata.

        The result is intentionally simple so it can be serialized to JSON,
        TOON, or other text formats by a higher-level formatter.
        """

        branch_name: str | None = None
        try:
            branch_name = self.repo.active_branch.name
        except Exception:  # noqa: BLE001
            branch_name = None

        head_commit: dict[str, object] | None = None
        try:
            commit = self.repo.head.commit
            head_commit = {
                "hash": commit.hexsha,
                "message": commit.message.strip(),
                "author": commit.author.name if commit.author else None,
                "committed_at": commit.committed_datetime.isoformat(),
            }
        except Exception:  # noqa: BLE001
            head_commit = None

        return {
            "path": str(self.repo_path),
            "branch": branch_name,
            "head_commit": head_commit,
            "remote_url": getattr(
                getattr(self.repo.remotes, "origin", None), "url", None
            ),
            "repository_web_url": self.get_repository_web_url(),
            "semantic_version_tags": self.get_semantic_version_tags(),
        }

    def get_repository_info_toon(self) -> str:
        """Return repository metadata encoded as TOON.

        This uses the official :mod:`toon_format` Python package when it is
        installed. The import is intentionally lazy so the rest of the CLI can
        keep working without TOON support enabled.
        """
        try:
            encode = import_module("toon_format").encode
        except ImportError as error:
            raise ImportError(
                "TOON output requires the optional toon-python dependency"
            ) from error

        return encode(self.get_repository_info())
