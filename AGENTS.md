# Project instructions

Before planning or modifying files, read:

`~/projects/AGENTS.md`

If the workspace policy cannot be read, stop and report that it is unavailable.

The rules below supplement or tighten the workspace policy for this repository.

## Project boundary

- This active local automation tool launches applications and controls KWin windows on KDE Plasma/Wayland.
- Preserve the declarative YAML schema, argument-array execution model, KWin transport boundary, and user-level installation behavior.
- Tests must remain synthetic and must not require a live desktop session, launch operator applications, or alter the user's window layout.

## Commands and external boundary

- Setup: `make env`; tests: `make test`.
- `make run ARGS=...` launches configured applications and changes desktop state; run it only on a direct request with a synthetic configuration.
- `install.sh` and `uninstall.sh` modify user-level installation/configuration state and require an explicit installation task.
- There is no `make check` or `make ci`. GitHub Actions runs pytest plus compile, shell syntax, ShellCheck, and JavaScript syntax checks directly.

## Done criteria

- Python behavior changes require focused pytest coverage and `make test`.
- Installer, completion, or KWin backend changes should also mirror their applicable syntax/static checks from `.github/workflows/ci.yml`.
- Report any live KDE verification not performed.
