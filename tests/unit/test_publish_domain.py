"""Unit tests for domain/publish.py SPDX license validation (issue #18).

These tests verify that ``validate_spdx_license`` delegates to
``pdomain_book_tools.licenses.is_valid_spdx_id`` and therefore accepts only
canonical-case SPDX identifiers (``Apache-2.0``, not ``apache-2.0``).

RED phase: all tests in this file are written BEFORE the production code
change so they fail against the bundled-subset implementation.
"""

from __future__ import annotations

import pytest

from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.domain.publish import validate_spdx_license

# ---------------------------------------------------------------------------
# Acceptance: canonical-case SPDX IDs from pdomain-book-tools must be accepted
# ---------------------------------------------------------------------------


def test_validate_accepts_canonical_case_apache() -> None:
    """Apache-2.0 (canonical SPDX case) must be accepted without raising."""
    validate_spdx_license("Apache-2.0")  # must not raise


def test_validate_accepts_canonical_case_mit() -> None:
    """MIT (canonical SPDX case) must be accepted without raising."""
    validate_spdx_license("MIT")  # must not raise


def test_validate_accepts_canonical_case_cc_by_4() -> None:
    """CC-BY-4.0 (canonical SPDX case) must be accepted without raising."""
    validate_spdx_license("CC-BY-4.0")  # must not raise


def test_validate_accepts_canonical_case_cc0() -> None:
    """CC0-1.0 (canonical SPDX case) must be accepted without raising."""
    validate_spdx_license("CC0-1.0")  # must not raise


# ---------------------------------------------------------------------------
# Rejection: non-canonical case must now be rejected (pdomain-book-tools is
# case-sensitive; lowercase "apache-2.0" is NOT a valid SPDX identifier)
# ---------------------------------------------------------------------------


def test_validate_rejects_lowercase_apache() -> None:
    """apache-2.0 (lowercase) is NOT a valid SPDX id — must raise 409."""
    with pytest.raises(AppError) as exc_info:
        validate_spdx_license("apache-2.0")
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "publish.license_missing"


def test_validate_rejects_lowercase_mit() -> None:
    """mit (lowercase) is NOT a valid SPDX id — must raise 409."""
    with pytest.raises(AppError) as exc_info:
        validate_spdx_license("mit")
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "publish.license_missing"


# ---------------------------------------------------------------------------
# Rejection: garbage input
# ---------------------------------------------------------------------------


def test_validate_rejects_completely_invalid_id() -> None:
    """Completely bogus string must raise 409 publish.license_missing."""
    with pytest.raises(AppError) as exc_info:
        validate_spdx_license("NOT_A_REAL_LICENSE_123")
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "publish.license_missing"


# ---------------------------------------------------------------------------
# Source of truth: SPDX_VALID_IDS in publish.py must come from pdomain-book-tools
# ---------------------------------------------------------------------------


def test_spdx_valid_ids_delegates_to_pdomain_book_tools() -> None:
    """domain.publish.SPDX_VALID_IDS must be the pdomain_book_tools frozenset (518+ entries)."""
    from pdomain_book_tools.licenses import SPDX_VALID_IDS as upstream_set

    from pdomain_ocr_trainer_spa.domain.publish import SPDX_VALID_IDS as local_set

    assert local_set is upstream_set, (
        "domain/publish.py must import SPDX_VALID_IDS directly from pdomain_book_tools.licenses "
        "rather than bundling a hand-rolled subset."
    )
