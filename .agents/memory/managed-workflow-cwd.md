---
name: Managed workflow CWD
description: Artifact managed workflows do not run from the workspace root; use pnpm -w run to invoke root scripts.
---

The run command in an artifact's `artifact.toml` [services.development] section is NOT executed from the workspace root. Both relative paths (`bash python-backend/start.sh`) and artifact-relative paths (`bash artifacts/api-server/start.sh`) fail with "No such file or directory".

**Why:** The managed workflow runner appears to resolve the command from an unknown directory, not the monorepo root.

**How to apply:** Always route artifact dev commands through `pnpm -w run <script>` — the `-w` flag forces resolution from the workspace root, and pnpm itself is always in PATH. Add the script to the root `package.json` scripts section. Example:
- `package.json`: `"dev:python": "bash python-backend/start.sh"`
- `artifact.toml`: `run = "pnpm -w run dev:python"`
