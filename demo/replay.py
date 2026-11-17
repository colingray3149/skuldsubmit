"""Replay one validation run end to end from the data in this repository (no OpenFOAM needed, ~5 s).

The run: the B5 1D CJ gate case, 2H2:O2:7Ar at 1 atm and 300 K on detonationFluid (5,682 cells, Courant 0.1),
and its chemistry check. Steps, each from stored evidence:
  1. reference: D_CJ and the ZND induction length from the B1 row (SDToolbox on Cantera, Burke 2012);
  2. chemistry: rerun Cantera's 0D ignition and compare with the stored OpenFOAM-14 histories (gate 2 %);
  3. solve record: the run's line in RUNS.tsv and its measured cost in COST;
  4. evaluation: fit the lead-shock speed from the raw probe traces and apply the unchanged 1 % gate on both grids;
  5. the counter-case: the same evaluation on stoichiometric H2-air (known-unstable), which must not pass.
Usage: python demo/replay.py
"""
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code/chem0d"))
sys.path.insert(0, str(ROOT / "code/det1d"))
import cantera_ignition as ci  # noqa: E402
import speed_fit as sf  # noqa: E402


def rule(title):
    print(f"\n== {title}")


rule("1. reference (B1, SDToolbox CJspeed + zndsolve on Burke 2012)")
for r in csv.DictReader(open(ROOT / "data/b1/refs-subset.csv")):
    if r["mech"] == "Burke2012.yaml":
        print(f"  {r['id']:22s} D_CJ {float(r['d_cj']):8.2f} m/s   p_vN {float(r['p_vn'])/1e5:6.2f} bar   "
              f"T_vN {float(r['t_vn']):7.1f} K   L_ind {float(r['l_ind'])*1e6:7.2f} um")

rule("2. chemistry: OpenFOAM-14 0D ignition vs Cantera 3.2 (same mechanism; gate |diff| <= 2 %)")
for row in ci.main():
    ok = abs(row["tau_rel_diff_pct"]) <= 2.0
    print(f"  -> {row['case']}: {'PASS' if ok else 'FAIL'}")

rule("3. the solve (RUNS.tsv line and measured cost)")
for line in open(ROOT / "data/runs/RUNS.tsv"):
    if "znd-ar7" in line:
        utc, wp, run, host, status, wall, summary = line.rstrip("\n").split("\t")
        print(f"  {utc} {run:16s} {host} {status} wall {float(wall)/60:5.1f} min")
for r in csv.DictReader(open(ROOT / "data/cost/b5-of14-cost.csv")):
    if "7Ar" in r["case"]:
        core_h = float(r["wall_s"]) * int(r["ranks"]) / 3600
        print(f"  {int(r['cells']):6,d} cells  {int(r['steps']):6,d} steps  {r['ranks']} ranks  "
              f"c = {float(r['c_core_us_per_cell_step']):.1f} core-us/cell-step  {core_h:.2f} core-h")

rule("4. evaluation: lead-shock speed from 29 probes (x >= 10 mm), gate |D/D_CJ - 1| <= 1 % on both grids")
gate = [sf.fit(ROOT / f"data/det1d/probes-ar7-{g}.npz") for g in ("coarse", "medium")]
for r in gate:
    print(f"  {r['case']:12s} D {r['D']:8.2f} m/s  error {r['D_err_pct']:+.3f} %  "
          f"(first/second half {r['D_first_half']:.1f}/{r['D_second_half']:.1f})  {'PASS' if r['gate_within_1pct'] else 'FAIL'}")
falls = abs(gate[1]["D_err_pct"]) < abs(gate[0]["D_err_pct"])
print(f"  error falls with refinement: {falls}")
print(f"  1D CJ gate on 2H2:O2:7Ar: {'PASS' if all(r['gate_within_1pct'] for r in gate) and falls else 'FAIL'}")

rule("5. counter-case: stoichiometric H2-air, same method (recorded known-unstable, not a gate)")
for g in ("coarse", "medium"):
    r = sf.fit(ROOT / f"data/det1d/probes-h2air-co01-{g}.npz")
    print(f"  {r['case']:18s} D {r['D']:8.2f} m/s  error {r['D_err_pct']:+.3f} %  "
          f"(halves {r['D_first_half']:.1f} -> {r['D_second_half']:.1f})  {'PASS' if r['gate_within_1pct'] else 'FAIL'}")
print("  the coarse grid's +1.08 % is held up by numerical dissipation; refined, the front decays (-21 %).")
print("  The evaluator does not tune until it passes: the gate moved to a stable mixture by the owner's decision,")
print("  with the criterion unchanged, and H2-air stays recorded as a failure.")
