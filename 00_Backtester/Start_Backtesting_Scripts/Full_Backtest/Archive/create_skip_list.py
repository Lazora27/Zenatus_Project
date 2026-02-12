"""Erstelle SKIP_INDICATORS Liste für PROBLEMSOLVING"""
import json
from pathlib import Path

base = Path(r"/opt/Zenatus_Dokumentation\Dokumentation")

# Load Problem IDs
targets = json.load(open(base / 'PROBLEMSOLVING_TARGETS.json'))
problem_ids = set(targets['error_106'] + targets['timeout_9'] + targets['few_8'] + targets['failed_1'])

print(f"Problem IDs: {len(problem_ids)}")
print(f"Range: {min(problem_ids)} - {max(problem_ids)}")

# Create SKIP list: All IDs from 1-600 EXCEPT problem IDs
all_ids = set(range(1, 601))
skip_ids = sorted(all_ids - problem_ids)

print(f"SKIP IDs: {len(skip_ids)}")
print(f"First 10: {skip_ids[:10]}")
print(f"Last 10: {skip_ids[-10:]}")

# Save as Python list for easy copy-paste
with open(base / 'SKIP_INDICATORS_PROBLEMSOLVING.txt', 'w') as f:
    f.write(f"SKIP_INDICATORS = {skip_ids}\n")
    f.write(f"\n# Total: {len(skip_ids)} indicators to skip\n")
    f.write(f"# Testing: {len(problem_ids)} problem indicators\n")

print(f"\nCreated SKIP_INDICATORS_PROBLEMSOLVING.txt")
