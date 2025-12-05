import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from backend import main
    print("Syntax OK")
except Exception as e:
    print(f"Syntax Error: {e}")
