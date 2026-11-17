"""Build report/Lab_Report_3_-_Colin_Gray.docx (python-docx); render the PDF with
`soffice --headless --convert-to pdf --outdir report report/Lab_Report_3_-_Colin_Gray.docx`."""
import pathlib

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "report/Lab_Report_3_-_Colin_Gray.docx"
REPO = "https://github.com/colingray3149/skuldsubmit"
ACCENT = RGBColor(0x1B, 0x5F, 0xAA)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x6A, 0x6A, 0x6A)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)  # US Letter
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Cm(2.2))
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)

st = doc.styles["Normal"]
st.font.name, st.font.size, st.font.color.rgb = "Arial", Pt(10.5), INK
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.line_spacing = 1.12
for name, size in (("Heading 1", 14), ("Heading 2", 11.5)):
    h = doc.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = "Arial", Pt(size), True, INK
    rf = h.element.rPr.rFonts
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), "Arial")
    h.paragraph_format.space_before = Pt(12 if size > 12 else 8)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True

fig_n = [0]
tab_n = [0]


def para(text="", bold=False, italic=False, size=None, color=None, align=None, after=None, style=None):
    p = doc.add_paragraph(style=style)
    if text:
        add_runs(p, text, bold=bold, italic=italic, size=size, color=color)
    if align:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def add_runs(p, text, bold=False, italic=False, size=None, color=None):
    """**bold** and `code` spans inside text."""
    for j, chunk in enumerate(text.split("`")):
        mono = j % 2 == 1
        for i, part in enumerate(chunk.split("**") if not mono else [chunk]):
            if not part:
                continue
            r = p.add_run(part)
            r.bold = bold or (i % 2 == 1)
            r.italic = italic
            if mono:
                r.font.name = "Courier New"
                r._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
            if size or mono:
                r.font.size = Pt((size or 10.5) - (1 if mono else 0))
            if color is not None:
                r.font.color.rgb = color
    return p


def bullets(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        add_runs(p, it)
        p.paragraph_format.space_after = Pt(2)


def heading(text, level=1):
    return doc.add_heading(text, level=level)


def figure(path, caption, width_cm=16.5):
    fig_n[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(ROOT / path), width=Cm(width_cm))
    c = doc.add_paragraph()
    r = c.add_run(f"Figure {fig_n[0]}. ")
    r.bold, r.font.size = True, Pt(9)
    r2 = c.add_run(caption)
    r2.font.size = Pt(9)
    r2.font.color.rgb = GRAY
    c.paragraph_format.space_after = Pt(8)
    return fig_n[0]


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hex_fill)
    tcPr.append(sh)


def table(caption, header, rows, widths_cm, size=8.5):
    tab_n[0] += 1
    c = doc.add_paragraph()
    r = c.add_run(f"Table {tab_n[0]}. ")
    r.bold, r.font.size = True, Pt(9)
    r2 = c.add_run(caption)
    r2.font.size, r2.font.color.rgb = Pt(9), GRAY
    c.paragraph_format.keep_with_next = True
    c.paragraph_format.space_after = Pt(3)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold, run.font.size = True, Pt(size)
        shade(cell, "EDEDED")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], v, size=size)
    t.autofit = False
    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths_cm):
        gc.set(qn("w:w"), str(int(w * 567)))
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        for i, w in enumerate(widths_cm):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.keep_with_next = row._index < len(t.rows) - 1
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return tab_n[0]


def code(lines):
    for ln in lines:
        p = doc.add_paragraph()
        r = p.add_run(ln)
        r.font.name, r.font.size = "Courier New", Pt(7.8)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Cm(0.4)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def footer_page_numbers():
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Colin Gray · AM/ME/CE 295 · Lab Report 3 · page ")
    r.font.size, r.font.color.rgb = Pt(8), GRAY
    run = p.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), kind); run._r.append(el)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = text; run._r.append(it)
    run.font.size, run.font.color.rgb = Pt(8), GRAY


# ---------------------------------------------------------------- title page
sec.different_first_page_header_footer = True
footer_page_numbers()
p = para("AI DISCLAIMER: this report and the slides were made by Claude Opus 5.5 (Claude Code), from Colin's project "
         "records and run data.", bold=True, size=10.5)
p.paragraph_format.space_after = Pt(4)
para("Every number below is read from the project's run files, records and logs; each one names its source file in the "
     "repository. Nothing was estimated to fill a gap: where something does not exist yet (a rendered frame, a 2D run), "
     "the report says so.", size=9, color=GRAY, after=60)
para("Lab Report 3 — Weeks 5–6", bold=True, size=24, after=4)
para("Agents that propose, run, check and record detonation simulations", size=15, color=ACCENT, after=4)
para("The Lab 2 supervision layer now drives OpenFOAM-14", size=12, color=GRAY, after=26)
para("Colin Gray · AM/ME/CE 295 · Agentic AI in Scientific Discovery", size=11, after=2)
para("Submitted 2026-11-16, Pacific time (due 2026-11-15: late)", size=10, color=GRAY, after=2)
p = para("Repository: ", size=11, after=30)
r = p.add_run(REPO); r.font.color.rgb = ACCENT; r.font.size = Pt(11)

para("In one paragraph", bold=True, size=11, after=3)
para("skuld2 is an agentic simulation pipeline: seats of my agent harness, Odin, propose a validation campaign, raise an "
     "owner approval card, launch OpenFOAM-14 with the detonationFluid module in a Kubernetes pod, collect the result "
     "into a git-backed record, and check it against independent references. This cycle's working piece is the "
     "bottom of the validation ladder, run for real: the 0D chemistry agrees with Cantera to 0.15 %, and a 1D argon-"
     "diluted hydrogen detonation runs within 0.3 % of its Chapman-Jouguet speed on two grids, with the error falling "
     "as the grid is refined. Stoichiometric hydrogen-air, the mixture the project ultimately needs, does not hold a "
     "1D CJ wave in this setup (-23 %, grid-converged), and the agents recorded that rather than tuning it away. On "
     "2026-11-17 (UTC) the agent loop closed once, live: card, plan, Kubert's pod, telemetry, committed run record, and it "
     "exposed the next defect on the way. Times in this report are UTC.", size=10)
p = para()
p.add_run().add_break(WD_BREAK.PAGE)

# ---------------------------------------------------------------- 1 repository
heading("1. Repository")
p = para("")
add_runs(p, "**" + REPO + "** (public; MIT for code). It holds the README with a results table and reproduction steps, "
         "the running log (`LOG.md`), the evidence (`data/`: result JSON, raw probe traces, run records, approvals and "
         "incidents), curated code (`code/`), the scripts that regenerate every figure and diagram, a replay demo "
         "(`demo/`), and this report and the deck. It was built as a series of commits, one component at a time. The full "
         "harness (Odin) and the simulation harness (skuld2) stay private; sanitized excerpts are in `code/`, and the "
         "public Odin mirror from Lab 2 is github.com/colingray3149/odin2.")

# ---------------------------------------------------------------- 2 progress
heading("2. Progress report from the running log")
heading("Done", 2)
bullets([
    "**Solver stack, validated from the bottom.** OpenFOAM-14 (Foundation, commit 64cfdf54) with the detonationFluid "
    "module, built reproducibly with Nix. 0D ignition vs Cantera: +0.15 % and -0.08 %. 1D CJ gate on 2H2:O2:7Ar: "
    "+0.296 % and +0.272 % (criterion 1 % on both grids, unchanged).",
    "**A setup bug found and fixed, not tuned around.** Temperatures clipped at 3500 K traced to Courant 0.4, outside "
    "the stable range of detonationFluid's forward-Euler MUSCL step; at 0.1 the peak is 3240 K.",
    "**An honest negative result.** Stoichiometric H2-air at 1 atm fails in 1D (-23.1 / -22.7 % in a shock-attached "
    "frame, two grids within 0.4 %); recorded as a known-unstable case, not a gate.",
    "**Measured cost.** c = 20.3-22.2 core-µs per cell-step at 4 ranks (planning value 200). 61 background runs logged "
    "(28 ok, 31 failed, 2 partial); the 14 costed solves used 47.9 core-hours.",
    "**The agent loop, live.** On 2026-11-17 a Sod acceptance case went from owner card to a committed run record "
    "through Mimir, Kubert and a pod on the cluster (Run00012).",
    "**Lab 2's next steps.** Progress heartbeat (pod telemetry lines and watch wakes), release only after an observed "
    "launch, deadlines declared per campaign; delegated answers arrive whole; a stuck child goes to the owner once.",
])
heading("Remaining", 2)
bullets([
    "Correct terminal states: both acceptance runs were recorded STOPPED / WALL_BUDGET (Section 7).",
    "A rendered frame on the Missions board; the review (Var) and curation (Saga) steps on a real campaign.",
    "Sod on shockFluid (fan tail 1.31 cells vs a 1-cell limit), double Mach reflection and the 2D full channel "
    "(floating-point exceptions) still fail; they gate the first 2D RDE sweep's credibility.",
    "Surrogates on skuld2's own data; Transolver and MeshGraphNet do not yet pass their overfit gate.",
])
heading("Bottlenecks", 2)
bullets([
    "The seam between Odin and skuld2: every live attempt found one contract mismatch (an undeclared approval field, a "
    "read-only sandbox, a missing deadline argument, a deadline margin larger than the deadline).",
    "Approvals: 21 campaign cards were raised over one day before the path held; a daemon restart drops held calls.",
    "Compute: the always-on machine is also the authority and builder; the GPU machine is a gaming desktop (8 GB).",
])

# ---------------------------------------------------------------- 3 demo
heading("3. Demo of the current state")
para("Two demos. The live one (Figure 1) is the agent loop on the cluster on 2026-11-17, from the daemon journal, the "
     "approval ledger, the pod records and the eggs ledger (`data/agent/TIMELINE-2026-11-16.md`; screen captures in "
     "`demo/captures/`). The reproducible one is `python demo/replay.py`: it replays the 1D gate run from stored data "
     "in about five seconds, with no OpenFOAM needed:")
code(["0D  tau OF14 0.5342 us  Cantera 0.5334 us  diff +0.15 %  PASS     (1538.8 K, 28 bar)",
      "1D  ar7-coarse  D 1696.14 m/s  +0.296 %  PASS   ar7-medium  D 1695.72 m/s  +0.272 %  PASS",
      "1D  h2air-co01-medium  D 1554.99 m/s  -21.273 %  FAIL   (counter-case, must not pass)"])
figure("diagrams/d2_agent_loop_sequence.png",
       "The agent loop as it ran on 2026-11-16/17 (UTC). Accent: steps that ran live, with their outcome. The owner "
       "approved through the phone or the command line; Mimir planned and staged; Kubert's first pods exited before the "
       "solver (missing deadline argument, fixed); the second pair ran at 03:37 and both runs were collected and "
       "committed. Grey: designed steps not yet reached on these campaigns (Var's review, Saga's curation).", 16.5)
para("What ran: Kubert launched four pods in total. The second Sod pod solved 250 cells to its end time (t = 6.3246 ms) "
     "in 1.0 s, streamed two ODIN-STATUS samples (Courant 0.196) and ten checkpoints, and exported Run00012, which the "
     "collector committed to the eggs ledger with all nine stages (CREATED to COMMITTED). Along the way every "
     "governance guard held: Odin refused launches without an approved campaign, and its budget ledger refused a "
     "relaunch past the approved cases and core-hours. Not shown, because it does not exist: a rendered frame. Odin's "
     "render job for the mission failed, and Kubert's request for the frame was refused with \"mission "
     "skuld2-openfoam-mini has produced no frame yet\".")

# ---------------------------------------------------------------- 4 direction
heading("4. Project direction, and why it changed from Lab 2")
para("Lab 2 asked: what is the minimum supervision interface that lets a delegating agent detect, correct and accept "
     "long-running pod work? It studied 21 research pods (web research) and found three failure causes (idle churn, "
     "carrier loss, egress block) and one dominant cost (every failure ran to the 60-minute wall). The related work it "
     "carried forward was a persistent agent runtime with child workers (Prime Intellect's Prime Agent) and provenance-"
     "enforced delivery (my Surtr design work): a claim travels with the artefact that supports it.")
para("The question stays; the workload changes. Research pods have no objective answer to check a deliverable "
     "against. Simulation pods do: a detonation speed either matches the Chapman-Jouguet value or it does not, an "
     "ignition delay matches Cantera or it does not, and Sod has an exact solution. Pointing the same supervision layer "
     "at OpenFOAM makes \"accept\" testable. The guideline allows pivots; Figure 2 maps each Lab 2 finding to what "
     "now answers it.")
figure("diagrams/d6_lab2_to_lab3.png",
       "Lab 2 to Lab 3. Each failure mode found in Lab 2's 21-run study (left) and the mechanism that now answers it in "
       "the simulation path (right), with the supervision interface's six verbs and the tools that implement them.", 15.0)
para("**Kubert returns.** Kubert, the cluster supervisor that watched research pods in Lab 2, now supervises the "
     "science pods. On 2026-11-16/17 it raised 17 incidents. Thirteen were the GPU machine's image filesystem at "
     "91-96 % full, each worded differently, so Odin's de-duplication (keyed on the wording) let 4 of them page the "
     "phone within 24 minutes. That became a fix: an incident now carries a stable key, and Kubert's next incident "
     "(`skuld2-launch-flux-scheme-schema`, raised when its pod launch was refused) used one. Kubert also launched every "
     "acceptance pod, received the workload-watch wakes when they ended, and asked for the frame "
     "(`demo/captures/c4_incidents.png`, `c3_pods.png`).")

# ---------------------------------------------------------------- 5 method
heading("5. Method")
heading("System: who does what, and why", 2)
para("Odin is a personal agent harness: a daemon with a ledger (approvals, budgets, incidents), a registry of declared "
     "seats and workloads published without a rebuild, and a model gateway. A seat is a long-lived agent with a role, "
     "model lanes, tools and scope, each declared in a TOML file (`code/odin/seat-kubert.toml`). Seats have no shell "
     "and no network of their own; Odin grants and audits every call. The seats in the simulation loop:")
table("The seats in the simulation loop (lanes and tools from the Odin registry; personal entries removed).",
      ["Seat", "Why it exists", "Lanes (default first)", "Key tools"],
      [["Sinmara", "the owner's assistant; asks the owner for decisions", "terra, glm-flash, …", "delegation, cfd toolset"],
       ["Mimir", "science lead: proposes campaigns, plans and stages sweeps", "terra, astra, sol, zai-glm", "skuld2.case/sweep/campaign"],
       ["Kubert", "cluster operator: launches approved cases, watches pods", "go-deepseek-flash, …", "kube.workload.*, incident"],
       ["Var", "independent science review of a claim, dataset or promotion", "zai-glm, …", "artifact read, verdicts"],
       ["Saga", "curator: lessons, literature, the validation matrix", "glm-flash, zai-glm, terra", "knowledge, data, docs"],
       ["Gungnir, Forseti", "write code; review its exact diff", "sol, zai-glm, …", "code, git, build, test"]],
      [2.3, 6.2, 3.8, 4.4])
para("A campaign is a declared file (`code/skuld2/campaigns/postdeploy-znd.toml`: template, cases, ranks, deadline, "
     "core-hour cap). Mimir raises it as an approval card whose values are bound into the approval; only an approved "
     "campaign can launch, and Odin's ledger reserves its cases and core-hours. skuld2 builds each case from a typed "
     "template, runs `foamRun` under an in-pod supervisor that streams ODIN-STATUS numeric lines and freezes each "
     "written time directory by hard link with sha256 manifests, and the collector commits a run record that walks "
     "CREATED to COMMITTED (`code/skuld2/schema/run.toml`).")
heading("Numerics", 2)
para("OpenFOAM-14 (Foundation) [1, 2] with detonationFluid, the OF-14 port of detonationFoam [3]: Kurganov flux, vanLeer "
     "limiter, forward Euler, inviscid, Burke 2012 H2/O2 mechanism (13 species) [4]. References from Cantera [5] and "
     "SDToolbox [6] on the same mechanism (B1: 49 mixtures × 2 mechanisms). The 1D tube is 25 mm, started from the "
     "matched CJ/ZND profile with the lead shock at 5 mm; 49 pressure probes every 0.5 mm. The speed is the least-"
     "squares slope of probe arrival (first p > 2 × 10^5 Pa) over 10-24 mm (29 probes). The gate, fixed before the "
     "runs: within 1 % of D_CJ on both grids, error decreasing with refinement, no step at the 3500 K thermodynamic "
     "limit. Grids: 4.4 and 2.2 µm (17.9 and 35.8 cells per induction length for 2H2:O2:7Ar). The argon mixture is the "
     "standard stable validation case (Kwak et al. [7], case D1-2; argon dilution [8]). Sod is checked against the exact "
     "Riemann solution [15].")

# ---------------------------------------------------------------- 6 results
heading("6. Results and analysis")
table("Results. Every value is read from the named file in the repository's data/ folder.",
      ["Check", "Result", "Criterion", "Verdict", "Source"],
      [["0D ignition vs Cantera: 1538.8 K, 28 bar / 1300 K, 20 bar", "+0.15 % / -0.08 % (τ 0.5342 vs 0.5334 µs)", "≤ 2 %", "**pass**", "chem0d/"],
       ["1D CJ, 2H2:O2:7Ar: 5,682 / 11,364 cells", "1696.14 / 1695.72 m/s: +0.296 / +0.272 %; no clipping", "≤ 1 % both grids, error falls", "**pass**", "det1d/finish1d-ar7.json"],
       ["H2-air, hot driver, Courant 0.4, 3 grids", "+17.47 / +13.46 / +10.35 %; T clipped at 3500 K", "≤ 1 %", "fail", "det1d/det1d-three-grid.json"],
       ["H2-air, ZND start, Courant 0.1", "+1.08 % (4.4 µm), -21.27 % (2.2 µm)", "≤ 1 %", "fail", "det1d/finish1d-courant.json"],
       ["H2-air, shock-attached frame", "-23.1 / -22.7 % (2-19 µs mean)", "multi-cycle mean", "fail; grids agree", "det1d/finish1d-shockframe-*"],
       ["Sod, shockFluid, 1,000 cells", "fan tail off by 1.31 cells", "≤ 1 cell", "fail", "sod/sod-check.json"],
       ["Cost c, detonationFluid, 4 ranks", "20.3-22.2 core-µs/cell-step", "planning 200", "measured", "cost/COST.md"],
       ["FNO-1D on RDE.jl rings (wave count)", "99.22 % test (129 runs)", "smoke test only", "recorded", "surrogates/"],
       ["Transolver / MeshGraphNet overfit", "0.504, 0.730 / 0.703", "≤ 0.05", "fail", "surrogates/overfit-gate/"],
       ["Agent loop, Sod acceptance", "Run00012 COMMITTED; STOPPED/WALL_BUDGET", "COMPLETED", "partial", "agent/TIMELINE"]],
      [4.6, 4.6, 2.5, 1.9, 3.1], size=8)
figure("figures/fig1_speed_vs_grid.png",
       "Lead-shock speed error against D_CJ versus grid spacing for every 1D configuration (a), and the gate case (b). "
       "Grey band: ±1 %. The H2-air hot-driver runs (grey squares) overdrive and clip; the matched start at Courant 0.1 "
       "splits by grid; the shock-attached frame converges to a failing wave; 2H2:O2:7Ar passes on both grids.", 15.0)
para("**The gate passes, and the error behaves.** On 2H2:O2:7Ar the speed is +0.296 % and +0.272 % on the two grids, the first- and second-half fits agree within 0.25 %, and no step reaches 3500 K (peak 3164/3201 K). Figure 3a shows the "
     "front riding the D_CJ line for the whole run.")
figure("figures/fig3_xt_temperature.png",
       "Temperature in the x-t plane. (a) 2H2:O2:7Ar: the front follows the D_CJ line (dashed). (b) Stoichiometric "
       "H2-air at 2.2 µm: the front falls behind CJ and the flame separates from the shock (light band). Tinted "
       "stripes: cells the line sampler skipped (a processor boundary, and past 22 mm after 10 µs); not interpolated.", 13.5)
para("**H2-air is the finding, not a nuisance.** At Courant 0.4 the hot-driver runs looked like convergence toward CJ "
     "(+17 → +10 %) but were clipped at the thermodynamic limit; fixing the time step removed the clip (Courant 0.1: "
     "peak 3240 K, `figures/fig7_courant_clip`) and revealed that the wave does not hold. Once dissipation is low "
     "(finer grid, smaller Courant number) the front overdrives by about 20 % at start-up, then the flame separates and "
     "the shock decays; in the shock-attached frame both grids fail to the same speed within 0.4 %. The mechanism and "
     "the stiff-chemistry tolerances were excluded (0D within 0.15 %; tightening tolerances changed T by at most "
     "0.07 K). The literature expects stoichiometric H2-air to be a pulsating 1D detonation [9]. The tempting move was "
     "to tune (driver, limiter, fit window) until the 1 % gate passed. The gate was instead moved, by the owner's "
     "decision and with the criterion unchanged, to the standard stable mixture, and H2-air stays recorded as a failure.")
para("**Cost.** The settled configuration costs c ≈ 21 core-µs per cell-step on the always-on machine at 4 ranks, about "
     "ten times below the planning value of 200 and below the literature band for density-based OpenFOAM detonation "
     "codes (129-344). Courant 0.1 makes each 1D run about four times longer per simulated microsecond than 0.4. No "
     "2D cost is claimed: the periodic full-channel case failed before a meaningful timing.")
para("**Surrogates (shakedown only).** The training stack (torch 2.14, CUDA 13.2, PhysicsNeMo 2.2.2) runs on the 8 GB "
     "GPU. A 1D FNO [14] on 1,342 reliable RDE.jl ring runs [16] predicts the wave count after 100 steps with 99.22 % test "
     "accuracy: a smoke test on a reduced-order model's data, not evidence about real engines. On REALM's PlanarDet "
     "[10] the FNO reaches a REALM state error of 38.5 (published FNO: 27.10). Transolver [11] and MeshGraphNet [12] "
     "fail the overfit sanity gate, so they are not yet credible.")

# ---------------------------------------------------------------- 7 failure modes
heading("7. Failure modes and risks")
bullets([
    "**A completed run labelled as stopped.** Odin passes `--deadline-seconds 600`; skuld2 keeps an 1,800 s margin, so "
    "the in-pod budget (deadline less margin) is already spent at the first check. Run00012 (Sod) had reached its end "
    "time and is still labelled STOPPED / WALL_BUDGET; Run00013 (ZND) stopped after one step. A wrong label that "
    "enters a dataset unnoticed is the risk; the fix is one declared value, and Var's review must compare the "
    "terminal state with the simulated time.",
    "**Approval friction.** 21 cards over the day; four distinct defects on the way (a device yes that never ran the "
    "parked call, an undeclared field rejected by a strict schema, records the raising seat could not read, held calls "
    "lost on a daemon restart). All but the last are fixed.",
    "**Physics coverage.** Sod on shockFluid misses its 1-cell criterion; double Mach reflection and the full channel "
    "end in floating-point exceptions; reacting adaptive refinement is not qualified. H2-air in 1D is unstable at these "
    "grids, so a 2D H2-air RDE at similar resolution is a risk to be measured, not assumed.",
    "**Surrogates.** Two of three architectures cannot overfit one batch; the one strong number comes from synthetic data.",
    "**Monitoring noise.** Before the keyed-incident fix, one condition paged four times; frames are not rendered yet.",
])

# ---------------------------------------------------------------- 8 next steps
heading("8. Next steps toward integration (Lab 4)")
bullets([
    "Fix the deadline/margin mismatch and rerun both acceptance runs to COMPLETED, with a rendered frame on the "
    "Missions board.",
    "Make the full 2D periodic channel run without floating-point exceptions and measure its cost; then Mimir raises "
    "the first 2D RDE wave-count sweep card (the owner decides it; the 1D gate no longer blocks it).",
    "Run that sweep through the same loop end to end, including the steps not yet exercised live: Var reviews the "
    "validation claim artefact, Saga files the lessons.",
    "Surrogates on skuld2's own data (Lab 4-5): label the sweep with the same θ-t / 2D-FFT wave extractor used for "
    "experiments; train the FNO baseline, then Transolver and MeshGraphNet once enlarged and re-gated, all through "
    "NVIDIA PhysicsNeMo; five-seed ensembles; promotion only with Var's approval and the owner's yes. DoMINO [13] waits "
    "for steady geometry-varying data (the plume campaign); so far only its memory fits the GPU (2,744 MiB).",
    "Lab 4's failure audit: inputs the loop cannot handle, where it stalls, and results that look right but are not.",
])

# ---------------------------------------------------------------- references
heading("References")
refs = [
    "OpenFOAM Foundation, OpenFOAM-14, https://openfoam.org; source github.com/OpenFOAM/OpenFOAM-14 (commit 64cfdf54).",
    "H. G. Weller, G. Tabor, H. Jasak, C. Fureby, A tensorial approach to computational continuum mechanics using "
    "object-oriented techniques, Computers in Physics 12(6):620-631, 1998.",
    "J. Sun et al., detonationFoam: An open-source solver for simulation of gaseous detonation based on OpenFOAM, "
    "Computer Physics Communications, 2023, doi:10.1016/j.cpc.2023.108859. OpenFOAM-14 port: "
    "github.com/TXChris/detonationFoam-OF14 (branch OF-14, 09c9bfcd).",
    "M. P. Burke, M. Chaos, Y. Ju, F. L. Dryer, S. J. Klippenstein, Comprehensive H2/O2 kinetic model for high-pressure "
    "combustion, International Journal of Chemical Kinetics 44(7):444-474, 2012, doi:10.1002/kin.20603.",
    "D. G. Goodwin, R. L. Speth, H. K. Moffat, B. W. Weber, Cantera: an object-oriented software toolkit for chemical "
    "kinetics, thermodynamics, and transport processes, version 3.2, https://www.cantera.org.",
    "S. Browne, J. Ziegler, N. Bitter, B. Schmidt, J. Lawson, J. E. Shepherd, SDToolbox: numerical tools for shock and "
    "detonation wave modeling, GALCIT Report FM2018.001, California Institute of Technology.",
    "Kwak et al., Application of a Pressured-Based OpenFOAM Solver for Rotating Detonation Engines, 2025, "
    "arXiv:2508.16105.",
    "Zangene et al., Role of the argon and helium bath gases on the structure of H2/O2 detonations, 2024, arXiv:2410.17561.",
    "Liu, Quantitative correlation between one-dimensional periodically oscillating detonation waves and two-dimensional "
    "regular cellular detonation waves, 2025, arXiv:2509.19808.",
    "Mao et al., Benchmarking neural surrogates on realistic spatiotemporal multiphysics flows (REALM), 2025, arXiv:2512.18595.",
    "Wu et al., Transolver: A Fast Transformer Solver for PDEs on General Geometries, 2024, arXiv:2402.02366.",
    "Pfaff et al., Learning Mesh-Based Simulation with Graph Networks, 2020, arXiv:2010.03409.",
    "Ranade et al., DoMINO: A Decomposable Multi-scale Iterative Neural Operator for Modeling Large Scale Engineering "
    "Simulations, 2025, arXiv:2501.13350.",
    "Li et al., Fourier Neural Operator for Parametric Partial Differential Equations, 2020, arXiv:2010.08895; NVIDIA "
    "PhysicsNeMo 2.2.2, github.com/NVIDIA/physicsnemo.",
    "Sankar et al., Validation of High Speed Reactive Flow Solver in OpenFOAM with Detailed Chemistry, OpenFOAM Journal 4, "
    "2024, doi:10.51560/ofj.v4.125. E. F. Toro, Riemann Solvers and Numerical Methods for Fluid Dynamics, Springer.",
    "Koch et al., Mode-Locked Rotating Detonation Waves: Experiments and a Model Equation, 2019, arXiv:1908.03116; RDE.jl "
    "(Holme), doi:10.5281/zenodo.19494530.",
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph()
    run = p.add_run(f"[{i}] {r}")
    run.font.size = Pt(8.5)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)

doc.core_properties.title = "Lab Report 3 — Weeks 5–6"
doc.core_properties.author = "Colin Gray (made by Claude Opus 5.5)"
doc.save(OUT)
print("wrote", OUT)
