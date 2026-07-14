"""Curve plots for route scoring model evaluation."""

from __future__ import annotations

from html import escape
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

from algorithm.model.utils.score_mixing import PREFERENCE_MIX, SCORE_NAMES


LABEL_COLOR = "#2563eb"
PREDICTION_COLOR = "#dc2626"
GRID_COLOR = "#e5e7eb"
TEXT_COLOR = "#111827"
MUTED_TEXT_COLOR = "#6b7280"


def build_score_curve_frames(
    route_eval: pd.DataFrame,
    ranking_eval: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    preference: str = "balanced",
) -> dict[str, pd.DataFrame]:
    route_scores = route_eval[["candidate_group_id", "route_id", *SCORE_NAMES]].merge(
        predictions,
        on=["candidate_group_id", "route_id"],
        how="inner",
        validate="one_to_one",
    )
    curves: dict[str, pd.DataFrame] = {}
    for score_name in SCORE_NAMES:
        curves[score_name] = pd.DataFrame(
            {
                "label": route_scores[score_name].astype(float),
                "prediction": route_scores[f"pred_{score_name}"].astype(float),
            }
        )

    preference_rows = ranking_eval[ranking_eval["preference"].astype(str) == preference].copy()
    if not preference_rows.empty:
        recommend = preference_rows[["candidate_group_id", "route_id", "recommend_score"]].merge(
            predictions,
            on=["candidate_group_id", "route_id"],
            how="inner",
            validate="one_to_one",
        )
        pred_scores = recommend[[f"pred_{name}" for name in SCORE_NAMES]].to_numpy(dtype=float)
        recommend["pred_recommend_score"] = pred_scores @ PREFERENCE_MIX[preference]
        curves[f"recommend_score_{preference}"] = pd.DataFrame(
            {
                "label": recommend["recommend_score"].astype(float),
                "prediction": recommend["pred_recommend_score"].astype(float),
            }
        )
    return curves


def _sample_curve(frame: pd.DataFrame, max_points: int) -> pd.DataFrame:
    clean = frame.dropna(subset=["label", "prediction"]).sort_values("label").reset_index(drop=True)
    if max_points > 0 and len(clean) > max_points:
        positions = np.linspace(0, len(clean) - 1, max_points).round().astype(int)
        clean = clean.iloc[np.unique(positions)].reset_index(drop=True)
    return clean


def _polyline(values: np.ndarray, *, left: int, top: int, width: int, height: int) -> str:
    if len(values) == 0:
        return ""
    x_scale = width / max(len(values) - 1, 1)
    clipped = np.clip(values, 0.0, 100.0)
    points = []
    for index, value in enumerate(clipped):
        x = left + index * x_scale
        y = top + height - (float(value) / 100.0) * height
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def write_score_curve_svg(
    curves: dict[str, pd.DataFrame],
    output_path: Path,
    *,
    title: str,
    max_points: int = 400,
) -> None:
    names = list(curves)
    if not names:
        raise ValueError("No curves available to plot")

    columns = 2
    panel_width = 520
    panel_height = 260
    plot_left_pad = 58
    plot_right_pad = 24
    plot_top_pad = 44
    plot_bottom_pad = 42
    title_height = 78
    rows = ceil(len(names) / columns)
    width = columns * panel_width
    height = title_height + rows * panel_height + 24

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="32" y="34" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="{TEXT_COLOR}">{escape(title)}</text>',
        f'<text x="32" y="58" font-family="Arial, sans-serif" font-size="13" fill="{MUTED_TEXT_COLOR}">X-axis: evaluation samples sorted by label value. Y-axis: score value.</text>',
        f'<line x1="{width - 210}" y1="33" x2="{width - 174}" y2="33" stroke="{LABEL_COLOR}" stroke-width="3"/>',
        f'<text x="{width - 166}" y="38" font-family="Arial, sans-serif" font-size="13" fill="{TEXT_COLOR}">label</text>',
        f'<line x1="{width - 110}" y1="33" x2="{width - 74}" y2="33" stroke="{PREDICTION_COLOR}" stroke-width="3"/>',
        f'<text x="{width - 66}" y="38" font-family="Arial, sans-serif" font-size="13" fill="{TEXT_COLOR}">prediction</text>',
    ]

    for curve_index, name in enumerate(names):
        row = curve_index // columns
        column = curve_index % columns
        panel_x = column * panel_width
        panel_y = title_height + row * panel_height
        plot_left = panel_x + plot_left_pad
        plot_top = panel_y + plot_top_pad
        plot_width = panel_width - plot_left_pad - plot_right_pad
        plot_height = panel_height - plot_top_pad - plot_bottom_pad
        curve = _sample_curve(curves[name], max_points)

        parts.append(f'<text x="{panel_x + 24}" y="{panel_y + 24}" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="{TEXT_COLOR}">{escape(name)}</text>')
        parts.append(f'<rect x="{plot_left}" y="{plot_top}" width="{plot_width}" height="{plot_height}" fill="#ffffff" stroke="{GRID_COLOR}"/>')

        for tick in (0, 25, 50, 75, 100):
            y = plot_top + plot_height - (tick / 100.0) * plot_height
            parts.append(f'<line x1="{plot_left}" y1="{y:.2f}" x2="{plot_left + plot_width}" y2="{y:.2f}" stroke="{GRID_COLOR}" stroke-width="1"/>')
            parts.append(f'<text x="{plot_left - 10}" y="{y + 4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="{MUTED_TEXT_COLOR}">{tick}</text>')

        if len(curve):
            label_points = _polyline(curve["label"].to_numpy(dtype=float), left=plot_left, top=plot_top, width=plot_width, height=plot_height)
            prediction_points = _polyline(curve["prediction"].to_numpy(dtype=float), left=plot_left, top=plot_top, width=plot_width, height=plot_height)
            parts.append(f'<polyline points="{label_points}" fill="none" stroke="{LABEL_COLOR}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
            parts.append(f'<polyline points="{prediction_points}" fill="none" stroke="{PREDICTION_COLOR}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>')

        parts.append(f'<text x="{plot_left + plot_width / 2:.2f}" y="{panel_y + panel_height - 12}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="{MUTED_TEXT_COLOR}">samples sorted by label</text>')
        parts.append(f'<text x="{panel_x + 16}" y="{plot_top + plot_height / 2:.2f}" transform="rotate(-90 {panel_x + 16} {plot_top + plot_height / 2:.2f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="{MUTED_TEXT_COLOR}">score</text>')

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_score_curve_png(
    curves: dict[str, pd.DataFrame],
    output_path: Path,
    *,
    title: str,
    max_points: int = 400,
) -> None:
    names = list(curves)
    if not names:
        raise ValueError("No curves available to plot")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is not installed. Run `uv sync --extra algorithm` or install matplotlib in .venv."
        ) from exc

    columns = 2
    rows = ceil(len(names) / columns)
    figure, axes = plt.subplots(rows, columns, figsize=(14, 3.6 * rows), squeeze=False)
    figure.suptitle(title, fontsize=16, fontweight="bold")

    for curve_index, name in enumerate(names):
        axis = axes[curve_index // columns][curve_index % columns]
        curve = _sample_curve(curves[name], max_points)
        x = np.arange(len(curve))
        axis.plot(x, curve["label"].to_numpy(dtype=float), color=LABEL_COLOR, linewidth=1.9, label="label")
        axis.plot(
            x,
            curve["prediction"].to_numpy(dtype=float),
            color=PREDICTION_COLOR,
            linewidth=1.7,
            alpha=0.9,
            label="prediction",
        )
        axis.set_title(name, fontsize=11, fontweight="bold")
        axis.set_xlabel("samples sorted by label")
        axis.set_ylabel("score")
        axis.set_ylim(0, 100)
        axis.grid(True, color=GRID_COLOR, linewidth=0.8)
        axis.legend(loc="best", frameon=False)

    for empty_index in range(len(names), rows * columns):
        axes[empty_index // columns][empty_index % columns].axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
