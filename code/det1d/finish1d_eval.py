# Source: bg/b5-of14/finish1d_eval.py (verbatim but for paths).
# Shows: the gate evaluation that produced data/det1d/finish1d-*.json (speed fit, per-step Tmax, 3500 K count).
"""B5 1D gate evidence for ZND-initialised cases. Usage: finish1d_eval.py <case>...
Runs det1d_check.py's probe fit (DET_FIT_FROM..end, first p > DET_SHOCK_DETECT_P) and adds per-step full-domain
Tmax (postProcessing/temperatureMax), steps at or above the 3500 K JANAF ceiling, and first/second-half window speeds.
Environment as det1d_check.py (source b5.conf). Writes JSON to stdout."""
import glob, json, os, subprocess, sys
import numpy as np
B5 = os.path.dirname(os.path.abspath(__file__))
cases = sys.argv[1:]
chk = json.loads(subprocess.check_output([sys.executable, f"{B5}/det1d_check.py", f"{B5}/../b1-refcalc/refs.csv",
                                          os.environ.get("MIX_ID", "h2air-phi1-1atm-300K"), "Burke2012.yaml", *cases]))
thr, fit_from = float(os.environ["DET_SHOCK_DETECT_P"]), float(os.environ["DET_FIT_FROM"])
d_cj = chk["ref"]["d_cj"]
for c in chk["cases"]:
    case = c["case"]
    f = sorted(glob.glob(f"{case}/postProcessing/probes/*/p"))[0]
    xs = np.array([float(l.split("(")[1].split()[0]) for l in open(f) if l.startswith("# Probe")])
    a = np.loadtxt(f, comments="#"); t, p = a[:, 0], a[:, 1:]
    arr = np.array([(x, t[np.argmax(p[:, i] > thr)]) for i, x in enumerate(xs) if (p[:, i] > thr).any() and x >= fit_from])
    h = len(arr) // 2
    c["D_first_half"] = float(np.polyfit(arr[:h, 1], arr[:h, 0], 1)[0])
    c["D_second_half"] = float(np.polyfit(arr[h:, 1], arr[h:, 0], 1)[0])
    c["fit_window_mm"] = [float(arr[0, 0] * 1e3), float(arr[-1, 0] * 1e3)]
    tm = sorted(glob.glob(f"{case}/postProcessing/temperatureMax/*/volFieldValue.dat"))
    if tm:
        T = np.concatenate([np.loadtxt(x, comments="#")[:, 1] for x in tm])
        c["step_Tmax_K"] = float(T.max()); c["steps_sampled"] = int(len(T)); c["steps_at_3500K"] = int((T >= 3499.99).sum())
    else:
        c["step_Tmax_K"] = None
for c in chk["cases"]:
    c["gate_D_within_1pct"] = abs(c["D_err_pct"]) <= float(os.environ["DET_DCJ_TOL_PCT"])
print(json.dumps(chk, indent=1))
