"""Architecture diagrams D1-D6 (Graphviz for the box diagrams, matplotlib for the sequence). python diagrams/make_diagrams.py

Black on white, one accent (the path a skuld2 run takes), Liberation Sans. Each diagram is written as PDF, SVG and PNG.
Facts come from the project records cited in the report; the seat map's lanes and tool families were read from the
Odin registry with every [personal] line removed (see SEATS below).
"""
import pathlib

import graphviz
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = pathlib.Path(__file__).resolve().parent
INK, GRAY, LIGHT, ACCENT, TINT = "#1a1a1a", "#8a8a8a", "#f2f2f2", "#1B5FAA", "#e8eef7"
FONT = "Liberation Sans"


def graph(name, rankdir="LR", **attrs):
    g = graphviz.Digraph(name, format="pdf")
    base = dict(rankdir=rankdir, fontname=FONT, fontsize="11", bgcolor="white", pad="0.2", nodesep="0.35", ranksep="0.45")
    g.attr(**{**base, **attrs})
    g.attr("node", shape="box", style="rounded", fontname=FONT, fontsize="10", color=INK, penwidth="0.9", margin="0.12,0.06")
    g.attr("edge", fontname=FONT, fontsize="8.5", color=INK, penwidth="0.8", arrowsize="0.6")
    return g


def render(g, name):
    for fmt in ("pdf", "svg", "png"):
        g.format = fmt
        if fmt == "png":
            g.attr(dpi="200")
        g.render(OUT / name, cleanup=True)
    print("wrote", name)


def acc(**kw):  # the accent style: the skuld2 run path
    return dict(color=ACCENT, fontcolor=INK, penwidth="1.4", **kw)


# D1: full-system architecture
def d1():
    g = graph("d1", rankdir="TB", compound="true")
    with g.subgraph(name="cluster_mini") as m:
        m.attr(label="mini: always-on authority (k3s server, 12 ranks for CFD)", style="rounded", color=INK, fontsize="10")
        with m.subgraph(name="cluster_odin") as o:
            o.attr(label="Odin (Rust): the agent harness", style="rounded,filled", fillcolor=LIGHT, color=GRAY)
            o.node("odind", "odind\ndaemon, kernel, ledger\n(approvals, budgets, incidents)")
            o.node("registry", "registry (TOML)\nseats, lanes, workloads,\nmodel cards; published, no rebuild")
            o.node("huginn", "Huginn\nsessions, chat, phone,\nodin view")
            o.node("seats", "seats on the loom harness\nSinmara · Mimir · Kubert · Var · Saga\nGungnir · Forseti · Reginn ...")
            o.node("gateway", "model gateway (LiteLLM)\nlanes: terra, astra, zai-glm,\nglm-flash, local/* ...")
            o.node("brain", "brain / knowledge\nproject pages, lessons,\npaper corpus")
        m.node("skuld2", "skuld2 (Rust CLI + MCP adapter)\ncampaigns, cases, sweeps,\ncollect, datasets, surrogates", **acc())
        m.node("eggs", "skuld2-eggs (git)\nrun records, sweeps,\nsurrogate registry, bench", **acc())
        m.node("podmini", "OpenFOAM-14 pods\nskuld2-openfoam image\nfoamRun + detonationFluid", **acc())
    with g.subgraph(name="cluster_pc") as p:
        p.attr(label="pc: gaming desktop, burst compute (k3s agent)", style="rounded", color=INK, fontsize="10")
        p.node("podpc", "CFD pods when not gaming")
        p.node("gpu", "RTX 3070 8 GB\nsurrogate training\n(torch 2.14 + PhysicsNeMo 2.2.2)")
    g.node("laptop", "laptop\nviews, chat client")
    g.node("owner", "owner\n(phone, chat, CLI)", shape="ellipse")
    g.edge("owner", "huginn", label="asks, approves")
    g.edge("laptop", "huginn", label="odin view")
    g.edge("huginn", "odind")
    g.edge("odind", "seats", label="turns, wakes")
    g.edge("seats", "gateway", label="model calls")
    g.edge("registry", "odind", label="publication")
    g.edge("seats", "brain", label="search, notes", style="dashed")
    g.edge("seats", "skuld2", label="skuld2.* tools (MCP)", **acc())
    g.edge("odind", "podmini", label="kube.workload.create", **acc())
    g.edge("odind", "podpc", label="placement, gaming yield", style="dashed")
    g.edge("podmini", "odind", label="ODIN-STATUS, exports", **acc(style="dashed"))
    g.edge("skuld2", "eggs", label="collect, commit", **acc())
    g.edge("eggs", "gpu", label="datasets", style="dashed")
    g.edge("gpu", "eggs", label="surrogate rows", style="dashed")
    render(g, "d1_system_architecture")


# D2: the agent loop as a sequence diagram
def d2():
    lanes = ["Owner", "Sinmara", "Mimir", "Odin\n(ledger, cards)", "Kubert", "OpenFOAM pod", "skuld2-eggs", "Var", "Saga"]
    msgs = [  # (from, to, text, ran live on 2026-11-16/17?)
        (0, 1, "asks for the two acceptance campaigns", True),
        (1, 2, "seat.ask.mimir (delegates)", True),
        (2, 3, "skuld2.campaign_approve: card with bound values", True),
        (3, 0, "approval card (phone / chat / CLI)", True),
        (0, 3, "yes  (21 cards over the day; 3 pairs consumed)", True),
        (3, 6, "campaign approved (eggs commit)", True),
        (2, 6, "sweep_plan, sweep_stage: Run00010/11 CASE_BUILT", True),
        (4, 3, "kube.workload.create_many (campaign reservation)", True),
        (3, 5, "pod on mini (seat kubert, lane kubert-skuld2)", True),
        (5, 4, "1st launch: exit 2, no --deadline-seconds (fixed; -2 cards approved)", True),
        (4, 3, "incident.raise (stable key) / workload_watch wake", True),
        (3, 5, "2nd launch 03:37 UTC: Sod Run00012, ZND Run00013", True),
        (5, 4, "ODIN-STATUS samples, 10 checkpoints; Sod reaches end time", True),
        (5, 6, "collect: export -> run records COMMITTED (STOPPED/WALL_BUDGET)", True),
        (2, 7, "seat.ask.var: validation claim artifact", False),
        (7, 2, "verdict: approve / changes", False),
        (2, 8, "lessons, brain pages, validation matrix", False),
        (2, 1, "summary to the owner", False),
    ]
    n = len(lanes)
    fig, ax = plt.subplots(figsize=(11, 8.0))
    ax.set_xlim(-0.6, n - 0.4); ax.set_ylim(len(msgs) + 0.9, -1.1); ax.axis("off")
    for i, name in enumerate(lanes):
        ax.text(i, -0.55, name, ha="center", va="center", fontsize=9, family=FONT, color=INK,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=INK, lw=0.8))
        ax.plot([i, i], [0, len(msgs) + 0.5], color=GRAY, lw=0.6, ls=(0, (2, 3)))
    for k, (a, b, text, live) in enumerate(msgs):
        y = k + 0.6
        col = ACCENT if live else GRAY
        ax.annotate("", xy=(b, y), xytext=(a, y),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.3 if live else 1.0, ls="-" if live else "--",
                                    shrinkA=2, shrinkB=2, mutation_scale=9))
        ax.text((a + b) / 2, y - 0.17, f"{k + 1}. {text}", ha="center", va="bottom", fontsize=7.6, family=FONT, color=INK)
    ax.plot([], [], color=ACCENT, lw=1.3, label="ran live, 2026-11-16/17 (UTC), with the outcome shown")
    ax.plot([], [], color=GRAY, lw=1.0, ls="--", label="designed; exercised in earlier live checks, not yet on these campaigns")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=1, fontsize=8, frameon=False, prop={"family": FONT})
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"d2_agent_loop_sequence.{ext}", bbox_inches="tight", dpi=200, facecolor="white")
    plt.close(fig)
    print("wrote d2_agent_loop_sequence")


# D3: seat map (lanes are each seat's declared `models`, first = default; tool families from non-[personal] lines)
SEATS = [
    ("Sinmara", "coordinator", "the owner's assistant: chat, phone, delegation; asks the owner for decisions",
     "terra, glm-flash, gemini-hydrogen, astra, ...", "seat/task delegation, cfd toolset, kube, simulation, knowledge", "all"),
    ("Mimir", "coordinator", "science lead: proposes campaigns, plans and stages sweeps, owns validation status",
     "terra, astra, sol, zai-glm", "skuld2.* (case, sweep, campaign, dataset, surrogate), seat.ask.*, simulation", "skuld2"),
    ("Kubert", "operator", "cluster operator: launches approved cases, watches pods, raises incidents",
     "go-deepseek-flash, glm-flash, kubert-mini, astra, ...", "kube.workload.* (create, create_many, pause, steer, cancel), compute.lease.*, incident", "odin, skuld2"),
    ("Var", "judge", "independent science review of a dataset, promotion or validation claim",
     "zai-glm, gemini-hydrogen, glm-flash", "science review, artifact read, skuld2 status", "skuld2"),
    ("Saga", "builder", "curator: brain pages, lessons, literature, the validation matrix",
     "glm-flash, zai-glm, terra", "knowledge, data, docs, skuld2 lessons", "skuld2"),
    ("Gungnir", "builder", "writes code in its own clone, gets it reviewed, proposes the branch",
     "sol, zai-glm, kimi-k31, astra", "code, git, build, test, capsule", "odin, skuld2"),
    ("Forseti", "judge", "independent code review of a builder's exact diff",
     "sol, astra, zai-glm", "code, test, simulation read", "odin, skuld2"),
    ("Reginn", "builder", "geometry and CAD scripting (nozzles, injectors)",
     "sol, zai-glm, kimi-k31, astra", "code, git, capsule", "skuld2"),
    ("Supervisor", "coordinator", "watches project lanes and steers delegated work; never builds or merges",
     "terra, glm-flash, astra, zai-glm", "task, kube, simulation read", "odin, skuld2"),
]


def d3():
    rows = ['<tr><td align="left"><b>seat</b></td><td align="left"><b>kind</b></td><td align="left"><b>why it exists</b></td>'
            '<td align="left"><b>model lanes (first = default)</b></td><td align="left"><b>tool families</b></td>'
            '<td align="left"><b>project</b></td></tr>']
    for name, kind, role, lanes, tools, scope in SEATS:
        hi = name in ("Mimir", "Kubert", "Var", "Saga", "Sinmara")
        b = f'<font color="{ACCENT}"><b>{name}</b></font>' if hi else f"<b>{name}</b>"
        rows.append(f'<tr><td align="left">{b}</td><td align="left">{kind}</td><td align="left">{role}</td>'
                    f'<td align="left">{lanes}</td><td align="left">{tools}</td><td align="left">{scope}</td></tr>')
    label = ('<<table border="0" cellborder="1" cellspacing="0" cellpadding="5" color="#8a8a8a">'
             + "".join(rows) + '</table>>')
    g = graph("d3", rankdir="TB")
    g.node("t", label=label, shape="plaintext", fontsize="9")
    g.attr(label="accent: the seats in the simulation loop. Lanes and tool families from the Odin registry (personal-tagged lines "
           "removed); every seat runs with no shell and no network of its own; Odin grants and audits each call.",
           labelloc="b", fontsize="9", fontcolor=GRAY)
    render(g, "d3_seat_map")


# D4: validation ladder
def d4():
    g = graph("d4", rankdir="LR")
    passed = dict(color=ACCENT, penwidth="1.6")
    failed = dict(color=INK, style="rounded,dashed")
    g.node("c0", "0D ignition chemistry\nOpenFOAM-14 vs Cantera, Burke 2012\nPASS: +0.15 % (1539 K, 28 bar)\n-0.08 % (1300 K, 20 bar)", **passed)
    g.node("b1", "B1 CJ / ZND references\nSDToolbox, 49 mixtures × 2 mechanisms\nqualified PASS (6 pair misses\nat φ ≤ 0.73 recorded)", **passed)
    g.node("d1a", "1D ZND/CJ, 2H2:O2:7Ar 1 atm\ndetonationFluid, Co 0.1\nPASS: +0.296 % / +0.272 %\nerror falls with refinement", **passed)
    g.node("d1h", "1D H2-air φ=1 1 atm\nknown-unstable, not a gate\nfails to -23 % (shock frame,\ngrids within 0.4 %)", **failed)
    g.node("sod", "Sod, shockFluid\nFAIL: fan tail 1.31 cells\nat 1,000 cells (limit 1)\nESI KNP at Co 0.1 converges", **failed)
    g.node("dmr", "double Mach reflection\nFAIL / incomplete\nsqrt FPE in fluxPredictor", **failed)
    g.node("amr", "planarRefiner AMR\ntopology, mapping PASS\nreacting AMR not qualified", **failed)
    g.node("rde", "2D RDE wave-count sweep\nunblocked by the 1D gate;\nfull channel FPE'd; card\nnot yet raised (owner decides)", style="rounded,dashed", color=GRAY)
    g.node("sur", "surrogates on skuld2 data\nFNO / Transolver / MGN / DoMINO\n(Lab 4-5)", style="rounded,dashed", color=GRAY)
    g.edge("c0", "d1a"); g.edge("b1", "d1a"); g.edge("b1", "d1h", style="dashed")
    g.edge("d1a", "rde"); g.edge("sod", "rde", style="dashed"); g.edge("dmr", "rde", style="dashed"); g.edge("amr", "rde", style="dashed")
    g.edge("rde", "sur")
    with g.subgraph() as s:
        s.attr(rank="same"); s.node("c0"); s.node("b1")
    with g.subgraph() as s:
        s.attr(rank="same"); s.node("d1a"); s.node("d1h"); s.node("sod"); s.node("dmr"); s.node("amr")
    g.attr(label="accent border: passed its gate · dashed black: failed or incomplete (recorded, not waived) · grey: not started",
           labelloc="b", fontsize="9", fontcolor=GRAY)
    render(g, "d4_validation_ladder")


# D5: data and surrogate pipeline
def d5():
    g = graph("d5", rankdir="LR")
    g.node("of", "OpenFOAM-14 run\nin a pod (detonationFluid)", **acc())
    g.node("obs", "frozen observations\nhard-linked time dirs,\nsha256 per file, mesh digest", **acc())
    g.node("rec", "eggs run record\nCREATED ... COMMITTED,\nprovenance, access flag", **acc())
    g.node("ds", "dataset version\nfrom committed clean runs;\nrestricted never public")
    g.node("ext", "outside data\nREALM PlanarDet (2D det.)\nRDE.jl rings (2,048 runs)\nThe Well, RDE-72 (smoke)")
    g.node("lab", "one wave extractor\nθ-t surface, 2D FFT:\nwave count, direction, speed")
    g.node("exp", "experimental data\nTU Berlin Zenodo record,\nliterature: 151 rows, 90 labelled")
    g.node("tr", "training on pc's GPU\nPhysicsNeMo 2.2.2 / neuraloperator:\nFNO · Transolver · MeshGraphNet\n(DoMINO: memory profile only)")
    g.node("gate", "overfit gate, held-out eval,\nfive-seed ensembles")
    g.node("reg", "surrogate registry (eggs)\nexternal-baseline / candidate;\npromotion = Var approve + owner yes")
    g.node("ask", "skuld2.ask: wave count,\ndirection, speed for a new\ngeometry / condition (Lab 5)", style="rounded,dashed", color=GRAY)
    for a, b in [("of", "obs"), ("obs", "rec"), ("rec", "ds")]:
        g.edge(a, b, **acc())
    g.edge("ds", "tr"); g.edge("ext", "tr"); g.edge("ds", "lab"); g.edge("exp", "lab"); g.edge("lab", "tr", label="labels")
    g.edge("tr", "gate"); g.edge("gate", "reg"); g.edge("reg", "ask", style="dashed")
    g.edge("exp", "reg", label="fused: evaluate,\nfine-tune, residual", style="dashed")
    render(g, "d5_data_surrogate_pipeline")


# D6: Lab 2 -> Lab 3 continuity
def d6():
    lab2 = [
        ("churn", "idle churn: pod re-posts its answer,\nsettlement stays 0; seat re-asks"),
        ("loss", "carrier loss: Job gone before\nits deliverable was read"),
        ("egress", "egress block: target unreachable\nfrom the pod's network"),
        ("wall", "60-minute wall: every failure\nburned the full budget"),
        ("hb", "no progress heartbeat the\ndelegating seat can read"),
        ("trust", "deliverable ≠ evidence of it"),
    ]
    lab3 = [
        ("a_churn", "whole answers relayed (cap is a registry value, a cut is labelled);\nsteer cap: 3 steers without progress -> escalate once to the owner"),
        ("a_loss", "release needs an applied launch observation with a matching Job UID;\nskuld2 freezes each time dir by hard link before purge"),
        ("a_egress", "science pods need no egress: cases staged by manifest,\nresults exported to /export and collected"),
        ("a_wall", "deadline and core-hour cap declared per campaign (2 h / 2 core-h);\nledger refuses a launch past them (seen live 11-17)"),
        ("a_hb", "ODIN-STATUS numeric lines -> Missions board; workload_watch wakes Kubert;\nKubert heartbeat hourly when changed; incidents keyed (dedup)"),
        ("a_trust", "eggs run record with sha256 manifests; approval bound to card values;\nVar reviews a claim artifact before promotion"),
    ]
    g = graph("d6", rankdir="LR", nodesep="0.2")
    with g.subgraph(name="cluster_l2") as c:
        c.attr(label="Lab 2: 21 research-pod runs, 7 failures", style="rounded", color=GRAY, fontsize="10")
        for k, t in lab2:
            c.node(k, t, width="2.9")
    with g.subgraph(name="cluster_l3") as c:
        c.attr(label="Lab 3: the same supervision layer, now driving simulation pods", style="rounded", color=ACCENT, fontsize="10")
        for k, t in lab3:
            c.node(k, t, color=ACCENT, width="5.6")
    for (k, _), (a, _) in zip(lab2, lab3):
        g.edge(k, a, **acc())
    g.node("iface", "supervision interface:  launch · status · heartbeat · steer · stop · accept\n"
           "kube.workload.create(_many) · skuld2.run_status · ODIN-STATUS / workload_watch · run_steer (stop file, maxCo) · "
           "kube.workload.cancel · collect + Var review", shape="box", style="rounded,filled", fillcolor=TINT, color=ACCENT)
    g.edge("trust", "iface", style="invis")
    render(g, "d6_lab2_to_lab3")


if __name__ == "__main__":
    d1(); d2(); d3(); d4(); d5(); d6()
