"""Generate schematic economic diagrams and fallback educational cards."""
from io import BytesIO
import textwrap
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def render(entry):
    name = entry["term"]
    key = name.casefold()
    fig, ax = plt.subplots(figsize=(9, 5.4), dpi=120)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f7fafc")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.15)
    ax.set_title(name, fontsize=18, fontweight="bold", pad=15)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_xticks([])
    ax.set_yticks([])
    x = np.linspace(0.4, 9.5, 300)
    specific = True
    note = "Illustrative diagram — not empirical data"
    if "cobb" in key or key in {"convex preferences", "tangency condition", "homothetic preferences"}:
        ax.set_xlabel("Good X")
        ax.set_ylabel("Good Y")
        for c in (8, 16, 24):
            y = c / x
            ax.plot(x, np.where(y <= 10, y, np.nan), lw=2)
        if "cobb" in key or key == "tangency condition":
            ax.plot([0, 9], [9, 0], color="#dc7c32", lw=2.5, label="Budget line")
            ax.scatter([4.5], [4.5], color="#dc7c32", s=50, zorder=5)
            ax.legend(frameon=False)
        note = "Example: u(x,y)=xy; indifference curves and a budget line"
    elif key == "giffen good":
        ax.set_xlabel("Quantity demanded")
        ax.set_ylabel("Price")
        ax.plot([2, 8], [2, 8], lw=3, color="#1763a6")
        note = "Giffen demand: income effect outweighs substitution effect"
    elif key in {"engel curve", "income offer curve", "expansion path"}:
        ax.set_xlabel("Income / output target")
        ax.set_ylabel("Quantity / input use")
        ax.plot(x, 0.8*x + 1, lw=3, color="#1763a6")
        note = "Illustrative relationship; actual shape depends on preferences or technology"
    elif key in {"monopoly deadweight loss", "marginal revenue", "lerner index", "monopoly markup rule", "natural monopoly"}:
        q = np.linspace(0, 9, 200)
        ax.set_xlabel("Output")
        ax.set_ylabel("Price / Cost")
        ax.plot(q, 9-0.8*q, label="Demand", color="#1763a6")
        ax.plot(q, 9-1.6*q, label="Marginal revenue", color="#dc7c32")
        ax.axhline(3, label="Constant MC", color="#228b70")
        ax.legend(frameon=False)
    elif key in {"tax wedge", "tax incidence", "specific tax", "pigouvian tax", "marginal social cost", "marginal external cost"}:
        q = np.linspace(0, 9, 200)
        ax.set_xlabel("Quantity")
        ax.set_ylabel("Price / Cost")
        ax.plot(q, 9-0.8*q, label="Marginal benefit", color="#1763a6")
        ax.plot(q, 1+0.6*q, label="Private MC", color="#228b70")
        ax.plot(q, 3+0.6*q, label="MC + external cost / tax", color="#dc7c32")
        ax.legend(frameon=False, fontsize=9)
    elif key in {"isoquant", "marginal rate of technical substitution", "cost-minimizing input mix", "conditional factor demand", "fixed-proportions technology"}:
        ax.set_xlabel("Labor")
        ax.set_ylabel("Capital")
        if key == "fixed-proportions technology":
            ax.plot([3,3,9], [9,3,3], lw=3)
            ax.plot([5,5,9], [9,5,5], lw=2)
        else:
            for c in (12,20,28):
                ax.plot(x, np.where(c/x <= 10, c/x, np.nan), lw=2)
    elif key in {"cournot equilibrium", "best response", "strategic substitutes", "strategic complements"}:
        ax.set_xlabel("Firm 1 output")
        ax.set_ylabel("Firm 2 output")
        q = np.linspace(0, 9, 200)
        if key == "strategic complements":
            ax.plot(q, 1+0.6*q, label="Increasing best response")
        else:
            ax.plot(q, 8-0.7*q, label="Firm 2 best response")
            ax.plot(q, 11-1.6*q, label="Firm 1 best response")
            ax.scatter([10/3],[17/3],color="#dc7c32",s=55,zorder=5)
        ax.legend(frameon=False)
    elif key in {"production possibility frontier", "marginal rate of transformation"}:
        ax.set_xlabel("Good X")
        ax.set_ylabel("Good Y")
        q = np.linspace(0, 9, 200)
        ax.plot(q, 9*np.sqrt(1-(q/10)**2), lw=3)
    else:
        specific = False
        ax.axis("off")
        ax.set_title("")
        fig.text(0.08, 0.79, "MICROECONOMICS • CONCEPT CARD", fontsize=12, color="#1763a6", weight="bold")
        fig.text(0.08, 0.62, "\n".join(textwrap.wrap(name, 30)), fontsize=25, color="#1a2c42", weight="bold", va="center")
        fig.text(0.08, 0.38, "KEY IDEA", fontsize=11, color="#dc7c32", weight="bold")
        fig.text(0.08, 0.32, "\n".join(textwrap.wrap(entry["definition"], 77)[:6]), fontsize=12, color="#1a2c42", va="top", linespacing=1.5)
        note = "Varian vocabulary • educational illustration"
    fig.text(0.5, 0.035, note, ha="center", fontsize=9, color="#64748b")
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf, specific
