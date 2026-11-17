# Source: bg/b5-of14/det1d_check.py (verbatim but for paths).
# Shows: the lead-shock speed fit (first p > threshold at each probe, least squares over x >= 10 mm) against B1 D_CJ.
"""B5 (b): 1D detonation tube against B1. Usage: det1d_check.py <b1 refs.csv> <mixture id> <mech> <case dir>...
Shock speed: least-squares fit of probe arrival times (first p > DET_SHOCK_DETECT_P) over x >= DET_FIT_FROM.
L_ind proxy: reconstructed full-mesh pressure shock to peak heat release behind it. Qdot is not ZND thermicity;
the comparison is diagnostic, not a valid thermicity-based acceptance measurement.
Tolerances and fit window come from b5.conf through the environment."""
import csv, glob, json, os, re, sys
import numpy as np

thr = float(os.environ["DET_SHOCK_DETECT_P"]); fit_from = float(os.environ["DET_FIT_FROM"])
tol_d, tol_l = float(os.environ["DET_DCJ_TOL_PCT"]), float(os.environ["DET_LIND_TOL_PCT"])
refs, mid, mech = sys.argv[1], sys.argv[2], sys.argv[3]
ref = next(r for r in csv.DictReader(open(refs)) if r["id"] == mid and r["mech"] == mech)
d_cj, l_ind = float(ref["d_cj"]), float(ref["l_ind"])
out = dict(ref=dict(id=mid, mech=mech, d_cj=d_cj, l_ind=l_ind), cases=[])
for case in sys.argv[4:]:
    f = sorted(glob.glob(f"{case}/postProcessing/probes/*/p"))[0]
    xs = [float(l.split("(")[1].split()[0]) for l in open(f) if l.startswith("# Probe")]
    a = np.loadtxt(f, comments="#")
    t, p = a[:, 0], a[:, 1:]
    arr = [(x, t[np.argmax(p[:, i] > thr)]) for i, x in enumerate(xs) if (p[:, i] > thr).any() and x >= fit_from]
    x_, t_ = np.array(arr).T if arr else (np.array([]), np.array([]))
    D = float(np.polyfit(t_, x_, 1)[0]) if len(x_) > 2 else float("nan")
    times = sorted((p for p in glob.glob(f"{case}/*") if os.path.isdir(p) and re.fullmatch(r"[0-9.eE+-]+", os.path.basename(p)) and float(os.path.basename(p)) > 0 and os.path.exists(f"{p}/Qdot")), key=lambda p: float(os.path.basename(p)))
    if not times:
        out["cases"].append(dict(case=case, probes_fitted=len(x_), D=D, D_err_pct=100 * (D - d_cj) / d_cj, L_ind=None, note="no reconstructed final fields"))
        continue
    def field(name):
        text = open(f"{times[-1]}/{name}").read()
        m = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(\s*(.*?)\s*\)", text, re.S)
        if not m:
            raise ValueError(f"missing nonuniform {name} in {times[-1]}")
        v = np.fromstring(m.group(2), sep=" ")
        if len(v) != int(m.group(1)):
            raise ValueError(f"invalid {name} field length")
        return v
    P, heat = field("p"), field("Qdot")
    if len(P) != len(heat):
        raise ValueError("pressure and heat-release field lengths differ")
    length = float(os.environ["DET_LENGTH"])
    dx = length / len(P)
    x = (np.arange(len(P)) + 0.5) * dx
    i_s = int(np.nonzero(P > thr)[0].max())
    xs_ = x[i_s]
    behind = (x < xs_) & (x > xs_ - 20 * l_ind)
    i_t = np.nonzero(behind)[0][np.argmax(heat[behind])]
    L = float(xs_ - x[i_t])
    out["cases"].append(dict(case=case, cells=len(x), dx=dx, cells_per_lind=l_ind / dx, probes_fitted=len(x_), D=D,
                             D_err_pct=100 * (D - d_cj) / d_cj, L_ind_heat_release_proxy=L, L_proxy_err_pct=100 * (L - l_ind) / l_ind,
                             p_peak=float(P.max()), shock_x=float(xs_), field_time=float(os.path.basename(times[-1]))))
c = sorted((c for c in out["cases"] if c.get("dx")), key=lambda c: c["dx"])
if not c:
    json.dump(out, sys.stdout, indent=1); sys.exit()
fine = c[0]
mono = len(c) >= 3 and all(abs(a["D_err_pct"]) <= abs(b["D_err_pct"]) for a, b in zip(c, c[1:]))
out["pass"] = dict(D=abs(fine["D_err_pct"]) <= tol_d if len(c) >= 3 else None, L_ind=None, monotone_D=mono if len(c) >= 3 else None)
out["note"] = "L_ind gate unevaluated: Qdot peak is not the ZND thermicity peak."
json.dump(out, sys.stdout, indent=1)
