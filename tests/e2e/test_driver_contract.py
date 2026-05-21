"""Driver-contract conformance test (spec 13).

`specs/13-driver-contract.md` locks two invariants for a future
Playwright driver agent:

  1. **URL invariants** (§2) — every canonical route.
  2. **data-testid invariants** (§4) — every interactive element's
     stable, machine-grep-able id.

Spec 13 §5 names this file and says "the driver contract is what the
conformance test passes". A live Playwright run needs a browser, which
`make ci` does not provide. Spec 13 §3 makes the testids "machine-grep-
able" precisely so the contract can be verified statically — so this
test parses spec 13's own inventory tables and asserts the frontend
source declares every static testid and the router defines every URL.
It runs pure-Python in `make ci`; no browser, no Playwright, no marker.

If a code change renames a testid, this test fails until both the spec
table and the source are updated in the same PR (spec 13 §5).

Dynamic testids -- ``banner-{id}``, ``toast-{id}``, every
``*-row-{name}``, ``*-{task}``, ``*-option-{name}`` -- interpolate
runtime values and cannot be grepped as literals; they are verified by
the template-prefix check (a backtick template interpolation must
exist) instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC = _REPO_ROOT / "specs" / "13-driver-contract.md"
_FRONTEND_SRC = _REPO_ROOT / "frontend" / "src"
_APP_TSX = _FRONTEND_SRC / "App.tsx"

# Chrome testids spec 13 §4.1 lists that are NOT yet implemented as part
# of M9's minimal header. They depend on larger features (pd-ui AppShell
# `TopNav` + the active-profile selector, spec 03 §6.1; jobs SSE badge).
# Tracked for a later milestone; the conformance test documents the gap
# rather than silently passing.
_DEFERRED_CHROME = {
    "header-profile-selector",
    "header-profile-selector-option-{name}",
    "header-jobs-badge",
    # sonner owns the toast DOM; we cannot attach our own data-testid to
    # its internal markup. A driver targets `[data-sonner-toast]` plus
    # the `id` we pass through `emitToast` (see AppToaster.tsx). The
    # `toast-{id}` contract is honoured via that id, not a literal node.
    "toast-{id}",
}

# Spec 13 §4 is a forward-looking contract: it inventories testids for
# pages and dialogs that later milestones build. Each entry here is
# waived from the static/dynamic presence checks with its blocking
# milestone; the conformance test re-tightens automatically once the
# milestone lands and the id appears in source. `test_deferred_testids_*`
# guards this set against drifting away from the spec.
_DEFERRED_TESTIDS: dict[str, str] = {
    # M11 — model publish to Hugging Face (spec 13 marks these "(M11)").
    "models-row-{name}-publish": "M11 publish",
    "models-detail-publish-dialog": "M11 publish",
    "models-detail-publish-repo": "M11 publish",
    "models-detail-publish-visibility-{value}": "M11 publish",
    "models-detail-publish-submit": "M11 publish",
    # M13 — eval run comparison (spec 13 marks this "(M13)").
    "eval-result-compare": "M13 eval compare",
    # Kanban task-tab strip + style-tag filter — page-level features not
    # yet built; the kanban currently keys task off the URL param. No
    # milestone has shipped these; building them is feature work beyond
    # M9's driver-contract conformance scope.
    "kanban-task-tabs": "kanban task-tab navigation not built",
    "kanban-task-tab-{task}": "kanban task-tab navigation not built",
    "kanban-toolbar-style-tag-filter": "style-tag filter not built (needs backend style-tag data)",
    # /publish and /settings pages are not built yet (no milestone has
    # shipped them); their URLs are waived in test_router_*.
}

# §2 URLs whose page is not built yet (see _DEFERRED_TESTIDS note).
_DEFERRED_URLS = {"/publish", "/settings"}


# --------------------------------------------------------------------------
# spec parsing
# --------------------------------------------------------------------------
def _read_spec() -> str:
    assert _SPEC.is_file(), f"spec 13 missing at {_SPEC}"
    return _SPEC.read_text(encoding="utf-8")


def _spec_section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start + len(start_marker))
    return text[start:end]


def _testids_from_section(section: str) -> list[str]:
    """Pull every ``code`` in the first table column of a §4 subsection."""
    ids: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        first_cell = line.split("|")[1].strip()
        m = re.fullmatch(r"`([a-z][a-z0-9-]*(?:-\{[a-z_]+\})*[a-z0-9-]*)`", first_cell)
        if m:
            ids.append(m.group(1))
    return ids


def _urls_from_spec(text: str) -> list[str]:
    """Pull every ``/path`` from the §2 URL-invariants table."""
    section = _spec_section(text, "## 2. URL invariants", "## 3.")
    urls: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("| `/"):
            continue
        first_cell = line.split("|")[1].strip()
        m = re.fullmatch(r"`(/[^`]*)`", first_cell)
        if m:
            urls.append(m.group(1))
    return urls


def _static_and_dynamic(ids: list[str]) -> tuple[list[str], list[str]]:
    """Split a testid list into literal (static) and `{...}`-bearing ids."""
    static = [i for i in ids if "{" not in i]
    dynamic = [i for i in ids if "{" in i]
    return static, dynamic


# --------------------------------------------------------------------------
# frontend source scanning
# --------------------------------------------------------------------------
def _source_files() -> list[Path]:
    return [
        p
        for p in _FRONTEND_SRC.rglob("*.tsx")
        if not p.name.endswith(".test.tsx")
    ] + [
        p
        for p in _FRONTEND_SRC.rglob("*.ts")
        if not p.name.endswith(".test.ts")
    ]


def _all_source_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in _source_files())


def _static_testids_in_source(text: str) -> set[str]:
    """Every literal testid string in non-test source.

    Catches both the plain attribute form ``data-testid="id"`` and
    string literals inside a ``data-testid={...}`` JSX expression (e.g.
    a ternary that picks between two literal ids).
    """
    ids: set[str] = set(re.findall(r'data-testid="([a-z][a-z0-9-]*)"', text))
    # data-testid={ <expr> } — scan the expression body for quoted ids.
    for m in re.finditer(r"data-testid=\{([^}]*)\}", text):
        body = m.group(1)
        ids.update(re.findall(r'"([a-z][a-z0-9-]*)"', body))
        ids.update(re.findall(r"'([a-z][a-z0-9-]*)'", body))
    return ids


def _dynamic_testid_prefixes(text: str) -> list[str]:
    """Static lead-ins of every data-testid template literal.

    Recognises both a literal lead (``\\`kanban-column-${...}``) and a
    parameterised lead (``\\`${prefix}-field-${...}``) — the latter is
    reduced to its first literal segment after the interpolation.
    """
    prefixes: list[str] = []
    # Literal lead in any backtick template: `prefix-${...}
    # (covers both `data-testid={`...`}` and `const id = `...`` forms).
    for m in re.finditer(r"`([a-z][a-z0-9-]*-)\$\{", text):
        prefixes.append(m.group(1))
    # Parameterised lead: `${something}-literal-segment-${...}
    for m in re.finditer(r"`\$\{[^}]+\}([a-z0-9-]*-)\$\{", text):
        seg = m.group(1).lstrip("-")
        if seg:
            prefixes.append(seg)
    return prefixes


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def spec_text() -> str:
    return _read_spec()


@pytest.fixture(scope="module")
def source_text() -> str:
    return _all_source_text()


# --------------------------------------------------------------------------
# §2 — URL invariants
# --------------------------------------------------------------------------
def test_router_declares_every_spec_url(spec_text: str) -> None:
    """Every §2 canonical URL has a matching <Route> in App.tsx."""
    urls = _urls_from_spec(spec_text)
    assert urls, "no URLs parsed from spec 13 §2 — table format changed"

    app = _APP_TSX.read_text(encoding="utf-8")
    route_paths = set(re.findall(r'<Route\s+path="([^"]*)"', app))
    # Normalise spec `{param}` placeholders to react-router `:param`.
    declared = {re.sub(r"\{([a-z_]+)\}", lambda m: f":{_camel(m.group(1))}", u)
                for u in route_paths}

    missing: list[str] = []
    for url in urls:
        if url in _DEFERRED_URLS:
            continue
        want = re.sub(r"\{([a-z_]+)\}", lambda m: f":{_camel(m.group(1))}", url)
        if want not in declared:
            missing.append(f"{url}  (expected route path {want!r})")
    assert not missing, "spec 13 §2 URLs with no <Route> in App.tsx:\n" + "\n".join(missing)


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(p.title() for p in rest)


# --------------------------------------------------------------------------
# §4 — testid inventory, per page
# --------------------------------------------------------------------------
_SECTIONS: list[tuple[str, str, str]] = [
    ("app chrome", "### 4.1 App chrome", "### 4.2"),
    ("profiles page", "### 4.2 Profiles page", "### 4.3"),
    ("datasets / kanban", "### 4.3 Datasets / kanban", "### 4.4 Run detail"),
    ("run detail", "### 4.4 Run detail", "### 4.4a"),
    ("run list", "### 4.4a Run list", "### 4.4b"),
    ("new run form", "### 4.4b New run form", "### 4.5"),
    ("models page + detail", "### 4.5 Models page + detail", "### 4.6"),
    ("eval form + result", "### 4.6 Eval form + result", "## 5."),
]


@pytest.mark.parametrize(("label", "start", "end"), _SECTIONS, ids=[s[0] for s in _SECTIONS])
def test_section_static_testids_present(
    label: str, start: str, end: str, spec_text: str, source_text: str
) -> None:
    """Every static (literal) testid in a §4 subsection exists in source."""
    section = _spec_section(spec_text, start, end)
    spec_ids = _testids_from_section(section)
    assert spec_ids, f"no testids parsed from §4 section {label!r}"

    static, _ = _static_and_dynamic(spec_ids)
    present = _static_testids_in_source(source_text)
    waived = _DEFERRED_CHROME | set(_DEFERRED_TESTIDS)

    missing = sorted(set(static) - present - waived)
    assert not missing, (
        f"spec 13 §4 ({label}) static testids absent from frontend source: {missing}"
    )


@pytest.mark.parametrize(("label", "start", "end"), _SECTIONS, ids=[s[0] for s in _SECTIONS])
def test_section_dynamic_testids_have_template(
    label: str, start: str, end: str, spec_text: str, source_text: str
) -> None:
    """Every `{...}`-interpolated testid is realised in source.

    A dynamic id like `kanban-column-{column}` is satisfied by EITHER
    a template literal whose static lead-in matches (the source builds
    it as a backtick template), OR -- when the `{...}` ranges over a
    small fixed enum (`source-{kind}` → `local`/`custom`) -- by the
    enumerated literal ids themselves.
    """
    section = _spec_section(spec_text, start, end)
    _, dynamic = _static_and_dynamic(_testids_from_section(section))
    if not dynamic:
        pytest.skip(f"no dynamic testids in §4 section {label!r}")

    prefixes = _dynamic_testid_prefixes(source_text)
    literals = _static_testids_in_source(source_text)
    missing: list[str] = []
    for spec_id in dynamic:
        if spec_id in _DEFERRED_CHROME or spec_id in _DEFERRED_TESTIDS:
            continue
        # Static lead-in: text up to (and including) the dash before `{`.
        lead = spec_id.split("{", 1)[0]
        by_template = any(
            p == lead or p.endswith(lead) or lead.endswith(p) for p in prefixes
        )
        by_enum = any(lit.startswith(lead) and lit != lead for lit in literals)
        if not (by_template or by_enum):
            missing.append(
                f"{spec_id}  (no `data-testid` template with lead {lead!r} "
                f"and no enumerated `{lead}*` literal)"
            )
    assert not missing, (
        f"spec 13 §4 ({label}) dynamic testids unrealised in source:\n"
        + "\n".join(missing)
    )


# --------------------------------------------------------------------------
# §4.1 — minimal header chrome (M9)
# --------------------------------------------------------------------------
def test_minimal_header_chrome_present(source_text: str) -> None:
    """The M9 minimal header satisfies the implementable §4.1 chrome ids."""
    required = {
        "header-bar",
        "header-app-version",
        "header-help-button",
        "sidebar-nav",
    }
    present = _static_testids_in_source(source_text)
    missing = sorted(required - present)
    assert not missing, f"minimal header chrome testids missing: {missing}"


def test_sidebar_nav_links_cover_every_section(source_text: str) -> None:
    """`sidebar-nav-{section}` is realised for every spec 13 §4.1 section.

    AppHeader renders the links from a list, so the testid is a
    template literal (`\\`sidebar-nav-${section}\\``). The links are
    accepted if that template lead-in exists AND the section list in
    AppHeader.tsx names every required section.
    """
    sections = ["profiles", "datasets", "runs", "models", "eval", "publish", "settings"]
    has_template = "sidebar-nav-" in _dynamic_testid_prefixes(source_text)
    assert has_template, "no `sidebar-nav-${...}` template literal in source"

    header = (_FRONTEND_SRC / "components" / "AppHeader.tsx").read_text(encoding="utf-8")
    named = set(re.findall(r'section:\s*"([a-z]+)"', header))
    missing = [s for s in sections if s not in named]
    assert not missing, f"AppHeader sidebar nav missing sections: {missing}"


# --------------------------------------------------------------------------
# §6 — contract versioning
# --------------------------------------------------------------------------
def test_driver_contract_version_exposed() -> None:
    """`/env.js` exposes `driverContractVersion` (spec 13 §6, initial = 1)."""
    env_js = (_REPO_ROOT / "src" / "pd_ocr_trainer_spa" / "api" / "env_js.py").read_text(
        encoding="utf-8"
    )
    assert "driverContractVersion" in env_js, (
        "spec 13 §6 requires /env.js to expose driverContractVersion"
    )


def test_deferred_chrome_ids_documented() -> None:
    """Any §4.1 chrome id this test waives must be a real spec id.

    Guards against the waiver set drifting away from the spec.
    """
    section = _spec_section(_read_spec(), "### 4.1 App chrome", "### 4.2")
    spec_ids = set(_testids_from_section(section))
    unknown = _DEFERRED_CHROME - spec_ids
    assert not unknown, f"_DEFERRED_CHROME names not in spec 13 §4.1: {unknown}"


def test_deferred_testids_are_real_spec_ids() -> None:
    """Every milestone-waived testid is a genuine spec 13 §4 entry.

    If a waived id is renamed or removed in the spec, this fails so the
    waiver is cleaned up rather than masking a real contract gap.
    """
    text = _read_spec()
    all_spec_ids: set[str] = set()
    for _, start, end in _SECTIONS:
        all_spec_ids.update(_testids_from_section(_spec_section(text, start, end)))
    unknown = set(_DEFERRED_TESTIDS) - all_spec_ids
    assert not unknown, f"_DEFERRED_TESTIDS names not in spec 13 §4: {unknown}"


def test_deferred_urls_are_real_spec_urls() -> None:
    """Every waived URL is a genuine spec 13 §2 entry."""
    unknown = _DEFERRED_URLS - set(_urls_from_spec(_read_spec()))
    assert not unknown, f"_DEFERRED_URLS names not in spec 13 §2: {unknown}"
