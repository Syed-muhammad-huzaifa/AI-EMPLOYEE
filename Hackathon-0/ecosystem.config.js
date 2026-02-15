module.exports = {
  apps: [
    {
      name: 'gmail-watcher',
      script: 'python',
      args: '-m src.watchers.gmail_watcher',
      cwd: '/home/syedhuzaifa/AI-EMPLOYEE/Hackathon-0',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: 'logs/gmail_watcher_error.log',
      out_file: 'logs/gmail_watcher_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'approved-email-sender',
      script: 'python',
      args: '-m src.watchers.approved_email_sender',
      cwd: '/home/syedhuzaifa/AI-EMPLOYEE/Hackathon-0',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: 'logs/approved_email_sender_error.log',
      out_file: 'logs/approved_email_sender_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'ralph-loop',
      script: 'python',
      args: '-m src.ralph.loop_manager',
      cwd: '/home/syedhuzaifa/AI-EMPLOYEE/Hackathon-0',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: 'logs/ralph_loop_error.log',
      out_file: 'logs/ralph_loop_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    }
  ]
};
