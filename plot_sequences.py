#!/usr/bin/env python3
"""Plot the fresh b-file columns as a self-contained SVG for the README."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
SEQUENCES = (
    ("gap", "Gap", "A002386", "#0072B2", ""),
    ("lonely", "Lonely", "A023186", "#D55E00", ""),
    ("aloof", "Aloof", "A096265", "#009E73", ""),
    ("equidistant", "Equidistant", "A058867", "#7B61A8", ""),
    ("balanced", "Balanced lonely", "new", "#B8860B", "7 5"),
    ("pairwise", "Pairwise", "A087770", "#B34770", "3 5"),
)
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def element(parent: ET.Element, name: str, **attrs: object) -> ET.Element:
    return ET.SubElement(parent, f"{{{NS}}}{name}", {key.replace("_", "-"): str(value) for key, value in attrs.items()})


def label(parent: ET.Element, text: str, x: float, y: float, **attrs: object) -> None:
    node = element(parent, "text", x=x, y=y, **attrs)
    node.text = text


def read_terms(path: Path) -> list[tuple[int, int]]:
    terms = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        n, prime, *_ = line.split()
        terms.append((int(n), int(prime)))
    if not terms or any(n != i or prime < 2 for i, (n, prime) in enumerate(terms, 1)):
        raise ValueError(f"invalid b-file terms in {path}")
    return terms


def build_svg(source: Path) -> ET.Element:
    data = [(name, title, oeis, color, dash, read_terms(source / f"{name}.txt"))
            for name, title, oeis, color, dash in SEQUENCES]
    max_n = max(terms[-1][0] for *_, terms in data)
    max_prime = max(terms[-1][1] for *_, terms in data)

    width, height = 1100, 700
    left, right, top, bottom = 118, 1058, 164, 570
    log_max = math.log10(max_prime * 1.45)

    def x(n: int) -> float:
        return left + (n - 1) / (max_n - 1) * (right - left)

    def y(prime: int) -> float:
        return bottom - math.log10(prime) / log_max * (bottom - top)

    svg = ET.Element(f"{{{NS}}}svg", {
        "width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}",
        "role": "img", "aria-labelledby": "chart-title chart-desc",
        "font-family": "system-ui, -apple-system, sans-serif",
    })
    element(svg, "title", id="chart-title").text = "Prime record sequences from fresh b-files"
    element(svg, "desc", id="chart-desc").text = (
        "Six color-coded sequences show prime p against term number n. "
        "The vertical axis is logarithmic. The key lists each sequence and its term count."
    )
    element(svg, "rect", width=width, height=height, fill="#FFFFFF")
    label(svg, "Prime record sequences", left, 48, fill="#17212B", font_size=30, font_weight=600)
    label(svg, "Prime p at term n · logarithmic vertical axis", left, 76,
          fill="#52616D", font_size=18)

    for i, (_, title, oeis, color, dash, terms) in enumerate(data):
        column, row = i % 3, i // 3
        lx, ly = left + column * 315, 111 + row * 30
        line_attrs = {"x1": lx, "x2": lx + 37, "y1": ly - 5, "y2": ly - 5,
                      "stroke": color, "stroke_width": 3.5, "stroke_linecap": "round"}
        if dash:
            line_attrs["stroke_dasharray"] = dash
        element(svg, "line", **line_attrs)
        element(svg, "circle", cx=lx + 19, cy=ly - 5, r=3.5, fill=color)
        label(svg, f"{title} · {oeis} ({len(terms)})", lx + 46, ly,
              fill="#17212B", font_size=17)

    # Powers of ten remain legible at README width; minor grid lines add clutter.
    for exponent in range(0, math.floor(log_max) + 1, 2):
        value = 10 ** exponent
        gy = y(value)
        element(svg, "line", x1=left, x2=right, y1=f"{gy:.2f}", y2=f"{gy:.2f}",
                stroke="#E2E7EB", stroke_width=1)
        label(svg, f"10^{exponent}", left - 14, gy + 6, text_anchor="end",
              fill="#394A56", font_size=17)

    for n in range(10, max_n + 1, 10):
        gx = x(n)
        element(svg, "line", x1=f"{gx:.2f}", x2=f"{gx:.2f}", y1=top, y2=bottom,
                stroke="#EEF1F3", stroke_width=1)
        label(svg, str(n), gx, bottom + 29, text_anchor="middle",
              fill="#394A56", font_size=17)

    element(svg, "rect", x=left, y=top, width=right - left, height=bottom - top,
            fill="none", stroke="#A8B4BC", stroke_width=1)

    for _, title, _, color, dash, terms in data:
        path = " ".join(("M" if i == 0 else "L") + f"{x(n):.2f},{y(prime):.2f}"
                        for i, (n, prime) in enumerate(terms))
        attrs = {"d": path, "fill": "none", "stroke": color, "stroke_width": 2.6,
                 "stroke_linejoin": "round", "stroke_linecap": "round",
                 "aria_label": title}
        if dash:
            attrs["stroke_dasharray"] = dash
        element(svg, "path", **attrs)
        for n, prime in terms:
            element(svg, "circle", cx=f"{x(n):.2f}", cy=f"{y(prime):.2f}",
                    r=3.2 if dash else 2.5, fill=color)

    label(svg, "Term number n", (left + right) / 2, 640, text_anchor="middle",
          fill="#17212B", font_size=21)
    label(svg, "Prime p (log scale)", 34, (top + bottom) / 2,
          transform=f"rotate(-90 34 {(top + bottom) / 2})", text_anchor="middle",
          fill="#17212B", font_size=21)
    label(svg, "Source: fresh/*.txt · first two columns (n, p) · run make graph to refresh",
          left, 679, fill="#52616D", font_size=14)
    return svg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "fresh")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "prime-sequences.svg")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(build_svg(args.source))
    ET.indent(tree, space="  ")
    tree.write(args.output, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
