"""Render dependency-free PNG/SVG report images from the bundled sample."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from portfolio_risk_analytics import analyze_portfolio

OUT = Path(__file__).resolve().parent
NAVY = (23, 42, 69)
BLUE = (46, 112, 220)
TEAL = (31, 164, 151)
MUTED = (103, 119, 139)
GRID = (225, 232, 240)
PALE = (244, 248, 252)
WHITE = (255, 255, 255)
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00100", "01000"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
}


class Canvas:
    def __init__(self, width: int = 1200, height: int = 760):
        self.width, self.height = width, height
        self.pixels = bytearray(WHITE * (width * height))

    def rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        for yy in range(max(0, y), min(self.height, y + h)):
            start = (yy * self.width + max(0, x)) * 3
            end = (yy * self.width + min(self.width, x + w)) * 3
            self.pixels[start:end] = bytes(color) * max(0, min(self.width, x + w) - max(0, x))

    def line(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thickness: int = 2) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.rect(x0 - thickness // 2, y0 - thickness // 2, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * err
            if twice >= dy:
                err += dy
                x0 += sx
            if twice <= dx:
                err += dx
                y0 += sy

    def text(self, x: int, y: int, value: str, color: tuple[int, int, int] = NAVY, scale: int = 2) -> None:
        cursor = x
        for char in value.upper():
            glyph = FONT.get(char)
            if glyph:
                for row, bits in enumerate(glyph):
                    for column, bit in enumerate(bits):
                        if bit == "1":
                            self.rect(cursor + column * scale, y + row * scale, scale, scale, color)
            cursor += 6 * scale

    def save(self, path: Path) -> None:
        raw = b"".join(b"\0" + bytes(self.pixels[y * self.width * 3:(y + 1) * self.width * 3])
                       for y in range(self.height))
        def chunk(tag: bytes, payload: bytes) -> bytes:
            return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">2I5B", self.width, self.height, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
        path.write_bytes(png)


def svg_save(name: str, inner: str) -> None:
    template = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
<rect width="1200" height="760" fill="#ffffff"/>
<style>text{{font-family:Arial,sans-serif;fill:#172a45}} .muted{{fill:#67778b}} .grid{{stroke:#e1e8f0;stroke-width:1}} .card{{fill:#f4f8fc;stroke:#e1e8f0}}</style>
{inner}</svg>'''
    (OUT / f"{name}.svg").write_text(template, encoding="utf-8")


def main() -> None:
    source = json.loads((ROOT / "examples/sample_portfolio.json").read_text(encoding="utf-8"))
    result = analyze_portfolio(source)
    portfolio = result["portfolio"]
    wealth = [point["value"] for point in portfolio["wealth_series"]]
    risk_items = result["asset_risk_contributions"]
    pct_return = portfolio["total_return"] * 100
    ann_vol_pct = portfolio["annualized_volatility"] * 100
    mdd_pct = portfolio["maximum_drawdown"] * 100
    canvas = Canvas()
    canvas.text(56, 38, "PORTFOLIO RISK ANALYTICS", NAVY, 4)
    canvas.text(58, 82, "SYNTHETIC SAMPLE - TRANSPARENT RETURN AND RISK MEASURES", MUTED, 2)
    cards = [
        ("TOTAL RETURN", f"{pct_return:+.2f}%"),
        ("ANNUAL VOL", f"{ann_vol_pct:.2f}%"),
        ("MAX DRAWDOWN", f"{mdd_pct:.2f}%"),
    ]
    for i, (label, value) in enumerate(cards):
        x = 56 + i * 366
        canvas.rect(x, 126, 334, 104, PALE)
        canvas.text(x + 18, 145, label, MUTED, 2)
        canvas.text(x + 18, 178, value, BLUE if i == 0 else TEAL, 3)
    canvas.text(58, 266, "SYNTHETIC SAMPLE WEALTH INDEX", NAVY, 3)
    chart = (95, 330, 1050, 280)
    for j in range(5):
        y = chart[1] + j * chart[3] // 4
        canvas.line(chart[0], y, chart[0] + chart[2], y, GRID, 1)
    low, high = min(wealth), max(wealth)
    span = high - low or 1.0
    points = [
        (chart[0] + i * chart[2] // (len(wealth) - 1),
         chart[1] + chart[3] - int((value - low) / span * chart[3]))
        for i, value in enumerate(wealth)
    ]
    for left, right in zip(points, points[1:]):
        canvas.line(*left, *right, BLUE, 4)
    for x, y in points:
        canvas.rect(x - 4, y - 4, 8, 8, TEAL)
    canvas.text(58, 642, "CLOSE-TO-CLOSE | CONSTANT WEIGHTS | DAILY REBALANCING | 11 RETURNS", MUTED, 2)
    canvas.text(58, 695, "ILLUSTRATIVE DATA ONLY - NOT A FORECAST OR INVESTMENT ADVICE", MUTED, 2)
    canvas.save(OUT / "overview.png")

    svg_points = []
    for index, value in enumerate(wealth):
        x = 95 + index * 1050 / (len(wealth) - 1)
        y = 610 - (value - low) / span * 260
        svg_points.append(f"{x:.1f},{y:.1f}")
    metric_markup = "".join(
        f'<rect class="card" x="{56+i*366}" y="126" width="334" height="104" rx="14"/>'
        f'<text class="muted" x="{74+i*366}" y="158" font-size="15">{label}</text>'
        f'<text x="{74+i*366}" y="205" font-size="30" font-weight="700" fill="#2e70dc">{value}</text>'
        for i, (label, value) in enumerate(cards)
    )
    grid_markup = "".join(
        f'<line class="grid" x1="95" y1="{330+j*70}" x2="1145" y2="{330+j*70}"/>'
        for j in range(5)
    )
    svg_save("overview", f'''
<text x="56" y="76" font-size="34" font-weight="700">PORTFOLIO RISK ANALYTICS</text>
<text class="muted" x="58" y="106" font-size="16">SYNTHETIC SAMPLE - TRANSPARENT RETURN AND RISK MEASURES</text>
{metric_markup}<text x="58" y="296" font-size="22" font-weight="700">SYNTHETIC SAMPLE WEALTH INDEX</text>
{grid_markup}<polyline points="{' '.join(svg_points)}" fill="none" stroke="#2e70dc" stroke-width="4"/>
{''.join(f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="5" fill="#1fa497"/>' for p in svg_points)}
<text class="muted" x="58" y="664" font-size="14">CLOSE-TO-CLOSE | CONSTANT WEIGHTS | DAILY REBALANCING | 11 RETURNS</text>
<text class="muted" x="58" y="710" font-size="14">ILLUSTRATIVE DATA ONLY - NOT A FORECAST OR INVESTMENT ADVICE</text>''')

    flow = Canvas()
    flow.text(56, 38, "PORTFOLIO RISK - ANALYTICS FLOW", NAVY, 4)
    flow.text(58, 82, "INPUT PRICES FLOW THROUGH VALIDATION INTO PORTFOLIO RISK OUTPUTS", MUTED, 2)
    stages = [("PRICE", "HISTORIES"), ("VALIDATE", "DATES / WEIGHTS"), ("DAILY", "RETURNS"), ("RISK", "ATTRIBUTION")]
    for i, (top, bottom) in enumerate(stages):
        x = 56 + i * 286
        flow.rect(x, 142, 224, 88, PALE)
        flow.text(x + 15, 159, top, BLUE, 2)
        flow.text(x + 15, 188, bottom, NAVY, 1)
        if i < len(stages) - 1:
            flow.line(x + 229, 185, x + 270, 185, TEAL, 3)
            flow.line(x + 261, 176, x + 270, 185, TEAL, 3)
            flow.line(x + 261, 194, x + 270, 185, TEAL, 3)
    flow.text(58, 280, "ANNUALIZED VOLATILITY CONTRIBUTION BY ASSET", NAVY, 3)
    max_value = max((item["annualized_volatility_contribution"] for item in risk_items), default=1) or 1
    for i, item in enumerate(risk_items):
        y = 356 + i * 90
        flow.text(66, y, item["symbol"], NAVY, 2)
        x = 300
        width = int(item["annualized_volatility_contribution"] / max_value * 650)
        flow.rect(x, y - 5, max(3, width), 28, BLUE if i == 0 else TEAL)
        flow.text(x + max(12, width + 16), y, f'{item["risk_share"] * 100:.1f}% RISK SHARE', MUTED, 2)
    flow.text(58, 650, "COVARIANCE CONTRIBUTIONS SUM TO MODELED PORTFOLIO VOLATILITY", MUTED, 2)
    flow.text(58, 700, "SHORT SYNTHETIC HISTORY - NOT A FORECAST", MUTED, 2)
    flow.save(OUT / "flow.png")

    bar_rows = []
    max_rc = max((item["annualized_volatility_contribution"] for item in risk_items), default=1) or 1
    for i, item in enumerate(risk_items):
        y = 382 + i * 78
        width = item["annualized_volatility_contribution"] / max_rc * 650
        bar_rows.append(
            f'<text x="66" y="{y+20}" font-size="16">{item["symbol"]}</text>'
            f'<rect x="300" y="{y}" width="{width:.1f}" height="28" rx="6" fill="{("#2e70dc" if i == 0 else "#1fa497")}"/>'
            f'<text class="muted" x="{320+width:.1f}" y="{y+20}" font-size="15">{item["risk_share"]*100:.1f}% RISK SHARE</text>'
        )
    stage_svg = []
    for i, (top, bottom) in enumerate(stages):
        x = 56 + i * 286
        stage_svg.append(
            f'<rect class="card" x="{x}" y="142" width="224" height="88" rx="12"/>'
            f'<text x="{x+16}" y="177" font-size="18" font-weight="700">{top}</text>'
            f'<text class="muted" x="{x+16}" y="205" font-size="13">{bottom}</text>'
        )
        if i < len(stages) - 1:
            stage_svg.append(f'<path d="M{x+232} 186 H{x+267}" stroke="#1fa497" stroke-width="3" marker-end="url(#arrow)"/>')
    svg_save("flow", f'''
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#1fa497"/></marker></defs>
<text x="56" y="76" font-size="34" font-weight="700">PORTFOLIO RISK - ANALYTICS FLOW</text>
<text class="muted" x="58" y="106" font-size="16">INPUT PRICES FLOW THROUGH VALIDATION INTO PORTFOLIO RISK OUTPUTS</text>
{''.join(stage_svg)}<text x="58" y="296" font-size="22" font-weight="700">ANNUALIZED VOLATILITY CONTRIBUTION BY ASSET</text>
{''.join(bar_rows)}<text class="muted" x="58" y="665" font-size="14">COVARIANCE CONTRIBUTIONS SUM TO MODELED PORTFOLIO VOLATILITY</text>
<text class="muted" x="58" y="710" font-size="14">SHORT SYNTHETIC HISTORY - NOT A FORECAST</text>''')


if __name__ == "__main__":
    main()
