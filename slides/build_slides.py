"""Build slides/Lab3_skuld2_demo.pptx (python-pptx); render the PDF with
`soffice --headless --convert-to pdf --outdir slides slides/Lab3_skuld2_demo.pptx`."""
import pathlib

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "slides/Lab3_skuld2_demo.pptx"
INK, GRAY, ACCENT = RGBColor(0x1A, 0x1A, 0x1A), RGBColor(0x6A, 0x6A, 0x6A), RGBColor(0x1B, 0x5F, 0xAA)
FONT = "Arial"
W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]
count = [0]


def text(slide, x, y, w, h, lines, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, spacing=1.1):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        bullet = line.startswith("• ")
        body = line[2:] if bullet else line
        if bullet:
            r = p.add_run(); r.text = "•  "; r.font.color.rgb = ACCENT; r.font.size = Pt(size); r.font.name = FONT
        for j, part in enumerate(body.split("**")):
            if not part:
                continue
            r = p.add_run(); r.text = part
            r.font.name, r.font.size, r.font.color.rgb = FONT, Pt(size), color
            r.font.bold = bold or (j % 2 == 1)
        p.space_after = Pt(size * 0.45)
    return tb


def image(slide, path, x, y, w, h):
    """Fit an image inside the box (inches), centred."""
    im = Image.open(ROOT / path)
    iw, ih = im.size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    slide.shapes.add_picture(str(ROOT / path), Inches(x + (w - dw) / 2), Inches(y + (h - dh) / 2), Inches(dw), Inches(dh))


def slide(title, kicker=None, notes=None):
    count[0] += 1
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(1, Inches(0.6), Inches(0.42), Inches(0.08), Inches(0.62))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()
    text(s, 0.8, 0.3, 11.8, 0.8, title, size=30, bold=True)
    if kicker:
        text(s, 0.8, 1.0, 11.8, 0.5, kicker, size=16, color=GRAY)
    text(s, 0.6, 7.02, 9, 0.35, "Colin Gray · AM/ME/CE 295 · Lab Report 3 · github.com/colingray3149/skuldsubmit", size=10, color=GRAY)
    text(s, 11.9, 7.02, 0.9, 0.35, str(count[0]), size=10, color=GRAY, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def caption(s, x, y, w, t):
    text(s, x, y, w, 0.4, t, size=11, color=GRAY)


# 1 title
count[0] += 1
s = prs.slides.add_slide(BLANK)
bar = s.shapes.add_shape(1, Inches(0.8), Inches(1.55), Inches(0.12), Inches(2.0))
bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()
text(s, 1.1, 1.45, 11.8, 0.9, "Agents that propose, run, check and record", size=36, bold=True)
text(s, 1.1, 2.25, 11.8, 0.9, "detonation simulations", size=36, bold=True, color=ACCENT)
text(s, 1.1, 3.2, 11.5, 0.6, "skuld2: the Lab 2 supervision layer now drives OpenFOAM-14", size=22, color=GRAY)
text(s, 1.1, 4.4, 11.5, 0.5, "Colin Gray · AM/ME/CE 295 Agentic AI in Scientific Discovery · Lab Report 3 (weeks 5-6)", size=18)
text(s, 1.1, 4.9, 11.5, 0.5, "github.com/colingray3149/skuldsubmit", size=18, color=ACCENT)
text(s, 1.1, 6.15, 11.5, 0.8, "Made by Claude Opus 5.5 (Claude Code), from Colin's project records and run data. "
     "Every number is read from a file in the repository.", size=14, color=GRAY)
s.notes_slide.notes_text_frame.text = ("Lab 2 studied how an agent supervises long-running pods. Lab 3 points the same "
                                       "supervision layer at real science: detonation simulations with answers we can check.")

# 2 problem
s = slide("The problem", "Lab 2's question, now with an answer key",
          notes="Research pods gave us no ground truth. Simulation does. Same supervisor, testable acceptance.")
text(s, 0.8, 1.7, 5.8, 5, [
    "**Lab 2 asked:** what is the minimum supervision interface that lets a delegating agent detect, correct and "
    "accept long-running pod work?",
    "• 21 research pods: 14 delivered in 7-16 min, 7 ran to the 60-min wall",
    "• failure causes: idle churn, carrier loss, egress block",
    "• but \"accept\" had nothing objective to check against",
], size=17)
text(s, 7.0, 1.7, 5.6, 5, [
    "**Lab 3:** keep the question, change the workload.",
    "• agents run OpenFOAM-14 detonation simulations in cluster pods",
    "• each result has a reference: Cantera ignition delay, Chapman-Jouguet speed, the exact Sod solution",
    "• goal (Lab 4-5): rotating-detonation wave count, direction and speed, and surrogates that predict them",
    "• so the agents' \"accept\" is now testable, and so are they",
], size=17)

# 3 system
s = slide("The system", "a home cluster, an agent harness (Odin) and a simulation harness (skuld2)",
          notes="mini is the always-on authority; pc is a gaming desktop with one 8 GB GPU; the laptop is a client. Seats are long-lived agents declared in TOML.")
image(s, "diagrams/d1_system_architecture.png", 0.3, 1.4, 8.6, 5.6)
text(s, 9.0, 1.6, 4.0, 5.3, [
    "**Seats, and why each exists**",
    "• **Sinmara**: the owner's assistant; asks for decisions",
    "• **Mimir**: science lead; proposes campaigns, plans sweeps",
    "• **Kubert**: cluster operator; launches and watches pods",
    "• **Var**: independent science review",
    "• **Saga**: curator of lessons and the validation matrix",
    "• **Gungnir / Forseti**: write code / review its diff",
    "No shell, no network of their own: Odin grants and audits every call. Full map: diagrams/d3_seat_map.",
], size=13)

# 4 agent loop
s = slide("The agent loop, live on 2026-11-17", "card → plan → pod → telemetry → committed record (UTC)",
          notes="Accent arrows ran live. Two acceptance campaigns: Sod and ZND, one case each, 2 core-hours. The first pods failed before the solver; the second pair ran.")
image(s, "diagrams/d2_agent_loop_sequence.png", 0.6, 1.45, 8.0, 5.5)
text(s, 8.8, 1.7, 4.1, 5.2, [
    "• Mimir raised the cards; the owner approved from a device",
    "• guards held: no launch without an approved campaign; the ledger refused a relaunch past its core-hours",
    "• 02:57 first pods: exit 2, missing --deadline-seconds",
    "• 03:37 second pods: **Sod Run00012 ran to its end time**, collected, **COMMITTED**",
    "• not yet live: Var's review, Saga's curation",
], size=14)

# 5 demo captures
s = slide("Demo: what the system showed", "odin view Missions board and Kubert's pods, captured live (sanitized)",
          notes="Board: two failed pods (no sample) and two that ran (samples, checkpoints). Logs: ODIN-STATUS and checkpoint lines streamed by the in-pod supervisor. No frame rendered: the render job failed, and we show that rather than fake one.")
image(s, "demo/captures/c1_missions_board.png", 0.6, 1.45, 8.2, 2.05)
image(s, "demo/captures/c3_pods.png", 0.6, 3.6, 8.2, 3.35)
image(s, "demo/captures/c6_status.png", 9.0, 1.45, 3.9, 3.6)
text(s, 9.0, 5.15, 3.9, 1.8, [
    "Run00012 went through all nine stages, CREATED → COMMITTED. Honest gaps: terminal state STOPPED / WALL_BUDGET "
    "(Odin's 600 s deadline < skuld2's 1,800 s margin) and no rendered frame yet.",
], size=12)

# 6 Kubert returns
s = slide("Kubert makes the return", "Lab 2's cluster supervisor now watches the science pods",
          notes="Thirteen differently worded incidents for one disk condition, four phone pages. The fix: a stable key. Kubert's next incident used one.")
image(s, "demo/captures/c4_incidents.png", 0.6, 1.5, 7.9, 5.4)
text(s, 8.7, 1.6, 4.2, 5.3, [
    "• launched every acceptance pod (seat kubert, lane kubert-skuld2) and got the watch wakes when they ended",
    "• raised **17 incidents** on 11-16/17",
    "• 13 for one condition (GPU machine's image disk 91-96 % full), each worded differently: de-duplication keyed on "
    "the wording missed them, **4 phone pages in 24 min**",
    "• fix: incidents carry a **stable key**; the next one (skuld2-launch-flux-scheme-schema) used it",
], size=14)

# 7 validation ladder
s = slide("The validation ladder", "each rung has an independent reference and a fixed tolerance",
          notes="Pass marks are gate passes. Dashed boxes failed or are incomplete, recorded not waived. The 2D sweep is unblocked by the 1D gate but its card is the owner's call.")
image(s, "diagrams/d4_validation_ladder.png", 0.6, 1.5, 12.1, 5.4)

# 8 results
s = slide("Results: the bottom of the ladder passes", "0D chemistry and the 1D Chapman-Jouguet gate",
          notes="0D within 0.15 percent of Cantera on the same mechanism. 1D argon-diluted: plus 0.296 and plus 0.272 percent, error falling with refinement, no clipping.")
image(s, "figures/fig1_speed_vs_grid.png", 0.5, 1.45, 7.6, 4.3)
image(s, "figures/fig2_ignition_0d.png", 8.2, 1.6, 4.8, 2.0)
text(s, 8.3, 3.8, 4.6, 3.1, [
    "• 0D ignition vs Cantera: **+0.15 %** (1538.8 K, 28 bar), **-0.08 %** (1300 K, 20 bar)",
    "• 1D CJ on 2H2:O2:7Ar: **+0.296 %** (5,682 cells), **+0.272 %** (11,364): 1 % gate, both grids, unchanged",
    "• rerun it: python demo/replay.py (~5 s)",
], size=14)
caption(s, 0.6, 5.85, 7.4, "Speed error vs grid spacing for every 1D configuration (left) and the gate case (right); grey band ±1 %.")

# 9 honest failure
s = slide("The honest failure: stoichiometric H2-air", "the agents' runs refused to tune until it passes",
          notes="At Courant 0.1 and finer grids the H2-air front overdrives then decays; in the shock frame both grids fail to minus 23 percent within 0.4 percent of each other. Mechanism and ODE tolerances excluded. Recorded as known-unstable; the gate moved to the standard stable mixture with the criterion unchanged.")
image(s, "figures/fig3_xt_temperature.png", 0.4, 1.45, 7.6, 4.9)
caption(s, 0.6, 6.4, 7.4, "Temperature, x-t. Dashed: the CJ trajectory. Tinted: cells the line sampler skipped (not interpolated).")
image(s, "figures/fig4_local_speed.png", 8.2, 4.6, 4.8, 2.4)
text(s, 8.2, 1.5, 4.8, 3.1, [
    "• hydrogen-air at 1 atm does not hold a 1D CJ wave here: **-21.3 %** (2.2 µm), **-23.1 / -22.7 %** in a "
    "shock-attached frame, two grids within 0.4 %",
    "• excluded: the mechanism (0D within 0.15 %) and stiff-chemistry tolerances (≤ 0.07 K)",
    "• the literature expects a pulsating 1D wave; here the converged inviscid answer is a failing one",
    "• not tuned: the gate moved, by the owner's decision, to the standard stable mixture with the **same 1 % "
    "criterion**; H2-air stays recorded as a failure",
], size=13)

# 10 cost and clip
s = slide("Cost, and the 3500 K clip", "measured, not estimated",
          notes="c about 21 core-microseconds per cell-step, ten times below the planning value. The clip came from Courant 0.4; at 0.1 the peak is 3240 K but runs take four times longer per simulated microsecond.")
image(s, "figures/fig6_cost.png", 0.4, 1.45, 7.4, 4.3)
image(s, "figures/fig7_courant_clip.png", 7.9, 1.5, 5.1, 2.4)
text(s, 8.0, 4.1, 4.9, 2.8, [
    "• c = **20.3-22.2 core-µs per cell-step** at 4 ranks (planning value 200; literature 129-344)",
    "• 61 runs logged: 28 ok, 31 failed, 2 partial; 47.9 core-h for the 14 costed solves",
    "• clip traced to Courant 0.4 (unstable for forward-Euler MUSCL): at 0.1, peak **3240 K**",
], size=14)
caption(s, 0.5, 5.85, 7.3, "Measured cost per cell-step (accent: the gate runs) and core-hours per run.")

# 11 continuity
s = slide("Lab 2 → Lab 3", "every Lab 2 failure mode has an answer in the simulation path",
          notes="Idle churn: whole answers and a steer cap. Carrier loss: release needs a matching Job. Egress: science pods need none. The wall: declared deadlines and core-hour caps. Heartbeat: telemetry lines and watch wakes. Evidence: hashed run records and review.")
image(s, "diagrams/d6_lab2_to_lab3.png", 0.5, 1.45, 12.3, 4.9)
text(s, 0.8, 6.35, 12, 0.6, "Also live since Lab 2: Sinmara's requests fell from ~73k to 12.4-20.1k prompt tokens, 80-99 % cached, on Odin's lean harness.",
     size=13, color=GRAY)

# 12 next steps
s = slide("Next: Lab 4 integration, then surrogates", "the same loop on the first 2D RDE sweep, with PhysicsNeMo models on its data",
          notes="Fix the deadline margin, get a frame, make the full channel run, then the sweep card. Surrogates: FNO baseline first; Transolver and MeshGraphNet re-gated; DoMINO when steady geometry-varying data exists.")
image(s, "diagrams/d5_data_surrogate_pipeline.png", 0.5, 1.45, 12.3, 2.1)
image(s, "figures/fig8_surrogates.png", 0.6, 3.7, 6.3, 2.5)
text(s, 7.2, 3.65, 5.7, 3.3, [
    "• fix the deadline/margin mismatch; rerun both acceptance runs to COMPLETED; a rendered frame",
    "• make the 2D periodic channel run, measure its cost; Mimir raises the first 2D RDE sweep card",
    "• full loop including **Var's review** and **Saga's curation**",
    "• surrogates via **NVIDIA PhysicsNeMo**: FNO baseline, then Transolver / MeshGraphNet once they pass the overfit "
    "gate; DoMINO for steady geometry-varying data",
], size=14)
caption(s, 0.6, 6.25, 6.3, "Shakedown so far: FNO passes the overfit gate; Transolver and MeshGraphNet do not. 99.22 % is on synthetic RDE.jl data.")

prs.save(OUT)
print("wrote", OUT, count[0], "slides")
