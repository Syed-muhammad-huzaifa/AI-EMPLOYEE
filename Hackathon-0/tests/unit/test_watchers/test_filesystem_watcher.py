"""Unit tests for FilesystemWatcher."""

import pytest
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.watchers.filesystem_watcher import FilesystemWatcher


@pytest.fixture
def vault(tmp_path):
    for d in ["Needs_Action", "In_Progress", "Plans", "Done", "Logs",
              "Pending_Approval", "Approved", "Rejected"]:
        (tmp_path / d).mkdir()
    (tmp_path / "Company_Handbook.md").write_text("# Handbook")
    (tmp_path / "Dashboard.md").write_text("# Dashboard")
    (tmp_path / "Business_Goals.md").write_text("# Goals")
    return tmp_path


@pytest.fixture
def watcher(vault):
    with patch("src.watchers.base_watcher.load_secrets", return_value={}):
        with patch("src.watchers.base_watcher.VaultManager") as MockVM:
            mock_vm = MagicMock()
            mock_vm.vault_path = vault
            mock_vm.directories = {'logs': vault / "Logs"}
            MockVM.return_value = mock_vm
            w = FilesystemWatcher(str(vault), [str(vault)], check_interval=1)
            w.needs_action_dir = vault / "Needs_Action"
            return w


class TestFilesystemWatcherHashing:
    def test_get_file_hash_returns_md5(self, vault, watcher):
        f = vault / "test.md"
        f.write_text("hello")
        h = watcher._get_file_hash(f)
        expected = hashlib.md5(b"hello").hexdigest()
        assert h == expected

    def test_get_file_hash_unreadable_returns_empty_hash(self, vault, watcher):
        fake = vault / "nonexistent.md"
        h = watcher._get_file_hash(fake)
        assert h == hashlib.md5(b"").hexdigest()

    def test_initial_hashes_populated(self, vault, watcher):
        assert len(watcher.file_hashes) > 0


class TestFilesystemWatcherChangeDetection:
    def test_detects_modified_file(self, vault, watcher):
        f = vault / "Company_Handbook.md"
        original_content = f.read_text()
        f.write_text(original_content + "\nNew line added")
        changes = watcher.check_for_updates()
        changed_paths = [c['path'] for c in changes]
        assert str(f) in changed_paths

    def test_detects_new_file(self, vault, watcher):
        new_file = vault / "new_doc.md"
        new_file.write_text("brand new file")
        changes = watcher.check_for_updates()
        changed_paths = [c['path'] for c in changes]
        assert str(new_file) in changed_paths

    def test_no_changes_when_unchanged(self, vault, watcher):
        changes = watcher.check_for_updates()
        assert changes == []

    def test_detects_deleted_file(self, vault, watcher):
        # Register the file in initial hashes first
        f = vault / "Company_Handbook.md"
        watcher.file_hashes[str(f)] = watcher._get_file_hash(f)
        f.unlink()
        changes = watcher.check_for_updates()
        deleted_paths = [c['path'] for c in changes if c['type'] == 'file_deleted']
        assert str(f) in deleted_paths


class TestFilesystemWatcherActionFile:
    def test_creates_action_file_in_needs_action(self, vault, watcher):
        item = {
            'type': 'file_change',
            'path': str(vault / "Company_Handbook.md"),
            'previous_hash': 'abc',
            'current_hash': 'def',
            'timestamp': '2024-01-01T00:00:00',
        }
        action_file = watcher.create_action_file(item)
        assert action_file.exists()
        assert action_file.parent == vault / "Needs_Action"
        assert action_file.suffix == ".md"

    def test_action_file_contains_change_info(self, vault, watcher):
        item = {
            'type': 'file_change',
            'path': '/some/file.md',
            'previous_hash': 'aaa',
            'current_hash': 'bbb',
            'timestamp': '2024-01-01T12:00:00',
        }
        action_file = watcher.create_action_file(item)
        content = action_file.read_text()
        assert "file_change" in content
        assert "/some/file.md" in content
