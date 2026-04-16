#!/usr/bin/env python3
"""
Generate PDF version of docs/counterparty_risk_methodology.md.

Lightweight markdown renderer tuned to the actual structure of the
methodology doc: headings (H1/H2/H3), paragraphs with **bold** /
`inline code`, pipe tables, unordered bullets, triple-backtick code
blocks, and horizontal rules.

Usage:
    python docs/generate_methodology_pdf.py
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "docs" / "counterparty_risk_methodology.md"
PDF_PATH = ROOT / "docs" / "counterparty_risk_methodology.pdf"

# --- Palette (matches user_stories/generate_pdf.py) ------------------------
BLUE = (0, 102, 204)
DARK = (30, 41, 59)
MEDIUM = (71, 85, 105)
LIGHT_BG = (248, 250, 252)
WHITE = (255, 255, 255)
TABLE_HEADER_BG = (15, 23, 42)
TABLE_HEADER_FG = (255, 255, 255)
TABLE_ROW_ALT = (241, 245, 249)
CODE_BG = (241, 245, 249)
CODE_FG = (30, 41, 59)
RULE = (203, 213, 225)


_UNICODE_REPLACEMENTS = {
    "\u2014": "-",     # em-dash
    "\u2013": "-",     # en-dash
    "\u2212": "-",     # minus sign
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u2192": "->",    # right arrow
    "\u2190": "<-",
    "\u2194": "<->",
    "\u00d7": "x",
    "\u00b5": "u",
    "\u03a3": "Sum",   # Sigma
    "\u03b5": "eps",
    "\u00f7": "/",
    "\u00b7": "*",
    "\u2022": "-",     # bullet
    "\u00a0": " ",     # non-breaking space
    "\u2009": " ",     # thin space
    "\u00b1": "+/-",
    "\u2248": "~=",
    "\u2260": "!=",
    "\u2264": "<=",
    "\u2265": ">=",
}


def sanitize(text: str) -> str:
    """Replace unicode chars Helvetica can't encode."""
    for src, dst in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    # Final safety net - strip any remaining non-latin1 chars
    return text.encode("latin-1", "replace").decode("latin-1")


# --- Inline markdown parsing ----------------------------------------------

_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITAL_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")

_INLINE_RXS = (_BOLD_RE, _ITAL_RE, _CODE_RE)


def parse_inline(text: str) -> list[tuple[str, str]]:
    """Return a list of (style, fragment) tuples.

    style in {"", "B", "I", "CODE"} — regular / bold / italic / inline code.
    """
    text = _LINK_RE.sub(r"\1", text)  # replace [label](url) with "label"
    fragments: list[tuple[str, str]] = []
    i = 0
    while i < len(text):
        bold = _BOLD_RE.match(text, i)
        ital = _ITAL_RE.match(text, i)
        code = _CODE_RE.match(text, i)
        if bold:
            fragments.append(("B", bold.group(1)))
            i = bold.end()
        elif code:
            fragments.append(("CODE", code.group(1)))
            i = code.end()
        elif ital:
            fragments.append(("I", ital.group(1)))
            i = ital.end()
        else:
            next_pos = len(text)
            for rx in _INLINE_RXS:
                m = rx.search(text, i)
                if m and m.start() < next_pos:
                    next_pos = m.start()
            fragments.append(("", text[i:next_pos]))
            i = next_pos
    return fragments


# --- PDF class -------------------------------------------------------------

class MethodologyPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=20, top=18, right=20)
        self._first_page_drawn = False

    def header(self):
        if not self._first_page_drawn:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MEDIUM)
        self.cell(0, 6, "Monika  |  Counterparty Risk Methodology", align="L")
        self.cell(0, 6, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        y = self.get_y() + 1
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(5)

    def footer(self):
        if not self._first_page_drawn:
            return
        self.set_y(-14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MEDIUM)
        self.cell(0, 10, "Ashland Hill Media Finance  |  Confidential", align="C")

    # -- Cover ------------------------------------------------------------
    def cover(self):
        self.add_page()
        self.ln(36)
        self.set_font("Helvetica", "B", 30)
        self.set_text_color(*BLUE)
        self.cell(0, 14, "Counterparty Risk", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(*DARK)
        self.cell(0, 12, "Methodology", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(8)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(*MEDIUM)
        self.cell(0, 8, "Monika  |  Ashland Hill Media Finance",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "Version 0.1.0  |  April 2026",
                  align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(10)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        cx = self.w / 2
        self.line(cx - 30, self.get_y(), cx + 30, self.get_y())

        self.ln(14)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        blurb = (
            "Credit-scoring methodology for Pre-Sales, Gap / Unsold, and Tax Credit "
            "collateral; rating bands mapped to S&P/Fitch; metric inventory and "
            "transformation rules; machine-learning layer producing an interpretable "
            "blended score with feature importance and per-deal contributions."
        )
        self.set_x(40)
        self.multi_cell(self.w - 80, 6, sanitize(blurb), align="C")

        self._first_page_drawn = True

    # -- Element renderers ------------------------------------------------
    def h1(self, text: str):
        self._break_if(20)
        self.ln(2)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*BLUE)
        self.multi_cell(0, 10, sanitize(text))
        self.ln(1)

    def h2(self, text: str):
        self._break_if(16)
        self.ln(3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*DARK)
        self.multi_cell(0, 7, sanitize(text))
        # Thin accent bar
        y = self.get_y()
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        self.line(self.l_margin, y, self.l_margin + 18, y)
        self.ln(3)

    def h3(self, text: str):
        self._break_if(12)
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*DARK)
        self.multi_cell(0, 6, sanitize(text))
        self.ln(1)

    def paragraph(self, text: str):
        self._render_inline_block(text, line_h=5.2, size=10)
        self.ln(2)

    def bullet(self, text: str, depth: int = 0):
        indent = 4 + depth * 6
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.set_x(self.l_margin + indent)
        self.cell(4, 5, "-")
        self._render_inline_block(text, line_h=5, size=10, x_start=self.l_margin + indent + 4)

    def ordered(self, number: str, text: str, depth: int = 0):
        indent = 4 + depth * 6
        marker = f"{number}."
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.set_x(self.l_margin + indent)
        self.cell(8, 5, marker)
        self._render_inline_block(text, line_h=5, size=10, x_start=self.l_margin + indent + 8)

    def rule(self):
        self.ln(2)
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(4)

    def code_block(self, lines: list[str]):
        self._break_if(8 + 4.5 * len(lines))
        self.set_font("Courier", "", 8.5)
        self.set_text_color(*CODE_FG)
        self.set_fill_color(*CODE_BG)
        x0 = self.l_margin
        w = self.w - self.l_margin - self.r_margin
        for line in lines:
            self.set_x(x0)
            self.cell(w, 4.5, " " + sanitize(line), fill=True)
            self.ln(4.5)
        self.ln(2)

    def table(self, rows: list[list[str]]):
        if not rows:
            return
        n_cols = max(len(r) for r in rows)
        avail = self.w - self.l_margin - self.r_margin
        col_w = self._compute_col_widths(rows, n_cols, avail)
        header, body = rows[0], rows[1:]

        self._break_if(12)
        self._render_table_row(header, col_w, is_header=True, fill_color=TABLE_HEADER_BG,
                               text_color=TABLE_HEADER_FG)
        for i, row in enumerate(body):
            while len(row) < n_cols:
                row.append("")
            bg = TABLE_ROW_ALT if (i % 2 == 0) else WHITE
            self._render_table_row(row, col_w, is_header=False, fill_color=bg, text_color=DARK)
        self.ln(3)

    def _compute_col_widths(self, rows: list[list[str]], n_cols: int, avail: float) -> list[float]:
        """Pick column widths so every cell's longest word fits and columns
        share the rest of the page proportional to their average cell length."""
        self.set_font("Helvetica", "", 9)
        longest_word = [0.0] * n_cols   # widest single token
        avg_len = [0.0] * n_cols        # sum of cell widths for weighting
        for row in rows:
            for c, cell in enumerate(row[:n_cols]):
                txt = sanitize(_strip_inline(cell))
                avg_len[c] += self.get_string_width(txt)
                for word in txt.split():
                    w = self.get_string_width(word)
                    if w > longest_word[c]:
                        longest_word[c] = w

        pad = 4.0  # 2mm padding each side
        min_w = [lw + pad for lw in longest_word]
        min_total = sum(min_w)
        if min_total >= avail:
            # Can't fit the longest words — scale down proportionally.
            scale = avail / min_total
            return [w * scale for w in min_w]

        # Distribute the remaining space weighted by avg cell length.
        remaining = avail - min_total
        total_len = sum(avg_len) or 1.0
        return [min_w[c] + remaining * (avg_len[c] / total_len) for c in range(n_cols)]

    def _render_table_row(self, cells: list[str], col_w: list[float],
                          is_header: bool, fill_color: tuple, text_color: tuple) -> None:
        # Pre-compute the wrapped height for each cell
        line_h = 4.5
        font_size = 9
        style = "B" if is_header else ""
        self.set_font("Helvetica", style, font_size)
        heights = []
        for cell_text, w in zip(cells, col_w):
            txt = sanitize(_strip_inline(cell_text))
            lines = self._wrap_lines(txt, w - 3, font_size=font_size, style=style)
            heights.append(len(lines) * line_h + 2)
        row_h = max(heights + [7.0])

        self._break_if(row_h + 2)
        y0 = self.get_y()
        x0 = self.l_margin

        # Draw each cell: border+fill, then text
        self.set_fill_color(*fill_color)
        self.set_text_color(*text_color)
        self.set_font("Helvetica", style, font_size)
        x = x0
        for cell_text, w in zip(cells, col_w):
            self.set_xy(x, y0)
            self.cell(w, row_h, "", border=1, fill=True)
            txt = sanitize(_strip_inline(cell_text))
            self._draw_wrapped_text(txt, x + 1.5, y0 + 1.2, w - 3,
                                    line_h=line_h, font_size=font_size, style=style)
            x += w
        self.set_y(y0 + row_h)

    def _wrap_lines(self, text: str, max_w: float, font_size: float, style: str) -> list[str]:
        """Word-wrap text to fit max_w at the given font."""
        self.set_font("Helvetica", style, font_size)
        out: list[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                out.append("")
                continue
            line = ""
            for word in words:
                test = (line + " " + word).strip() if line else word
                if self.get_string_width(test) <= max_w:
                    line = test
                else:
                    if line:
                        out.append(line)
                    # If single word longer than column, hard-split it
                    if self.get_string_width(word) > max_w:
                        buf = ""
                        for ch in word:
                            if self.get_string_width(buf + ch) > max_w:
                                out.append(buf)
                                buf = ch
                            else:
                                buf += ch
                        line = buf
                    else:
                        line = word
            if line:
                out.append(line)
        return out

    def _draw_wrapped_text(self, text: str, x: float, y: float, max_w: float,
                           line_h: float, font_size: float, style: str) -> None:
        lines = self._wrap_lines(text, max_w, font_size=font_size, style=style)
        self.set_font("Helvetica", style, font_size)
        cy = y
        for line in lines:
            self.set_xy(x, cy)
            self.cell(max_w, line_h, line)
            cy += line_h

    # -- Internals --------------------------------------------------------
    def _break_if(self, needed: float):
        if self.get_y() + needed > self.h - 20:
            self.add_page()

    def _row_height(self, cells: list[str], col_w: float, font_size: float, line_h: float) -> float:
        """Estimate row height from wrapped lines per cell."""
        self.set_font("Helvetica", "", font_size)
        max_lines = 1
        for cell in cells:
            text = sanitize(_strip_inline(cell))
            # Approximate chars per line based on col width
            approx_chars = max(5, int(col_w / 1.9))
            lines = 0
            for segment in text.split("\n"):
                if not segment:
                    lines += 1
                    continue
                lines += max(1, (len(segment) + approx_chars - 1) // approx_chars)
            max_lines = max(max_lines, lines)
        return max(7.0, max_lines * line_h + 2)

    def _render_cell(self, x: float, y: float, w: float, h: float, text: str,
                     style: str, align: str, fill: bool, line_h: float):
        # Draw filled box
        self.set_xy(x, y)
        if fill:
            self.cell(w, h, "", border=1, fill=True)
        else:
            self.cell(w, h, "", border=1)
        # Inline-styled content
        self.set_xy(x + 1.5, y + 1.2)
        self._render_inline_block(
            _strip_inline(text), line_h=line_h, size=9, max_w=w - 3,
            justify_align=align, base_style=style,
        )

    def _render_inline_block(self, text: str, line_h: float = 5.2, size: float = 10,
                             x_start: float | None = None, max_w: float | None = None,
                             justify_align: str = "L", base_style: str = ""):
        """Render a paragraph with inline bold/code, wrapping at word boundaries."""
        if x_start is None:
            x_start = self.l_margin
        if max_w is None:
            max_w = self.w - self.r_margin - x_start

        self.set_text_color(*DARK)
        self.set_x(x_start)
        # Tokenise into (style, word) pairs preserving spaces
        tokens: list[tuple[str, str]] = []
        for style, frag in parse_inline(text):
            combo_style = base_style if base_style and style == "" else style
            # Split on whitespace but keep spaces by rejoining
            words = re.split(r"(\s+)", frag)
            for w in words:
                if w == "":
                    continue
                tokens.append((combo_style, sanitize(w)))

        cursor_x = x_start
        for style, word in tokens:
            font = ("Courier", "", size * 0.9) if style == "CODE" else ("Helvetica", style, size)
            self.set_font(*font)
            w = self.get_string_width(word)
            # If token itself is wider than line, break into chars
            if w > max_w:
                for ch in word:
                    cw = self.get_string_width(ch)
                    if cursor_x + cw > x_start + max_w:
                        self.ln(line_h)
                        cursor_x = x_start
                        self.set_x(cursor_x)
                    self._emit(ch, style, size)
                    cursor_x += cw
                continue
            if cursor_x + w > x_start + max_w:
                # Wrap — but strip leading whitespace on the next line
                self.ln(line_h)
                cursor_x = x_start
                self.set_x(cursor_x)
                if word.isspace():
                    continue
            self._emit(word, style, size)
            cursor_x += w

        self.ln(line_h)

    def _emit(self, word: str, style: str, size: float):
        if style == "CODE":
            # Monospaced with subtle background highlight via a filled cell
            self.set_font("Courier", "", size * 0.9)
            self.set_text_color(*CODE_FG)
            self.set_fill_color(*CODE_BG)
            w = self.get_string_width(word)
            self.cell(w, size * 0.45, word, fill=True)
            self.set_text_color(*DARK)
        else:
            self.set_font("Helvetica", style, size)
            self.set_text_color(*DARK)
            self.cell(self.get_string_width(word), size * 0.45, word)


def _strip_inline(text: str) -> str:
    """For width estimation — strip ** and backticks but keep content."""
    return text.replace("**", "").replace("`", "")


# --- Markdown parser -------------------------------------------------------

def parse_markdown(md: str) -> list[tuple[str, object]]:
    """Tokenise the MD into a list of (kind, payload) blocks.

    kinds: h1, h2, h3, p, ul_item, table, code, hr, blank
    """
    lines = md.splitlines()
    blocks: list[tuple[str, object]] = []
    i = 0
    n = len(lines)

    def is_table_sep(line: str) -> bool:
        stripped = line.strip().strip("|")
        if not stripped:
            return False
        cells = [c.strip() for c in stripped.split("|")]
        return all(re.fullmatch(r":?-+:?", c or "") for c in cells)

    while i < n:
        raw = lines[i]
        line = raw.rstrip()

        # Blank
        if not line.strip():
            i += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"-{3,}", line.strip()):
            blocks.append(("hr", None))
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            blocks.append(("code", buf))
            continue

        # Headings
        if line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
            continue
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            i += 1
            continue

        # Table
        if line.lstrip().startswith("|") and i + 1 < n and is_table_sep(lines[i + 1]):
            rows: list[list[str]] = []
            # Header
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
            i += 2  # header + separator
            while i < n and lines[i].lstrip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row)
                i += 1
            blocks.append(("table", rows))
            continue

        # Unordered list
        if re.match(r"^(\s*)[-*]\s+", line):
            while i < n and re.match(r"^(\s*)[-*]\s+", lines[i].rstrip()):
                m = re.match(r"^(\s*)[-*]\s+(.*)$", lines[i].rstrip())
                depth = min(2, len(m.group(1)) // 2)
                blocks.append(("ul_item", (m.group(2), depth)))
                i += 1
            continue

        # Ordered list
        if re.match(r"^(\s*)\d+\.\s+", line):
            while i < n and re.match(r"^(\s*)\d+\.\s+", lines[i].rstrip()):
                m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", lines[i].rstrip())
                depth = min(2, len(m.group(1)) // 2)
                blocks.append(("ol_item", (m.group(2), m.group(3), depth)))
                i += 1
            continue

        # Paragraph — collect until blank
        para: list[str] = [line]
        i += 1
        while i < n and lines[i].strip() and not _is_block_boundary(lines[i], lines[i + 1] if i + 1 < n else ""):
            para.append(lines[i].rstrip())
            i += 1
        blocks.append(("p", " ".join(para)))

    return blocks


def _is_block_boundary(line: str, next_line: str) -> bool:
    ls = line.lstrip()
    if ls.startswith(("#", "```", "- ", "* ", "|")):
        return True
    if re.fullmatch(r"-{3,}", line.strip()):
        return True
    return False


# --- Driver ----------------------------------------------------------------

def render(md: str) -> MethodologyPDF:
    pdf = MethodologyPDF()
    pdf.cover()
    pdf.add_page()

    blocks = parse_markdown(md)
    # Skip the first H1 — already on cover
    skip_first_h1 = True
    for kind, payload in blocks:
        if kind == "h1" and skip_first_h1:
            skip_first_h1 = False
            continue
        if kind == "h1":
            pdf.h1(payload)
        elif kind == "h2":
            pdf.h2(payload)
        elif kind == "h3":
            pdf.h3(payload)
        elif kind == "p":
            pdf.paragraph(payload)
        elif kind == "ul_item":
            text, depth = payload
            pdf.bullet(text, depth=depth)
        elif kind == "ol_item":
            number, text, depth = payload
            pdf.ordered(number, text, depth=depth)
        elif kind == "table":
            pdf.table(payload)
        elif kind == "code":
            pdf.code_block(payload)
        elif kind == "hr":
            pdf.rule()
    return pdf


def main() -> None:
    md = MD_PATH.read_text()
    pdf = render(md)
    pdf.output(str(PDF_PATH))
    print(f"wrote {PDF_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
