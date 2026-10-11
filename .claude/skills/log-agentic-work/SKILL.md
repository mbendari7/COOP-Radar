---
name: log-agentic-work
description: Append an entry to docs/agentic-workflow.md describing what the AI assistant built this session and what the developer reviewed or changed.
disable-model-invocation: true
---

## Recent commits
!`git log --oneline -15 || true`

Append one entry to `docs/agentic-workflow.md` (create it if missing) with:
- Date and a one-line title of the feature or change
- What the AI assistant did (files, skills, or subagents used)
- What I reviewed, rejected, or rewrote, and why (ask me if you don't know — never invent this part)
- Tests/evals added and their actual result (counts from the real run, not expectations)

Keep it to 6–10 lines. This file is portfolio evidence, so be specific and honest.

Commits for this work follow the repo rules: conventional messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`)
and **no `Co-Authored-By` or other AI attribution lines**.
