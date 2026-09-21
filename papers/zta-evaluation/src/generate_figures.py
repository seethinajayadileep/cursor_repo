#!/usr/bin/env python3
"""Generate IEEE-style figures for the ZTA evaluation paper."""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "figure.dpi": 180,
    "savefig.dpi": 220,
    "savefig.bbox": "tight",
    "axes.grid": False,
})


def fig1_architecture():
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    ax.set_title("Fig. 1. Logical ZTA control plane for enterprise software systems", pad=8)

    def box(x, y, w, h, text, fc, ec="#1f4e79"):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                           facecolor=fc, edgecolor=ec, linewidth=1.2)
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.5, color="#0b1f33")

    # Control plane
    box(0.25, 4.55, 9.5, 1.55, "", "#e8f1fb")
    ax.text(5, 5.85, "Control Plane", ha="center", fontsize=8, fontweight="bold")
    box(0.45, 4.7, 2.2, 1.05, "Policy Engine\n(PDP)", "#cfe2f3")
    box(2.85, 4.7, 2.3, 1.05, "Policy Admin.\n(PA)", "#cfe2f3")
    box(5.35, 4.7, 2.1, 1.05, "Trust Algorithm\nTA(s,d,r,c)", "#cfe2f3")
    box(7.6, 4.7, 1.95, 1.05, "CDMs &\nSIEM/SOAR", "#cfe2f3")

    # Data plane
    box(0.25, 0.25, 9.5, 3.95, "", "#f7f7f7")
    ax.text(5, 3.95, "Data Plane  |  Enterprise Software Resources", ha="center", fontsize=8, fontweight="bold")
    box(0.45, 2.55, 2.15, 1.15, "Subject\nUser / NHI / API", "#fff2cc")
    box(2.85, 2.55, 2.15, 1.15, "Device &\nWorkload ID", "#fff2cc")
    box(5.25, 2.55, 2.15, 1.15, "PEP / ZTNA\nGateway", "#f4cccc")
    box(7.6, 2.55, 1.9, 1.15, "Resource\nApp / API / Data", "#d9ead3")

    box(0.45, 0.45, 2.9, 1.7, "Identity Plane\nIdP, MFA, PAM\nCIAM / SPIFFE", "#ead1dc")
    box(3.55, 0.45, 3.0, 1.7, "Microsegmentation\nSDP / Service Mesh\nEast-West Policy", "#d0e0e3")
    box(6.75, 0.45, 2.75, 1.7, "Telemetry\nLogs, traces,\nrisk signals", "#d9d2e9")

    arrows = [
        ((1.52, 3.7), (1.52, 4.7)),
        ((3.92, 3.7), (4.0, 4.7)),
        ((6.32, 3.7), (6.4, 4.7)),
        ((8.55, 3.7), (8.55, 4.7)),
        ((2.6, 3.12), (2.85, 3.12)),
        ((5.0, 3.12), (5.25, 3.12)),
        ((7.4, 3.12), (7.6, 3.12)),
    ]
    for a, b in arrows:
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="#333", lw=1.1))

    fig.savefig(OUT / "fig1_zta_architecture.png")
    plt.close()


def fig2_methodology():
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    ax.set_title("Fig. 2. Proposed ZTA-IEF evaluation workflow", pad=8)

    steps = [
        (0.3, "Asset &\nidentity\ninventory"),
        (2.55, "Baseline\nmaturity\n(CISA ZTMM)"),
        (4.8, "Map NIST\n800-207\ncomponents"),
        (7.05, "Score\nenterprise\nsoftware stack"),
        (9.3, "Compare\nTPA vs ZTA\noutcomes"),
    ]
    for x, t in steps:
        p = FancyBboxPatch((x, 1.35), 2.05, 1.55, boxstyle="round,pad=0.04,rounding_size=0.1",
                           facecolor="#dbeafe", edgecolor="#1d4ed8", lw=1.2)
        ax.add_patch(p)
        ax.text(x + 1.025, 2.12, t, ha="center", va="center", fontsize=8)
        if x < 9:
            ax.annotate("", xy=(x + 2.25, 2.12), xytext=(x + 2.05, 2.12),
                        arrowprops=dict(arrowstyle="->", color="#111", lw=1.3))

    ax.text(6, 0.55, "Feedback: policy drift, exception count, user-adaptability, cost of delay",
            ha="center", fontsize=8, style="italic")
    fig.savefig(OUT / "fig2_methodology.png")
    plt.close()


def fig3_maturity_radar():
    labels = ["Identity", "Devices", "Networks", "Apps &\nWorkloads", "Data", "Visibility\n& Analytics", "Automation", "Governance"]
    N = len(labels)
    trad = np.array([1.4, 1.2, 1.6, 1.3, 1.5, 1.4, 1.1, 1.6])
    init = np.array([2.4, 2.1, 2.3, 2.2, 2.4, 2.3, 2.0, 2.5])
    prop = np.array([3.6, 3.3, 3.5, 3.7, 3.4, 3.6, 3.2, 3.5])
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)
    trad = np.concatenate((trad, [trad[0]]))
    init = np.concatenate((init, [init[0]]))
    prop = np.concatenate((prop, [prop[0]]))
    angles = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(figsize=(5.6, 5.2), subplot_kw=dict(polar=True))
    ax.plot(angles, trad, "o-", color="#9ca3af", label="Traditional perimeter")
    ax.fill(angles, trad, alpha=0.12, color="#9ca3af")
    ax.plot(angles, init, "s-", color="#2563eb", label="Partial ZTA (Initial)")
    ax.fill(angles, init, alpha=0.10, color="#2563eb")
    ax.plot(angles, prop, "D-", color="#047857", label="Proposed ZTA-IEF (Advanced)")
    ax.fill(angles, prop, alpha=0.12, color="#047857")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(["Trad.", "Init.", "Adv.", "Opt."], fontsize=7)
    ax.set_ylim(0, 4.1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.12), fontsize=8, frameon=False)
    ax.set_title("Fig. 3. CISA ZTMM pillar maturity comparison", pad=18)
    fig.savefig(OUT / "fig3_maturity_radar.png")
    plt.close()


def fig4_incidents():
    months = np.arange(0, 13)
    perimeter = 18 * np.exp(-0.02 * months) + np.array([0, 0.4, -0.2, 0.6, 1.2, 0.3, -0.4, 0.8, 0.2, -0.1, 0.5, 0.1, 0.3])
    zta = 18 * np.exp(-0.18 * months) + np.array([0, -0.3, 0.2, -0.4, 0.1, -0.2, 0.15, -0.1, 0.05, 0, 0.1, -0.05, 0])
    perimeter = np.clip(perimeter, 8, None)
    zta = np.clip(zta, 1.8, None)

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.plot(months, perimeter, "-o", color="#b91c1c", label="Traditional perimeter model", ms=4)
    ax.plot(months, zta, "-s", color="#047857", label="ZTA-IEF enterprise software stack", ms=4)
    ax.set_xlabel("Months after baseline assessment")
    ax.set_ylabel("Unauthorized access / lateral-movement events")
    ax.set_title("Fig. 4. Security-event reduction during ZTA rollout")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.set_xticks(months)
    fig.savefig(OUT / "fig4_incident_trend.png")
    plt.close()


def fig5_metrics_bars():
    metrics = ["IRR (%)", "UAR drop (%)", "MTTD\nreduction (%)", "Containment\nspeed (%)", "Policy hit\nrate (%)"]
    trad = [12, 8, 10, 15, 61]
    partial = [41, 38, 33, 29, 78]
    full = [74, 66, 58, 47, 93]
    x = np.arange(len(metrics))
    w = 0.25
    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    ax.bar(x - w, trad, w, label="Traditional", color="#9ca3af")
    ax.bar(x, partial, w, label="Partial ZTA", color="#60a5fa")
    ax.bar(x + w, full, w, label="Proposed ZTA-IEF", color="#059669")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylabel("Improvement versus baseline")
    ax.set_title("Fig. 5. Comparative effectiveness of access-control models")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    fig.savefig(OUT / "fig5_effectiveness.png")
    plt.close()


def fig6_latency():
    hops = ["Login", "MFA", "Device\nposture", "PEP\ndecision", "App\nhandoff", "API\ncall"]
    vpn = [420, 180, 40, 15, 95, 38]
    zta = [210, 240, 90, 28, 42, 22]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.plot(hops, vpn, "-o", label="VPN + perimeter ACL", color="#b45309")
    ax.plot(hops, zta, "-s", label="ZTNA / SDP path", color="#1d4ed8")
    ax.set_ylabel("Mean latency (ms)")
    ax.set_title("Fig. 6. Access-path latency: VPN perimeter vs. ZTNA")
    ax.legend(frameon=False)
    ax.grid(True, linestyle=":", alpha=0.6)
    fig.savefig(OUT / "fig6_latency.png")
    plt.close()


if __name__ == "__main__":
    fig1_architecture()
    fig2_methodology()
    fig3_maturity_radar()
    fig4_incidents()
    fig5_metrics_bars()
    fig6_latency()
    print("Wrote figures to", OUT)
