import sys
import os

# Shared infrastructure (core/, config/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
# Sprint root — allows `from agents.agent_06_writer import write_estimate`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
