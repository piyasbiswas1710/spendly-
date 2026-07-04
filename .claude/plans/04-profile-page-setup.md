# Plan: Step 4 — Profile Page Design

Replace the render-only `GET /profile` stub (`return "Profile page — coming in Step 4"`) with a login-protected view that renders a new `profile.html` populated entirely from **hardcoded** context assembled in `app.py`. No database queries this step — the UI (user card, summary stats, transaction table, category breakdown) is built in isolation so the design can be validated before Step 5 wires in real data. Based on `.claude/specs/04-profile-page.md`.

## Design source: `spendly-ui-designer` skill (`.claude/skills/frontend-design/SKILL.md`)
Per the user's explicit choice, the UI follows the **spendly-ui-designer** skill's design language: card-based composition, generous whitespace, a summary-card row + transaction table + category breakdown, right-aligned amounts with `font-variant-numeric: tabular-nums`, row hover on the table, and the skill's restraint principles (solid over gradient, border over heavy shadow). The skill's own guidance (SKILL.md lines 27, 39) says to **override its default palette/fonts to match what already exists** — so:

**Two skill-vs-repo conflicts, resolved with the user:**
1. **Icons — vanilla glyphs / inline SVG, NOT Lucide.** The skill suggests Lucide via CDN, but that adds an external JS library and edits shared `base.html`, violating CLAUDE.md ("Vanilla JavaScript Only", no new deps). User chose vanilla glyphs (like the existing `◈`). No `base.html` change, no CDN.
2. **Colors — repo CSS variables, NOT the skill's indigo `#6366F1` defaults.** CLAUDE.md/spec forbid hardcoded hex and the app's accent is green (`--accent: #1a472a`). Using the skill's palette would clash with nav/landing/auth. The skill explicitly endorses this override.

## Context (verified against the code)
- `app.py` already imports `session` and sets `app.secret_key`. `login()` stores `session["user_id"]` and `session["user_name"]` on success, then redirects to `profile`. The `profile()` view is a raw-string stub with a bare `@app.route("/profile")` (GET only) and **no auth guard**.
- `templates/base.html` navbar is already session-aware: shows Profile / Logout when `session.get('user_id')`, else Sign in / Get started. Blocks available: `title`, `head`, `content`, `scripts`.
- `templates/login.html` / `register.html` set the template idiom: `{% extends "base.html" %}`, `{% block title %}`, a `<section>` wrapper, and reuse of design-system classes.
- `database/db.py` is fully implemented: `users` (`id, name, email, password_hash, created_at`) and `expenses` (`id, user_id, amount, category, date, description, created_at`) tables, plus a `CATEGORIES` list (Food, Transport, Bills, Health, Entertainment, Shopping, Other). **No DB changes needed** — spec confirms this.
- `static/css/style.css` defines design tokens (`--ink`, `--ink-muted`, `--ink-soft`, `--accent`, `--accent-2`, `--accent-light`, `--accent-2-light`, `--paper-card`, `--border`, `--radius-sm/md/lg`, fonts) and reusable patterns (`.dash-stats`, `.dash-bar-*`, `.mock-card`, `.feature-card`) but **no profile-specific classes**.
- Seed user for testing: `demo@spendly.com` / `demo123` with 8 sample expenses across every category.

## 1. `app.py` — real `profile()` view
- Keep `@app.route("/profile")` (GET only — matches spec; no POST).
- **Auth guard first:** `if not session.get("user_id"): return redirect(url_for("login"))`.
- Assemble **hardcoded** literals (no `get_db()` call this step, per spec):
  - `user` — dict: `name`, `email`, `initials` (e.g. `"DU"`), `member_since` (e.g. `"January 2026"`).
  - `stats` — dict: `total_spent` (e.g. `3949`), `transaction_count` (e.g. `8`), `top_category` (e.g. `"Bills"`).
  - `transactions` — list of ≥5 dicts: `date`, `description`, `category`, `amount` (mirroring the seed fixtures for realism).
  - `categories` — list of dicts: `name`, `amount`, `percent` (bar width).
- `return render_template("profile.html", user=user, stats=stats, transactions=transactions, categories=categories)`.
- No SQL and no business logic in the route — it only builds literals and renders (data is static this step).

## 2. `templates/profile.html` — new template (skill design language)
- `{% extends "base.html" %}`, `{% block title %}Profile — Spendly{% endblock %}`.
- A `<section class="profile-section">` with four card-based blocks (skill: group related info in surfaces), all using new `profile-*` classes:
  1. **User info card** — avatar circle showing `user.initials` (glyph/initials, no icon lib), then `user.name`, `user.email`, `user.member_since`. Left-aligned hierarchy per skill.
  2. **Summary stats row** — three stat cards (skill's "summary cards on top" pattern): total spent (`₹`), transaction count, top category. Amounts use `tabular-nums`.
  3. **Transaction history table** — `<table>` with Date / Description / Category / Amount; **amount column right-aligned with `tabular-nums`, row hover** (skill table rules); category rendered as `<span class="category-badge category-badge--{{ t.category|lower }}">` (CSS class, never inline color).
  4. **Category breakdown** — progress-bar rows: `category.name`, `₹` amount, and a bar fill whose width is `style="width: {{ category.percent }}%"`.
- Optional meaningful glyphs (inline SVG/Unicode, one per section heading — skill's "one icon per section, icons carry meaning" density), rendered vanilla — no Lucide/CDN.
- All internal links via `url_for()`; amounts prefixed with `₹` (Indian Rupee convention); `{% for %}` loops over the context lists.
- Mobile: stack cards vertically and make the table horizontally scrollable below ~768px (skill's mobile rule) using the repo's existing responsive breakpoint style.

## 3. `static/css/style.css` — append a Profile section (skill aesthetic, repo tokens)
- New classes (skill's scoped-prefix convention): `.profile-section`, `.profile-header`, `.profile-card`, `.profile-avatar`, `.profile-stats`, `.stat-card`, `.stat-label`, `.stat-value`, `.txn-table`, `.category-badge` + one modifier per category (`--food`, `--transport`, `--bills`, `--health`, `--entertainment`, `--shopping`, `--other`), `.breakdown-row`, `.breakdown-track`, `.breakdown-bar`.
- **Only CSS variables** for colors (`--accent`, `--accent-2`, `--accent-light`, `--accent-2-light`, `--ink-*`, `--paper-card`, `--border`, `--danger`, …) — no new hex literals; overrides the skill's indigo defaults per its own "match existing" instruction. Reuse spacing/radius tokens (`--radius-sm/md/lg`).
- Skill visual rules applied via existing tokens: soft border + subtle shadow on cards (border over heavy shadow), `font-variant-numeric: tabular-nums` on all amount values, right-aligned numeric table column, subtle row-hover background, fully-rounded category badges.

## Bar-width decision (confirmed with user)
Category-breakdown bar widths are dynamic layout data. Approach chosen: set `style="width: {{ percent }}%"` on the **bar-fill element only** — mirrors the existing `.mock-bar` pattern. All colors/styling stay in CSS classes; only the numeric width is inline.

## Deviations (flagged)
- **CSS file addition:** The spec's "Files to create/change" lists only `templates/profile.html` and `app.py`, but its own rules ("No inline styles", "Category badges must use a CSS class") cannot be satisfied without new CSS. This plan **adds** a Profile section to `static/css/style.css`. No new hex values (CSS variables only).
- **Skill vs. Lucide:** The `spendly-ui-designer` skill recommends Lucide icons via CDN; this plan deliberately does **not** follow that (uses vanilla glyphs/inline SVG) to respect CLAUDE.md's vanilla-only / no-new-deps rule and avoid editing shared `base.html`. Per user decision.
- **Skill vs. palette:** The skill's default indigo palette is **not** used; repo CSS variables drive all color, per the skill's own "override to match existing" guidance and CLAUDE.md's no-hardcoded-hex rule.

## No changes
- `database/db.py` (no DB work this step), `templates/base.html` (navbar already session-aware), `requirements.txt` (no new deps), other stub routes (untouched). App stays on **port 5001**.

## Guardrails
- No SQLAlchemy/ORM; parameterized queries only if any DB call is ever added (none this step).
- All templates extend `base.html`; every internal link uses `url_for()`.
- Colors via CSS variables only; category badges use CSS classes, not inline color.
- Auth guard uses `session.get("user_id")`; unauthenticated → `redirect(url_for("login"))`.

## Verification (post-implementation, delegated to a subagent per CLAUDE.md)
- `GET /profile` while logged out → 302 → `/login`.
- `GET /profile` while logged in (`demo@spendly.com` / `demo123`) → HTTP 200.
- Page shows: user card (name + email), ≥3 summary stats, transaction table with ≥3 rows, category breakdown with ≥3 categories.
- Navbar shows Profile / Logout.
- `profile.html` extends `base.html`; every link uses `url_for()`; category badges use CSS classes; colors are CSS variables only; no DB query in the route.
