import json, subprocess, hashlib, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probes import P
here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{here}/out", exist_ok=True)
res = {}
for p in P:
    argv = ["./harness", p["mode"], p["model"], p["rom"]]
    if p["script"] is not None:
        sf = f"out/{p['id']}.script"; open(f"{here}/{sf}", "w").write("\n".join(p["script"]) + "\n"); argv.append(sf)
    env = dict(os.environ); env["SEED"] = "1"; env.update(p["env"])
    t = time.time()
    r = subprocess.run(argv, cwd=here, env=env, capture_output=True, timeout=120,
                       input=(p["stdin"] or "").encode(), )
    dt = time.time() - t
    open(f"{here}/out/{p['id']}.txt", "wb").write(r.stdout)
    res[p["id"]] = dict(exit=r.returncode, md5=hashlib.md5(r.stdout).hexdigest(), bytes=len(r.stdout),
                        stderr=r.stderr.decode()[-300:], seconds=round(dt, 3), argv=argv, env=p["env"])
json.dump(res, open(f"{here}/out/results.json", "w"), indent=1)
print(len(res), "probes;", sum(v["exit"] != 0 for v in res.values()), "nonzero exits")
