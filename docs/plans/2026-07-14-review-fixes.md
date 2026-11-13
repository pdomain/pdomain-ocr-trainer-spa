---
Status: partial
Owner: CT
Created: 2026-07-14
Last verified: 2026-11-07
Kind: plan
---

# Confirmed bug fixes — pdomain-ocr-trainer-spa (2026-07-14)

## Agent Index

- **Kind:** plan
- **Status:** partial
- **Read when:** deciding the remaining run-form device mapping or tracing
  completed suite mount, settings navigation, and shortcut fixes.
- **Search terms:** app_id unknown, suite mount, InstalledApp, TrainerRail,
  useTrainerShortcuts, driver contract, pin deferral.

## Goal

Resolve the remaining run-form device mapping. The suite mount, dead settings
link, shortcut registrations, and driver-contract corrections are implemented.
The dependency block is resolved. No auth is added; this app is no-auth by v1
design.

## Architecture

`bootstrap.py` builds the suite app and migrates old preferences before mounting
routes under the real app ID. The rail omits `/settings`, and the shortcut hook
registers only `?`. `tests/e2e/test_driver_contract.py` parses spec 13's tables.
The original implementation used the pattern from
`pdomain-prep-for-pgdp/src/pdomain_prep_for_pgdp/bootstrap.py`.

## Tech Stack

Current dependency floors are Python 3.13, FastAPI 0.141, and
`pdomain-ops>=0.11.2`. The frontend uses React 19, TypeScript, and Vitest.
Documentation uses docgraph. The old 0.11.1 FastAPI constraint no longer blocks
this repository; `pyproject.toml` records that 0.11.2 loosened the pins.

## Global Constraints

- No auth added (v1 no-auth design). No new SettingsPage/route. Do not wire
  NewRunPage to the device preference until string-to-index and CPU semantics
  are decided. The former dependency pin restriction is obsolete.
- TDD: failing test first for code tasks. `AI=1 just ci` before each commit. Never bare pytest. Worktree isolation. Conventional commits. Nothing pushed.
- After spec edits: docgraph reindex + check same-turn.

## Verified outcomes

Checked on 2026-11-07 by reading the following source and tests. This check
does not claim a fresh test run.

- Task 1 is implemented in `src/pdomain_ocr_trainer_spa/bootstrap.py` and
  `src/pdomain_ocr_trainer_spa/pdomain-suite.json`.
  `tests/unit/test_bootstrap_suite_app.py` covers the app ID, preference
  migration, and device persistence. Existing real-app preferences win; in
  that case, the old `unknown` value is retained.
- Tasks 2 and 3 are implemented in `frontend/src/shell/TrainerRail.tsx` and
  `frontend/src/shell/useTrainerShortcuts.ts`. Their colocated tests cover
  the missing settings link and the single `?` binding.
- Task 4 remains unresolved. `frontend/src/pages/NewRunPage.tsx` sends no
  device. `CreateRunRequest.device` in
  `src/pdomain_ocr_trainer_spa/api/runs.py` is `int | None`, while suite
  preferences store a string. Track the decision in
  [the intent map](../context/intent-map.md#needs-owner-decision).
- Task 5 is implemented in `specs/03-frontend.md`,
  `specs/13-driver-contract.md`, and `tests/e2e/test_driver_contract.py`.
  Settings are dock-only, `/publish` is stable, and `_DEFERRED_URLS` is empty.
  Spec 03 still describes wider projected routes; its drift note remains.
- Task 6 is superseded by the dependency floors in `pyproject.toml`.

Tasks 1–6 and Sequencing below preserve the July implementation instructions.
They describe the original defects and proposed work, not the current task
list. Do not repeat the completed fixes or restore the old dependency floor.

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
