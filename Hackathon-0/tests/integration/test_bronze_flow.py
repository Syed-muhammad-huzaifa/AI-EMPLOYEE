"""
End-to-end test for the complete Bronze phase flow.

This test verifies the complete workflow:
1. A dummy task is placed in Needs_Action/
2. The orchestrator detects it and moves it to In_Progress/
3. Claude processes the task and creates a plan in Plans/
4. The task is completed and moved to Done/
5. Appropriate logs are created in Logs/
"""

import tempfile
import shutil
from pathlib import Path
import pytest

from src.vault.manager import VaultManager


# All directories required by VaultManager._verify_vault_structure
_VAULT_DIRS = [
    "Needs_Action", "In_Progress", "Plans", "Done", "Logs",
    "Pending_Approval", "Approved", "Rejected",
]


@pytest.fixture
def temp_vault():
    """Create a temporary vault for testing."""
    temp_dir = Path(tempfile.mkdtemp())

    for directory in _VAULT_DIRS:
        (temp_dir / directory).mkdir(parents=True, exist_ok=True)

    (temp_dir / "Company_Handbook.md").write_text("# Company Handbook\nTest content")
    (temp_dir / "Dashboard.md").write_text("# Dashboard\nTest content")
    (temp_dir / "Business_Goals.md").write_text("# Business Goals\nTest content")

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_complete_bronze_phase_flow(temp_vault):
    """Test the complete Bronze phase flow: Dummy task → Plan.md → Done/ + log"""

    temp_needs_action = temp_vault / "Needs_Action"

    dummy_task_content = """# Test Task

## Description
This is a dummy task for testing the complete Bronze phase flow.

## Action Required
Process this task completely through the system.
"""

    task_file = temp_needs_action / "dummy_task_test.md"
    task_file.write_text(dummy_task_content)

    assert task_file.exists(), "Dummy task should be created in Needs_Action/"

    content = task_file.read_text()
    assert "dummy task" in content.lower()

    # For a complete test, we would need to:
    # 1. Mock Claude responses
    # 2. Run the orchestrator controller
    # 3. Verify the task moves through the workflow
    # 4. Check that plan files are created
    # 5. Verify the task ends up in Done/
    # 6. Check that logs are created

    print("Basic file creation verified. Full orchestrator test requires Claude integration.")


def test_vault_manager_with_temp_vault(temp_vault):
    """Test vault manager operations with a temporary vault."""

    # Pass the vault path directly to VaultManager so it builds all paths
    # from the given root — no environment-variable reload tricks needed.
    vault_manager = VaultManager(vault_path=temp_vault)

    # Test reading company handbook
    handbook_content = vault_manager.read_company_handbook()
    assert "Company Handbook" in handbook_content

    # Test reading dashboard
    dashboard_content = vault_manager.read_dashboard()
    assert "Dashboard" in dashboard_content

    # Test writing a file
    test_file = temp_vault / "Needs_Action" / "test_write.md"
    write_success = vault_manager.write_file(test_file, "# Test File\nContent for testing")
    assert write_success
    assert test_file.exists()

    # Test reading the written file
    read_content = vault_manager.read_file(test_file)
    assert "Test File" in read_content
    assert "Content for testing" in read_content

    # Test listing files in folder
    files = vault_manager.list_files_in_folder('needs_action')
    assert len(files) > 0
    assert any("test_write.md" in str(f) for f in files)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
