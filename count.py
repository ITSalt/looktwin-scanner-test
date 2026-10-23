"""Count gitleaks misses per file: python3 count.py gl.json
A key counts as found when its line number appears with RuleID openai-api-key."""
import json, os, sys
from collections import defaultdict

found = defaultdict(set)
for f in json.load(open(sys.argv[1])):
    if f["RuleID"] == "openai-api-key":
        found[os.path.basename(f["File"])].add(f["StartLine"])
print(f"{'file':28} {'missed':>7}")
for name in sorted(f for f in os.listdir("data") if f.endswith(".txt")):
    n = sum(1 for _ in open(os.path.join("data", name)))
    print(f"{name:28} {n - len(found[name]):>7}")
