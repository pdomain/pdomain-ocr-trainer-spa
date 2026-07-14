---
Status: draft
Owner: CT
Created: 2026-07-14
Last verified: 2026-07-14
Kind: plan
---

# Confirmed bug fixes — pdomain-ocr-trainer-spa (2026-07-14)

## Agent Index

- **Kind:** plan
- **Status:** draft
- **Read when:** fixing the app_id="unknown" suite mount, dead /settings nav,
  dead chord shortcuts, or stale specs 03/13.
- **Search terms:** app_id unknown, suite mount, InstalledApp, TrainerRail,
  useTrainerShortcuts, driver contract, pin deferral.

## Goal

Fix four confirmed bugs; file issues for feature-scope gaps; defer the blocked pin bump. No auth is added (this app is no-auth by v1 design).

## Architecture

Port the proven `_build_suite_app()` + `_migrate_unknown_app_prefs()` pattern from the now-merged `pdomain-prep-for-pgdp/src/pdomain_prep_for_pgdp/bootstrap.py`. Frontend fixes are deletions in `frontend/src/shell/`. Docs + e2e updated together because `tests/e2e/test_driver_contract.py` parses spec 13's tables.

## Tech Stack

Python 3.13, FastAPI 0.139.0, `pdomain-ops==0.11.0` (pin stays — 0.11.1 hard-pins fastapi<0.137, incompatible; see ocr-container-meta#399), React 19 + TS, Vitest, docgraph.

## Global Constraints

- No auth added (v1 no-auth design). No new SettingsPage/route (that's a feature). No NewRunPage device wiring (feature → issue). No pin bump (blocked → #399).
- TDD: failing test first for code tasks. `make ci AI=1` before each commit. Never bare pytest. Worktree isolation. Conventional commits. Nothing pushed.
- After spec edits: docgraph reindex + check same-turn.

## Task 1 — Fix app_id="unknown" suite mount (D-T21)

`bootstrap.py:126-128` calls `mount_routes(app)` bare → device/prefs/healthz keyed on `"unknown"`. No `pdomain-suite.json` exists — create `src/pdomain_ocr_trainer_spa/pdomain-suite.json` (`app_id:"pdomain-ocr-trainer-spa"`, display_name "OCR Trainer", package, default_port 8081, icon). Add `_build_suite_app()` (json + sys.executable + importlib.metadata.version) and `_migrate_unknown_app_prefs()` (clear compute_device from apps["unknown"], copy to real app_id if empty — PrefsAdapter has no delete), ported from prep-for-pgdp. `mount_routes(app, SuiteAdapters.local(), suite_app=_build_suite_app())`, preserving the existing best-effort try/except. **Verify hatchling packages the new json** (VCS-tracked; the test proves resources.files finds it). Test first: `tests/unit/test_bootstrap_suite_app.py` — /healthz reports real app_id, device PUT persists under it, migration copies+clears, doesn't clobber existing. Commit: `fix: mount suite routes under real app_id, not "unknown"`.

## Task 2 — Remove dead /settings sidebar link

`frontend/src/shell/TrainerRail.tsx:10` links to `/settings` but no route/page exists (settings live in the dock via `trainerSettingsPanels.ts`). Delete the `settings` NAV_SECTIONS entry. Update `TrainerRail.test.tsx` (drop "settings" from the parametrized sections; add a negative assertion). Do NOT build a SettingsPage. Commit: `fix: remove dead /settings nav link`.

## Task 3 — Remove dead chord shortcuts + false comment

`frontend/src/shell/useTrainerShortcuts.ts:15-18` registers `g p/g r/g m/g e` chords with `noop` and a false "wired via useNavigate" comment; the installed pdomain-ui `useShortcuts` splits only on `+` and matches a single `KeyboardEvent.key`, so 2-key chords can never fire. Delete the four chord entries, keep `"?"` (handled by the ShortcutsProvider itself), rewrite the comment to state the real limitation. Update `useTrainerShortcuts.test.ts`. Commit: `fix: remove unfireable chord shortcuts`. (A pdomain-ui chord-support issue is filed separately.)

## Task 4 — File device-wiring issue (NO CODE)

Suite panel persists a device STRING; `CreateRunRequest.device` (`api/runs.py:56`) is a CUDA INDEX (int); `NewRunPage.tsx` never sets it. Wiring needs a string→index + CPU-semantics mapping decision = feature. File an issue (prerequisite: Task 1). No code.

## Task 5 — Correct stale specs 03/13 + stop under-testing /publish

`specs/13-driver-contract.md:49` documents `/settings` as a stable page (doesn't exist); `specs/03-frontend.md:88,133` list SettingsPage.tsx + route (don't exist); `tests/e2e/test_driver_contract.py:82` waives `/publish` and `/settings` as "not built" but `/publish` IS built. Remove the `/settings` spec rows, note settings are dock-only, flag the wider 03 route-table drift for follow-up, and set `_DEFERRED_URLS = set()` (both waivers stale — the guard at ~line 364 requires deferred URLs to appear in the spec, so `/settings` must leave both). Reindex docgraph + check. Commit: `docs: fix stale /settings + /publish waivers`.

## Task 6 — Record pin deferral (comment only)

`pyproject.toml:17` — add a comment above `pdomain-ops>=0.11.0` explaining the pin stays put (0.11.1 hard-pins fastapi<0.137 vs our 0.139; ocr-container-meta#399). No version change. Commit: `docs: record pdomain-ops pin deferral (#399)`.

## Sequencing

Task 1 (bootstrap + json), Tasks 2+3 (frontend shell), Task 5 (specs + e2e), Task 6 (pyproject) touch disjoint files — parallelizable. Task 4 is an issue. `make ci AI=1` after each commit.
