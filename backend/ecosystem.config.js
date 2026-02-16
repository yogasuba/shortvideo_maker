module.exports = {
  apps: [
    {
      name: "api-server",
      script: "python",
      args: "main.py",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        PORT: 8001,
        PYTHONIOENCODING: "utf-8",
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "scheduler-worker",
      script: "python",
      args: "scheduler_worker.py",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        PYTHONIOENCODING: "utf-8",
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
