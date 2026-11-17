"""Regenerate every figure in figures/ from data/ (no network, no OpenFOAM). python figures/make_figures.py

Style: black on white, one accent, Liberation Sans (Arial metrics), thin marks, labelled axes with units.
Each figure is written as vector PDF and SVG plus a 200 dpi PNG.
"""
import csv
import json
import math
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "figures"
sys.path.insert(0, str(ROOT / "code/chem0d"))
sys.path.insert(0, str(ROOT / "code/det1d"))

INK, GRAY, LIGHT, ACCENT = "#1a1a1a", "#8a8a8a", "#e8e8e8", "#1B5FAA"
plt.rcParams.update({
    "font.family": "Liberation Sans", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.edgecolor": INK, "axes.linewidth": 0.6, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.grid": True, "grid.color": LIGHT, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 8,
    "lines.linewidth": 1.4, "lines.markersize": 5, "savefig.dpi": 200, "pdf.fonttype": 42, "svg.fonttype": "none",
    "svg.hashsalt": "skuldsubmit",
})


def save(fig, name):
    for ext in ("pdf", "svg", "png"):
        meta = {"CreationDate": None} if ext == "pdf" else {"Date": None} if ext == "svg" else {}
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", facecolor="white", metadata=meta)
    plt.close(fig)
    print("wrote", name)


def load(rel):
    return json.load(open(DATA / rel))


def b1(mixture):
    for r in csv.DictReader(open(DATA / "b1/refs-subset.csv")):
        if r["id"] == mixture and r["mech"] == "Burke2012.yaml":
            return r
    raise KeyError(mixture)


# Fig. 1: 1D detonation speed error vs grid spacing, every configuration tried
def fig_speed_vs_grid():
    ar7 = load("det1d/finish1d-ar7.json")["cases"]
    hot = load("det1d/det1d-three-grid.json")["cases"]
    co = load("det1d/finish1d-courant.json")["cases"]
    sf = [load(f"det1d/finish1d-shockframe-{g}.json")[0] for g in ("coarse", "medium")]
    sf_mean = {"coarse": -23.1, "medium": -22.7}  # 2-19 us mean lab-equivalent speed, bg STATUS / COST.md
    dx = lambda c: c["dx"] * 1e6
    series = [
        ("H2-air, hot driver, Co 0.4 (clipped at 3500 K)", [dx(c) for c in hot], [c["D_err_pct"] for c in hot], GRAY, "s", "--"),
        ("H2-air, matched ZND start, Co 0.1", [dx(c) for c in co[:2]], [c["D_err_pct"] for c in co[:2]], INK, "o", "-"),
        ("H2-air, matched ZND start, Co 0.05", [dx(co[2])], [co[2]["D_err_pct"]], INK, "D", ""),
        ("H2-air, shock-attached frame, Co 0.1 (2-19 µs mean)", [c["dx_um"] for c in sf], [sf_mean["coarse"], sf_mean["medium"]], GRAY, "v", ":"),
        ("2H2:O2:7Ar, matched ZND start, Co 0.1 (gate)", [dx(c) for c in ar7], [c["D_err_pct"] for c in ar7], ACCENT, "o", "-"),
    ]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.9), gridspec_kw={"width_ratios": [1.35, 1]})
    for ax in (a, b):
        ax.axhspan(-1, 1, color=LIGHT, lw=0, zorder=0)
        ax.axhline(0, color=INK, lw=0.6)
        ax.set_xscale("log", base=2)
        ax.set_xlabel("grid spacing Δx (µm), finer to the right")
        ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([1.1, 2.2, 4.4]))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FixedFormatter(["1.1", "2.2", "4.4"]))
        ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    for label, x, y, col, mk, ls in series:
        a.plot(x, y, ls=ls or "none", marker=mk, color=col, mfc="white" if col == GRAY else col, label=label)
    a.set_ylabel("lead-shock speed error vs D_CJ (%)")
    a.set_title("(a) every 1D configuration tried", loc="left")
    a.text(1.0, 2.2, "±1 % gate", fontsize=7, color=GRAY, ha="right")
    a.set_xlim(5.5, 0.95); a.set_ylim(-27, 20)
    fig.legend(*a.get_legend_handles_labels(), loc="lower center", ncol=2, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    c = ar7
    b.plot([dx(x) for x in c], [x["D_err_pct"] for x in c], marker="o", color=ACCENT)
    for x in c:
        b.annotate(f"{x['D_err_pct']:+.3f} %\n{x['cells']:,} cells", (dx(x), x["D_err_pct"]), xytext=(0, 9),
                   textcoords="offset points", ha="center", fontsize=7.5)
    b.set_ylim(-1.5, 1.5); b.set_xlim(6, 1.6)
    b.set_ylabel("speed error (%)")
    b.set_title("(b) 2H2:O2:7Ar gate, D_CJ 1691.12 m/s", loc="left")
    b.text(0.03, 0.06, "error falls with refinement;\nno step reaches 3500 K", transform=b.transAxes, fontsize=7.5, color=INK)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    save(fig, "fig1_speed_vs_grid")


# Fig. 2: 0D ignition, OpenFOAM-14 vs Cantera
def fig_ignition():
    import cantera_ignition as ci
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
    for ax, (name, T0, p0) in zip(axes, ci.CASES):
        row, (tf, Tf), (tc, Tc) = ci.compare(name, T0, p0)
        ax.plot(tc * 1e6, Tc, color=GRAY, lw=3.2, label="Cantera 3.2 (reference)")
        ax.plot(tf * 1e6, Tf, color=ACCENT, lw=1.2, label="OpenFOAM-14 multicomponentFluid")
        ax.axvline(row["of14_tau_us"], color=INK, lw=0.6, ls=":")
        ax.set_xlabel("time (µs)"); ax.set_ylabel("temperature (K)")
        ax.set_title(f"T0 {T0:.1f} K, p0 {p0/1e5:.0f} bar", loc="left")
        ax.text(0.97, 0.08, f"τ_ign OF14 {row['of14_tau_us']:.4f} µs\nCantera {row['cantera_tau_us']:.4f} µs\n"
                f"difference {row['tau_rel_diff_pct']:+.2f} %", transform=ax.transAxes, ha="right", fontsize=7.5)
        ax.set_xlim(0, tf[-1] * 1e6)
    axes[0].legend(loc="center right", fontsize=7)
    fig.tight_layout()
    save(fig, "fig2_ignition_0d")


# Fig. 3: x-t diagrams of temperature, stable argon wave vs decaying H2-air wave
def fig_xt():
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    cases = [("ar7-coarse", "2h2-o2-7ar-1atm", "(a) 2H2:O2:7Ar, 4.4 µm: steady"),
             ("h2air-co01-medium", "h2air-phi1-1atm-300K", "(b) H2-air, 2.2 µm: decays")]
    cmap = matplotlib.colormaps["Greys"].copy(); cmap.set_bad("#cfdcef")
    for ax, (tag, mix, title) in zip(axes, cases):
        d = np.load(DATA / f"det1d/xt-{tag}.npz")
        t, x, T = d["t_s"] * 1e6, d["x_m"] * 1e3, d["T_k"].astype(float)
        im = ax.pcolormesh(x, t, T, cmap=cmap, vmin=300, vmax=3300, shading="auto", rasterized=True)
        dcj = float(b1(mix)["d_cj"])
        # CJ trajectory through the lead shock at the first sample with a shock past 10 mm
        p = d["p_pa"]
        xs = np.array([x[np.nonzero(row > 2e5)[0].max()] if (row > 2e5).any() else np.nan for row in p])
        k = int(np.nanargmin(np.abs(xs - 10.0)))
        tt = np.linspace(t[0], t[-1], 2)
        ax.plot(xs[k] + dcj * (tt - t[k]) * 1e-3, tt, color=ACCENT, lw=1.0, ls="--", label=f"D_CJ = {dcj:.0f} m/s")
        ax.set_xlim(0, 25); ax.set_ylim(t[0], t[-1])
        ax.set_xlabel("x (mm)"); ax.set_title(title, loc="left")
        ax.legend(loc="upper left", fontsize=7, frameon=True, facecolor="white", edgecolor="white", framealpha=1)
        ax.grid(False)
    axes[0].set_ylabel("time (µs)")
    cb = fig.colorbar(im, ax=axes, shrink=0.9, pad=0.02)
    cb.set_label("temperature (K)")
    save(fig, "fig3_xt_temperature")


# Fig. 4: local lead-shock speed from neighbouring probe arrivals
def fig_local_speed():
    import speed_fit as sf
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    styles = {"ar7-coarse": (ACCENT, "-", "o"), "ar7-medium": (ACCENT, "--", "s"),
              "h2air-co01-coarse": (INK, "-", "o"), "h2air-co01-medium": (INK, "--", "s")}
    names = {"ar7-coarse": "2H2:O2:7Ar, 4.4 µm", "ar7-medium": "2H2:O2:7Ar, 2.2 µm",
             "h2air-co01-coarse": "H2-air, 4.4 µm", "h2air-co01-medium": "H2-air, 2.2 µm"}
    for tag, (col, ls, mk) in styles.items():
        x, ta = sf.arrivals(DATA / f"det1d/probes-{tag}.npz", x_min=0.0051)
        v = np.diff(x) / np.diff(ta)
        dcj = sf.d_cj(sf.MIXTURE[tag.split("-")[0]])
        xm = 0.5 * (x[1:] + x[:-1]) * 1e3
        v2 = np.convolve(v, np.ones(2) / 2, mode="valid")  # pairs of intervals, as finish1d_speed.py prints
        ax.plot(xm[1:], v2 / dcj, color=col, ls=ls, marker=mk, ms=3, mfc="white", label=names[tag])
    ax.axhspan(0.99, 1.01, color=LIGHT, lw=0)
    ax.axhline(1, color=INK, lw=0.6)
    ax.axvline(10, color=GRAY, lw=0.6, ls=":"); ax.text(10.2, 1.2, "fit window starts", fontsize=7, color=GRAY)
    ax.set_xlabel("lead-shock position x (mm)"); ax.set_ylabel("local speed / D_CJ")
    ax.legend(ncol=2, loc="lower left", fontsize=7)
    fig.tight_layout()
    save(fig, "fig4_local_speed")


# Fig. 5: Sod against the exact Riemann solution
def sod_exact(x, t, g=1.4, cp=1004.5, pL=1e5, TL=348.432, pR=1e4, TR=278.746):
    R = cp * (g - 1) / g
    rL, rR = pL / (R * TL), pR / (R * TR)
    aL, aR = math.sqrt(g * pL / rL), math.sqrt(g * pR / rR)

    def f(p, pk, rk, ak):
        if p > pk:
            A, B = 2 / ((g + 1) * rk), (g - 1) / (g + 1) * pk
            return (p - pk) * math.sqrt(A / (p + B))
        return 2 * ak / (g - 1) * ((p / pk) ** ((g - 1) / (2 * g)) - 1)
    lo, hi = 1e-9, 10 * pL
    for _ in range(200):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if f(m, pL, rL, aL) + f(m, pR, rR, aR) < 0 else (lo, m)
    ps = 0.5 * (lo + hi)
    us = 0.5 * (f(ps, pR, rR, aR) - f(ps, pL, rL, aL))
    rsL = rL * (ps / pL) ** (1 / g)
    rsR = rR * ((ps / pR + (g - 1) / (g + 1)) / ((g - 1) / (g + 1) * ps / pR + 1))
    asL = math.sqrt(g * ps / rsL)
    S = us * rsR / (rsR - rR)
    p, u, r = np.empty_like(x), np.empty_like(x), np.empty_like(x)
    for i, xi in enumerate(x):
        s = xi / t
        if s < -aL:
            p[i], u[i], r[i] = pL, 0, rL
        elif s < us - asL:
            u[i] = 2 / (g + 1) * (aL + s); a = aL - (g - 1) / 2 * u[i]
            r[i] = rL * (a / aL) ** (2 / (g - 1)); p[i] = pL * (a / aL) ** (2 * g / (g - 1))
        elif s < us:
            p[i], u[i], r[i] = ps, us, rsL
        elif s < S:
            p[i], u[i], r[i] = ps, us, rsR
        else:
            p[i], u[i], r[i] = pR, 0, rR
    return p, u, p / (r * R)


def fig_sod():
    t = 0.0063246
    xe = np.linspace(-5, 5, 4001)
    pe, ue, Te = sod_exact(xe, t)
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5))
    for n, col, ls in [(250, GRAY, "-"), (1000, ACCENT, "-")]:
        a = np.loadtxt(DATA / f"sod/profile-n{n}.xy", comments="#")
        for ax, k, scale in zip(axes, (3, 2, 1), (1e-3, 1, 1)):
            ax.plot(a[:, 0], a[:, k] * scale, color=col, lw=1.0, ls=ls, label=f"OpenFOAM-14, {n:,} cells")
    for ax, y, lab in zip(axes, (pe * 1e-3, ue, Te), ("pressure (kPa)", "velocity (m/s)", "temperature (K)")):
        ax.plot(xe, y, color=INK, lw=0.8, ls="--", label="exact Riemann solution")
        ax.set_xlabel("x (m)"); ax.set_ylabel(lab)
    axes[0].legend(fontsize=6.5, loc="lower left")
    chk = load("sod/sod-check.json")["cases"]
    c1000 = next(c for c in chk if c["cells"] == 1000)
    axes[2].text(0.02, 0.96, f"1,000 cells, Co 0.2:\nfan tail off by {c1000['dev_cells']['fan_tail']:.2f} cells\n(limit 1 cell: FAIL)",
                 transform=axes[2].transAxes, va="top", fontsize=6.5)
    fig.tight_layout()
    save(fig, "fig5_sod")


# Fig. 6: measured cost and run core-hours
def fig_cost():
    rows = list(csv.DictReader(open(DATA / "cost/b5-of14-cost.csv")))
    short = []
    for r in rows:
        case = r["case"]
        lab = ("2H2:O2:7Ar " if "7Ar" in case else "H2-air " if "H2-air" in case else "") + \
              ("strip " if "strip" in case else "") + ("shock frame " if "shock-attached" in case else "")
        if "multicomponentFluid" in case:
            lab = "multicomponentFluid H2-air "
        co = "Co 0.05" if "Co 0.05" in case else "Co 0.1" if ("Co 0.1" in case or "7Ar" in case or "shock-attached" in case) else "Co 0.4"
        if "90 atm" in case or ("H2-air 1D, vanLeer" in case and "grid" in case):
            lab += "hot driver, "
        lab = f"{lab}{int(r['cells']):,} cells, " + ("" if "strip" in case else f"{co}, ") + f"{r['host']}, {r['ranks']} ranks"
        core_h = float(r["wall_s"]) * int(r["ranks"]) / 3600
        short.append((lab, float(r["c_core_us_per_cell_step"]), core_h, "7Ar" in case))
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 4.0), sharey=True)
    y = np.arange(len(short))[::-1]
    a.axvspan(129, 344, color=LIGHT, lw=0)
    a.text(236, y[len(y) // 2], "literature band\n129-344", ha="center", va="center", fontsize=7, color=GRAY)
    a.axvline(200, color=GRAY, lw=0.8, ls="--"); a.text(203, y[0] + 0.6, "planning value 200", fontsize=7, color=GRAY)
    for yi, (lab, c, h, gate) in zip(y, short):
        col = ACCENT if gate else INK
        a.barh(yi, c, height=0.6, color=col)
        a.text(c + 4, yi, f"{c:.1f}", va="center", fontsize=7)
        b.barh(yi, h, height=0.6, color=col)
        b.text(h + 0.05, yi, f"{h:.2f}", va="center", fontsize=7)
    a.set_yticks(y); a.set_yticklabels([s[0] for s in short], fontsize=7)
    a.set_xlabel("c (core-µs per cell-step, wall based)"); a.set_xlim(0, 360)
    b.set_xlabel("run cost (core-hours)")
    a.set_title("(a) measured cost per cell-step", loc="left"); b.set_title("(b) cost of each B5 run", loc="left")
    a.grid(axis="y", visible=False); b.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, "fig6_cost")


# Fig. 7: the 3500 K clip, Courant 0.4 vs 0.1
def fig_courant():
    rows = list(csv.DictReader((l for l in open(DATA / "det1d/courant-fix-Tmax.csv") if not l.startswith("#"))))
    fig, ax = plt.subplots(figsize=(5.6, 2.6))
    for tag, col, mk, lab in [("co04", GRAY, "s", "maxCo 0.4 (before)"), ("co01", ACCENT, "o", "maxCo 0.1 (after)")]:
        r = [x for x in rows if x["case"] == tag]
        t = np.array([float(x["t_us"]) for x in r]); T = np.array([float(x["Tmax_K"]) for x in r])
        ax.plot(t, T, color=col, marker=mk, ms=2.5, lw=1.0, label=lab)
    ax.axhline(3500, color=INK, lw=0.6, ls="--")
    ax.text(0.2, 3512, "3500 K: upper limit of the NASA7 polynomials (JANAF clamp)", fontsize=7)
    ax.set_ylim(2800, 3600)
    ax.set_xlabel("time (µs)"); ax.set_ylabel("max temperature on the line (K)")
    ax.set_title("H2-air, matched ZND start, 5,682 cells, vanLeer", loc="left")
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    save(fig, "fig7_courant_clip")


# Fig. 8: surrogate shakedown: overfit gate and the one wave-count result
def fig_surrogates():
    gate = {}
    for p in sorted((DATA / "surrogates/overfit-gate").glob("*.json")):
        d = json.load(open(p))
        gate[p.stem] = (d["overfit_loss"], d["max_loss"], d["passed"])
    order = ["fno1d-rdejl", "fno-planardet-full", "transolver-planardet-pool2", "transolver-points-planardet-pool2",
             "mgn-planardet-pool2", "fno-rde72-smoke"]
    labels = {"fno1d-rdejl": "FNO-1D, RDE.jl rings", "fno-planardet-full": "FNO (full resolution), PlanarDet",
              "transolver-planardet-pool2": "Transolver (grid), PlanarDet",
              "transolver-points-planardet-pool2": "Transolver (points), PlanarDet",
              "mgn-planardet-pool2": "MeshGraphNet, PlanarDet", "fno-rde72-smoke": "FNO, RDE-72 (zero fields; smoke)"}
    order = [o for o in order if o in gate]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 2.8), gridspec_kw={"width_ratios": [1.6, 1]})
    y = np.arange(len(order))[::-1]
    for yi, k in zip(y, order):
        loss, mx, ok = gate[k]
        a.plot([loss], [yi], marker="o" if ok else "X", ms=7, color=ACCENT if ok else INK, ls="none")
        a.plot([mx, mx], [yi - 0.35, yi + 0.35], color=GRAY, lw=1.2)
        a.text(loss * 2.2, yi, f"{loss:.3g} {'pass' if ok else 'FAIL'}", va="center", fontsize=7)
    a.set_xscale("log"); a.set_yticks(y); a.set_yticklabels([labels[k] for k in order], fontsize=7)
    a.set_xlabel("overfit loss on one batch (grey tick: gate threshold)")
    a.set_title("(a) overfit sanity gate", loc="left"); a.grid(axis="y", visible=False)
    a.set_xlim(5e-3, 1e8)
    m = load("surrogates/fno1d-rdejl.metrics.json")["per_seed"]["11"]
    vals = [m["val"]["wave_count_acc"] * 100, m["test"]["wave_count_acc"] * 100]
    b.plot([0, 1], vals, ls="none", marker="o", ms=8, color=ACCENT)
    for i, v in enumerate(vals):
        b.text(i, v + 0.5, f"{v:.2f} %", ha="center", fontsize=7.5)
    b.set_xticks([0, 1]); b.set_xticklabels([f"val ({m['val']['n_runs']} runs)", f"test ({m['test']['n_runs']} runs)"], fontsize=7.5)
    b.set_xlim(-0.6, 1.6); b.set_ylim(94, 101); b.set_ylabel("wave-count accuracy at 100 steps (%)")
    b.text(0.5, 94.6, "axis starts at 94 %", ha="center", fontsize=6.5, color=GRAY)
    b.set_title("(b) FNO-1D on RDE.jl (smoke test)", loc="left")
    fig.tight_layout()
    save(fig, "fig8_surrogates")


if __name__ == "__main__":
    fig_speed_vs_grid(); fig_ignition(); fig_xt(); fig_local_speed(); fig_sod(); fig_cost(); fig_courant(); fig_surrogates()
