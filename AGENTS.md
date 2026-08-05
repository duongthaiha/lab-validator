# AGENTS.md

Working notes for coding agents live in
[`.github/copilot-instructions.md`](.github/copilot-instructions.md).

Read it before changing anything. The short version:

- `python -m pytest -q` and `python -m ruff check .` must both pass. The suite
  is offline; no test needs a browser or a live lab.
- Edited `SKILL.md`, `references/`, `assets/`, `src/`, `scripts/` or
  `pyproject.toml`? Run `python -m lab_validator.cli install-skill`. The
  repository *is* the skill; there is no staging step.
- Docs are tested against the code — rename a module or add a CLI flag and you
  must update `README.md`, `SKILL.md` and `docs/cli.md` in the same change.
- Changing how the skill *judges*? Run the evals — see `evals/README.md`. They
  need no lab and no browser.
- Never commit anything under `runs/`, `artifacts/`, `.auth/` or
  `.browser-profile/`; they carry real lab credentials.
