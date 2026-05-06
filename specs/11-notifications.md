# 11 — Notifications

Toasts, busy overlays, and the persistent error banner. The SPA
surfaces three classes of feedback; each maps to a specific UI
primitive.

> Required reading: [`02-backend.md`](02-backend.md) §6 (errors),
> [`10-jobs-and-sse.md`](10-jobs-and-sse.md).

---

## 1. Three classes

| Class | Lifetime | UI primitive | Examples |
|---|---|---|---|
| **Toast** | Auto-dismiss 5s (info), 10s (success), persistent (error/warn) | `sonner` toast | "Run started", "Sidecar regenerated", "Save failed: …" |
| **Busy overlay** | While a synchronous action is in flight | `<BusyOverlay>` portal | Profile create, kanban move, copy-to-datasets |
| **Banner** | Until resolved or dismissed | top-of-page strip | "HF token missing", "Disk almost full", "App version mismatch" |

Toasts are ephemeral; the user accepts data loss on tab close.
Banners are session-persistent; banner state is not stored on the
backend in v1 (the SPA re-derives at fetch time). Busy overlays
never persist beyond the action.

---

## 2. Toast contract

```ts
type ToastKind = "info" | "success" | "warn" | "error";

interface Toast {
  id: string;                    // monotonic; sonner-generated unless we override
  kind: ToastKind;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };  // e.g. "Open run"
  durationMs?: number;           // default per kind, 0 = persistent
}
```

Conventions:

- **Title under 50 chars.** Description carries the long form.
- Errors always get an explicit description. Never `kind="error"`
  without one.
- One actionable toast per user gesture. If a backend mutation
  fires three concurrent invalidations, do not toast each; toast
  on the gesture.
- Action buttons trigger client-side navigation only — never
  another mutation.

### 2.1 Mapping `ErrorEnvelope` → toast

Every `ErrorEnvelope.code` (see [`02-backend.md`](02-backend.md) §6)
maps in the frontend `lib/errorMessages.ts`:

```ts
export const errorMessages: Record<string, (env: ErrorEnvelope) => Toast> = {
  "training.cuda_oom": (e) => ({
    kind: "error",
    title: "Out of GPU memory",
    description: "The trainer ran out of CUDA memory. Try reducing batch size.",
    action: { label: "Clone run with smaller batch", onClick: ... },
  }),
  "publish.license_missing": (e) => ({
    kind: "error",
    title: "Missing license",
    description: `${e.details?.length ?? 0} rows have no license. Set a per-row license before publishing.`,
  }),
  // ...
};
```

Codes without entries fall back to `{kind: "error", title:
errorEnvelope.message, description: errorEnvelope.code}`.

A code-to-message smoke test asserts that **every** code in
`api/types.ts` (string-literal union of error codes generated from
the backend) has an entry — drift fails CI.

---

## 3. Banners

```ts
interface Banner {
  id: string;                    // stable per cause: "hf-token-missing", "disk-low", "app-version-mismatch"
  severity: "info" | "warn" | "error";
  title: string;
  description: string;
  action?: { label: string; href: string };
  dismissible: boolean;
}
```

The SPA queries `GET /api/banners` on app load; the backend
synthesises this list from environment checks:

- `hf-token-missing` — `Settings.hf_token_path` doesn't exist on
  disk and `enable_hf_publish` is true.
- `disk-low` — `<shared-models-dir>` is on a partition with < 5%
  free.
- `app-version-mismatch` — frontend bundle's `__APP_ENV__.version`
  doesn't match `_version.__version__`. Dismiss reloads.

```python
class Banner(BaseModel):
    id: str
    severity: Literal["info", "warn", "error"]
    title: str
    description: str
    action: BannerAction | None = None
    dismissible: bool = True
```

Dismissal is **per-tab** in v1, kept in `sessionStorage`. No
backend state ([Q22](../OPEN_QUESTIONS.md): persist dismissals
per-browser?).

Banner refresh: re-query every 60 s while any banner is shown,
otherwise on page-visibility-change.

---

## 4. Busy overlay

Used when a mutation is short (< 2 s) and synchronous and the user
shouldn't be allowed to act in the same context until it lands.

- Triggered by react-query mutation `isPending` flag.
- Renders a translucent overlay over the relevant region (kanban,
  form, dialog) — **not** a full-screen blocker.
- Has a 200 ms onset delay so fast mutations don't flash an
  overlay.
- Empty content; no spinner text. Spinner only.

```tsx
<BusyOverlay show={mutation.isPending} delay={200} />
```

Long-running operations never use a BusyOverlay; they create a
`Job` and bounce to `/runs/{run_id}` or surface progress in the
JobsBadge.

---

## 5. SSE-driven notifications

Job-state transitions emit toasts:

| Job event | Toast |
|---|---|
| `complete` (training) | `success`: "Training finished — `<model_name>`" with `Open Model` action. |
| `complete` (eval) | `success`: "Eval done — CER `<n>`, WER `<n>`" with `Open Result` action. |
| `complete` (publish-dataset) | `success`: "Published `<repo>` @ `<rev>`" with `Open on HF` action. |
| `failed` | `error`: title from `code`, description from `message`. Persistent until dismissed. |
| `cancelled` | `info`: "Run cancelled." Quiet 5 s auto-dismiss. |

Toasts fire from `useNotificationStream`, a top-level hook
mounted in `App.tsx` that subscribes to all active job IDs (from
`/api/jobs/active-count` plus the run-detail page's per-run
subscription). Subscription deduplicates: a toast for a given
`(job_id, type)` pair fires once per session.

---

## 6. Sonner setup

```tsx
// App.tsx
<Toaster
  position="top-right"
  duration={5000}
  closeButton
  expand={false}
  richColors                        // success=green, error=red, warn=amber
  theme="system"
/>
```

`<Toaster />` is mounted once at the App root.

Custom toast types are created via `toast.custom(...)` so we can
render an action button without sonner's default linking.

---

## 7. Accessibility

- Toasts use ARIA `role="status"` (info/success) or `role="alert"`
  (warn/error). Sonner does this by default; assert it in a unit
  test.
- Banners use `role="region"` with `aria-live="polite"` for warn
  and `aria-live="assertive"` for error.
- Busy overlays use `aria-busy="true"` on the parent region.

---

## 8. Acceptance behaviour

1. POST a kanban move that fails with `409 profile.has_data`. A
   single error toast appears; the kanban state rolls back.
2. Start a training run. Toast: "Training started". Bounce to
   run page. After completion, second toast: "Training finished".
3. Without an HF token, navigate anywhere. The
   `hf-token-missing` banner is visible at the top. Click
   dismiss; the banner stays gone for this tab.
4. Force a CUDA-OOM during training (mocked via the
   `local_subprocess` runner). The `training.cuda_oom` toast
   appears with a "Clone run with smaller batch" action; clicking
   it opens a prefilled run form.

---

## 9. Citations

- Error envelope: [`02-backend.md`](02-backend.md) §6.
- Sonner usage pattern: `pd-ocr-labeler-spa/specs/11-notifications.md`.
- pgdp-prep banner pattern: `pd-prep-for-pgdp/frontend/src/components/Banners/`.
