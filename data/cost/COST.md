# Measured solver cost on mini and pc, next to the literature band

Metric (12 §1, B2): c = core-µs per cell-step. "c_loop" excludes initialisation and MPI start-up (solver
ExecutionTime between the first and last step); "c" is plain wall time. Raw lines: `b2-esi/bench.jsonl`,
`b5-of14/bench.jsonl`. Planning value in 12 §1: c = 200 for detonationFluid.

## Literature band (validation-matrix §5)
- OpenFOAM density-based, detailed chemistry (Wen 2025 detonationFoam 129-192; Sankar 2024 rhoCentral-class 330-344
  ASSUMED steps): 129-344. Production LES codes 26-34. Kwak multicomponentFluid 59-632 (Δt not reported, not used).
- Per simulated µs at RDE resolution (Δx 60-100 µm): ≈ 3e4 core-µs per cell per sim-µs (Sato, Bao, Farcas, Kwak).

## Measured: non-reacting explicit KNP (ESI 2512 rhoCentralFoam), serial c_loop
| host | shockTube 100k cells | forwardStep 64,512 cells |
|---|---|---|
| mini (clean) | 0.20 | 0.38 |
| mini (during an OpenFOAM build) | 0.26 | 0.51 |
| pc | 0.34 | 0.64 |
pc/mini ≈ 1.9 per core; a build on mini costs ≈ 1.35×.

## Measured: OpenFOAM-14 (B5)

| host | solver / case | cells | ranks | steps | wall s | c | c_loop |
|---|---|---:|---:|---:|---:|---:|---:|
| mini | detonationFluid, H2-air 1D, 90 atm driver, vanLeer, Co 0.4 | 5,682 | 8 | 13,269 | 251.043 | 26.638 | 26.040 |
| mini | detonationFluid, H2-air 1D, vanLeer, medium grid | 11,364 | 8 | 26,954 | 1,174.42 | 30.673 | 27.720 |
| mini | detonationFluid, H2-air 1D, vanLeer, fine grid | 22,727 | 8 | 55,849 | 3,833.62 | 24.163 | 24.079 |
| pc | detonationFluid, H2-air 1D, 90 atm driver, vanLeer, Co 0.4 | 5,682 | 4 | 13,273 | 875.784 | 46.450 | 45.932 |
| mini | multicomponentFluid, H2-air 1D, Euler/upwind Co 0.1, laminar | 5,682 | 8 | 37,343 | 858.39 | 32.364 | 31.777 |
| mini | detonationFluid, reacting symmetry-wall strip, 0.25 mm | 5,000 | 8 | 305 | 9.206 | 48.295 | 29.603 |
| mini | detonationFluid, reacting symmetry-wall strip, 0.125 mm | 20,000 | 8 | 305 | 27.323 | 35.833 | 30.804 |
| mini | detonationFluid, H2-air 1D CJ/ZND-matched, vanLeer, Co 0.1 (2026-11-16) | 5,682 | 4 | 35,556 | 1,579.92 | 31.281 | 31.102 |
| mini | detonationFluid, H2-air 1D CJ/ZND-matched, vanLeer, Co 0.1, medium (2026-11-16) | 11,364 | 4 | 71,962 | 4,179.56 | 20.444 | 20.364 |
| mini | detonationFluid, H2-air 1D CJ/ZND-matched, vanLeer, Co 0.05 (2026-11-16) | 5,682 | 4 | 70,388 | 2,187.66 | 21.880 | 21.765 |
| mini | detonationFluid, H2-air 1D shock-attached frame, vanLeer, Co 0.1, 2.2 µm (2026-11-16) | 9,091 | 4 | 317,643 | 14,628 | 20.263 | 20.173 |
| mini | detonationFluid, H2-air 1D shock-attached frame, vanLeer, Co 0.1, 4.4 µm (2026-11-16) | 4,545 | 4 | 92,096 | 2,259 | 21.588 | 21.512 |
| mini | detonationFluid, 2H2:O2:7Ar 1D CJ/ZND-matched, vanLeer, Co 0.1 (2026-11-16, gate) | 5,682 | 4 | 32,990 | 1,038.74 | 22.166 | 22.010 |
| mini | detonationFluid, 2H2:O2:7Ar 1D CJ/ZND-matched, vanLeer, Co 0.1, medium (2026-11-16, gate) | 11,364 | 4 | 67,324 | 4,035.28 | 21.098 | 20.938 |

2026-11-16 (finish-1d): settled 1D configuration is detonationFluid Kurganov/vanLeer at maxCo 0.1 (fork tutorial
value; 0.4 is outside forward-Euler MUSCL stability and clipped at 3500 K). Its measured c on mini at 4 ranks is
20.4-21.9 core-µs per cell-step with the machine otherwise quiet; the 31.3 coarse Co 0.1 row shared mini with an
8-rank multicomponentFluid run. Versus the earlier 8-rank Co 0.4 rows (24.2-30.7) this is a delta of about -3 to -9
per cell-step, but each step is 4× shorter, so a 1D tube costs about 4× more wall per simulated µs. The fine grid at
Co 0.1 needs ~3.2e9 cell-steps (~28 core-h). None of these runs qualifies the physics (see summary).
The two shock-frame rows (stopped by hand when the flame reached the outflow; wall from the solver ClockTime)
confirm the settled c ≈ 20-22 at 4 ranks; the shock frame needs ~14k steps per simulated µs at 2.2 µm.

These are measured core-µs per cell-step, not validated production physics. The recovered case reaches
the shock stop but remains overdriven: probe-fit speed 2320.3 m/s versus Burke CJ 1975.2 m/s (+17.47%).
The solver also reports JANAF out-of-range temperatures and caps T at 3500 K. The original graph sampler
missed portions of the decomposed 1D line; reconstructed full-mesh fields now exist at 9.5 µs. Cantera
thermicity peaks only two cells (8.80 µm) behind the measured shock versus the 199.37 µm ZND CJ length;
this overdriven, clipped, poorly resolved transient fails that comparison, not a qualified CJ result.
Three-grid speeds are 2320.30, 2241.04 and 2179.62 m/s in increasing resolution. The error decreases
monotonically but the finest remains +10.35% versus CJ, failing the unchanged 1% gate; see `b5-of14/det1d-three-grid.json`.
pc and mini had different rank counts, so their ratio 1.74 for this case combines hardware and MPI scaling;
the pc solve ran before GPU training. The two strip cases use a hot tube driver and symmetry walls, not RDE
injection or periodic boundaries; their five-microsecond timing is a cost probe, not scientific qualification.
Medium-grid timing is recovered from `time.txt` (solver only, no reconstruction); the wrapper failed
after solver exit 0 because its script was edited while running. A concurrent CLI build affected ~25 s.
The multicomponentFluid run experienced swap and a concurrent build; laminar transport differs from the
inviscid detonationFluid reference, so neither the timing nor speed is a solver-only comparison.
The measured value is substantially below the planning 200 but should not replace it for a 2D RDE campaign
until the full-channel timing and scientific qualification are available.

The actual W4 periodic 125×240 full-channel case failed after 14.646 s, before a meaningful timing: the
solver produced grossly out-of-range temperatures (including negative millions of kelvin) before an FPE in
`totalPressure`/`dynamicPressure` `pow`. `channel/Run99999/case/log.solver` and `RUNS.tsv` retain the evidence.
The initiating physical/numerical instability is not established, and no stable wave count is claimed.

## B5/B6 qualification summary

| Criterion | Result and evidence |
|---|---|
| B5 Sod, shockFluid | **FAIL**: at 1,000 cells fan-tail error 1.31 cells (Co 0.2) or 1.13 (Co 0.1), versus one-cell limit; density L1 order passes. `b5-of14/sod-check-co*.json` and `RUNS.tsv`. |
| B5 1D CJ gate, 2H2:O2:7Ar 1 atm 300 K (Colin 2026-11-16) | **PASS**: D_CJ 1691.12 m/s (Burke); coarse 1696.14 (+0.296%), medium 1695.72 (+0.272%), 1% on both grids, error decreasing, zero steps at 3500 K (Tmax 3164/3201 K). Co 0.1, vanLeer, 4 ranks. `b5-of14/finish1d-ar7.json`. |
| B5 H2-air 1D (known-unstable case, not a gate) | Recorded, not gated: known-unstable, fails to −23% (grid-converged in the shock frame). History: Hot-driver tubes +17.47/+13.46/+10.35% and clipped (`b5-of14/det1d-three-grid.json`). Matched CJ/ZND start at Co 0.1: coarse +1.08%, medium −21.27%, both unclipped; coarse at Co 0.05 −3.43%; fine not run at stable Co. Speeds are not converged in Courant number or grid: once dissipation is low (medium Co 0.1, coarse Co 0.05, multicomponentFluid fine) the front overdrives +20% at start-up then fails or gallops (post-shock T ≈ 1000 K, flame 2-4 mm behind). Mechanism kinetics (0D OF14 vs Cantera ≤ 0.15%) and ODE tolerance (no effect) excluded. `b5-of14/finish1d-courant.json`. Shock-attached frame (Co 0.1): the wave fails on both grids without completing a cycle; mean lab-equivalent speed 2-19 µs 1519.6 / 1526.2 m/s (−23.1 / −22.7%, two grids within 0.4%), unclipped. `b5-of14/finish1d-shockframe-*.json`. |
| B5 multicomponentFluid | Completed diagnostic: 2270.28 m/s, +14.94% CJ; no induction result; laminar vs inviscid comparison and build overlap qualify timing. `b5-of14/multicomponent-upwind-result.json`. Inviscid matched-CJ start (Co 0.1): 1996.41/1992.44/1616.83 m/s, unclipped; the fine front decays like detonationFluid medium Co 0.1 (within ~2-3% per probe); seulex tolerance 1e-6/1e-3 → 1e-10/1e-8 changes nothing (|ΔT| ≤ 0.07 K to 4 µs). |
| B5 double Mach reflection | **FAIL / incomplete**: both 240 grids fail with sqrt FPE in `shockFluid::fluxPredictor`; coarse ridge diagnostics invalid, 480 grid not run, no triple-point GCI/reference comparison. Origin of invalid state not established. `b5-of14/DMR.md`. |
| B5 strip and full channel | Two five-µs reacting symmetry-strip timings measured above. W4 periodic full channel failed on an FPE after nonphysical temperatures; no defensible full-channel cost or stable wave count. |
| B6 topology, mapping, restart | Fork utility passed slab/localized/wedge cycles and integral relative tolerance 2e-10; fully-coarsened utility restart passed and re-refined. Actual coupled reacting solver correctly refused an active-split restart; fully-coarsened coupled restart not shown. `b6-refiner/reacting-evidence.md`. |
| B6 Sod AMR | **Provisional**, not a measured GCI: three solvers completed, AMR errors inside assumed-order two-grid band; checkMesh reports 16 severely nonorthogonal faces, maximum 82.405°. |
| B6 reacting ZND / Kwak RDE | **Not qualified**: reacting AMR stopped at 3.6/10 µs with clipping; unqualified B5 CJ baseline prevents ZND comparison. Kwak matched uniform/AMR, chemistry-weighted redistribution and required long-time comparison unrun; installed build lacks Zoltan and reversible mode refuses redistribution. |

These are documented failures and incomplete scientific criteria, not waived tolerances or production
qualification. Any qualified acceptance is an explicit decision, separate from the numerical results.
