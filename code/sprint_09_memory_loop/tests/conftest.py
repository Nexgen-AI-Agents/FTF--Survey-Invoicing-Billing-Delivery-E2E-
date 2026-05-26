import sys
from pathlib import Path

# Shared core (settings, models, db, etc.)
sys.path.insert(0, str(Path(__file__).parents[3] / "shared"))
# Sprint 9 agents root
sys.path.insert(0, str(Path(__file__).parents[1] / "agents"))
