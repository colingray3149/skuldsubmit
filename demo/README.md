# demo/: the current state, replayed and captured

## 1. Replay one run end to end (anyone, ~5 s, no OpenFOAM)

```sh
python demo/replay.py
```

It takes the B5 1D CJ gate case (2H2:O2:7Ar, 1 atm, 300 K, detonationFluid) from reference to verdict using only
`data/`: the B1 reference state, Cantera's 0D ignition against the stored OpenFOAM-14 histories, the solve's run
line and measured cost, the lead-shock speed fit from the raw probe traces with the unchanged 1 % gate, and the
H2-air counter-case that must fail. Output: `replay-output.txt` (and `captures/c7_replay.png`).

## 2. Captures of the live system (2026-11-17, 03:30-03:45 UTC)

Taken from the running system by the session that built this repository: `odin view` in a fixed-size terminal
(tmux, 160×48), `kubectl`, the `skuld2` CLI, the Odin journal and approval ledger. Each PNG is rendered from the
text file beside it (`.ansi` keeps the terminal colours) with charm `freeze`; icon glyphs became `•`.

| Capture | What it shows |
|---|---|
| `c1_missions_board` | `odin view`, Missions tab: the two acceptance pods that failed at 02:57 (no sample) and the two that ran at 03:37 (samples, 1 and 10 checkpoints) |
| `c2_mission_sod`, `c2b_mission_znd` | a mission opened: its run id and the last ODIN-STATUS sample (cells, Courant, Δt, ranks) |
| `c3_pods` | the four pods Kubert launched (seat and lane labels), and the logs of the two that ran: ODIN-STATUS and ODIN-CHECKPOINT lines, `RunNNNNN exported` |
| `c4_incidents` | every incident Kubert raised that day: 13 pc-disk incidents with 13 different signatures (4 phone pages), then a keyed one after the de-duplication fix |
| `c5_approvals` | the campaign approval cards Mimir raised: 21 cards, how each ended, how the owner decided |
| `c6_status` | `skuld2 status Run00012`: the Sod acceptance run CREATED to COMMITTED in eggs, with its terminal state |
| `c7_replay` | the replay above |

Sanitized: only seat, mission and pod views (no conversation tabs, which hold unrelated personal work), no host
addresses, registry hosts or chat identifiers. Approval deciders are shown as the kind of channel only.

**Not available, and not faked:** an ODIN-RENDER frame and the Missions sparklines. Each acceptance run sent only
two ODIN-STATUS samples (the runs were cut short, see below), so there is no history to draw, and Odin's render job
for the Sod mission failed; Kubert's own frame request was refused with "mission skuld2-openfoam-mini has produced
no frame yet". `c2_mission_sod` shows that state.

## 3. What the captures say, honestly

- The loop closed once end to end on 2026-11-17: owner card, Mimir's plan and stage, Kubert's pod on mini,
  telemetry back to Odin, collection, COMMITTED run record (Run00012, Sod). See `../data/agent/TIMELINE-2026-11-16.md`.
- It is not yet a validated result: both runs were recorded `STOPPED / WALL_BUDGET`, because Odin passed
  `--deadline-seconds 600` and skuld2 keeps an 1,800 s deadline margin. The Sod run had already reached its end time;
  the ZND run stopped after its first step.
- The first launch, 40 minutes earlier, failed before the solver: the pod command lacked `--deadline-seconds`.
