---
status: active
created: 2026-06-10
repo: pdomain/pdomain-ocr-trainer-spa
tracks: "Track F — re-enable downgraded ESLint rules"
gh-issue: 24
---

# Re-enable Downgraded ESLint Rules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.
> **SEQUENCING NOTE:** This track executes **AFTER** the pdomain-ui adoption
> plan (`2026-06-10-pdomain-ui-adoption-and-compute-panel.md`) merges to main.
> That plan deletes `AppChrome.tsx` and `AppHeader.tsx`, rewrites `App.tsx` and
> several test files, and adds new shell files — all of which would collide with
> a mass rule-fix pass on the old code. The violation counts below were measured
> on 2026-06-10 against the pre-migration codebase. **Re-measure all counts
> against the post-migration tree before starting each task**, as some
> violations will be resolved or introduced by the migration.

**Goal:** Promote all downgraded ESLint rules from `warn` to `error` in
`frontend/eslint.config.js` so that `make frontend-lint` enforces them as CI
failures, bringing the frontend linter from partially-enforced to fully strict.

**Architecture:** Fix all existing violations in a set of focused commits (one
rule group per commit), then flip each rule to `error` and verify `make
frontend-lint` exits 0. Final state: `--max-warnings 0` is set in the lint
invocation (or each rule is `error` so any violation breaks CI). No new
abstractions needed — pure code fixes.

**Tech Stack:** ESLint flat config (`eslint.config.js`), `typescript-eslint`
strict + stylistic configs, `eslint-plugin-jsx-a11y`, React 18.

---

## Violation inventory (measured 2026-06-10, pre-migration)

> Re-measured 2026-06-10 post-merges (pdomain-ui AppShell + labeler-import +
> M12). Current tree: **63 warnings (0 errors)**. Deltas from pre-migration:
> Group 1: 16→22 (+ActiveJob shell files, +JSX); Group 2: 5→9 (+a11y);
> Group 3: 0→1; Group 6: 4→5; Group 7: 1→3; Group 10: 0→5 (new void);
> Group 11: 0→5 (new misused-spread); Group 13: 1→2; Group 14: 0→1.

Run to reproduce:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1
```

Total: **63 warnings (0 errors)** across the following rule groups:

### Group 1: `@typescript-eslint/no-deprecated` — JSX namespace

Rule currently: `warn`. Target: `error`.

Fix: replace `JSX.Element` return type with `React.JSX.Element` (or remove
explicit return type — TypeScript infers it from JSX).

| File | Line | Violation |
| --- | --- | --- |
| `src/components/LossChart.tsx` | 21 | `JSX` is deprecated |
| `src/components/ProfileEditDialog.tsx` | 37 | `JSX` is deprecated |
| `src/components/PublishDialog.tsx` | 51 | `JSX` is deprecated |
| `src/components/RunArgsEditor.tsx` | 82, 125 | `JSX` is deprecated |
| `src/pages/DatasetsPage.tsx` | 33 | `JSX` is deprecated |
| `src/pages/EvalFormPage.tsx` | 15 | `JSX` is deprecated |
| `src/pages/EvalResultPage.tsx` | 11 | `JSX` is deprecated |
| `src/pages/ModelDetailPage.tsx` | 15 | `JSX` is deprecated |
| `src/pages/ModelsPage.tsx` | 8 | `JSX` is deprecated |
| `src/pages/NewRunPage.tsx` | 18 | `JSX` is deprecated |
| `src/pages/ProfileDetailPage.tsx` | 30 | `JSX` is deprecated |
| `src/pages/ProfilesPage.tsx` | 14 | `JSX` is deprecated |
| `src/pages/PublishPage.tsx` | 16 | `JSX` is deprecated |
| `src/pages/RunDetailPage.tsx` | 17 | `JSX` is deprecated |
| `src/pages/RunListPage.tsx` | 29 | `JSX` is deprecated |
| `src/components/kanban/KanbanBoard.tsx` | 204 | `aria-grabbed` is deprecated |

Count: **16 violations** across 16 files (15 JSX namespace + 1 deprecated ARIA
attribute).

### Group 2: `jsx-a11y/*` rules

Rules currently: `warn` for `click-events-have-key-events`,
`no-noninteractive-element-interactions`, `no-noninteractive-tabindex`,
`no-redundant-roles`. Target: `error`.

All violations are in `src/components/kanban/KanbanBoard.tsx`:

| Line | Rule | Fix |
| --- | --- | --- |
| 174 | `no-redundant-roles` | remove `role="region"` from `<section>` |
| 190 | `no-redundant-roles` | remove `role="list"` from `<ul>` |
| 200 | `no-redundant-roles` | remove `role="listitem"` from `<li>` |
| 200 | `no-noninteractive-element-interactions` | add key handler |
| 203 | `no-noninteractive-tabindex` | move tabIndex to child |

Count: **5 violations** in 1 file.

### Group 3: `@typescript-eslint/no-unsafe-*` rules

Rules currently: `warn` for `no-unsafe-assignment`, `no-unsafe-member-access`,
`no-unsafe-argument`, `no-unsafe-call`, `no-unsafe-return`. Target: `error`.

No violations currently in the codebase — these rules fire on `any`-typed
values. The count was 0 at time of measurement. After pdomain-ui adoption (which
adds new shell files), re-measure before enabling. If the migration introduces
`any`-typed patterns, fix them first.

Count: **0 violations** (pre-migration). Re-measure after migration.

### Group 4: `@typescript-eslint/prefer-optional-chain`

Rule currently: `warn`. Target: `error`.

| File | Line | Current code | Fix |
| --- | --- | --- | --- |
| `src/components/kanban/KanbanBoard.tsx` | 118 | `x && x.y` | `x?.y` |
| `src/pages/RunDetailPage.tsx` | 63 | `x && x.y` | `x?.y` |

Count: **2 violations**.

### Group 5: `@typescript-eslint/no-unnecessary-type-assertion`

Rule currently: `warn`. Target: `error`.

| File | Lines | Fix |
| --- | --- | --- |
| `KanbanBoard.tsx` | 122, 123, 124, 145 | Remove unnecessary `as T` casts |
| `src/pages/DatasetsPage.tsx` | 78 | Remove unnecessary cast |

Count: **5 violations**.

### Group 6: `@typescript-eslint/no-base-to-string`

Rule currently: `warn`. Target: `error`.

| File | Line | Fix |
| --- | --- | --- |
| `RunArgsEditor.tsx` | 172 | object in template literal — use typed accessor |
| `useNotificationStream.ts` | 56 | unknown — cast via type guard or String() |
| `RunDetailPage.tsx` | 68 | cast payload fields to `string` first |

Count: **4 violations** (3 locations, 4 warning instances).

### Group 7: `@typescript-eslint/no-unnecessary-condition`

Rule currently: `warn`. Target: `error`.

| File | Line | Fix |
| --- | --- | --- |
| `errorMessages.ts` | 209 | Remove always-true/false condition |

Count: **1 violation**.

### Group 8: `@typescript-eslint/no-non-null-assertion`

Rule currently: `warn`. Target: `error`.

| File | Line | Fix |
| --- | --- | --- |
| `main.tsx` | 5 | `getElementById("root")!` — add null check or `?? throw` |

Count: **1 violation**.

### Group 9: `@typescript-eslint/no-dynamic-delete`

Rule currently: `warn`. Target: `error`.

| File | Line | Fix |
| --- | --- | --- |
| `datasetsStore.ts` | 108 | Cache-invalidation delete — document it |

Count: **1 violation** (intentional — document rather than rewrite).

### Group 10: `@typescript-eslint/no-invalid-void-type`

Rule currently: `warn`. Target: `error`.

No violations at time of measurement. Re-measure after migration.

Count: **0 violations** (pre-migration).

### Group 11: `@typescript-eslint/no-misused-spread`

Rule currently: `warn`. Target: `error`.

No violations at time of measurement. Re-measure after migration.

Count: **0 violations** (pre-migration).

### Group 12: `@typescript-eslint/no-unnecessary-type-conversion`

Rule currently: `warn`. Target: `error`.

No violations at time of measurement. Re-measure after migration.

Count: **0 violations** (pre-migration).

### Group 13: `react-refresh/only-export-components`

Rule currently: `warn`. Target: `error`.

| File | Line | Fix |
| --- | --- | --- |
| `RunArgsEditor.tsx` | 63 | Move exported constant to a sibling file |

Count: **1 violation**.

### Group 14: `@typescript-eslint/no-empty-function` + `@typescript-eslint/require-await`

Rules currently: `warn`. Target: `error`.

No violations at time of measurement (re-measure after migration).

Count: **0 violations** (pre-migration).

### Group 15: `@typescript-eslint/no-unused-vars` (warn, with ignore patterns)

Rule currently: `warn`. Already uses `argsIgnorePattern`, `varsIgnorePattern`,
`caughtErrorsIgnorePattern` for `^_`. No count violations recorded. This rule is
already near-error; ensure no violations remain after migration.

Count: **0 violations** (pre-migration).

---

## File structure

No new files created. Files modified per task below.

---

## Milestone T1 — Baseline re-measure + lint-deviations doc

### Task T1: Re-measure violations after pdomain-ui adoption merge

**Context:** Do this task first, before any fixes. The pdomain-ui adoption plan
will delete AppChrome, AppHeader, AppToaster, rewrite App.tsx and several pages.
Many JSX-namespace violations will disappear; new shell files may introduce new
ones.

**Files:**

+ Read: current `frontend/src/` tree
+ Modify: `docs/conventions/lint-deviations.md` (ensure it exists)

+ [ ] **Step 1: Confirm pdomain-ui adoption is merged**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git log --oneline -5
```

Expected: commits from the pdomain-ui adoption plan are in main.

+ [ ] **Step 2: Re-run lint and capture output**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | tee /tmp/eslint-baseline.txt
grep "warning\|error" /tmp/eslint-baseline.txt | wc -l
```

Expected: some number of warnings (likely fewer than 60 if migration deleted
files).

+ [ ] **Step 3: Ensure `docs/conventions/lint-deviations.md` exists**

```bash
DEVS=/workspaces/ocr-container/pdomain-ocr-trainer-spa/docs/conventions
ls "$DEVS/lint-deviations.md" 2>/dev/null || echo "MISSING"
```

If missing, create it:

```markdown
# Lint deviations

This file catalogues every `// eslint-disable` and `// eslint-disable-next-line`
annotation
in the frontend source, plus every `warn`-instead-of-`error` rule entry in
`eslint.config.js`.
Each entry records the rule, the file location, and the rationale for the
deviation.

## Active deviations

| Rule | File:line | Rationale |
|---|---|---|
| `@typescript-eslint/no-dynamic-delete` | `src/stores/datasetsStore.ts:108` |
Deliberate cache-key invalidation; key is always a known string from the store's
own type |
```

+ [ ] **Step 4: Commit the baseline doc**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add docs/conventions/lint-deviations.md
git commit -m "docs(lint): add lint-deviations catalogue (Track F baseline)"
```

---

## Milestone T2 — Group 1: JSX namespace + deprecated ARIA

### Task T2: Fix `@typescript-eslint/no-deprecated` violations

**Context:** Replace `JSX.Element` with `React.JSX.Element` in all component
return type annotations. The simplest fix in React 18.3+ is to either (a) use
`React.JSX.Element` explicitly, or (b) remove explicit return type annotations
entirely (TypeScript infers `React.JSX.Element` from JSX). This codebase uses
explicit return types as a convention — use option (a).

For `aria-grabbed` in `KanbanBoard.tsx`: remove the deprecated attribute
entirely; drag state is tracked via the component's existing CSS class logic,
not via `aria-grabbed`.

After the pdomain-ui adoption migration, `AppChrome.tsx` and `AppHeader.tsx`
will have been deleted. Re-check which files still have `JSX.Element` — the list
below is post-migration expected residual.

**Files:** All files listed in Group 1 above that still exist after migration.

+ [ ] **Step 1: Count remaining violations before fixing**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | grep "no-deprecated" | wc -l
```

Note the count. If 0 (all fixed by migration), skip to Task T3.

+ [ ] **Step 2: Fix JSX namespace in bulk (non-test source files)**

Run the safe sed-substitution:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
# Replace ): JSX.Element with ): React.JSX.Element in all non-test source files
grep -rn "): JSX\.Element" src/ --include="*.tsx" --include="*.ts" -l | \
  grep -v "\.test\." | while read f; do
  sed -i 's/): JSX\.Element/): React.JSX.Element/g' "$f"
  echo "patched: $f"
done
```

+ [ ] **Step 3: Verify React import is present in each patched file**

```bash
grep -rn "React.JSX.Element" frontend/src/ --include="*.tsx" -l | \
  while read f; do
  if ! grep -q "^import.*React" "$f" && \
    ! grep -q "from 'react'" "$f" && \
    ! grep -q 'from "react"' "$f"; then
    echo "MISSING REACT IMPORT: $f"
  fi
done
```

For any file listed as missing React import, add `import React from "react";`
(or `import * as React from "react";`) at the top.

+ [ ] **Step 4: Fix `aria-grabbed` in `KanbanBoard.tsx`**

In `frontend/src/components/kanban/KanbanBoard.tsx`, locate the element with
`aria-grabbed` (line ~204 pre-migration) and remove the `aria-grabbed`
attribute. The drag-grabbed state should be conveyed via `aria-selected` or CSS
alone per current WAI-ARIA 1.2 guidance.

Before:

```tsx
<li
  role="listitem"
  aria-grabbed={isDragging}
  tabIndex={0}
  ...
>
```

After:

```tsx
<li
  aria-selected={isDragging}
  tabIndex={0}
  ...
>
```

(Remove `role="listitem"` too — that fix is in Group 2 / Task T3.)

+ [ ] **Step 5: Run lint — verify Group 1 violations gone**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | grep "no-deprecated"
```

Expected: no output (0 violations).

+ [ ] **Step 6: Promote rule to `error`**

In `frontend/eslint.config.js`, change:

```js
"@typescript-eslint/no-deprecated": "warn",
```

to:

```js
"@typescript-eslint/no-deprecated": "error",
```

+ [ ] **Step 7: Run lint — verify 0 errors**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | grep "error"
```

Expected: no output (0 errors, 0 warnings from this rule).

+ [ ] **Step 8: Run full CI**

```bash
make ci 2>&1 | tail -10
```

Expected: green.

+ [ ] **Step 9: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/ frontend/eslint.config.js
git commit -m "fix(lint): replace JSX namespace with React.JSX.Element; remove \
  deprecated aria-grabbed; promote no-deprecated to error"
```

---

## Milestone T3 — Group 2: jsx-a11y accessibility rules

### Task T3: Fix jsx-a11y violations in `KanbanBoard.tsx`

**Context:** All 5 jsx-a11y violations are in the vendored KanbanBoard shim. The
fixes are:

1. Remove redundant `role` attributes from semantic HTML elements (`<section
   role="region">`, `<ul role="list">`, `<li role="listitem">`).
2. Refactor the draggable `<li>` to use a proper interactive pattern: either
   wrap the drag-handle in a `<button>` or add `onKeyDown` alongside `onClick`
   for the non-interactive element interaction.
3. Move `tabIndex` from the `<li>` to the focusable drag-handle `<button>`
   inside it.

Note: After the pdomain-ui adoption plan merges, the vendored KanbanBoard shim
may or may not still exist (the adoption plan retains it if pdomain-ui still has
not shipped a real KanbanBoard). Check its existence before this task.

**Files:**

+ Modify: `frontend/src/components/kanban/KanbanBoard.tsx`

+ [ ] **Step 1: Check the file still exists after migration**

```bash
ls \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/components/kanban/KanbanBoard.tsx
```

If the file was replaced by a pdomain-ui import during migration, skip this
task.

+ [ ] **Step 2: Count current jsx-a11y violations**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | grep "jsx-a11y"
```

Note the count.

+ [ ] **Step 3: Remove redundant role attributes**

In `frontend/src/components/kanban/KanbanBoard.tsx`, locate and remove:

+ `role="region"` from any `<section>` element (section already has implicit
  region role)
+ `role="list"` from any `<ul>` element
+ `role="listitem"` from any `<li>` element

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
grep -n 'role="region"\|role="list"\|role="listitem"' \
  src/components/kanban/KanbanBoard.tsx
```

Edit to remove those attributes while preserving the rest of the JSX. Example:

```tsx
// Before
<section role="region" data-testid={...}>
// After
<section data-testid={...}>

// Before
<ul role="list" style={...}>
// After
<ul style={...}>

// Before
<li role="listitem" tabIndex={0} onClick={...} onKeyDown={...}>
// After  — keep onKeyDown if it was absent; add it for the no-noninteractive
// fix
<li tabIndex={-1}>
  <button type="button" tabIndex={0} onClick={...} onKeyDown={...}>
    {chipContent}
  </button>
</li>
```

Note: Moving interaction to a `<button>` is the cleanest fix for both
`no-noninteractive-element-interactions` and `no-noninteractive-tabindex`. If
the drag-handle pattern requires the `<li>` itself to receive keyboard events,
add both `onClick` and `onKeyDown` handlers (for `Enter`/`Space`) to the `<li>`
and change it to `role="option"` inside a `listbox`, which is an interactive
role.

+ [ ] **Step 4: Run lint — verify jsx-a11y violations gone**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | grep "jsx-a11y"
```

Expected: no output.

+ [ ] **Step 5: Promote jsx-a11y rules to `error`**

In `frontend/eslint.config.js`, in the jsx-a11y config block, change the four
downgraded rules from `"warn"` to `"error"`:

```js
"jsx-a11y/click-events-have-key-events": "error",
"jsx-a11y/no-noninteractive-element-interactions": "error",
"jsx-a11y/no-noninteractive-tabindex": "error",
"jsx-a11y/no-redundant-roles": "error",
```

+ [ ] **Step 6: Run full CI**

```bash
make ci 2>&1 | tail -10
```

Expected: green.

+ [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/components/kanban/KanbanBoard.tsx frontend/eslint.config.js
git commit -m "fix(lint): fix jsx-a11y violations in KanbanBoard; promote a11y \
  rules to error"
```

---

## Milestone T4 — Groups 4–8: TypeScript safety rules

### Task T4a: Fix `prefer-optional-chain` (Group 4)

**Files:**

+ Modify: `frontend/src/components/kanban/KanbanBoard.tsx`
+ Modify: `frontend/src/pages/RunDetailPage.tsx`

+ [ ] **Step 1: Count violations**

```bash
make frontend-lint 2>&1 | grep "prefer-optional-chain" | wc -l
```

+ [ ] **Step 2: Fix in `KanbanBoard.tsx` (line ~118)**

Find the `x && x.y` pattern and replace with `x?.y`:

```bash
grep -n "prefer-optional-chain" <(cd \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa && make frontend-lint 2>&1)
```

Read the reported line, then edit: `someObj && someObj.method()` →
`someObj?.method()`.

+ [ ] **Step 3: Fix in `RunDetailPage.tsx` (line ~63)**

Same pattern — replace with optional chain.

+ [ ] **Step 4: Promote rule**

```js
"@typescript-eslint/prefer-optional-chain": "error",
```

+ [ ] **Step 5: Run lint, then CI**

```bash
make frontend-lint 2>&1 | grep "prefer-optional-chain" && make ci 2>&1 | tail -5
```

Expected: 0 violations, CI green.

+ [ ] **Step 6: Commit**

```bash
git add frontend/src/ frontend/eslint.config.js
git commit -m "fix(lint): use optional chain; promote prefer-optional-chain to \
  error"
```

---

### Task T4b: Fix `no-unnecessary-type-assertion` (Group 5)

**Files:**

+ Modify: `frontend/src/components/kanban/KanbanBoard.tsx`
+ Modify: `frontend/src/pages/DatasetsPage.tsx`

+ [ ] **Step 1: Count violations**

```bash
make frontend-lint 2>&1 | grep "no-unnecessary-type-assertion" | wc -l
```

+ [ ] **Step 2: Remove unnecessary casts**

For each reported location, read the file at the given line. If `x as T` where
`x` is already of type `T`, remove the cast:

```tsx
// Before
const result = (someValue as string);
// After
const result = someValue;
```

+ [ ] **Step 3: Promote rule**

```js
"@typescript-eslint/no-unnecessary-type-assertion": "error",
```

+ [ ] **Step 4: Run lint + CI**

```bash
make frontend-lint 2>&1 | grep "no-unnecessary-type-assertion" && \
  make ci 2>&1 | tail -5
```

+ [ ] **Step 5: Commit**

```bash
git add frontend/src/ frontend/eslint.config.js
git commit -m "fix(lint): remove unnecessary type assertions; promote rule to \
  error"
```

---

### Task T4c: Fix `no-base-to-string` (Group 6)

**Files:**

+ Modify: `frontend/src/components/RunArgsEditor.tsx`
+ Modify: `frontend/src/hooks/useNotificationStream.ts`
+ Modify: `frontend/src/pages/RunDetailPage.tsx`

+ [ ] **Step 1: Fix `RunArgsEditor.tsx` line ~172**

```bash
SRC=/workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src
grep -n "current" "$SRC/components/RunArgsEditor.tsx" | head -10
```

Identify the template literal using `current` (an object). Likely a ref value
used as a string. Fix by accessing the typed string field: e.g. `current.value`
or `String(current.someField)`.

+ [ ] **Step 2: Fix `useNotificationStream.ts` lines ~56**

```bash
sed -n '50,65p' \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/hooks/useNotificationStream.ts
```

`cer` and `wer` are typed `unknown` from `event.payload`. Cast to number:

```ts
// Before
const metrics = cer !== undefined && wer !== undefined
  ? `CER ${String(cer)}, WER ${String(wer)}`
  : label;
// After — ensure cer/wer are narrowed to number first
const cerNum = typeof cer === "number" ? cer : undefined;
const werNum = typeof wer === "number" ? wer : undefined;
const metrics = cerNum !== undefined && werNum !== undefined
  ? `CER ${cerNum.toFixed(3)}, WER ${werNum.toFixed(3)}`
  : label;
```

+ [ ] **Step 3: Fix `RunDetailPage.tsx` line ~68**

```bash
sed -n '60,75p' \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/pages/RunDetailPage.tsx
```

`event.payload.line ?? event.payload.message ?? ""` — `payload` is `unknown` or
loosely typed. Narrow to string:

```ts
const payloadLine = typeof event.payload?.line === "string" ?
  event.payload.line : undefined;
const payloadMsg = typeof event.payload?.message === "string" ?
  event.payload.message : undefined;
const logLine = payloadLine ?? payloadMsg ?? "";
```

+ [ ] **Step 4: Promote rule**

```js
"@typescript-eslint/no-base-to-string": "error",
```

+ [ ] **Step 5: Run lint + CI**

```bash
make frontend-lint 2>&1 | grep "no-base-to-string" && make ci 2>&1 | tail -5
```

+ [ ] **Step 6: Commit**

```bash
git add frontend/src/ frontend/eslint.config.js
git commit -m "fix(lint): narrow unknown payload types before string \
  interpolation; promote no-base-to-string to error"
```

---

### Task T4d: Fix remaining single-violation rules (Groups 7–9 + 13)

**Files:**

+ Modify: `frontend/src/lib/errorMessages.ts` (Group 7)
+ Modify: `frontend/src/main.tsx` (Group 8)
+ Modify: `frontend/src/stores/datasetsStore.ts` +
  `docs/conventions/lint-deviations.md` (Group 9)
+ Modify: `frontend/src/components/RunArgsEditor.tsx` (Group 13)

+ [ ] **Step 1: Fix `no-unnecessary-condition` in `errorMessages.ts` (line
  ~209)**

```bash
sed -n '205,215p' \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/lib/errorMessages.ts
```

The rule fires when a condition is always-true or always-false based on types.
Remove the redundant check. If the type is genuinely narrowed already, delete
the dead branch:

```ts
// Before (if TypeScript knows x is always string here):
if (typeof x === "string" || x !== null) { ... }
// After:
{ ... }  // the condition was always true — remove it
```

Read the actual code at line 209 to apply the right fix.

+ [ ] **Step 2: Fix `no-non-null-assertion` in `main.tsx` (line ~5)**

```bash
head -10 /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/main.tsx
```

Replace:

```tsx
ReactDOM.createRoot(document.getElementById("root")!).render(...)
```

With:

```tsx
const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("Root element #root not found in DOM");
ReactDOM.createRoot(rootEl).render(...);
```

+ [ ] **Step 3: Handle `no-dynamic-delete` in `datasetsStore.ts` (line ~108) —
  document, do not rewrite**

```bash
sed -n '104,112p' \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/stores/datasetsStore.ts
```

This is an intentional cache-invalidation pattern. Add an inline disable comment
with rationale:

```ts
// eslint-disable-next-line @typescript-eslint/no-dynamic-delete --
// intentional: dynamic key from store's own typed key set
delete staged[pageKey];
```

Add to `docs/conventions/lint-deviations.md`:

```markdown
| `@typescript-eslint/no-dynamic-delete` | `src/stores/datasetsStore.ts:108` |
Deliberate cache-key invalidation; `pageKey` is always a string key from the
store's own `staged` record type |
```

+ [ ] **Step 4: Fix `react-refresh/only-export-components` in
  `RunArgsEditor.tsx` (line ~63)**

```bash
sed -n '58,70p' \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/components/RunArgsEditor.tsx
```

The rule fires because a non-component (a constant or function) is exported from
a component file. Move it to a sibling file:

```bash
# If the exported item is e.g. ARG_SCHEMA or similar:
# Create frontend/src/components/runArgsEditorSchema.ts
# Move the export there
# Update RunArgsEditor.tsx to import from the sibling
```

+ [ ] **Step 5: Promote all four rules**

In `frontend/eslint.config.js`:

```js
"@typescript-eslint/no-unnecessary-condition": "error",
"@typescript-eslint/no-non-null-assertion": "error",
"@typescript-eslint/no-dynamic-delete": "error",  // one suppression in
  lint-deviations.md
"react-refresh/only-export-components": ["error",
  { allowConstantExport: true }],
```

+ [ ] **Step 6: Run lint + CI**

```bash
RULES="no-unnecessary-condition|no-non-null-assertion"
RULES+="|no-dynamic-delete|only-export-components"
make frontend-lint 2>&1 | grep -E "$RULES" \
  && make ci 2>&1 | tail -5
```

Expected: 0 violations, CI green.

+ [ ] **Step 7: Commit**

```bash
git add frontend/src/ frontend/eslint.config.js \
  docs/conventions/lint-deviations.md
git commit -m "fix(lint): fix single-occurrence violations; document \
  intentional dynamic-delete; promote 4 rules to error"
```

---

## Milestone T5 — Zero-violation rules: re-measure and promote

### Task T5: Promote zero-violation rules

**Context:** Groups 3, 10, 11, 12, 14 had 0 violations in the pre-migration
tree. After migration and all preceding fixes, they should still have 0. Verify
and promote.

**Files:**

+ Modify: `frontend/eslint.config.js`

+ [ ] **Step 1: Re-measure zero-violation rules**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-lint 2>&1 | grep -E \
  "no-unsafe|no-invalid-void|no-misused-spread|no-unnecessary-type-conversion|no-empty-function|require-await"
```

Expected: no output (0 violations).

+ [ ] **Step 2: If any violations found, fix them first**

Read the violation lines, fix them the same way as tasks above (narrow types,
add explicit typing, remove empty functions).

+ [ ] **Step 3: Promote all zero-violation rules**

In `frontend/eslint.config.js`, change from `warn` to `error`:

```js
"@typescript-eslint/no-unsafe-assignment": "error",
"@typescript-eslint/no-unsafe-member-access": "error",
"@typescript-eslint/no-unsafe-argument": "error",
"@typescript-eslint/no-unsafe-call": "error",
"@typescript-eslint/no-unsafe-return": "error",
"@typescript-eslint/no-invalid-void-type": "error",
"@typescript-eslint/no-misused-spread": "error",
"@typescript-eslint/no-unnecessary-type-conversion": "error",
"@typescript-eslint/no-empty-function": "error",
"@typescript-eslint/require-await": "error",
```

+ [ ] **Step 4: Run full lint**

```bash
make frontend-lint 2>&1 | tail -5
```

Expected: `✖ 0 problems (0 errors, 0 warnings)`.

+ [ ] **Step 5: Run full CI**

```bash
make ci 2>&1 | tail -10
```

Expected: green.

+ [ ] **Step 6: Commit**

```bash
git add frontend/eslint.config.js
git commit -m "fix(lint): promote zero-violation rules from warn to error"
```

---

## Milestone T6 — Enable `--max-warnings 0`

### Task T6: Add `--max-warnings 0` to the lint invocation

**Context:** Even with all rules at `error`, the
`react-refresh/only-export-components` rule for `warn`-mode constants and
`@typescript-eslint/no-unused-vars` in `warn` mode can still accumulate warnings
silently. Setting `--max-warnings 0` means any warning breaks CI, completing the
enforcement.

**Files:**

+ Modify: `Makefile`
+ Modify: `frontend/eslint.config.js` (ensure
  `@typescript-eslint/no-unused-vars` is at `warn`, which is intentional for
  `^_` pattern — or promote to `error` if all violations are gone)

+ [ ] **Step 1: Check current lint invocation in Makefile**

```bash
grep -n "eslint\|frontend-lint" \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/Makefile | head -10
```

+ [ ] **Step 2: Verify zero warnings remain**

```bash
make frontend-lint 2>&1 | tail -3
```

Expected: `✖ 0 problems (0 errors, 0 warnings)`. If any warnings remain, fix
them before adding `--max-warnings 0`.

+ [ ] **Step 3: Add `--max-warnings 0` to the ESLint invocation**

In `Makefile`, find the `frontend-lint` target and add the flag:

```makefile
frontend-lint:
 cd frontend && pnpm exec eslint src --max-warnings 0
```

+ [ ] **Step 4: Run lint with the new flag**

```bash
make frontend-lint 2>&1 | tail -5
```

Expected: exit 0, `0 problems`.

+ [ ] **Step 5: Run full CI**

```bash
make ci 2>&1 | tail -10
```

Expected: green.

+ [ ] **Step 6: Close GH issue #24**

```bash
gh issue close 24 --repo pdomain/pdomain-ocr-trainer-spa \
  --comment "All rules promoted from warn to error; --max-warnings 0 enforced \
    in CI."
```

+ [ ] **Step 7: Final commit**

```bash
git add Makefile
git commit -m "fix(lint): enable --max-warnings 0; all ESLint rules fully \
  enforced (closes #24)"
```

---

## Open questions

1. **`@typescript-eslint/no-unused-vars` at `warn`:** This rule is intentionally
   kept at `warn` (not `error`) because `^_` prefix patterns mean false
   negatives are common in destructured params. After `--max-warnings 0` is
   enabled, any unused-var warning will break CI. Confirm CT is comfortable with
   this or add `@typescript-eslint/no-unused-vars: off` and rely solely on
   TypeScript's `noUnusedLocals`/`noUnusedParameters` for compile-time
   enforcement.

2. **`array-type` rule at `off`:** Currently `off` to allow mixing `T[]` and
   `Array<T>`. Enabling it as `error` would require a style decision. Deferred —
   not in scope for this plan.

3. **Post-migration violation count:** The 60-warning baseline was measured on
   2026-06-10 against the pre-migration tree. After the pdomain-ui adoption plan
   merges, re-measure before Task T2 — the actual count will be lower (deleted
   files) or potentially higher (new shell files). This is explicitly called out
   in the sequencing note at the top.
