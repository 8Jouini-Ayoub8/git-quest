#!/usr/bin/env python3
"""Quest CI — inspects the agent file of the fork owner. Runs inside the student's fork."""
import os
import re
import subprocess
import sys
from pathlib import Path

owner = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OWNER", "")).strip()
summary = os.environ.get("GITHUB_STEP_SUMMARY")
REQUIRED = {
    "agent": "your GitHub username",
    "codename": "your hacker codename (Level 1)",
    "motto": "every agent needs a motto — add a line like  motto: Hack fast, defend faster",
}

print("🛰️  Quest CI — booting inspection droid…")
print(f"   repository owner : {owner}")

errors = []
agents = Path("agents")
path = next((p for p in agents.glob("*.md") if p.stem.lower() == owner.lower()), None)
fields = {}
if path is None:
    errors.append((f"agents/{owner}.md", f"Agent file agents/{owner}.md not found on this branch."))
else:
    print(f"   agent file       : {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*?)\s*$", line)
        if m:
            fields.setdefault(m.group(1).lower(), m.group(2))
    for key, why in REQUIRED.items():
        if not fields.get(key, "").strip():
            errors.append((str(path), f"Missing field '{key}:' → {why}"))
    if fields.get("agent", "").lower() not in ("", owner.lower()):
        errors.append((str(path), f"'agent:' is {fields['agent']!r}, expected {owner!r}"))

grep = subprocess.run(["git", "grep", "-n", "-I", "-E", r"^(<<<<<<<|>>>>>>>)( |$)|^=======$", "--", ".", ":(exclude).github"],
                      capture_output=True, text=True)
for line in grep.stdout.splitlines()[:5]:
    f, n, _ = line.split(":", 2)
    errors.append((f, f"Conflict marker left at line {n}"))

print()
if errors:
    for f, msg in errors:
        print(f"::error file={f}::{msg}")
        print(f"   ❌ {msg}")
    print("\n🔴 Inspection FAILED — fix the items above, commit, push. CI will run again automatically.")
    if summary:
        with open(summary, "a", encoding="utf-8") as s:
            s.write("## 🔴 Quest CI failed\n\n" + "\n".join(f"- ❌ {m}" for _, m in errors) + "\n")
    sys.exit(1)

print(f"   ✅ agent    : {fields['agent']}")
print(f"   ✅ codename : {fields['codename']}")
print(f"   ✅ motto    : {fields['motto']}")
print("\n🟢 All systems online. Welcome aboard, agent.")
if summary:
    with open(summary, "a", encoding="utf-8") as s:
        s.write(f"## 🟢 Agent `{fields['agent']}` cleared\n\n| field | value |\n|---|---|\n"
                + "".join(f"| {k} | {v} |\n" for k, v in fields.items()))
