# Running log: weeks 5-6 (2026-11-02 to 2026-11-17)

Dates are UTC. Sources: the project's work briefs and their STATUS sections, `data/runs/RUNS.tsv`, the eggs ledger,
the Odin journal, and the commit histories of the harness (Odin) and the simulation harness (skuld2). Activity: 848
commits to Odin between 11-02 and 11-16, 174 to skuld2 (including its predecessor, from 11-05), 193 to the plan.

## 2026-11-02 / 03: the Lab 2 study
- 21 research-pod runs from one seat: 14 delivered in 7-16 min, 7 ran to the 60-minute wall. Three failure causes:
  idle churn, carrier loss, egress block (Lab 2 report).
- Next steps promised: a progress heartbeat, release gated on an export read, a timeout from data.

## 2026-11-05 / 06: supervision fixes from the study
- Pods get their whole brief, declarable run limits, a context checkpoint at 70 % of the window and a rollover
  instead of a failure; partial delivery.
- Carrier loss: a pod's node is read from its live pod, so its export is found after the Job is gone; cancelled
  runs settle without node reads; an automatic restart no longer leaves an agent pod empty.
- Pod reviews reach their launcher and raise one cluster incident (Kubert as supervisor of pods).
- Skuld Mark One, the first simulation harness (run record, eggs ledger, monitor/judge roles): first commits.

## 2026-11-07 to 12: quieter week
- 44 Odin commits in six days: pod follow-ups and maintenance.

## 2026-11-13: direction change
- Phone access to the owner's assistant (Agent Client Protocol); a paired device's yes now runs a held call.
- Decided to point the supervision layer at real science: skuld2, an OpenFOAM-14 detonation/RDE pipeline run by
  Odin's seats. Plan written: 18 documents, a 256-paper corpus, repositories and datasets checked, a validation
  matrix with reference values and tolerances.

## 2026-11-14: scope and parallel work
- Scope fixed (Odin upgrades + skuld2 prep); ten parallel work sessions with briefs and shared rules (every budget a
  declared value, no hard-coded limits).
- B1: CJ, von Neumann and ZND states for 49 mixtures × 2 mechanisms (SDToolbox on Cantera); pair D_CJ within 0.5 %
  for every N2-free mixture; 6 pair misses at φ ≤ 0.73 recorded.
- B3: data pulls (REALM PlanarDet, RDE-72, TU Berlin Zenodo record, The Well chunk, detonationFoam-OF14, OpenFOAM-14
  at `64cfdf54`). B4: 2,048 RDE.jl ring runs with known wave counts (1,342 reliable).

## 2026-11-15: the solver stack and the first detonation runs
- OpenFOAM-14 + detonationFluid built reproducibly with Nix; skuld2 forked from Mark One; images for pods.
- B2: measured cost on ESI rhoCentralFoam (0.19-0.38 core-µs per cell-step on mini, serial).
- B5 first H2-air tubes (hot driver, Courant 0.4): +17.47 / +13.46 / +10.35 % over D_CJ on three grids, and
  temperatures clipped at 3500 K. Sod on shockFluid: fan tail off by 1.31 cells at 1,000 cells (fail).
  DMR and the periodic full channel: floating-point exceptions.
- Surrogates: torch 2.14 + CUDA 13.2 + PhysicsNeMo 2.2.2 verified on the 8 GB GPU; dataset stores built; memory
  profiles (DoMINO 2,744 MiB); literature wave-count classifier (151 rows, 90 labelled).
- Integration: Run00005 (Sod) and Run00006 (ZND) ran in mini pods and went CREATED to COMMITTED in eggs
  (11-16 00:03-00:08).

## 2026-11-16: diagnosis, the gate, the agent harness
- The 3500 K clip traced to Courant 0.4, outside the forward-Euler MUSCL step's stable range; at 0.1 no step reaches
  3500 K (peak 3240 K). skuld2's ZND template default moved to 0.1.
- Mechanism conversion verified: 0D ignition OpenFOAM-14 vs Cantera +0.15 % (von Neumann state) and -0.08 %
  (1300 K, 20 bar). Stiff-chemistry tolerance excluded (≤ 0.07 K change).
- H2-air at Courant 0.1 still fails the 1 % gate (+1.08 % coarse, -21.27 % medium); in a shock-attached frame the
  wave fails on both grids (-23.1 / -22.7 %, grids within 0.4 %). Recorded as a known-unstable case, not tuned.
- Owner's decision: measure the 1D gate on the standard stable mixture 2H2:O2:7Ar (criterion unchanged).
  **Gate passed**: +0.296 % (5,682 cells) and +0.272 % (11,364 cells) vs D_CJ 1691.12 m/s, error falling with
  refinement, no clipping. Measured cost c ≈ 21-22 core-µs per cell-step at 4 ranks (planning value was 200).
- Surrogates recorded as baselines: FNO-1D on RDE.jl 99.22 % test wave-count accuracy (smoke test); FNO on
  PlanarDet front error 1.12 cells; Transolver and MeshGraphNet fail the overfit gate (0.504 / 0.730 / 0.703 vs 0.05).
- Agent harness: Sinmara and Kubert moved to Odin's lean "loom" harness: ~73k → 12.4-20.1k prompt tokens per
  request, 80-99 % cached. Delegated answers now arrive whole (a cut is labelled); a child steered 3 times without
  progress goes to the owner; a seat can read its own approval; incidents carry a stable key.
- Kubert raised 13 pc disk-pressure incidents with 13 different signatures (4 phone pages): the cause of the
  de-duplication fix.

## 2026-11-17: the loop closes once
- Acceptance campaigns `postdeploy-sod` / `postdeploy-znd`: 21 approval cards over the day before the path held;
  the budget ledger refused launches outside the approved cases.
- 02:57 first pods: exit 2, `--deadline-seconds` missing (fixed in Odin). 03:37 second pods: Sod Run00012 reached
  its end time in 1.0 s; ZND Run00013 stopped after one step; both COMMITTED in eggs as `STOPPED / WALL_BUDGET`
  (Odin's 600 s deadline vs skuld2's 1,800 s margin). No frame rendered.
- This repository built and published.

## Remaining (for Lab 4)
- Fix the deadline/margin mismatch and rerun both acceptance runs to a correct terminal state; a rendered frame.
- First 2D RDE wave-count sweep card (unblocked by the 1D gate; the owner decides it), then surrogates on skuld2 data.
- Sod on shockFluid and DMR still fail; the full-channel case must run without FPE before any 2D cost claim.

## Bottlenecks
- The seam between Odin and skuld2: each live attempt found one contract mismatch (approval id field, read-only
  sandbox, deadline argument, deadline margin).
- Compute: mini is also the authority and builder; pc is a gaming desktop with one 8 GB GPU.
- Model accounts: the strongest lanes were held at their weekly limit until 11-20, so seats ran on cheaper lanes.
