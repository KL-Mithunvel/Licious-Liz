# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **This is a template.** The contents of this file — and any `CLAUDE.md` derived from it — are not final. They must be updated throughout the project as the architecture evolves, new conventions are established, and the TODO list changes. Treat every section as a living document, not a one-time snapshot.

---

## Repository Purpose

This repo is a curated library of `CLAUDE.md` files. Each file serves as a project brief for AI-assisted development sessions — capturing architecture, rules, conventions, and status so that Claude Code can contribute effectively without needing to re-discover project context from scratch.

The files here are used as **standard templates and reference material** for future projects.

---

## Repo Structure

| File | Project |
|------|---------|
| `<project-id>.md` | `<Project name — one-line description>` |

New entries follow the same naming convention: `<short-project-id>.md`.

---

## How to Use These Files

When starting a new project or a new AI session on an existing project:

1. Copy the relevant `.md` file into the project root and rename it `CLAUDE.md`.
2. Update the **Project Overview**, **Architecture**, **Current Status**, and **TODO List** sections to match the actual project state.
3. Keep the **Development Rules** and **User Rules** sections verbatim — they are standard across all projects unless explicitly overridden.
4. Fill in `Schema Reference` and `Key Conventions` for any project with a database or non-obvious data encoding. Delete them only if the project has no data layer at all.
5. Fill in `Deployment Notes` for any project with a hardware or remote server target.

---

## Standard User Rules (Apply to Every Project)

These rules carry over to every `CLAUDE.md` derived from this library. Copy this entire section into derived files verbatim.

### Companion Files

Claude must maintain two files in every project root alongside `CLAUDE.md`. Create them on the first session if they do not exist.

#### `Claude_todo.md` — Task Tracker

Tracks what has been done and what still needs doing. Update it whenever a task is started, completed, or discovered.

```markdown
# Claude TODO

## In Progress
- [ ] <task>

## Done
- [x] <task> — <brief note on outcome>

## Not Started
- [ ] <task>
```

Rules:

- Move items from **Not Started → In Progress → Done** as work progresses. Never delete entries; they are the audit trail.
- Add newly discovered tasks immediately — do not hold them until the end of a session.
- Link to the relevant commit hash next to Done items where possible.

#### `Claude_log.md` — Session Log

Records what was actually done, session by session. Append a new entry at the start of every session and fill it in as work proceeds.

```markdown
# Claude Log

## YYYY-MM-DD — <one-line session summary>
- <action taken and outcome>
- <files changed and why>
- <decisions made and rationale>
- <anything left incomplete and why>
```

Rules:

- One dated entry per session. Multiple entries on the same date are allowed if there are distinct work blocks.
- Keep entries factual and concise — not a stream of consciousness. Focus on *what changed* and *why*.
- Both files must be committed alongside any code changes they describe. Never let them drift out of sync.

---

### Interaction Rules

- **Every git commit must include a co-author trailer** for `kl mithunvel <klm@smtw.in>`. Add the following line at the end of every commit message body (after a blank line):

  ```
  Co-authored-by: kl mithunvel <klm@smtw.in>
  ```

- **Always explain before acting.** Before making any code changes, edits, or file writes, describe exactly what you are going to do and wait for explicit confirmation from the user. List every file that will be changed and what will change in each. Do not proceed until the user says to go ahead.

---

### Deployment Model

**The hard rule: write and test on the development machine first. Hardware comes last.**

This applies to every project that has a hardware target (Raspberry Pi, Arduino, embedded Linux, remote server). It is not optional.

#### Stages — always in this order

1. **Code on dev machine** — write all logic, module interfaces, and data flows on the laptop/desktop. The dev machine is Windows or Linux; it has no GPIO, no I2C, no serial ports.
2. **Test on dev machine** — run the full test suite (`pytest`). Verify the feature works end-to-end using the simulation/dev stack (fake sensors, mock hardware, local SQLite). Fix all failures before moving on.
3. **Review for hardware impact** — before touching the device, explicitly state which parts of the change touch real hardware (GPIO pins, I2C addresses, serial ports, baud rates) and which parts are pure logic.
4. **Deploy to hardware** — only after steps 1–3 are complete. Transfer code via `git pull`, `rsync`, `scp`, or `arduino-cli` as appropriate for the project. Run the hardware smoke test.
5. **Verify on hardware** — run the hardware-specific test or verification script. Note any behaviour difference from simulation. If there is a discrepancy, fix it on the dev machine (step 1) and repeat — never patch directly on the device.

#### Rules that follow from this

- **Every hardware driver must have a simulated equivalent** that runs on the dev machine and produces the same data shape and exceptions. Code written without a simulation path cannot be tested in stage 2 and breaks the workflow.
- **Never hardcode hardware addresses, port names, or pin numbers in driver files.** They go in `config.yaml` and are passed as parameters. This lets the same code run in simulation (with dev values) and on hardware (with real values).
- **When proposing a change**, always separate it into: (a) logic that can be fully verified on the dev machine, and (b) hardware-specific parts that need device testing. State both explicitly so the user knows what to test where.
- **Never instruct the user to "just run it on the device"** as a substitute for a dev-machine test. If a test cannot be run on the dev machine due to a hardware dependency, say so clearly and explain what the device test will verify.

---

### Commands & Workflow

- **Always activate the project virtualenv before running any Python command.** Use `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows). Never invoke `python` or `pip` bare without the venv active.
- Track all dependencies in `requirements.txt`. Pin at least the major version. Run `pip freeze > requirements.txt` after installing anything new.
- A migration to `uv` is planned. Flag `uv` as a recommended replacement whenever suggesting new tooling or packaging steps.
- Run lints (`python -m py_compile` at minimum, `flake8` or `ruff` if configured) and the test suite before every commit.

---

### Software Engineering Preferences

- **DRY (Don't Repeat Yourself):** Extract shared logic into reusable functions. Avoid copy-pasting code blocks.
- **Testing is important:** Write tests for new functionality. Cover the happy path and key failure modes. Use `pytest`; tests live in `tests/`.
- **Consider edge cases:** Think about nulls, empty inputs, boundary values, and concurrent access. Clarify with me if requirements are ambiguous.
- **Explicit over implicit and clever:** Write clear, readable code. Avoid magic numbers, obscure one-liners, and hidden side effects. If someone has to puzzle over what it does, rewrite it.
- **Proper error handling:** Handle errors at the right level. Return meaningful messages. Don't silently swallow exceptions.
- **Deprecation:** Never use deprecated APIs, functions, or modules. If found, rewrite to avoid them after consulting me.

---

### General Principles

- **Simplicity first:** Minimal, straightforward code. No over-engineering.
- **Explain always:** Document your code and decisions. Explain choices and how things work.
- **Backend-heavy:** Prefer logic in the backend; keep frontends thin.

---

### Tech Stack Preferences

| Layer | Choice | Notes |
|-------|--------|-------|
| Languages | Python (latest stable), JavaScript/TypeScript | |
| Backend frameworks | Flask, FastAPI | Flag when FastAPI would be a better fit than Flask |
| Frontend frameworks | Vanilla JS / lightweight frameworks | Keep it simple |
| Python GUI | Tkinter | When a desktop UI is needed |
| Database | SQLite (preferred for local/app data) | Never write to read-only external sources |
| Python packaging | pip + venv | Planned migration to `uv` — flag when recommended |
| Configuration | YAML | For all settings and config files |
| Infrastructure | Windows, Debian/Raspberry Pi OS, Ubuntu LTS | Guard any OS-specific code behind checks |

---

## Standard Template Structure

Every `CLAUDE.md` in this library follows this skeleton. **Sections marked `[if applicable]` are included when relevant and omitted otherwise.** Each section includes a one-line description of exactly what belongs there — fill it in completely or delete it; a half-filled section is worse than a missing one.

```
# CLAUDE.md

## Project Overview
  — What the project is, who built it, the core problem it solves.
  — Author, license, entry point, minimum runtime versions.

## Running the System
  — Copy-paste-ready commands to start, test, and lint.
  — Virtualenv activation step first.
  — Dev/simulation mode commands separated from hardware/production commands.
  — Any seed-data or one-time setup steps.

## Architecture
  — Module responsibilities table (file → role).
  — Data flow diagram (ASCII).
  — Threading or async model (background threads, queues, event loops).
  — Two modes if applicable: simulation/dev vs real/hardware, and how to switch.

## Key Modules
  — One subsection per file or logical group.
  — Public interface: function names, parameters, return types, exceptions raised.
  — Side effects and I/O (files written, network calls, hardware access).

## Schema Reference  [if applicable — any project with a DB or external data source]
  — Path to the DDL / schema file and what it covers (table count, source DB engine).
  — Read-only vs writable databases — call out explicitly which is which.
  — Any tooling for probing or inspecting the DB (probe scripts, GUIs, CLI commands).
  — Path to the annotated schema doc (SCHEMA.md or equivalent) if one exists.
  — Standing instruction: update the annotated doc whenever a new table relationship
    or encoding is discovered — do it in the same commit, not as a follow-up.

## Key Conventions  [if applicable — any non-obvious encoding, key, or domain rule]
  — Universal row keys (name, type, which tables carry it).
  — Encoded fields: encoding formula AND decode formula, both written out in full.
    Never leave the decode implicit — Claude will guess wrong without it.
  — Sentinel / special values: what NULL means, what -1 means, what empty string means.
  — "Current record" pattern: which column and which value indicate the active row.
  — Per-tenant / per-instance data partitioning: directory layout, naming convention,
    and the helper function that resolves the path.
  — Environment variables: name, what it overrides, and the hard-coded default.

## Data Files
  — What is stored, where, and whether it is git-tracked.
  — Runtime-generated files (logs, caches, DBs) vs committed files.
  — Files that must never be committed (credentials, large binaries).

## Platform Constraints
  — Target OS(es) and any OS-specific branching in the code.
  — Libraries that are platform-specific and how each is guarded (try/except ImportError).
  — Hardware dependencies (I2C, UART, GPIO, RS485) and their dev-mode equivalents.

## Deployment Notes  [if applicable — projects with a hardware or remote server target]
  — Two-environment table: dev machine (OS, Python version, what hardware is absent)
    vs deployment target (OS, Python version, what hardware is present).
  — How to transfer code: exact command (git pull / rsync / scp / arduino-cli upload).
  — One-time setup steps on the target that are NOT in requirements.txt
    (apt packages, system services, udev rules, etc.).
  — Pre-deploy checklist: what must pass on the dev machine before touching hardware.
  — Hardware smoke-test: the exact command to run on the device to confirm it works.
  — Config / env differences between dev and deployment
    (port names, GPIO chip paths, I2C addresses, env vars that change).

## Known Technical Debt
  — Existing rule violations, numbered by the rule they violate (file + line if known).
  — Temporary workarounds that must be cleaned up before the next milestone.
  — Do not omit or minimise debt — document it so it is not accidentally perpetuated.

## Development Rules
  — Binding architectural rules, each numbered and sourced (wiki page, agreed spec, etc.).
  — Rules are referenced by number in TODO items and commit messages.

## Project TODO List
  Legend: 🔴 Bug / rule violation  |  🟡 Incomplete feature  |  🟢 Not started  |  ✅ Done
  Group by severity: CRITICAL → HIGH → MEDIUM → LOW → NOT STARTED → DONE.

## User Rules
  — Paste the full Standard User Rules section here verbatim.
  — Add project-specific overrides or additions below them, clearly labelled.
```

---

## Example: Schema Reference & Key Conventions

> **This is a generic example. Replace every value with your project's actual data.**

The two sections below are the most often under-filled. Use this block as a model when writing a new project brief.

### Schema Reference

- `schema/schema.sql` — Full DDL exported from the source database
- `schema/SCHEMA.md` — Annotated interpretation: table purposes, join paths, quirks
- **The source schema is read-only — never attempt to modify it.**
- Use `tooling/probe.py <TABLE_NAME>` to fetch sample records from any table.
- Update `schema/SCHEMA.md` in the same commit whenever a new table relationship or field encoding is discovered. Do not leave it as a follow-up.

### Key Conventions

- **`ENTITY_ID`** — universal primary key across all tables; always an integer; never null.
- **`PERIOD`** — integer encoded as `YEAR * 12 + MONTH` (not YYYYMM, not a date).
  - Encode: `P = year * 12 + month`
  - Decode: `month = P % 12 or 12`, `year = P // 12 - (1 if month == 12 else 0)`
  - Example: April 2024 → `2024 * 12 + 4 = 24292`
- **`ENTITY_MASTER`** — `END_DATE IS NULL` means current/active record. Always filter with `WHERE END_DATE IS NULL` when you want the current state.
- **Per-instance data** is stored under `backend/data/<INSTANCE_ID>/`. Always resolve this path via the `_data_dir(instance_id)` helper — never construct the path by hand.
- **`APP_DATA_ROOT`** env var overrides the data root directory. Default: `backend/data/`.

### What makes these sections effective

| Property | Why it matters |
|----------|----------------|
| Decode formula written out in full | Claude will derive the wrong formula from the field name alone |
| A worked numeric example for encoded fields | Confirms the formula is correct; catches off-by-one errors in the doc itself |
| "Current record" sentinel named explicitly | Without this, Claude queries all history rows and gets inflated results |
| PK type stated (text vs integer) | Prevents type-mismatch bugs in generated SQL and ORM queries |
| Path helper named | Prevents hand-rolled path strings scattered across the codebase |
| Env var default value stated | Lets Claude reason about behaviour without needing to read the source |

---

## Example: Deployment Notes

> **This is a generic example. Replace every value with your project's actual data.**

### Environments

| | Dev machine | Deployment target |
|--|-------------|-------------------|
| OS | Windows 11 / Ubuntu 22.04 | Raspberry Pi OS (Debian Bookworm, 64-bit) |
| Python | 3.12 (venv) | 3.11 (system) |
| Hardware | None — simulated via `hw/sim.py` | Actual sensors / actuators |
| Entry point | `python main_sim.py` | `python main.py` |
| Service URL | `http://127.0.0.1:5000` | `http://<device-ip>:5000` |

### Transferring Code

```bash
# On the target device — pull latest
git pull origin main

# From dev machine — push files directly
rsync -avz --exclude '.git' --exclude 'data/' ./ user@<device-ip>:~/project/
```

### One-Time Setup on Target (not in `requirements.txt`)

```bash
sudo apt install python3-smbus python3-libgpiod
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

### Pre-Deploy Checklist (must pass on dev machine first)

- [ ] `pytest tests/` passes with zero failures
- [ ] `python main_sim.py` starts and the UI/dashboard loads correctly
- [ ] Data files are being written each poll cycle
- [ ] No unfinished `TODO` stubs in any function called during the run

### Hardware Smoke Test (run on device after deploy)

```bash
# Test each hardware interface individually
python hw/sensor_a.py    # should print live readings
python hw/sensor_b.py    # should print live readings

# Run the full system
python main.py
```

### Config / Env Differences Between Dev and Target

| Setting | Dev value | Target value | Where set |
|---------|-----------|--------------|-----------|
| Hardware port | N/A | `/dev/ttyACM0` | `config.yaml` |
| GPIO chip | N/A | `/dev/gpiochip0` | `config.yaml` |
| `USE_REAL_HARDWARE` flag | `False` | `True` | Top of `main.py` — edit before deploy |

---

## Commit Message Style

Use imperative mood, short subject line (≤ 72 chars), no trailing period:

```
Add CLAUDE.md for project X
Update TODO list after database integration
Fix Key Conventions section for encoding bug
Add Schema Reference for new data source
```

Do not use vague messages like `update`, `fix stuff`, or `changes`.

---

## Quick Reference

```bash
# List all project briefs in this repo
ls *.md

# Copy a brief into a new project
cp <project-id>.md ~/projects/new-project/CLAUDE.md

# Always activate the venv first (every session, every project)
source venv/bin/activate    # Linux / macOS / Raspberry Pi
venv\Scripts\activate       # Windows
```