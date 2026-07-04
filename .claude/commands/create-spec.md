---
description: Create a spec file and feature branch for the next Spendly step
argument-hint: <step_number> <feature_name> (e.g. 2 registration)
allowed-tools: Read, Write, Glob, Bash(git:*)
---
You are a senior developer spinning up a new feature for the Spendly expense tracker. Always follow the rules in `CLAUDE.md`.

User input:

```text
$ARGUMENTS
```

## Step 1 — Check Working Directory

Run `git status` and verify the working directory is clean.

If there are any:

- Uncommitted changes
- Unstaged changes
- Untracked files

Stop immediately and tell the user to commit or stash their changes before proceeding.

Do **not** continue until the working directory is clean.

---

## Step 2 — Parse Arguments

Extract the following from `$ARGUMENTS`:

### `step_number`

- Integer
- Zero-pad to two digits

Examples:

- `2` → `02`
- `11` → `11`

### `feature_title`

A human-readable title in **Title Case**.

Examples:

- Registration
- Login and Logout

### `feature_slug`

Create a git-safe slug.

Rules:

- Lowercase
- Kebab-case
- Only `a-z`, `0-9`, and `-`
- Maximum 40 characters

Examples:

- registration
- login-logout

### `branch_name`

Format:

```text
feature/<feature_slug>
```

Example:

```text
feature/registration
```

If the required values cannot be inferred from `$ARGUMENTS`, ask the user for clarification before proceeding.

---

## Step 3 — Ensure Branch Name Is Available

Run:

```bash
git branch
```

If the intended branch already exists, append a numeric suffix:

```text
feature/registration-01
feature/registration-02
...
```

---

## Step 4 — Update Main Branch

Run:

```bash
git checkout main
git pull origin main
```

---

## Step 5 — Create the Feature Branch

Run:

```bash
git checkout -b <branch_name>
```

---

## Step 6 — Research the Codebase

Before writing the specification, read:

- `CLAUDE.md`
- `app.py`
- `database/db.py`
- Every file in `.claude/specs/`



---

## Step 7 — Generate the Specification

Create a specification document using the following structure.

### Spec: `<feature_title>`

#### Overview

A short paragraph describing:

- What this feature does.
- Why it belongs at this stage of the Spendly roadmap.

---

#### Depends on

List the previous implementation steps this feature requires.

---

#### Routes

Document every new route:

```text
METHOD /path — description — access level
```

Example:

```text
POST /login — Authenticate user — Public
GET /profile — Display profile — Logged-in
```

If no routes are required, write:

```text
No new routes.
```

---

#### Database Changes

Describe:

- New tables
- New columns
- Constraints

Always verify against `database/db.py`.

If none are required, write:

```text
No database changes.
```

---

#### Templates

##### Create

List all new templates with their paths.

##### Modify

List existing templates and describe the required changes.

---

#### Files to Change

List every existing file that will be modified.

---

#### Files to Create

List every new file that will be created.

---

#### New Dependencies

List any required Python packages.

If none:

```text
No new dependencies.
```

---

#### Rules for Implementation

Always include these constraints:

- No SQLAlchemy or ORMs.
- Parameterized SQL queries only.
- Hash passwords using `werkzeug`.
- Use CSS variables; never hardcode hex color values.
- All templates must extend `base.html`.

---

#### Definition of Done

Create a checklist where every item can be verified by running the application.

---

## Step 8 — Save the Specification

Save the document to:

```text
.claude/specs/<step_number>-<feature_slug>.md
```

---

## Step 9 — Report Completion

Print the following summary exactly:

```text
Branch:    <branch_name>
Spec file: .claude/specs/<step_number>-<feature_slug>.md
Title:     <feature_title>
```

Then print:

```text
Review the spec at .claude/specs/<step_number>-<feature_slug>.md then enter Plan Mode with Shift+Tab twice to begin implementation.
```

Do **not** print the full specification in chat unless the user explicitly requests it.