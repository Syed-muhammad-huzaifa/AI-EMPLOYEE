"""Vault manager for reading and writing files to the Obsidian vault."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import src.vault.constants as _constants

logger = logging.getLogger(__name__)


class VaultManager:
    """Manages reading and writing to the Obsidian vault."""

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = Path(vault_path) if vault_path is not None else _constants.VAULT_PATH
        self.directories = {
            'in_progress': self.vault_path / "In_Progress",
            'needs_action': self.vault_path / "Needs_Action",
            'plan': self.vault_path / "Plans",
            'done': self.vault_path / "Done",
            'logs': self.vault_path / "Logs",
            'pending_approval': self.vault_path / "Pending_Approval",
            'approved': self.vault_path / "Approved",
            'rejected': self.vault_path / "Rejected",
        }
        self._dashboard_file = self.vault_path / "Dashboard.md"
        self._handbook_file = self.vault_path / "Company_Handbook.md"
        self._business_goals_file = self.vault_path / "Business_Goals.md"
        
        # Verify vault structure
        self._verify_vault_structure()
    
    def _verify_vault_structure(self):
        """Ensure all vault directories exist, creating them if necessary."""
        for name, path in self.directories.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise OSError(
                    f"Cannot create vault directory '{name}' at '{path}': {exc}"
                ) from exc

        # Check for required files
        if not self._dashboard_file.exists():
            logger.warning(f"Dashboard file does not exist: {self._dashboard_file}")

        if not self._handbook_file.exists():
            logger.warning(f"Company handbook file does not exist: {self._handbook_file}")

        if not self._business_goals_file.exists():
            logger.warning(f"Business goals file does not exist: {self._business_goals_file}")

    def _validate_path(self, file_path: Path) -> Path:
        """Validate that a path is within vault boundaries.

        Args:
            file_path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is outside vault boundaries
        """
        try:
            # Resolve to absolute path, following symlinks
            resolved = file_path.resolve()
            vault_resolved = self.vault_path.resolve()

            # Check if resolved path is within vault
            if not str(resolved).startswith(str(vault_resolved)):
                raise ValueError(
                    f"Security error: Path '{file_path}' resolves to '{resolved}' "
                    f"which is outside vault boundaries '{vault_resolved}'"
                )

            return resolved
        except (OSError, RuntimeError) as e:
            # Handle cases where path resolution fails (broken symlinks, etc.)
            raise ValueError(f"Invalid path '{file_path}': {str(e)}")
    
    def read_file(self, file_path: Path) -> str:
        """Read content from a file in the vault."""
        try:
            # Validate path is within vault boundaries
            validated_path = self._validate_path(file_path)

            with open(validated_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Read file: {validated_path}")
            return content
        except ValueError as e:
            # Path validation error
            logger.error(f"Path validation failed for {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    def write_file(self, file_path: Path, content: str) -> bool:
        """Write content to a file in the vault."""
        try:
            # Validate path is within vault boundaries
            validated_path = self._validate_path(file_path)

            # Ensure parent directory exists (validate parent too)
            parent_path = validated_path.parent
            self._validate_path(parent_path)
            parent_path.mkdir(parents=True, exist_ok=True)

            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Wrote file: {validated_path}")
            return True
        except ValueError as e:
            # Path validation error
            logger.error(f"Path validation failed for {file_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {str(e)}")
            return False
    
    def move_file(self, source: Path, destination_dir: Path) -> bool:
        """Move a file from source to destination directory."""
        try:
            # Validate both source and destination are within vault
            validated_source = self._validate_path(source)
            validated_dest_dir = self._validate_path(destination_dir)

            validated_dest_dir.mkdir(parents=True, exist_ok=True)
            destination = validated_dest_dir / validated_source.name

            # Validate final destination path
            validated_destination = self._validate_path(destination)

            validated_source.rename(validated_destination)
            logger.info(f"Moved file: {validated_source} -> {validated_destination}")
            return True
        except ValueError as e:
            # Path validation error
            logger.error(f"Path validation failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error moving file {source} to {destination_dir}: {str(e)}")
            return False
    
    def list_files_in_folder(self, folder_name: str) -> List[Path]:
        """List all files in a specific vault folder."""
        if folder_name not in self.directories:
            raise ValueError(f"Unknown folder: {folder_name}")

        folder_path = self.directories[folder_name]

        # Validate folder path (should always pass since directories are set in __init__)
        validated_folder = self._validate_path(folder_path)

        files = []
        for file_path in validated_folder.iterdir():
            if file_path.is_file():
                # Each file should already be within vault, but validate for safety
                try:
                    validated_file = self._validate_path(file_path)
                    files.append(validated_file)
                except ValueError as e:
                    logger.warning(f"Skipping file outside vault boundaries: {file_path} - {str(e)}")
                    continue
        return files
    
    def log_activity(self, activity: str, details: Optional[Dict] = None):
        """Append an activity entry to today's human-readable markdown log.

        Log file: Logs/YYYY-MM-DD.md
        Each entry is a markdown bullet so it renders nicely in Obsidian.
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Build a compact detail string for the bullet line.
        detail_parts = []
        for k, v in (details or {}).items():
            detail_parts.append(f"`{k}`: {v}")
        detail_str = " | ".join(detail_parts)
        detail_suffix = f" — {detail_str}" if detail_str else ""

        entry = f"- **[{time_str}]** {activity}{detail_suffix}\n"

        log_file = self.directories['logs'] / f"{date_str}.md"
        try:
            # Create header if file is new.
            if not log_file.exists():
                header = f"# Activity Log — {date_str}\n\n"
                log_file.write_text(header, encoding="utf-8")

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)

            logger.info(f"Logged activity: {activity}")
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
    
    def read_company_handbook(self) -> str:
        """Read the company handbook file."""
        if self._handbook_file.exists():
            return self.read_file(self._handbook_file)
        else:
            logger.warning("Company handbook file not found")
            return ""

    def read_dashboard(self) -> str:
        """Read the dashboard file."""
        if self._dashboard_file.exists():
            return self.read_file(self._dashboard_file)
        else:
            logger.warning("Dashboard file not found")
            return ""

    def read_business_goals(self) -> str:
        """Read the business goals file."""
        if self._business_goals_file.exists():
            return self.read_file(self._business_goals_file)
        else:
            logger.warning("Business goals file not found")
            return ""