import sys
import os

# Shared infrastructure (core/, config/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
# Sprint 5 root — allows `from agents.agent_07_reviewer import review_estimate`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Sprint 4 root — reviewer imports write_estimate from sprint_04_writer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sprint_04_writer"))
