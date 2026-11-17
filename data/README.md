# data/: the evidence behind every number in the report

Small files only, copied by name from the project's run folders and records (an allowlist, never a whole folder).
Absolute paths were rewritten to `bg/...` (the background-solve folder) or removed. Fields of the multi-GB runs are not
here; what is here is enough to regenerate every figure and to rerun the speed evaluation.

| Path | What it is | Produced by |
|---|---|---|
| `b1/refs-subset.csv` | CJ, von Neumann and ZND reference states (SDToolbox on Cantera) for H2-air φ=1 and 2H2:O2:7Ar, 1 atm, 300 K, Burke 2012 and Mével 2017 mechanisms | B1 reference calculation |
| `chem0d/of14-*-T.dat` | OpenFOAM-14 0D constant-pressure ignition: temperature history at the von Neumann state (1538.8 K, 28 bar) and at 1300 K / 20 bar | B5 `chem0d` runs |
| `det1d/finish1d-ar7.json` | **The 1D CJ gate**: 2H2:O2:7Ar on two grids, speed fit, per-step Tmax, pass flags | `finish1d_eval.py` |
| `det1d/finish1d-courant.json` | H2-air at Courant 0.1 and 0.05 after the clip fix (coarse +1.08 %, medium -21.27 %, coarse Co 0.05 -3.43 %) | `finish1d_eval.py` |
| `det1d/finish1d-shockframe-*.json` | H2-air in the shock-attached frame: the wave fails on both grids | `finish1d_shockframe.py` |
| `det1d/det1d-three-grid.json` | H2-air hot-driver tube at Courant 0.4, three grids (+17.47/+13.46/+10.35 %, clipped at 3500 K): the "before" | `det1d_check.py` |
| `det1d/multicomponent-inviscid-three-grid.json` | the same tube on OpenFOAM's pressure-based `multicomponentFluid` | `det1d_check.py` |
| `det1d/probes-*.npz` | raw probe pressure traces (49 stations, every 0.5 mm, sampled every ~1 ns): `x_m`, `t_s`, `p_pa` | detonationFluid `probes` |
| `det1d/xt-*.npz` | line samples of p and T every 0.1 µs, interpolated to a common 3,126-point grid (T in float16): `t_s`, `x_m`, `p_pa`, `T_k` | detonationFluid `graph` |
| `sod/profile-n*.xy` | Sod final-time profiles (x, T, \|U\|, p) on 250-4,000 cells | OpenFOAM-14 `shockFluid` |
| `sod/sod-check*.json` | Sod against the exact Riemann solution at Co 0.2 and 0.1 | `sod_check.py` |
| `cost/COST.md`, `cost/b5-of14-cost.csv`, `cost/b5-bench.jsonl` | measured cost c (core-µs per cell-step) for every B5 solve, beside the literature band | bg session |
| `runs/RUNS.tsv` | one line per background run (61 runs, 2026-11-15/16): work package, run, host, status, wall s, summary | bg session |
| `runs/eggs/Run*.run.yaml` | run records from the eggs ledger: Run00005/06 committed from mini pods; Run00010/11 the staged acceptance cases | skuld2 |
| `surrogates/*.metrics.json`, `*.model.toml` | surrogate registry rows (FNO on RDE.jl and REALM PlanarDet, Transolver, literature classifier) | `skuld2 surrogate record` |
| `surrogates/overfit-gate/*.json` | the overfit sanity gate per model (FNO passes; Transolver and MeshGraphNet fail) | skuld2 training |
| `agent/TIMELINE-2026-11-16.md` | the agent loop for the two acceptance campaigns, card to pod, with sources | Odin journal, ledger, eggs |
| `agent/approvals-skuld2-campaign.tsv` | every skuld2 campaign approval card: raised, expired, decided, consumed | Odin approval ledger |
| `agent/incidents-seats-2026-11-16.tsv` | every incident Kubert and Mimir raised that day, with severity and whether it paged | Odin journal |
| `agent/pod-logs-2026-11-17.txt` | logs of the two acceptance pods Kubert launched | `kubectl logs` |

Run folder names inside the JSON (`runs/znd/...`) refer to the original run tree, kept on the project's workstation
(about 19 GB); they are not in this repository.
