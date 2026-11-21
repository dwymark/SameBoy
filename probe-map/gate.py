import json, sys, collections
LEVELS = {"measured", "source", "unverified"}
NEED = {
    "meta": {"format", "target", "shape", "read_order"},
    "build": {"repo", "commit", "invocation"},
    "assumption": {"choice", "reason", "alternative"},
    "control": {"name", "syntax", "effect", "evidence", "cites"},
    "probe": {"axis", "label", "argv", "digest", "evidence"},
    "finding": {"claim", "evidence", "rests_on"},
    "recipe": {"goal", "steps"},
    "owed": {"what", "command", "blocks"},
    "caveat": {"text"},
}
rs = [json.loads(l) for l in open(sys.argv[1])]
errs, ids = [], collections.Counter(r.get("id") for r in rs)
kind = {r.get("id"): r.get("type") for r in rs}
if rs[0].get("type") != "meta" or rs[0].get("format") != "probe-map/1":
    errs.append("first line must be meta with format probe-map/1")
for i, r in enumerate(rs, 1):
    t = r.get("type")
    if t not in NEED: errs.append(f"{i}: unknown type {t}"); continue
    if not r.get("id"): errs.append(f"{i}: missing id")
    if (m := NEED[t] - r.keys()): errs.append(f"{i} {r.get('id')}: missing {sorted(m)}")
    if "evidence" in r and r["evidence"] not in LEVELS: errs.append(f"{i}: evidence {r['evidence']}")
    for ref in r.get("rests_on", []):
        if ref not in ids and ":" not in ref: errs.append(f"{i}: rests_on {ref} unresolved")
    if t == "finding" and r.get("evidence") == "measured" and "probe" not in {kind.get(x) for x in r.get("rests_on", [])}:
        errs.append(f"{i}: measured finding rests on no probe")
errs += [f"duplicate id {k}" for k, n in ids.items() if n > 1]
print("\n".join(errs) or "GO")
