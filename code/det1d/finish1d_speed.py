# Source: bg/b5-of14/finish1d_speed.py (verbatim but for paths).
# Shows: local lead-shock speed between neighbouring probes (the decay/gallop diagnostic).
"""Local lead-shock speed history from probe arrivals (first p > threshold). Usage: finish1d_speed.py <case>..."""
import glob, os, sys
import numpy as np
thr = float(os.environ.get("DET_SHOCK_DETECT_P", 2e5)); dcj = 1975.1746278769756
for case in sys.argv[1:]:
    f = sorted(glob.glob(f"{case}/postProcessing/probes/*/p"))[0]
    xs = np.array([float(l.split("(")[1].split()[0]) for l in open(f) if l.startswith("# Probe")])
    a = np.loadtxt(f, comments="#"); t, p = a[:, 0], a[:, 1:]
    arr = np.array([(x, t[np.argmax(p[:, i] > thr)]) for i, x in enumerate(xs) if (p[:, i] > thr).any() and x > 0.0051])
    v = np.diff(arr[:, 0]) / np.diff(arr[:, 1])
    print(os.path.basename(case.rstrip("/")))
    for k in range(0, len(v), 2):
        seg = v[k:k + 2]
        print(f"  x {arr[k,0]*1e3:5.1f}-{arr[min(k+2,len(arr)-1),0]*1e3:5.1f} mm  t {arr[k,1]*1e6:5.2f} us  D {np.mean(seg):7.1f} ({100*(np.mean(seg)/dcj-1):+6.2f}%)")
