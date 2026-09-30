"""Publication figures rendered by the engine (matplotlib) so UI, exports and PDF all agree."""
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from app.interpretation import CONFIDENCE_LEVELS, get_lithology  # noqa: E402

plt.rcParams.update({
    "font.family": "DejaVu Sans Mono", "font.size": 9, "hatch.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False, "svg.hashsalt": "ves-studio",
})
STATUS_STYLE = {"PASS": ("#2563eb", "o"), "WARNING": ("#d97706", "D"), "EXCLUDED": ("#9ca3af", "x")}


def _save(fig, fmt: str, dpi: int = 200) -> bytes:
    if fmt not in ("png", "svg"):
        raise ValueError("Figure format must be 'png' or 'svg'.")
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight", facecolor="white",
                metadata={"Date": None} if fmt == "svg" else None)
    plt.close(fig)
    return buf.getvalue()


def spacing_column(table):
    for c in ("ab_half_m", "a_m", "x_m", "ab_m"):
        if c in table.columns:
            return c
    raise ValueError("No spacing column in table.")


def curve_figure(table, result=None, fmt: str = "png", title: str | None = None) -> bytes:
    key = spacing_column(table)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ok = table[(table.apparent_resistivity > 0)]
    for status, (color, marker) in STATUS_STYLE.items():
        d = ok[ok.qc_status == status]
        if len(d):
            ax.scatter(d[key], d.apparent_resistivity, c=color, marker=marker, s=26,
                       label={"PASS": "observed", "WARNING": "observed (warning)",
                              "EXCLUDED": "excluded by user"}[status], zorder=3)
    if result is not None:
        ax.plot(result.spacing, result.model_response, color="#059669", lw=1.8, label="model response", zorder=2)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Electrode spacing (m)"); ax.set_ylabel("Apparent resistivity (Ωm)")
    ax.grid(True, which="both", color="#e5e7eb", lw=0.5)
    if title:
        ax.set_title(title, fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="best")
    return _save(fig, fmt)


def column_figure(result, interpretation: list[dict] | None = None, fmt: str = "png",
                  title: str | None = None) -> bytes:
    """Geological column: stacked layers with lithology colour + hatch, depth scale, annotations."""
    n = len(result.resistivity)
    interp = list(interpretation or [])[:n] + [{}] * max(0, n - len(interpretation or []))
    last_top = float(result.depth_top[-1])
    total = max(last_top * 1.5, last_top + 5.0)
    fig, ax = plt.subplots(figsize=(6.4, max(4.0, min(9.0, 0.45 * total + 2.5))))
    col_w = 1.0
    for i in range(n):
        top = float(result.depth_top[i])
        bot = float(result.depth_bottom[i]) if result.depth_bottom[i] is not None and result.depth_bottom[i] != float("inf") else total
        lit = get_lithology(interp[i].get("lithology") or "unclassified")
        ax.add_patch(Rectangle((0, top), col_w, bot - top, facecolor=lit.color, edgecolor="#222222",
                               hatch=lit.hatch, lw=1.0))
        mid = (top + bot) / 2
        thick = "half-space" if i == n - 1 else f"h = {float(result.thickness[i]):.3g} m"
        conf = interp[i].get("confidence")
        name = lit.name if lit.id != "unclassified" else "Unclassified"
        conf_txt = f" ({conf} confidence)" if conf in CONFIDENCE_LEVELS and lit.id != "unclassified" else ""
        ax.text(col_w + 0.08, mid, f"Layer {i + 1}: {name}{conf_txt}\nρ = {float(result.resistivity[i]):.3g} Ωm · {thick}",
                va="center", ha="left", fontsize=8)
        if i < n - 1:
            ax.plot([-0.12, col_w], [bot, bot], color="#222222", lw=0.8)
            ax.text(-0.15, bot, f"{bot:.3g}", ha="right", va="center", fontsize=8)
    ax.text(-0.15, 0, "0", ha="right", va="center", fontsize=8)
    ax.set_xlim(-0.6, 3.6); ax.set_ylim(total, 0)
    ax.set_xticks([]); ax.set_ylabel("Depth (m)")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_yticks([])
    ax.annotate("", xy=(col_w / 2, total), xytext=(col_w / 2, total - total * 0.05),
                arrowprops=dict(arrowstyle="->", color="#222222"))
    ax.set_title(title or "Interpreted 1D geological column", fontsize=9, loc="left")
    ax.set_xlabel("Resistivity-derived model: lithology is interpretation, not measurement.",
                  fontsize=7, color="#555555", labelpad=8)
    return _save(fig, fmt)


def legend_figure(lithology_ids: list[str], fmt: str = "png") -> bytes:
    n = max(1, len(lithology_ids))
    fig, ax = plt.subplots(figsize=(3.6, 0.42 * n + 0.2))
    for k, lid in enumerate(lithology_ids):
        l = get_lithology(lid)
        ax.add_patch(Rectangle((0, -k), 1.0, 0.85, facecolor=l.color, edgecolor="#222222", hatch=l.hatch, lw=0.8))
        ax.text(1.2, -k + 0.42, l.name, va="center", fontsize=8)
    ax.set_xlim(0, 7); ax.set_ylim(-n + 0.6, 1); ax.axis("off")
    return _save(fig, fmt)
