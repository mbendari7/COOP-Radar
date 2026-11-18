# How CoopRadar uses Spec Kit

CoopRadar was built spec first. Before any code for a feature gets written there is a spec that says what it does
and why, a plan that says how, and a task list that says in what order. Claude Code does most of the typing
through the `/speckit-*` skills and the developer reads and fixes each document before moving to the next one.

This folder is the Spec Kit side of that. The feature documents themselves live in `specs/NNN-name/`.

## What is in here

| Path | What it is | Edit it? |
|---|---|---|
| `memory/constitution.md` | The project rules every plan is checked against | Yes, through `/speckit-constitution` or a PR with a version bump |
| `templates/spec-template.md` | The shape of `spec.md` (user stories, requirements, success criteria) | Yes, it is filled in for CoopRadar |
| `templates/plan-template.md` | The shape of `plan.md` with the CoopRadar stack and Constitution Check already in | Yes |
| `templates/tasks-template.md` | The shape of `tasks.md` with CoopRadar paths and test commands | Yes |
| `templates/checklist-template.md` | The shape of a review checklist | Yes |
| `templates/constitution-template.md` | The skeleton `/speckit-constitution` starts from | Rarely |
| `scripts/python/` | Helpers the skills run (make the feature folder, copy templates, check what exists) | No, Spec Kit owns them |
| `scripts/powershell/` | The same helpers for PowerShell | No |
| `workflows/speckit/workflow.yml` | The built in specify, plan, tasks, implement workflow with review stops | No |
| `init-options.json`, `integration.json`, `integrations/` | What `specify init` set up (Claude, Python scripts, version 1.1.3) | No |
| `feature.json` | Points at the feature you are working on right now. Git ignores it | The scripts rewrite it |

The scripts and the `speckit-*` skills in `.claude/skills/` come from Spec Kit and get replaced when you run
`specify` to upgrade. The manifests in `integrations/` keep a hash of each one so the upgrade can tell what you
changed. The templates here have been changed on purpose for CoopRadar, so if an upgrade asks, keep these
versions.

## The loop for one feature

Run these from the repo root in Claude Code, one at a time. Read what each one wrote before running the next.

| Step | Command | What it writes | What to check |
|---|---|---|---|
| 1 | `/speckit-specify <what you want>` | `specs/NNN-name/spec.md` and `checklists/requirements.md`, plus a new branch | User stories make sense on their own. No tech words in it |
| 2 | `/speckit-clarify` | Answers written back into `spec.md` | It asks up to 5 questions. Answer them like a product owner |
| 3 | `/speckit-plan <stack notes>` | `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md` | Constitution Check passes. Every new source links its terms and robots.txt |
| 4 | `/speckit-checklist <focus>` | `checklists/<focus>.md` | Tick items only when the spec really covers them |
| 5 | `/speckit-tasks` | `tasks.md` | Each task names a real file. Tests come before the code they test |
| 6 | `/speckit-analyze` | A report, nothing written | Fix any spec, plan and task mismatches it finds |
| 7 | `/speckit-implement` | The code, with tasks ticked as they finish | Run the checks below as it goes |
| 8 | `/speckit-converge` | New tasks added to `tasks.md` for anything still missing | Repeat 7 and 8 until it says Converged |
| 9 | `/log-agentic-work` | An entry in `docs/agentic-workflow.md` | Write the "what I reviewed" part yourself |

A good rule: the spec is the what and the why, the plan is the how. If the spec mentions FastAPI or React it is
doing the plan's job.

The checks to run while building, from `CLAUDE.md`:

```bash
# backend, in backend/ with the venv on and DATABASE_URL pointing at a throwaway Postgres with pgvector
ruff check . && mypy app && pytest -q -m 'not perf' && alembic check
pytest -q -m perf -s

# frontend
cd frontend && npm run lint && npm run typecheck && npm test && npm run build

# browser tests, with the site running
cd frontend && npm run test:e2e
```

## What the scripts do

You do not run these yourself most of the time. The skills call them and read the JSON they print.

| Script | Called by | What it does |
|---|---|---|
| `create_new_feature.py` | `/speckit-specify` | Picks the next number (009 next), makes `specs/NNN-short-name/`, copies the spec template in, makes the git branch, writes `feature.json` |
| `setup_plan.py` | `/speckit-plan` | Finds the current feature and copies the plan template to `plan.md` |
| `setup_tasks.py` | `/speckit-tasks` | Finds the current feature, lists which design docs exist and hands back the tasks template |
| `check_prerequisites.py` | clarify, checklist, analyze, implement, converge | Makes sure the docs a step needs are there and prints their paths |
| `resolve_template.py` | `/speckit-constitution` and others | Finds which copy of a template to use (overrides first, then these core ones) |
| `common.py` | all of them | Shared code: find the repo root, work out the feature folder, read `feature.json` |

If you ever want to run one by hand, for example to see which feature is active:

```bash
python .specify/scripts/python/check_prerequisites.py --json --paths-only
```

On Windows, set `PYTHONIOENCODING=utf-8` first if a script prints a template. The templates have tree drawing
characters that the default Windows console can not print, so without it you get a `UnicodeEncodeError`.

## Starting a new feature

1. `git checkout main && git pull`
2. In Claude Code: `/speckit-specify` followed by a plain description. Look at `docs/speckit-prompts.md` for the
   exact prompts used for 001 to 008. They are good examples of how much detail to give.
3. Follow the loop above.
4. When it is done, update the numbers in the README and guides if sources, tests or migrations changed, then
   open a pull request.

## Where every feature stands

| Feature | Folder | Status |
|---|---|---|
| 001 Browse and search postings | `specs/001-browse-search-postings/` | Built |
| 002 Accounts and application tracker | `specs/002-accounts-tracker/` | Built |
| 003 Real postings and smart search | `specs/003-ingestion-search/` | Built |
| 004 AI resume matcher | `specs/004-ai-resume-matcher/` | Core built. The tool using agent, MCP server and YAML evals are not |
| 005 Bring your own AI key and a resume first site | `specs/005-byok-resume-first/` | Built (spec written after the code) |
| 006 One command run and free hosting | `specs/006-one-command-free-hosting/` | Built (spec written after the code) |
| 007 Co-op matching and job board redesign | `specs/007-coop-matching-job-board/` | Built (spec written after the code) |
| 008 More job sources and instant first load | `specs/008-more-sources-fast-load/` | Built (spec written after the code) |

Features 005 to 008 were built in fast sessions straight from chat, without the full loop. Their specs were
written afterwards from the code, the commit history and `docs/agentic-workflow.md`, so the project has one
place that says what each part is meant to do. They follow the same templates, and their tasks are ticked because
the work is already on `main`. Anything that was planned but never built is left unticked so `/speckit-converge`
can pick it up later.

## Ideas for the next features

From `docs/progress.md` and `docs/PROJECT_GUIDE.md` section 12:

- The rest of 004: a tool using assistant that can search, compare and save with a confirm step, an MCP server
  with the same tools, `agent_runs` logging, and a YAML eval runner that gates CI at 80 percent
- An admin page for adding sources and reviewing low confidence fields
- Error tracking and a small usage dashboard for the live site
- Unsave from the jobs list
- Showing the fit score broken into its parts
