// BannerStack — renders the active environment banners (spec 11 §3, §7).
//
// Banners are top-of-page strips fetched from `GET /api/banners`.
// Dismissal is per-tab, persisted in sessionStorage (spec 11 §3); the
// backend keeps no banner state. The list refreshes every 60 s while any
// banner is shown and on page-visibility-change.

import { useCallback, useEffect, useState } from "react";
import type { Banner } from "../api/banners";
import { fetchBanners } from "../api/banners";

const DISMISS_STORAGE_KEY = "pd-trainer-dismissed-banners";
const REFRESH_INTERVAL_MS = 60_000;

function loadDismissed(): Set<string> {
  try {
    const raw = sessionStorage.getItem(DISMISS_STORAGE_KEY);
    if (raw === null) return new Set();
    return new Set(JSON.parse(raw) as string[]);
  } catch {
    return new Set();
  }
}

function saveDismissed(ids: Set<string>): void {
  try {
    sessionStorage.setItem(DISMISS_STORAGE_KEY, JSON.stringify([...ids]));
  } catch {
    /* sessionStorage unavailable — dismissal is best-effort */
  }
}

/** ARIA `aria-live` politeness for a banner severity (spec 11 §7). */
function ariaLiveFor(severity: Banner["severity"]): "polite" | "assertive" {
  return severity === "error" ? "assertive" : "polite";
}

export interface BannerStackProps {
  /** Override the banner fetcher (tests inject a fake). */
  fetcher?: () => Promise<{ banners: Banner[] }>;
}

/** Top-of-page stack of active environment banners. */
export function BannerStack({
  fetcher = fetchBanners,
}: BannerStackProps): JSX.Element | null {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(() =>
    loadDismissed(),
  );

  const refresh = useCallback(() => {
    // Banners are advisory — a failed fetch must never crash the shell.
    fetcher()
      .then((res) => setBanners(res?.banners ?? []))
      .catch(() => setBanners([]));
  }, [fetcher]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const visible = banners.filter((b) => !dismissed.has(b.id));

  // Refresh every 60 s while any banner is shown, plus on visibility change.
  useEffect(() => {
    const onVisible = (): void => {
      if (document.visibilityState === "visible") refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    let timer: ReturnType<typeof setInterval> | undefined;
    if (visible.length > 0) {
      timer = setInterval(refresh, REFRESH_INTERVAL_MS);
    }
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      if (timer !== undefined) clearInterval(timer);
    };
  }, [refresh, visible.length]);

  const dismiss = useCallback((id: string) => {
    setDismissed((prev) => {
      const next = new Set(prev);
      next.add(id);
      saveDismissed(next);
      return next;
    });
  }, []);

  if (visible.length === 0) return null;

  return (
    <div data-testid="banner-stack">
      {visible.map((banner) => (
        <div
          key={banner.id}
          data-testid={`banner-${banner.id}`}
          role="region"
          aria-label={banner.title}
          aria-live={ariaLiveFor(banner.severity)}
          data-severity={banner.severity}
        >
          <strong>{banner.title}</strong>
          <span> {banner.description}</span>
          {banner.action != null && (
            <a
              data-testid={`banner-${banner.id}-action`}
              href={banner.action.href}
            >
              {banner.action.label}
            </a>
          )}
          {banner.dismissible && (
            <button
              type="button"
              data-testid={`banner-${banner.id}-dismiss`}
              aria-label={`Dismiss ${banner.title}`}
              onClick={() => dismiss(banner.id)}
            >
              ×
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
