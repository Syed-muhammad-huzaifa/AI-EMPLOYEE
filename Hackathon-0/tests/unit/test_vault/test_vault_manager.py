"""Unit tests for VaultManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.vault.manager import VaultManager


@pytest.fixture
def vault(tmp_path):
    """Minimal vault fixture with required folder structure."""
    for d in ["Needs_Action", "In_Progress", "Plans", "Done", "Logs",
              "Pending_Approval", "Approved", "Rejected"]:
        (tmp_path / d).mkdir()
    (tmp_path / "Company_Handbook.md").write_text("# Company Handbook\nHello")
    (tmp_path / "Dashboard.md").write_text("# Dashboard\nStatus OK")
    (tmp_path / "Business_Goals.md").write_text("# Business Goals\nGrow revenue")
    return tmp_path


class TestVaultManagerInit:
    def test_accepts_vault_path_parameter(self, vault):
        vm = VaultManager(vault_path=vault)
        assert vm.vault_path == vault

    def test_builds_directory_paths_from_vault_path(self, vault):
        vm = VaultManager(vault_path=vault)
        assert vm.directories['needs_action'] == vault / "Needs_Action"
        assert vm.directories['in_progress'] == vault / "In_Progress"
        assert vm.directories['plan'] == vault / "Plans"
        assert vm.directories['done'] == vault / "Done"
        assert vm.directories['logs'] == vault / "Logs"

    def test_raises_when_directory_missing(self, tmp_path):
        # Only create some directories, not all
        (tmp_path / "Needs_Action").mkdir()
        with pytest.raises(FileNotFoundError):
            VaultManager(vault_path=tmp_path)


class TestVaultManagerFileOps:
    def test_read_file(self, vault):
        vm = VaultManager(vault_path=vault)
        content = vm.read_file(vault / "Company_Handbook.md")
        assert "Company Handbook" in content

    def test_write_file(self, vault):
        vm = VaultManager(vault_path=vault)
        target = vault / "Needs_Action" / "task_001.md"
        assert vm.write_file(target, "# Task\nDo something") is True
        assert target.exists()
        assert "Task" in target.read_text()

    def test_write_file_creates_parent_dirs(self, vault):
        vm = VaultManager(vault_path=vault)
        nested = vault / "Needs_Action" / "sub" / "deep.md"
        assert vm.write_file(nested, "content") is True
        assert nested.exists()

    def test_read_file_returns_content(self, vault):
        vm = VaultManager(vault_path=vault)
        f = vault / "Done" / "result.md"
        f.write_text("result content")
        assert vm.read_file(f) == "result content"

    def test_move_file(self, vault):
        vm = VaultManager(vault_path=vault)
        src = vault / "Needs_Action" / "task.md"
        src.write_text("task")
        assert vm.move_file(src, vault / "Done") is True
        assert not src.exists()
        assert (vault / "Done" / "task.md").exists()


class TestVaultManagerListFiles:
    def test_list_files_in_needs_action(self, vault):
        vm = VaultManager(vault_path=vault)
        (vault / "Needs_Action" / "a.md").write_text("a")
        (vault / "Needs_Action" / "b.md").write_text("b")
        files = vm.list_files_in_folder('needs_action')
        names = [f.name for f in files]
        assert "a.md" in names
        assert "b.md" in names

    def test_list_files_empty_folder(self, vault):
        vm = VaultManager(vault_path=vault)
        files = vm.list_files_in_folder('done')
        assert files == []

    def test_list_files_unknown_folder_raises(self, vault):
        vm = VaultManager(vault_path=vault)
        with pytest.raises(ValueError):
            vm.list_files_in_folder('nonexistent')

    def test_list_files_excludes_subdirectories(self, vault):
        vm = VaultManager(vault_path=vault)
        subdir = vault / "Needs_Action" / "subdir"
        subdir.mkdir()
        (vault / "Needs_Action" / "file.md").write_text("x")
        files = vm.list_files_in_folder('needs_action')
        assert all(f.is_file() for f in files)


class TestVaultManagerContextFiles:
    def test_read_company_handbook(self, vault):
        vm = VaultManager(vault_path=vault)
        content = vm.read_company_handbook()
        assert "Company Handbook" in content

    def test_read_dashboard(self, vault):
        vm = VaultManager(vault_path=vault)
        content = vm.read_dashboard()
        assert "Dashboard" in content

    def test_read_business_goals(self, vault):
        vm = VaultManager(vault_path=vault)
        content = vm.read_business_goals()
        assert "Business Goals" in content

    def test_read_company_handbook_missing_returns_empty(self, vault):
        (vault / "Company_Handbook.md").unlink()
        vm = VaultManager(vault_path=vault)
        assert vm.read_company_handbook() == ""

    def test_log_activity_creates_md_file(self, vault):
        from datetime import datetime
        vm = VaultManager(vault_path=vault)
        vm.log_activity("test_event", {"key": "value"})
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = vault / "Logs" / f"{date_str}.md"
        assert log_file.exists()
        content = log_file.read_text()
        assert "test_event" in content
        assert "key" in content

    def test_log_activity_appends_multiple_entries(self, vault):
        from datetime import datetime
        vm = VaultManager(vault_path=vault)
        vm.log_activity("first_event")
        vm.log_activity("second_event")
        date_str = datetime.now().strftime("%Y-%m-%d")
        content = (vault / "Logs" / f"{date_str}.md").read_text()
        assert "first_event" in content
        assert "second_event" in content
