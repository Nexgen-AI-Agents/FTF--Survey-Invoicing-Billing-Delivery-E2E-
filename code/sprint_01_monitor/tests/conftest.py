import sys
import os

# Shared infrastructure (core/, config/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
# Sprint root — allows `from agents.agent_02_monitor import run`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
