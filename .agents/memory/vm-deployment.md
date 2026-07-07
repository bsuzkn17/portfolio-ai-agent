---
name: VM deployment for Telegram bot
description: This FastAPI + Telegram bot project must use vm (not autoscale) deployment; APP_ENV must be set inline in the run command.
---

**Rule:** Use `deploymentTarget = "vm"` in `.replit [deployment]`. The bot must always be running to receive webhook calls reliably.

**Why:** Autoscale spins down idle instances; a Telegram webhook bot needs an always-on process.

**APP_ENV wiring:** `[deployment.postBuild].env` does NOT carry over to the runtime. Set it inline:
```toml
run = ["bash", "-c", "APP_ENV=production bash python-backend/start.sh"]
```

**How to apply:** The `.replit [deployment]` section is the canonical deployment config for this project because the `api` artifact kind is not recognized as a standalone deployable kind by the publishing UI. The `.replit` run/build commands unlock the Publish button.
