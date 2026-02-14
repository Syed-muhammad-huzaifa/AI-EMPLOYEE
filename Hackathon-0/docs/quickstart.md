
# Quickstart Guide - Bronze Phase

This guide will help you get the Personal AI Employee Bronze Phase up and running quickly.

## Prerequisites

- Python 3.12+
- uv package manager
- Access to your Obsidian vault at `C:\MY_EMPLOYEE`

## Setup

1. **Clone or create the project:**
   ```bash
   # If starting fresh
   mkdir hackathon-0
   cd hackathon-0
   uv init
   ```

2. **Install dependencies:**
   ```bash
   uv pip install watchdog psutil python-dotenv
   ```

3. **Configure your vault:**
   - Ensure your Obsidian vault exists at `C:\MY_EMPLOYEE`
   - Verify it has the required folders: `INBOX`, `NEEDS_ACTION`, `PLAN`, `DONE`, `LOGS`
   - Verify it has the required files: `dashboard.md`, `company_handbook.md`

4. **Set up environment:**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   # Edit .env to add your specific configuration
   ```

## Running the System

1. **Start both watcher and orchestrator:**
   ```bash
   python main.py --mode both --vault-path "C:\MY_EMPLOYEE"
   ```

2. **Monitor the system:**
   - Check the console output for logs
   - Monitor your vault's `LOGS/` folder for activity logs
   - Place test files in the `NEEDS_ACTION/` folder to see the orchestrator in action

3. **Stop the system:**
   - Press `Ctrl+C` to gracefully shut down

## Testing the System

1. **Test the filesystem watcher:**
   - Make changes to files in your vault directory
   - Observe that action files are created in the `NEEDS_ACTION/` folder

2. **Test the orchestrator:**
   - Place a test file in the `NEEDS_ACTION/` folder
   - Observe that it gets moved and processed

## Troubleshooting

- **Vault not found**: Verify the path in your `.env` file and `config/vault_config.json`
- **Permission errors**: Ensure the application has read/write access to your vault directory
- **No activity**: Check that the required folders exist in your vault

## Configuration

Edit `config/vault_config.json` to customize:
- Polling intervals
- Retry settings
- Folder names (if you use different names)

## Next Steps

Once the Bronze Phase is working:
1. Add the Gmail watcher for email processing
2. Implement MCP servers for external actions
3. Add more sophisticated skills
4. Implement the approval workflow