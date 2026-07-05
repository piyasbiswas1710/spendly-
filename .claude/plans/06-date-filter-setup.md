# Implementation Plan: Date Filter

A step-by-step build order for the Date Filter feature, sequenced so each piece can be built and tested before moving to the next.

---

## 1. `database/db.py` — Date range resolution helper (build first, no dependencies)

**`resolve_date_range(range_key, start_date=None, end_date=None)`**

- `all_time` → `(None, None)`
- `this_month` → `(first day of current month, today)` — bounding by today's date (rather than end-of-month) is safer since dates won't exceed today anyway
- `last_month` → `(first day of previous month, last day of previous month)` — needs careful month/year rollover math (e.g., January → previous December of prior year)
- `last_30_days` → `(today - 30 days, today)`
- `custom` → validate `start_date`/`end_date` are well-formed `YYYY-MM-DD` strings (try `datetime.strptime`); if either is missing/malformed, or `start_date > end_date`, fall back to `all_time` bounds `(None, None)`
- Anything unrecognized in `range_key` → fall back to `all_time`

**Test this in isolation first** (e.g., a quick Python shell or throwaway script) before touching the other helpers — it's pure logic with no DB/session dependency, so it's the cheapest thing to get right early, and everything else depends on it.

---

## 2. `database/db.py` — Extend the three existing helpers

For each of `get_recent_transactions`, `get_profile_stats`, `get_category_breakdown`:

- Add `start_date=None, end_date=None` params
- Append `AND date >= ?` / `AND date <= ?` to the existing `WHERE user_id = ?` clause **only when the corresponding value isn't `None`** — likely cleanest as building a clause list + params list conditionally, then joining, rather than nested if/else string branches
- Double check parameterization: every added clause uses `?` placeholders, values go in the params tuple — no f-strings
- Confirm ordering (`date DESC, id DESC`) and existing zero-result behavior (`0` / `"—"` / `[]`) are unchanged when bounds are `None`

**Test:** call each helper directly with a known `user_id` and a couple of hardcoded date ranges against your existing seed data, confirm row counts/sums match what you'd expect by eyeballing the data.

---

## 3. `app.py` — Wire up the `profile()` route

- Read `range = request.args.get('range', 'all_time')`, `start_date = request.args.get('start_date')`, `end_date = request.args.get('end_date')`
- Call `start_date, end_date = resolve_date_range(range, start_date, end_date)`
- Pass `start_date`/`end_date` into the three Step 5 helper calls
- Pass the *original* query-string values (`range`, raw `start_date`, raw `end_date` — not the resolved ones) back into `render_template()` so the form can re-populate correctly, including showing what the user actually typed even if it was invalid

**Test:** hit `/profile?range=this_month`, `/profile?range=custom&start_date=2026-01-01&end_date=2026-01-31`, and a malformed one like `/profile?range=custom&start_date=garbage` directly in the browser before touching the template — confirm no crashes and sane data via print/debug statements if needed.

---

## 4. `templates/profile.html` — Add the filter form

- `<form method="GET" action="{{ url_for('profile') }}">` above the transaction history card
- `<select name="range">` with the 5 options, marking the currently active one as `selected` using the value passed back from `app.py`
- Two `<input type="date" name="start_date">` / `name="end_date"`, pre-filled with whatever was passed back, wrapped in a container that's hidden unless `range == 'custom'`
- No submit button required if you're planning to auto-submit on change (Step 5 below), but include one anyway as a no-JS fallback

---

## 5. `static/js/main.js` — Small enhancement layer

- On `<select name="range">` change: toggle visibility of the custom date inputs (show only if value is `custom`)
- On the same change event (and optionally on date input change too): auto-submit the form, so filtering feels instant without a separate button click
- This is progressive enhancement — the form already works via plain `GET` + submit button without this JS, per the spec's "works without JavaScript" requirement

---

## 6. `static/css/style.css` — Style the new form

- Add styles for the filter form/select/date inputs using existing CSS variables only
- Reuse spacing/color patterns already established elsewhere in the file rather than introducing new hardcoded values

---

## Suggested build order (recap)

1. `resolve_date_range()` alone → test in isolation
2. Extend the 3 helpers → test via direct calls
3. Wire `app.py` → test via URL query params, no template changes yet
4. Update `profile.html` → test manually clicking through presets in browser
5. Add JS auto-submit/toggle → test UX feels smooth
6. Style it

---

## Final check against Definition of Done

Before calling it finished, walk the spec's Definition of Done checklist literally line by line against a running app — especially the two easy-to-miss ones:

- **Reload preserves the filter** — re-population from `app.py` → template must round-trip correctly.
- **Malformed custom date doesn't crash** — test this explicitly, don't just assume it works.