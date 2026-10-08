"""Retained company texts/classifications with visibly authored replay timing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import OWNER
from test_retained_watch_continuity import (
    test_real_labels_survive_new_repeat_gap_failure_stop_recovery_and_review,
)

test_real_labels_survive_new_repeat_gap_failure_stop_recovery_and_review(OWNER)
print(
    "Retained watch browser: original Alphabet reports and labels; authored arrivals/failures; two company alerts, one reviewed, all watches stopped."
)
