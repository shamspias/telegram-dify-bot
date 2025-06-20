from __future__ import annotations

import io
import re
import shutil
import textwrap
from typing import List

import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image

DPI = 100
TILE_PX = 800
FIGSIZE_INCHES = TILE_PX / DPI
WRAP_WIDTH = 90
CHAR_LIMIT = 550

rcParams.update({
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "figure.figsize": (FIGSIZE_INCHES, FIGSIZE_INCHES),
    "font.size": 14,
    "mathtext.fontset": "cm",
})

FULL_LATEX = bool(shutil.which("pdflatex") or
                  shutil.which("xelatex") or
                  shutil.which("lualatex"))
rcParams["text.usetex"] = FULL_LATEX

_UNSUPPORTED_TO_SAFE: dict[str, str] = {
    r"\implies": r"\Rightarrow",
    r"\qquad": r"\;",
    r"\enspace": r"\,",
}


def _patch_macros(tex: str) -> str:
    for bad, good in _UNSUPPORTED_TO_SAFE.items():
        tex = tex.replace(bad, good)
    return tex


def escape_latex(text: str) -> str:
    """
    Escape LaTeX special chars in non-math parts for usetex=True.
    """
    escape_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
    }

    def replacer(match):
        part = match.group(0)
        # If math ($...$), leave as is
        if part.startswith("$") and part.endswith("$"):
            return part
        # Else, escape special chars
        for char, escape in escape_chars.items():
            part = part.replace(char, escape)
        return part

    # Split into math and non-math regions
    pattern = r"(\$.*?\$|[^\$]+)"
    return re.sub(pattern, replacer, text, flags=re.DOTALL)


def md_heading_to_latex(text: str) -> str:
    """
    Convert Markdown headings to LaTeX headings (optional).
    """
    text = re.sub(r"^###### (.*)", r"\\paragraph{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^##### (.*)", r"\\subparagraph{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^#### (.*)", r"\\subsubsection{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^### (.*)", r"\\subsection{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.*)", r"\\section{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.*)", r"\\chapter{\1}", text, flags=re.MULTILINE)
    return text


class MarkdownMathTiler:
    """
    Convert mixed Markdown + LaTeX into 800x800 PNG images
    for Telegram. Handles long Markdown, math, and headings.
    """

    def render(self, markdown: str) -> List[io.BytesIO]:
        """
        Return list of 800x800 PNG image buffers from the markdown string.
        """
        cleaned = self._normalise_delimiters(markdown)
        if FULL_LATEX:
            cleaned = md_heading_to_latex(cleaned)  # Optional: convert headings
            cleaned = escape_latex(cleaned)  # Escape all non-math text
        blocks = self._split_blocks(cleaned)
        chunks = self._pack_blocks(blocks)
        return [self._draw_tile(chunk) for chunk in chunks]

    # ---------- STEP A : delimiters & macro fix -------------------------
    _INLINE_RE = re.compile(r"\\\((.*?)\\\)", re.DOTALL)
    _DISPLAY_RE = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
    _BOXED_RE = re.compile(r"\\boxed\s*\{([^{}]*?)\}")

    def _normalise_delimiters(self, text: str) -> str:
        # \( … \)  →  $ … $
        text = self._INLINE_RE.sub(r"$\1$", text)

        # \[ … \]  →  $$ … $$ (LaTeX) or $ … $ (mathtext)
        def _disp(m):
            body = " ".join(m.group(1).splitlines())
            return f"$${body}$$" if FULL_LATEX else f"${body}$"

        text = self._DISPLAY_RE.sub(_disp, text)

        if not FULL_LATEX:
            text = self._BOXED_RE.sub(r"\1", text)
            text = _patch_macros(text)
        return text

    # ---------- STEP B : block splitter --------------------------------
    _BLOCK_RE = re.compile(
        r"(```.*?```|"  # fenced code block
        r"\$\$.*?\$\$|"  # display math
        r"\$.*?\$|"  # inline math
        r"^\s*#{1,6} .*?$|"  # Markdown heading
        r"\s*---\s*$|"  # horizontal rule
        r"[^\n]*?(?:\n|$))",  # one normal line
        re.DOTALL | re.MULTILINE
    )

    def _split_blocks(self, text: str) -> List[str]:
        return [m.group(0).rstrip("\n")
                for m in self._BLOCK_RE.finditer(text)
                if m.group(0).strip()]

    # ---------- STEP C : greedy packer ---------------------------------
    def _pack_blocks(self, blocks: List[str]) -> List[str]:
        tiles, current = [], ""
        for blk in blocks:
            candidate = f"{current}\n\n{blk}" if current else blk
            if len(candidate) > CHAR_LIMIT:
                if current:
                    tiles.append(current.strip())
                current = blk
            else:
                current = candidate
        if current:
            tiles.append(current.strip())
        return tiles

    # ---------- STEP D : soft-wrap -------------------------------------
    _INLINE_MATH_RE = re.compile(r"(\$[^$]*\$)")

    def _wrap_line(self, line: str) -> str:
        if line.lstrip().startswith(("```", "#", "\\")):
            return line  # leave code/heading/LaTeX section intact

        parts, wrapped = self._INLINE_MATH_RE.split(line), ""
        for part in parts:
            if not part:
                continue
            if self._INLINE_MATH_RE.fullmatch(part):  # math
                wrapped += part
            else:  # plain
                wrapped += textwrap.fill(part, WRAP_WIDTH,
                                         subsequent_indent="")
        return wrapped

    # ---------- STEP E : drawing one tile ------------------------------
    def _draw_tile(self, chunk: str) -> io.BytesIO:
        wrapped = "\n".join(self._wrap_line(l) for l in chunk.splitlines())

        fig = plt.figure()
        fig.patch.set_facecolor("white")
        fig.subplots_adjust(left=0.03, right=0.97, top=0.97, bottom=0.03)
        fig.text(0.03, 0.97, wrapped, ha="left", va="top", wrap=True)

        tmp = io.BytesIO()
        fig.savefig(tmp, format="png", bbox_inches="tight", pad_inches=0.3)
        plt.close(fig)
        tmp.seek(0)

        # Centre-pad to exactly 800 × 800 px
        img = Image.open(tmp).convert("RGB")
        canvas = Image.new("RGB", (TILE_PX, TILE_PX), "white")
        xoff = max((TILE_PX - img.width) // 2, 0)
        yoff = max((TILE_PX - img.height) // 2, 0)
        canvas.paste(img, (xoff, yoff))

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        out.seek(0)
        return out
