import sys
import os

# Shared infrastructure (core/, config/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
# Sprint root — allows `from agents.agent_03_classifier import classify_order`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
