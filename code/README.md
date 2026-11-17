# code/: curated excerpts and runnable pieces

Every file starts with a header naming where it comes from and what it shows. Runnable here (Python 3.13 with
`requirements.txt`, no OpenFOAM needed):

| Command | What it does | Time |
|---|---|---|
| `python code/chem0d/cantera_ignition.py` | Cantera 0D ignition on Burke 2012 vs the stored OpenFOAM-14 histories (+0.15 %, -0.08 %) | ~3 s |
| `python code/det1d/speed_fit.py data/det1d/probes-*.npz` | lead-shock speed fit from the raw probe traces, against B1 D_CJ, with the 1 % gate | ~2 s |

The rest are the scripts and case files that produced the data; they need the project's run environment.

| Folder | Contents | Origin |
|---|---|---|
| `chem0d/` | the OpenFOAM-14 0D case at the von Neumann state, the original comparison script, the runnable one | background solves (B5) |
| `det1d/` | `znd_init.py` (matched CJ/ZND start), `det1d_check.py` / `finish1d_eval.py` (speed fit and gate), `finish1d_speed.py`, `finish1d_shockframe.py`, `sod_check.py`, `znd-run.sh`, every tunable in `b5.conf` / `znd.conf` / `ar7-*.conf` | background solves (B5) |
| `openfoam/sod-n1000/` | Sod tube on `shockFluid`, 1,000 cells, as run | OpenFOAM-14 tutorial `shockTube`, dimensional Sod |
| `openfoam/znd-2h2-o2-7ar-n5682/` | the 2H2:O2:7Ar gate case on `detonationFluid` (Kurganov flux, vanLeer, Courant 0.1), `constant/foam/` holds the converted Burke 2012 mechanism | B5 |
| `mechanism/` | `Burke2012.yaml` (Cantera format) with SDToolbox's licence | SDToolbox data directory |
| `skuld2/` | the campaign TOML (`postdeploy-znd`, `p0-znd`), the run-card schema (`schema/run.toml`), the `znd-1d` case template, the pod telemetry contract (`odin.rs`) and in-pod supervisor (`supervisor.rs`), the run record (`run.rs`) | skuld2, the simulation harness (private repo) |
| `odin/` | one seat declaration (`seat-kubert.toml`, `[personal]` lines removed) and two pieces of the supervision interface: the child report wake and the steer cap | Odin, the agent harness (public mirror: github.com/colingray3149/odin2) |

## Running the OpenFOAM part

Needs OpenFOAM-14 (Foundation, `OpenFOAM/OpenFOAM-14` at `64cfdf54`) with the `detonationFluid` module from
`TXChris/detonationFoam-OF14` (branch `OF-14`, `09c9bfcd`), Cantera 3 and SDToolbox for `znd_init.py`.

```sh
# Sod (seconds, 1 core)
cd code/openfoam/sod-n1000 && blockMesh && foamRun && foamPostProcess -func graphCell -latestTime
python ../../det1d/sod_check.py 0.0063246 .           # wave positions vs the exact Riemann solution

# 2H2:O2:7Ar ZND tube, 5,682 cells (about 17 min wall on 4 ranks; c ~ 22 core-us per cell-step)
cd code/openfoam/znd-2h2-o2-7ar-n5682
blockMesh
python ../../det1d/znd_init.py ...                    # writes 0/ from the CJ/ZND profile; see znd-run.sh for arguments
decomposePar && mpirun -np 4 foamRun -parallel
# then: python ../../det1d/finish1d_eval.py <case>     (env from b5.conf + ar7-b5.conf)
```

`znd-run.sh` is the exact sequence used (it also sources the configuration files and writes the `RUNS.tsv` line).
