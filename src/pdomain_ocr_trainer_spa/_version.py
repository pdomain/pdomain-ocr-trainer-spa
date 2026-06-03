"""Runtime package version."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdomain-ocr-trainer-spa")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
