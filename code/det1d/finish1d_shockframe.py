# Source: bg/b5-of14/finish1d_shockframe.py (verbatim but for paths).
# Shows: the shock-attached-frame evaluation (multi-cycle mean speed, complete cycles).
"""Shock-attached-frame 1D detonation: lab-equivalent lead-shock speed D_CJ + dx_s/dt from the graph samples
(x_s = largest x with p > DET_SHOCK_DETECT_P), cycles between successive peaks of the 0.5 us-smoothed speed,
the first peak (start-up overdrive) excluded. SF_T_MAX (s) truncates the record. Usage: finish1d_shockframe.py <case>... ; JSON to stdout."""
import glob, json, os, sys
import numpy as np
thr = float(os.environ.get("DET_SHOCK_DETECT_P", 2e5)); tol = float(os.environ.get("DET_DCJ_TOL_PCT", 1))
out = []
for case in sys.argv[1:]:
    init = json.load(open(f"{case}/znd-init.json")); D = init["D_CJ_m_s"]; dx = init["length_m"] / init["cells"]
    ts, xs = [], []
    for g in glob.glob(f"{case}/postProcessing/graph/*/line.xy"):
        a = np.loadtxt(g); hit = a[:, 1] > thr
        if hit.any(): ts.append(float(g.split("/")[-2])); xs.append(float(a[hit, 0].max()))
    o = np.argsort(ts); t, x = np.array(ts)[o], np.array(xs)[o]
    keep = t <= float(os.environ.get("SF_T_MAX", "inf")); t, x = t[keep], x[keep]   # e.g. before the flame reaches the outflow
    dt = np.median(np.diff(t)); k = max(1, int(round(0.5e-6 / dt / 2)))
    v = D + (x[2*k:] - x[:-2*k]) / (t[2*k:] - t[:-2*k]); tv = (t[2*k:] + t[:-2*k]) / 2   # centred 0.5 us speed
    # peaks: local maxima above the run mean, at least 1 us apart
    pk = [i for i in range(1, len(v) - 1) if v[i] >= v[i-1] and v[i] > v[i+1] and v[i] > v.mean()]
    peaks = []
    for i in pk:
        if peaks and tv[i] - tv[peaks[-1]] < 1e-6:
            if v[i] > v[peaks[-1]]: peaks[-1] = i
        else: peaks.append(i)
    r = dict(case=case, cells=init["cells"], dx_um=dx * 1e6, cells_per_lind=init["induction_length_m"] / dx, D_CJ=D,
             t_end_us=float(t[-1] * 1e6), x_shock_mm=[float(x[0] * 1e3), float(x.min() * 1e3), float(x.max() * 1e3), float(x[-1] * 1e3)],
             speed_peaks_us=[float(tv[i] * 1e6) for i in peaks], speed_peak_values=[float(v[i]) for i in peaks],
             D_whole_run=float(D + (x[-1] - x[0]) / (t[-1] - t[0])))
    cyc = peaks[1:]                       # drop the start-up overdrive peak
    if len(cyc) >= 2:
        i0, i1 = cyc[0], cyc[-1]
        j0, j1 = i0 + k, i1 + k            # same times in the x/t arrays
        Dm = D + (x[j1] - x[j0]) / (t[j1] - t[j0]); seg = v[i0:i1 + 1]
        r.update(complete_cycles=len(cyc) - 1, cycles_from_to_us=[float(t[j0] * 1e6), float(t[j1] * 1e6)],
                 D_mean_cycles=float(Dm), D_err_pct=float(100 * (Dm / D - 1)), gate_within_1pct=bool(abs(Dm / D - 1) * 100 <= tol),
                 period_us=float(np.mean(np.diff(tv[cyc])) * 1e6), period_spread_us=[float(z * 1e6) for z in np.diff(tv[cyc])],
                 D_min=float(seg.min()), D_max=float(seg.max()), amplitude_pct=float(100 * (seg.max() - seg.min()) / 2 / D))
    else:
        r.update(complete_cycles=max(0, len(cyc) - 1), gate_within_1pct=False, note="fewer than one complete cycle after start-up")
    tm = sorted(glob.glob(f"{case}/postProcessing/temperatureMax/*/volFieldValue.dat"))
    T = np.concatenate([np.loadtxt(f, comments="#")[:, 1] for f in tm]) if tm else np.array([np.nan])
    r.update(step_Tmax_K=float(T.max()), steps_sampled=int(len(T)), steps_at_3500K=int((T >= 3499.99).sum()))
    out.append(r)
print(json.dumps(out, indent=1))
