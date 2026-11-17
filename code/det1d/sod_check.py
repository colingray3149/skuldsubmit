# Source: bg/b5-of14/sod_check.py (verbatim but for paths).
# Shows: Sod against the exact Riemann solution: wave positions, L1 errors, observed order.
"""B5 (a): OF-14 shockFluid Sod against the exact Riemann solution.

Usage: python3 sod_check.py <t> <case dir> [<case dir> ...] > sod-check.json
Each case dir holds postProcessing/graph/<time>/*.xy (graphCell: x T mag(U) p). Reports wave positions (shock,
contact, fan head, fan tail) against exact, the L1 error of rho, u, p, and the observed L1 order between grids.
Gas, states and tolerances come from b5.conf through the environment (SOD_*), so nothing is pinned here.
"""
import glob, json, math, os, sys

import numpy as np

g = float(os.environ.get("SOD_GAMMA", 1.4))
R = float(os.environ.get("SOD_CP", 1004.5)) * (g - 1) / g
pL, TL = float(os.environ.get("SOD_PL", 1e5)), float(os.environ.get("SOD_TL", 348.432))
pR, TR = float(os.environ.get("SOD_PR", 1e4)), float(os.environ.get("SOD_TR", 278.746))
x0 = float(os.environ.get("SOD_X0", 0.0))
rL, rR = pL / (R * TL), pR / (R * TR)
aL, aR = math.sqrt(g * pL / rL), math.sqrt(g * pR / rR)


def star():
    def f(p, pk, rk, ak):
        if p > pk:
            A, B = 2 / ((g + 1) * rk), (g - 1) / (g + 1) * pk
            return (p - pk) * math.sqrt(A / (p + B))
        return 2 * ak / (g - 1) * ((p / pk) ** ((g - 1) / (2 * g)) - 1)
    lo, hi = 1e-12, 10 * max(pL, pR)
    for _ in range(200):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if f(m, pL, rL, aL) + f(m, pR, rR, aR) < 0 else (lo, m)
    p = 0.5 * (lo + hi)
    return p, 0.5 * (f(p, pR, rR, aR) - f(p, pL, rL, aL))


ps, us = star()
rsL = rL * (ps / pL) ** (1 / g)
rsR = rR * ((ps / pR + (g - 1) / (g + 1)) / ((g - 1) / (g + 1) * ps / pR + 1))
asL = aL * (ps / pL) ** ((g - 1) / (2 * g))
S = us * (rsR / rR) / ((rsR / rR) - 1)  # shock speed from mass conservation (right state at rest)


def exact(x, t):
    xi = (x - x0) / t
    rho, u, p = np.empty_like(xi), np.empty_like(xi), np.empty_like(xi)
    for i, s in enumerate(xi):
        if s < -aL:
            rho[i], u[i], p[i] = rL, 0, pL
        elif s < us - asL:
            uu = 2 / (g + 1) * (aL + s)
            c = 2 / (g + 1) * aL - (g - 1) / (g + 1) * s
            rho[i], u[i], p[i] = rL * (c / aL) ** (2 / (g - 1)), uu, pL * (c / aL) ** (2 * g / (g - 1))
        elif s < us:
            rho[i], u[i], p[i] = rsL, us, ps
        elif s < S:
            rho[i], u[i], p[i] = rsR, us, ps
        else:
            rho[i], u[i], p[i] = rR, 0, pR
    return rho, u, p


def positions(t):
    return dict(fan_head=x0 - aL * t, fan_tail=x0 + (us - asL) * t, contact=x0 + us * t, shock=x0 + S * t)


def read_fields(case, t):
    """Fallback for cases without a graph (ESI): <time>/{T,p,U,Cx} ascii internal fields."""
    import re
    td = sorted((d for d in glob.glob(f"{case}/[0-9]*") if os.path.basename(d).replace(".", "").replace("e-", "").isdigit()), key=lambda s: abs(float(os.path.basename(s)) - t))[0]
    def sc(name):
        s = open(f"{td}/{name}").read()
        m = re.search(r"internalField\s+nonuniform\s+List<scalar>\s*(\d+)\s*\(", s)
        return np.array(s[m.end():].split(None, int(m.group(1)))[: int(m.group(1))], float)
    s = open(f"{td}/U").read()
    m = re.search(r"internalField\s+nonuniform\s+List<vector>\s*(\d+)\s*\(", s)
    U = np.array(re.findall(r"\(([^()]*)\)", s[m.end():])[: int(m.group(1))][0:], dtype=object)
    U = np.array([float(v.split()[0]) for v in U])
    x, T, p = sc("Cx"), sc("T"), sc("p")
    o = np.argsort(x)
    return x[o], T[o], np.abs(U[o]), p[o]


def read(case, t):
    if not glob.glob(f"{case}/postProcessing/graph*"):
        return read_fields(case, t)
    d = sorted(glob.glob(f"{case}/postProcessing/graph*/*"), key=lambda s: abs(float(os.path.basename(s)) - t))[0]
    f = glob.glob(f"{d}/*.xy")[0]
    a = np.loadtxt(f)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]  # x T |U| p


def crossing(x, f, level, mask):
    """Rightmost interpolated x where f crosses level inside mask."""
    i = np.nonzero(mask[:-1] & mask[1:] & ((f[:-1] - level) * (f[1:] - level) <= 0))[0]
    if not len(i):
        return float("nan")
    k = i.max()
    return float(x[k] + (level - f[k]) * (x[k + 1] - x[k]) / (f[k + 1] - f[k]))


def measured(x, rho, u, p):
    """Shock and contact: mid-value crossings of p and rho. Fan head and tail: u is linear in x across the exact
    fan, so a straight line fitted to the fan's interior (u between 25 % and 75 % of u*) is extrapolated to u = 0
    and u = u* (kinks are smeared by the scheme; the extrapolation measures the fan, not the smearing)."""
    allx = np.ones_like(x, bool)
    shock = crossing(x, p, 0.5 * (ps + pR), allx)
    contact = crossing(x, rho, 0.5 * (rsL + rsR), x < shock)
    fan = (x < contact) & (u > 0.25 * us) & (u < 0.75 * us)
    a, b = np.polyfit(x[fan], u[fan], 1)
    return dict(shock=shock, contact=contact, fan_head=float(-b / a), fan_tail=float((us - b) / a))


def main():
    t = float(sys.argv[1])
    out, errs = dict(t=t, gamma=g, R=R, p_star=ps, u_star=us, shock_speed=S, exact=positions(t), cases=[]), []
    for case in sys.argv[2:]:
        x, T, U, p = read(case, t)
        rho = p / (R * T)
        re, ue, pe = exact(x, t)
        dx = x[1] - x[0]
        m = measured(x, rho, U, p)
        dev = {k: (m[k] - v) / dx for k, v in positions(t).items()}
        l1 = dict(rho=float(np.mean(np.abs(rho - re)) / rL), u=float(np.mean(np.abs(U - ue)) / aL), p=float(np.mean(np.abs(p - pe)) / pL))
        out["cases"].append(dict(case=case, cells=len(x), dx=dx, measured=m, dev_cells=dev, l1=l1))
        errs.append((dx, l1))
    for a, b in zip(errs, errs[1:]):
        b_order = {k: math.log(a[1][k] / b[1][k]) / math.log(a[0] / b[0]) for k in a[1]}
        out.setdefault("orders", []).append(dict(dx_coarse=a[0], dx_fine=b[0], order=b_order))
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
