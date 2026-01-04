from pathlib import Path
import re
import sys

inp = sys.argv[1]
p = Path(inp)
lines = p.read_text(encoding="utf-8-sig").splitlines()

out = []
prev = None
for ln in lines:
    # poista rivit, joissa on vain numero/merkkejä ja paljon whitespacea
    if re.fullmatch(r"\s*\d+\s*", ln):
        continue
    # tiivistä moninkertaiset tyhjät rivit
    if ln.strip() == "" and (prev is None or prev.strip() == ""):
        continue
    # poista täsmälleen peräkkäin toistuvat rivit
    if prev is not None and ln == prev:
        continue
    out.append(ln)
    prev = ln

p.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8-sig")
