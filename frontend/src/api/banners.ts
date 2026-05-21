// REST client for the /api/banners surface (spec 11-notifications §3).

export type BannerSeverity = "info" | "warn" | "error";

/** A call-to-action link rendered inside a banner. */
export interface BannerAction {
  label: string;
  href: string;
}

/** One environment banner — id is stable per cause (spec 11 §3). */
export interface Banner {
  id: string;
  severity: BannerSeverity;
  title: string;
  description: string;
  action?: BannerAction | null;
  dismissible: boolean;
}

export interface BannerListResponse {
  banners: Banner[];
}

/** Fetch the active environment banners synthesised by the backend. */
export async function fetchBanners(): Promise<BannerListResponse> {
  const resp = await fetch("/api/banners");
  if (!resp.ok) {
    // Banners are advisory — a failed fetch must never crash the shell.
    return { banners: [] };
  }
  return (await resp.json()) as BannerListResponse;
}
