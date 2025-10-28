module.exports = {
  apps: [
    {
      name: "neolight-backend",
      script: "uvicorn",
      args: "backend.main:app --host 0.0.0.0 --port 8000",
      autorestart: true,
      max_restarts: 50
    },
    {
      name: "neolight-agent",
      script: "python",
      args: "tools/agent_loop.py",
      autorestart: true,
      max_restarts: 50
    }
  ]
}
