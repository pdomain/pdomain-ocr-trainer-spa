"""Browser smoke tests verifying AppShell migration — runs against the real server.

Requires: make e2e-browser (frontend must be built + server must be running on
--base-url, defaulting to http://localhost:8081).

These tests are marked ``e2e`` so they are excluded from ``make test`` (which
runs pure-Python unit tests only) and only execute under ``make e2e-browser``.
"""

import pytest
from playwright.sync_api import Page, expect

TESTIDS_SPEC_13 = [
    "header-bar",
    "header-app-version",
    "header-help-button",
    "header-jobs-badge",
    "sidebar-nav",
    "sidebar-nav-profiles",
    "sidebar-nav-runs",
    "sidebar-nav-models",
]

APPSHELL_TESTIDS = [
    "app-shell",
    "app-shell-header",
    "app-shell-rail",
    "app-shell-main",
]


@pytest.mark.e2e
@pytest.mark.parametrize("testid", TESTIDS_SPEC_13 + APPSHELL_TESTIDS)
def test_spec13_testids_present(page: Page, base_url: str, testid: str) -> None:
    """All spec-13 chrome testids and AppShell shell testids are visible after shell
    migration."""
    page.goto(base_url)
    expect(page.locator(f'[data-testid="{testid}"]')).to_be_visible(timeout=8000)


@pytest.mark.e2e
def test_app_loads_no_console_error(page: Page, base_url: str) -> None:
    """App loads with no console errors (catches missing CSS/JS bundle)."""
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(base_url)
    page.locator('[data-testid="app-shell"]').wait_for(timeout=8000)
    assert not errors, f"Console errors: {errors}"


@pytest.mark.e2e
def test_profiles_route_renders(page: Page, base_url: str) -> None:
    """GET / redirects to /profiles; profiles page root testid is visible."""
    page.goto(base_url)
    expect(page.locator('[data-testid="profiles-page"]')).to_be_visible(timeout=8000)


@pytest.mark.e2e
def test_direct_subroute_renders(page: Page, base_url: str) -> None:
    """Direct navigation to /runs renders the RunListPage, not a 404."""
    page.goto(f"{base_url}/runs")
    expect(page.locator('[data-testid="run-list-page"]')).to_be_visible(timeout=8000)


@pytest.mark.e2e
def test_compute_settings_panel_opens(page: Page, base_url: str) -> None:
    """Clicking the settings gear opens the utility dock; Compute tab is present."""
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(base_url)
    page.locator('[data-testid="app-shell"]').wait_for(timeout=8000)
    # SettingsSlot renders a button with aria-label containing "Settings"
    # Use JS click to bypass stability check — the button may be in a layout that
    # Playwright considers "animating" (CSS transform / sticky positioning).
    settings_btn = page.locator('[data-testid="settings-slot-trigger"]')
    settings_btn.wait_for(timeout=4000)
    page.evaluate("el => el.click()", settings_btn.element_handle())
    expect(page.get_by_role("tab", name="Compute")).to_be_visible(timeout=4000)
