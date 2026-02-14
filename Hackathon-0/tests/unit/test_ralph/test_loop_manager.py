"""Unit tests for RalphLoopManager."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


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
def ralph(vault):
    from src.vault.manager import VaultManager
    from src.ralph.loop_manager import RalphLoopManager
    manager = RalphLoopManager.__new__(RalphLoopManager)
    manager.max_iterations = 3
    manager.check_interval = 0
    manager.vault_manager = VaultManager(vault_path=vault)
    return manager, vault


class TestCompletionDetection:
    def test_is_task_complete_false_when_no_marker(self, ralph):
        manager, vault = ralph
        (vault / "Plans" / "plan.md").write_text("# Plan\nNo marker here")
        assert manager._is_task_complete_in_vault() is False

    def test_is_task_complete_true_when_marker_in_plans(self, ralph):
        manager, vault = ralph
        (vault / "Plans" / "plan.md").write_text(
            "# Plan\nDone\n<promise>TASK_COMPLETE</promise>"
        )
        assert manager._is_task_complete_in_vault() is True

    def test_is_task_complete_true_when_marker_in_done(self, ralph):
        manager, vault = ralph
        (vault / "Done" / "task.md").write_text("<promise>TASK_COMPLETE</promise>")
        assert manager._is_task_complete_in_vault() is True

    def test_is_task_complete_true_when_marker_in_logs(self, ralph):
        manager, vault = ralph
        (vault / "Logs" / "log.md").write_text(
            "activity logged\n<promise>TASK_COMPLETE</promise>"
        )
        assert manager._is_task_complete_in_vault() is True

    def test_is_task_complete_string_check(self, ralph):
        manager, _ = ralph
        assert manager._is_task_complete("<promise>TASK_COMPLETE</promise>") is True
        assert manager._is_task_complete("all done") is False
        assert manager._is_task_complete("") is False

    def test_monitor_completion_marker_true(self, ralph):
        manager, vault = ralph
        f = vault / "Done" / "result.md"
        f.write_text("<promise>TASK_COMPLETE</promise>")
        assert manager.monitor_completion_marker(f) is True

    def test_monitor_completion_marker_false(self, ralph):
        manager, vault = ralph
        f = vault / "Done" / "result.md"
        f.write_text("still in progress")
        assert manager.monitor_completion_marker(f) is False

    def test_monitor_completion_marker_missing_file(self, ralph):
        manager, vault = ralph
        f = vault / "Done" / "no_such_file.md"
        assert manager.monitor_completion_marker(f) is False


class TestRalphLoopExecution:
    def test_execute_returns_on_completion(self, ralph):
        manager, vault = ralph
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "output"
            mock_run.return_value = mock_result

            # Simulate task completion marker appearing after first call
            plans_file = vault / "Plans" / "plan.md"

            def side_effect(*args, **kwargs):
                plans_file.write_text("<promise>TASK_COMPLETE</promise>")
                return mock_result

            mock_run.side_effect = side_effect
            result = manager.execute_with_persistence("do something")
            assert result == "output"
            assert mock_run.call_count == 1

    def test_execute_raises_on_max_iterations(self, ralph):
        manager, vault = ralph
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            with pytest.raises(Exception, match="Ralph loop failed"):
                manager.execute_with_persistence("never finishes")

            assert mock_run.call_count == manager.max_iterations
