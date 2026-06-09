# Agent Notes

## Local Execution

This repository lives in WSL Ubuntu at:

```text
/home/shogunix/AnotherEdenAI
```

Codex desktop may enter through the Windows UNC path:

```text
\\wsl.localhost\Ubuntu\home\shogunix\AnotherEdenAI
```

If sandboxed PowerShell or Node commands fail with a message like `windows sandbox failed: spawn setup refresh`, treat it as a host/sandbox bridge issue around the WSL UNC workspace, not as an application failure.

Use WSL directly for repo commands:

```powershell
wsl -d Ubuntu --cd /home/shogunix/AnotherEdenAI bash -lc '<command>'
```

## Python And Tests

Prefer the checked-in virtual environment when running tests:

```bash
.venv/bin/pytest tests/unit/test_pipeline.py
```

The system Python may not have project dependencies such as `nodriver`, and Windows PowerShell may not have `pytest` or `uv` on PATH.

## Git

When Git reports dubious ownership from the Windows UNC path, use a per-command safe directory rather than changing global config:

```bash
git -c safe.directory=/home/shogunix/AnotherEdenAI status --short
```

Do not read `.env` or other credential-bearing files while doing release sync or documentation work.
