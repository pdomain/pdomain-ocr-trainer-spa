"""Guard against two OpenCV distributions sharing the ``cv2/`` directory."""

from __future__ import annotations

from importlib.metadata import distributions

OPENCV_DISTRIBUTIONS = frozenset(
    {
        "opencv-python",
        "opencv-contrib-python",
        "opencv-python-headless",
        "opencv-contrib-python-headless",
    }
)


def _normalise(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def test_exactly_one_opencv_distribution_installed() -> None:
    """Every OpenCV wheel writes ``cv2/``; a second one breaks ``import cv2``."""
    installed = {
        _normalise(name) for dist in distributions() if (name := dist.metadata["Name"]) is not None
    } & OPENCV_DISTRIBUTIONS
    assert installed == {"opencv-python"}
