"""Lead-shock speed of a 1D detonation tube from its stored probe traces, and the B5 1% CJ gate.

Same method as det1d_check.py / finish1d_eval.py beside this file (which read the OpenFOAM case folders): at each
probe the arrival time is the first sample with p > 2e5 Pa (DET_SHOCK_DETECT_P in b5.conf); the speed is the
least-squares slope of x against arrival time over probes at x >= 10 mm (DET_FIT_FROM). D_CJ comes from the B1
reference row (SDToolbox CJspeed on the same Burke 2012 mechanism). Gate: |D - D_CJ| <= 1% (DET_DCJ_TOL_PCT).

Usage: python code/det1d/speed_fit.py data/det1d/probes-ar7-coarse.npz [more .npz]
"""
import csv
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
THRESHOLD_PA, FIT_FROM_M, TOL_PCT = 2e5, 0.010, 1.0
MIXTURE = {"ar7": "2h2-o2-7ar-1atm", "h2air": "h2air-phi1-1atm-300K"}


def d_cj(mixture_id, mech="Burke2012.yaml"):
    for row in csv.DictReader(open(ROOT / "data/b1/refs-subset.csv")):
        if row["id"] == mixture_id and row["mech"] == mech:
            return float(row["d_cj"])
    raise KeyError(f"no B1 reference for {mixture_id} / {mech}")


def arrivals(npz, x_min=FIT_FROM_M):
    d = np.load(npz)
    x, t, p = d["x_m"], d["t_s"], d["p_pa"]
    hit = p > THRESHOLD_PA
    keep = hit.any(axis=0) & (x >= x_min)
    return x[keep], t[np.argmax(hit[:, keep], axis=0)]


def fit(npz):
    x, ta = arrivals(npz)
    D = float(np.polyfit(ta, x, 1)[0])
    h = len(x) // 2
    tag = pathlib.Path(npz).stem.removeprefix("probes-")
    ref = d_cj(MIXTURE[tag.split("-")[0]])
    err = 100 * (D - ref) / ref
    return dict(case=tag, probes_fitted=int(len(x)), D=D, D_CJ=ref, D_err_pct=err,
                D_first_half=float(np.polyfit(ta[:h], x[:h], 1)[0]), D_second_half=float(np.polyfit(ta[h:], x[h:], 1)[0]),
                gate_within_1pct=abs(err) <= TOL_PCT)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        r = fit(path)
        print(f"{r['case']:20s} {r['probes_fitted']} probes  D {r['D']:8.2f} m/s  D_CJ {r['D_CJ']:8.2f}  "
              f"error {r['D_err_pct']:+7.3f} %  halves {r['D_first_half']:.1f}/{r['D_second_half']:.1f}  "
              f"gate {'PASS' if r['gate_within_1pct'] else 'FAIL'}")
