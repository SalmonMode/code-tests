# AGENTS.md

## Scope
- Default to working only in `inventory-reconciliation/` unless the user explicitly asks for another folder.

## First Read
- Before making changes in this project area, read:
  - `inventory-reconciliation/README.md`
  - `inventory-reconciliation/NOTES.md`

## Notes Ownership Protocol
- Keep user and assistant notes clearly separated in `inventory-reconciliation/NOTES.md`.
- Use this structure:
  - `## User Notes` for user-authored content.
  - `## Codex Notes (AI-authored only)` for assistant-authored content.
- Assistant entries must be appended with this header format:
  - `### [Codex] <title>`
- Do not edit or rewrite user-authored notes unless explicitly asked.

## Data-Scan Expectations
- When asked to scan snapshots, inspect all files under `inventory-reconciliation/data/`.
- In assistant findings, include precise evidence (file paths and line numbers when available).
- Flag potential reconciliation blockers explicitly (for example: schema drift, key formatting issues, duplicates, invalid quantities, date inconsistencies, whitespace anomalies).
