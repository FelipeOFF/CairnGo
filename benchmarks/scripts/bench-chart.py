#!/usr/bin/env python3
"""bench-chart — render aggregated.json into two deterministic SVG charts:
a grouped cost-per-successful-run bar chart paired with pass-rate text, and
a 4-way token-composition stacked-bar chart. Stdlib only, hand-rolled SVG.

Usage:
    bench-chart.py --in <aggregated.json> --out-dir <dir> --label <caption>

Behavior:
    1. Validate before writing anything: --in must exist, parse as JSON, and
       carry a top-level "cells" key; --label must slugify to something
       non-empty (die EXIT_USAGE otherwise). Only then is --out-dir created
       via mkdir(parents=True, exist_ok=True) — chart generation spends
       nothing, so unlike bench-aggregate.py there is deliberately no
       "parent must pre-exist" validate-before-spend guard.
    2. Write exactly two files, <out-dir>/<slug>-cost.svg and
       <out-dir>/<slug>-tokens.svg, where <slug> is --label lowercased with
       every run of non-[a-z0-9] characters collapsed to a single "-" and
       stripped at both ends.
    3. cost.svg: one horizontal group per task_id (sorted), one bar per
       baseline_id within the group (sorted). Bar height scales linearly
       against the single largest cost_median across every cell (0 ->
       baseline, max -> full chart height). Every bar carries a
       class="bar-value" text ("$X.XXXX") and every bar OR no-data
       placeholder carries its own class="bar-passrate" text ("N/M (P%)")
       — never a bar without its pass rate.
    4. Honesty rule: a null cost_median (n_passed == 0 upstream) renders NO
       bar and NO value — a class="bar-nodata" text reading "no data"
       instead, still paired with its real pass-rate text. Absence of data
       is rendered as absence, never as a fabricated zero-height bar.
    5. tokens.svg: one vertical stacked bar per cell (sorted
       task_id::baseline_id key order), segments in the FIXED order input,
       cache_creation, cache_read, output — never keyed off dict iteration.
       Each segment is a class="token-seg-<name>" rect plus a same-class
       text with the integer-rounded median. A cell whose medians are all
       null renders the same "no data" marker and zero segments.
    6. Both documents open with a class="chart-caption" text holding the
       escaped --label verbatim — the ONLY source of model-id/date in the
       output. No timestamps, no random ids, elements emitted strictly in
       sorted key order: identical --in bytes and --label always produce
       byte-identical SVG bytes.
    7. Every interpolated string (label, task_id, baseline_id, category)
       passes through the shared xml_escape() before entering any attribute
       or text node.
    8. An empty "cells" object still writes two syntactically valid SVGs
       carrying the caption and a "no data collected yet" text.

Exit codes:
    0  both SVGs written
    2  usage error (missing/bad flags, unreadable or shapeless --in)
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2

# Fixed 4-segment order for the token-composition chart — a tuple constant,
# never derived from dict iteration, so the stack order can never drift.
TOKEN_SEGMENTS = ("input", "cache_creation", "cache_read", "output")

# One warm tonal palette: near-white paper, warm ink, and a single
# green-slate ramp for the token segments (darkest = input, lightest =
# output). No gradients, no shadows — flat honest fills only.
PAPER = "#fbfaf7"
INK = "#2b2723"
MUTED = "#6e675c"
AXIS = "#d8d2c6"
COST_FILL = "#48604f"
SEG_FILLS = {
    "input": "#2f4237",
    "cache_creation": "#4a6152",
    "cache_read": "#6f8672",
    "output": "#9db092",
}


def die(msg, code):
    print(f"[bench-chart] error: {msg}", file=sys.stderr)
    sys.exit(code)


def xml_escape(s):
    """Escape the four XML-reserved characters for text nodes AND attribute
    values. The single shared choke point for every interpolated string."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def slugify(label):
    """Lowercase, collapse every run of non-[a-z0-9] to one '-', strip
    dashes from both ends — the output-filename prefix."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def fmt(x):
    """Compact deterministic coordinate formatting (ints stay bare)."""
    return f"{x:g}"


def load_aggregated(path):
    """Validate and parse --in; die EXIT_USAGE before anything is written."""
    p = Path(path)
    if not p.is_file():
        die(f"--in file not found: {path}", EXIT_USAGE)
    try:
        data = json.loads(p.read_text())
    except (ValueError, OSError) as exc:
        die(f"--in is not valid JSON: {path} ({exc})", EXIT_USAGE)
    if not isinstance(data, dict) or "cells" not in data:
        die(f'--in is missing a top-level "cells" key: {path}', EXIT_USAGE)
    return data["cells"]


def min_canvas_w(label, title, floor):
    """Deterministic minimum canvas width: the caption (font 15) and title
    (font 12), drawn at x=36, must never overflow the right edge."""
    return max(floor,
               math.ceil(72 + 0.62 * 15 * len(str(label))),
               math.ceil(72 + 0.62 * 12 * len(title)))


def svg_open(width, height):
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
         f'role="img" font-family="ui-sans-serif, system-ui, sans-serif">'),
        (f'  <rect x="0" y="0" width="{width}" height="{height}" '
         f'fill="{PAPER}"/>'),
    ]


def header_lines(label, title):
    """Caption (the escaped --label, verbatim — the only date/model-id
    source in the document) plus a static chart title."""
    return [
        (f'  <text class="chart-caption" x="36" y="30" font-size="15" '
         f'font-weight="600" fill="{INK}">{xml_escape(label)}</text>'),
        (f'  <text class="chart-title" x="36" y="52" font-size="12" '
         f'fill="{MUTED}">{xml_escape(title)}</text>'),
    ]


def empty_doc(label, title):
    """Valid SVG for an empty cells object: caption + an honest notice."""
    width, height = min_canvas_w(label, title, 640), 200
    lines = svg_open(width, height) + header_lines(label, title)
    lines.append(f'  <text class="chart-empty" x="36" y="120" font-size="13" '
                 f'font-style="italic" fill="{MUTED}">'
                 f'no data collected yet</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def render_cost_svg(cells, label):
    """Grouped cost bars (one group per task, one bar per baseline) — every
    bar or no-data placeholder paired with its own pass-rate text. Pure
    function: same cells + label always returns the same string."""
    title = "cost per successful run (median USD) with pass rate"
    if not cells:
        return empty_doc(label, title)

    groups = {}
    for key in sorted(cells):
        cell = cells[key]
        groups.setdefault(cell["task_id"], []).append(cell)
    task_ids = sorted(groups)
    for task_id in task_ids:
        groups[task_id].sort(key=lambda c: c["baseline_id"])

    bar_w, bar_gap, group_gap = 64, 14, 46
    m_left, m_right, m_top = 36, 36, 96
    chart_h = 220
    axis_y = m_top + chart_h
    height = axis_y + 92
    group_w = {t: len(groups[t]) * bar_w + (len(groups[t]) - 1) * bar_gap
               for t in task_ids}
    bars_w = (m_left + sum(group_w.values())
              + group_gap * (len(task_ids) - 1) + m_right)
    width = max(bars_w, min_canvas_w(label, title, 460))

    costs = [c["cost_median"] for t in task_ids for c in groups[t]
             if c["cost_median"] is not None]
    max_cost = max(costs) if costs else None

    lines = svg_open(width, height) + header_lines(label, title)
    lines.append(f'  <line class="axis" x1="{m_left}" y1="{axis_y}" '
                 f'x2="{width - m_right}" y2="{axis_y}" stroke="{AXIS}" '
                 f'stroke-width="1.5" stroke-linecap="round"/>')

    # Center the bar run when the caption/title floor widened the canvas.
    x = m_left + (width - bars_w) / 2
    for task_id in task_ids:
        group_x = x
        for cell in groups[task_id]:
            cx = x + bar_w / 2
            cost = cell["cost_median"]
            if cost is None:
                # Honesty rule: null median -> no bar, no value — an
                # explicit marker, never a fabricated zero-height rect.
                lines.append(f'  <text class="bar-nodata" x="{fmt(cx)}" '
                             f'y="{axis_y - 10}" text-anchor="middle" '
                             f'font-size="11" font-style="italic" '
                             f'fill="{MUTED}">no data</text>')
            else:
                bar_h = chart_h * (cost / max_cost) if max_cost else 0.0
                bar_y = axis_y - bar_h
                value = f"${cost:.4f}"
                lines.append(f'  <rect class="bar-cost" x="{x}" '
                             f'y="{fmt(bar_y)}" width="{bar_w}" '
                             f'height="{fmt(bar_h)}" fill="{COST_FILL}"/>')
                lines.append(f'  <text class="bar-value" x="{fmt(cx)}" '
                             f'y="{fmt(bar_y - 8)}" text-anchor="middle" '
                             f'font-size="11" font-weight="600" '
                             f'fill="{INK}">{xml_escape(value)}</text>')
            rate = round(cell["pass_rate"] * 100)
            passrate = f'{cell["n_passed"]}/{cell["n_total"]} ({rate}%)'
            lines.append(f'  <text class="bar-passrate" x="{fmt(cx)}" '
                         f'y="{axis_y + 20}" text-anchor="middle" '
                         f'font-size="11" fill="{INK}">'
                         f'{xml_escape(passrate)}</text>')
            lines.append(f'  <text class="bar-baseline" x="{fmt(cx)}" '
                         f'y="{axis_y + 38}" text-anchor="middle" '
                         f'font-size="10" fill="{MUTED}">'
                         f'{xml_escape(cell["baseline_id"])}</text>')
            x += bar_w + bar_gap
        x -= bar_gap
        group_cx = group_x + group_w[task_id] / 2
        lines.append(f'  <text class="group-task" x="{fmt(group_cx)}" '
                     f'y="{axis_y + 62}" text-anchor="middle" '
                     f'font-size="12" font-weight="600" fill="{INK}">'
                     f'{xml_escape(task_id)}</text>')
        category = groups[task_id][0].get("category")
        if category is not None:
            lines.append(f'  <text class="group-category" '
                         f'x="{fmt(group_cx)}" y="{axis_y + 78}" '
                         f'text-anchor="middle" font-size="10" '
                         f'font-style="italic" fill="{MUTED}">'
                         f'{xml_escape(category)}</text>')
        x += group_gap

    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def render_tokens_svg(cells, label):
    """One stacked token-composition bar per cell in sorted key order,
    segments in the fixed TOKEN_SEGMENTS order, each with a color-keyed
    integer-rounded value beside the bar. Pure function."""
    title = "token composition per cell (median tokens per successful run)"
    if not cells:
        return empty_doc(label, title)

    keys = sorted(cells)
    bar_w, slot_gap = 64, 96
    m_left, m_right, m_top = 56, 56, 96
    value_col = 60  # room for the swatch + value text after the LAST bar
    chart_h = 240
    axis_y = m_top + chart_h
    height = axis_y + 96
    n = len(keys)
    bars_w = m_left + n * bar_w + (n - 1) * slot_gap + value_col + m_right
    width = max(bars_w, min_canvas_w(label, title, 460))

    totals = []
    for key in keys:
        meds = [cells[key]["tokens"].get(f"{s}_median")
                for s in TOKEN_SEGMENTS]
        present = [m for m in meds if m is not None]
        if present:
            totals.append(sum(present))
    max_total = max(totals) if totals else None

    lines = svg_open(width, height) + header_lines(label, title)
    lines.append(f'  <line class="axis" x1="{m_left}" y1="{axis_y}" '
                 f'x2="{width - m_right}" y2="{axis_y}" stroke="{AXIS}" '
                 f'stroke-width="1.5" stroke-linecap="round"/>')

    # Center the bar run when the caption/title floor widened the canvas.
    x = m_left + (width - bars_w) / 2
    for key in keys:
        cell = cells[key]
        cx = x + bar_w / 2
        meds = {s: cell["tokens"].get(f"{s}_median") for s in TOKEN_SEGMENTS}
        if all(meds[s] is None for s in TOKEN_SEGMENTS):
            # Honesty rule: all-null medians -> zero segments, one marker.
            lines.append(f'  <text class="bar-nodata" x="{fmt(cx)}" '
                         f'y="{axis_y - 10}" text-anchor="middle" '
                         f'font-size="11" font-style="italic" '
                         f'fill="{MUTED}">no data</text>')
        else:
            y_cursor = float(axis_y)
            for seg in TOKEN_SEGMENTS:
                value = meds[seg]
                if value is None:
                    continue
                seg_h = chart_h * (value / max_total) if max_total else 0.0
                y_cursor -= seg_h
                lines.append(f'  <rect class="token-seg-{seg}" x="{x}" '
                             f'y="{fmt(y_cursor)}" width="{bar_w}" '
                             f'height="{fmt(seg_h)}" '
                             f'fill="{SEG_FILLS[seg]}"/>')
            # Color-keyed value column beside the bar, fixed segment order.
            for i, seg in enumerate(TOKEN_SEGMENTS):
                value = meds[seg]
                if value is None:
                    continue
                row_y = m_top + 12 + i * 16
                sx = x + bar_w + 8
                lines.append(f'  <rect class="seg-swatch" x="{sx}" '
                             f'y="{row_y - 8}" width="8" height="8" '
                             f'fill="{SEG_FILLS[seg]}"/>')
                lines.append(f'  <text class="token-seg-{seg}" '
                             f'x="{sx + 13}" y="{row_y}" font-size="11" '
                             f'fill="{INK}">{round(value)}</text>')
        lines.append(f'  <text class="bar-task" x="{fmt(cx)}" '
                     f'y="{axis_y + 20}" text-anchor="middle" '
                     f'font-size="11" font-weight="600" fill="{INK}">'
                     f'{xml_escape(cell["task_id"])}</text>')
        lines.append(f'  <text class="bar-baseline" x="{fmt(cx)}" '
                     f'y="{axis_y + 36}" text-anchor="middle" '
                     f'font-size="10" fill="{MUTED}">'
                     f'{xml_escape(cell["baseline_id"])}</text>')
        x += bar_w + slot_gap

    legend_y = height - 18
    legend_x = m_left
    for seg in TOKEN_SEGMENTS:
        lines.append(f'  <rect class="legend-swatch" x="{legend_x}" '
                     f'y="{legend_y - 8}" width="8" height="8" '
                     f'fill="{SEG_FILLS[seg]}"/>')
        lines.append(f'  <text class="legend-label" x="{legend_x + 13}" '
                     f'y="{legend_y}" font-size="11" fill="{MUTED}">'
                     f'{seg}</text>')
        legend_x += 13 + 7 * len(seg) + 22

    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        prog="bench-chart",
        description="Render aggregated.json into two deterministic SVG "
                    "charts: grouped cost-per-successful-run bars paired "
                    "with pass-rate text, and 4-way token-composition "
                    "stacked bars.")
    parser.add_argument("--in", dest="in_path", required=True,
                        metavar="AGGREGATED_JSON",
                        help="aggregated.json written by bench-aggregate.py "
                             "— the only input")
    parser.add_argument("--out-dir", required=True, metavar="DIR",
                        help="output directory for <slug>-cost.svg and "
                             "<slug>-tokens.svg (created if missing)")
    parser.add_argument("--label", required=True, metavar="CAPTION",
                        help="model-id/date caption rendered verbatim into "
                             "both charts and slugified into the output "
                             "filenames")
    args = parser.parse_args()

    slug = slugify(args.label)
    if not slug:
        die("--label must contain at least one alphanumeric character",
            EXIT_USAGE)

    cells = load_aggregated(args.in_path)

    cost_svg = render_cost_svg(cells, args.label)
    tokens_svg = render_tokens_svg(cells, args.label)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in ((f"{slug}-cost.svg", cost_svg),
                      (f"{slug}-tokens.svg", tokens_svg)):
        path = out_dir / name
        path.write_text(doc)
        print(f"[bench-chart] wrote {path} ({len(cells)} cell(s))")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
