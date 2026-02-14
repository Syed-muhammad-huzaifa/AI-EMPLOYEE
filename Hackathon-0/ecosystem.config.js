/**
 * PM2 ecosystem config for AI Employee system.
 *
 * Start:   pm2 start ecosystem.config.js
 * Stop:    pm2 stop ai-employee
 * Restart: pm2 restart ai-employee
 * Logs:    pm2 logs ai-employee
 * Status:  pm2 status
 * Monitor: pm2 monit
 */

module.exports = {
  apps: [
    {
      name: "ai-employee",
      script: "./start.sh",
      interpreter: "bash",
      args: "--mode both --vault-path /mnt/c/MY_EMPLOYEE --log-level INFO",
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
