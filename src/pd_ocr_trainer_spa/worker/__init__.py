"""Training-worker subprocess package (spec 02-backend §5, spec 06 §3).

The worker runs as ``python -m pd_ocr_trainer_spa.worker.train --run-dir
runs/<id>``. It is launched and supervised by the pd-ocr-ops ``LongJobRunner``;
the FastAPI web process never imports anything under this package (D-T1).
"""

from __future__ import annotations
