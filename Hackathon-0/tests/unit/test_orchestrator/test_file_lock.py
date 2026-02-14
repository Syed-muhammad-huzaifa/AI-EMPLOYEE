"""Unit tests for file locking and claim-by-move pattern."""

import pytest
from pathlib import Path

from src.utils.file_lock import FileLock, claim_task


@pytest.fixture
def task_file(tmp_path):
    f = tmp_path / "task.md"
    f.write_text("# Task\nSome work")
    return f


@pytest.fixture
def in_progress_dir(tmp_path):
    d = tmp_path / "In_Progress"
    d.mkdir()
    return d


class TestFileLock:
    def test_acquire_and_release(self, task_file):
        lock = FileLock(task_file, timeout=2)
        assert lock.acquire() is True
        assert lock.lock_file_path.exists()
        lock.release()
        assert not lock.lock_file_path.exists()

    def test_second_acquire_fails_while_held(self, task_file):
        lock1 = FileLock(task_file, timeout=0)
        lock2 = FileLock(task_file, timeout=0)
        assert lock1.acquire() is True
        assert lock2.acquire() is False
        lock1.release()

    def test_release_without_acquire_is_safe(self, task_file):
        lock = FileLock(task_file)
        lock.release()  # Should not raise


class TestClaimTask:
    def test_returns_new_path_on_success(self, task_file, in_progress_dir):
        new_path = claim_task(task_file, "orchestrator", in_progress_dir)
        assert new_path is not None
        assert new_path.exists()
        assert new_path == in_progress_dir / "orchestrator" / "task.md"

    def test_original_file_removed_after_claim(self, task_file, in_progress_dir):
        claim_task(task_file, "orchestrator", in_progress_dir)
        assert not task_file.exists()

    def test_claimed_file_has_correct_content(self, task_file, in_progress_dir):
        new_path = claim_task(task_file, "orchestrator", in_progress_dir)
        assert "Some work" in new_path.read_text()

    def test_returns_none_when_already_claimed(self, task_file, in_progress_dir):
        # First claim succeeds
        claim_task(task_file, "orchestrator", in_progress_dir)
        # Second attempt on the (now-moved) file returns None
        result = claim_task(task_file, "orchestrator", in_progress_dir)
        assert result is None

    def test_creates_agent_subdirectory(self, task_file, in_progress_dir):
        claim_task(task_file, "my_agent", in_progress_dir)
        assert (in_progress_dir / "my_agent").is_dir()
