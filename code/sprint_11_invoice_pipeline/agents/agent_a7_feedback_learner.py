"""Agent A7 — Feedback Learner (stubbed)

Previously scanned Teams channel replies for learnable pricing/workflow rules
and persisted them to data/learned_rules.json.

Teams has been retired. A7 is currently a no-op stub.
Future implementation: scan approval notes from OneDrive Excel (Approvals sheet)
for patterns that can be promoted to learned rules.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.logger import get_logger

log = get_logger("agent_a7_feedback_learner")


def run() -> dict:
    log.info("a7_feedback_learner: Teams retired — feedback learning paused")
    return {"skipped": True, "reason": "Teams retired; Excel-based learning not yet implemented"}


def main(argv=None) -> None:
    print(run())


if __name__ == "__main__":
    main()
