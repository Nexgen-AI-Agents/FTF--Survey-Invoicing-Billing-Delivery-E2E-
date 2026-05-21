import os
import sys

# Makes code/shared importable as 'core.*' and 'config.*' in all pytest runs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "code", "shared"))
