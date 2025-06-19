"""
────────────────────────────────────────────────────────
Render mixed Markdown + LaTeX into square 800 px images
optimised for Telegram.

Usage
-----
from bot.utils.markdown_math_tiler import MarkdownMathTiler

tiler    = MarkdownMathTiler()            # create once
buffers  = tiler.render(markdown_string)  # list[BytesIO]
for buf in buffers:
    await update.message.reply_photo(photo=buf)
"""

from __future__ import annotations

import io
import re
import shutil
import textwrap
from typing import List

import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image

# ────────────────────────────────────────────────
# 0. GLOBAL CONSTANTS
# ────────────────────────────────────────────────
DPI = 100  # 8 in × 100 dpi → 800 px
TILE_PX = 800
FIGSIZE_INCHES = TILE_PX / DPI
WRAP_WIDTH = 90  # characters before soft-wrap
CHAR_LIMIT = 550  # greedy pack limit per tile

rcParams.update({
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "figure.figsize": (FIGSIZE_INCHES, FIGSIZE_INCHES),
    "font.size": 14,
    "mathtext.fontset": "cm",
})

# ────────────────────────────────────────────────
# 1.  DETECT FULL LaTeX
# ────────────────────────────────────────────────
FULL_LATEX = bool(shutil.which("pdflatex") or
                  shutil.which("xelatex") or
                  shutil.which("lualatex"))
rcParams["text.usetex"] = FULL_LATEX

# ────────────────────────────────────────────────
# 2.  MAP UNSUPPORTED MACROS  (mathtext only)
# ────────────────────────────────────────────────
_UNSUPPORTED_TO_SAFE: dict[str, str] = {
    r"\implies": r"\Rightarrow",
    r"\qquad": r"\;",
    r"\enspace": r"\,",
    # add more if mathtext errors on them
}


def _patch_macros(tex: str) -> str:
    """Replace mathtext-unsupported macros with safe ones."""
    for bad, good in _UNSUPPORTED_TO_SAFE.items():
        tex = tex.replace(bad, good)
    return tex


# ────────────────────────────────────────────────
# 3.  MAIN RENDERER CLASS
# ────────────────────────────────────────────────
class MarkdownMathTiler:
    r"""
    Convert ChatGPT’s Markdown + LaTeX answers into Telegram-friendly
    800 × 800 PNG tiles (RGB) returned as BytesIO buffers.
    """

    # ---------- PUBLIC --------------------------------------------------
    def render(self, markdown: str) -> List[io.BytesIO]:
        """Return list of 800 × 800 PNG tiles (BytesIO)."""
        cleaned = self._normalise_delimiters(markdown)
        blocks = self._split_blocks(cleaned)
        chunks = self._pack_blocks(blocks)
        return [self._draw_tile(chunk) for chunk in chunks]

    # ---------- STEP A : delimiters & macro fix -------------------------
    _INLINE_RE = re.compile(r"\\\((.*?)\\\)", re.DOTALL)
    _DISPLAY_RE = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
    _BOXED_RE = re.compile(r"\\boxed\s*\{([^{}]*?)\}")

    def _normalise_delimiters(self, text: str) -> str:
        r"""
        • \( … \)  →  $ … $
        • \[ … \]  →  $$ … $$  (with LaTeX)  or  $ … $  (mathtext)
        • Strip \boxed{…} and unsupported macros if LaTeX is **not** present.
        """
        # inline math
        text = self._INLINE_RE.sub(r"$\1$", text)

        # display math
        def _disp(m):
            body = " ".join(m.group(1).splitlines())  # collapse new-lines
            return f"$${body}$$" if FULL_LATEX else f"${body}$"

        text = self._DISPLAY_RE.sub(_disp, text)

        if not FULL_LATEX:
            text = self._BOXED_RE.sub(r"\1", text)  # drop \boxed
            text = _patch_macros(text)  # replace bad macros

        return text

    # ---------- STEP B : block splitter --------------------------------
    _BLOCK_RE = re.compile(
        r"(```.*?```|"  # fenced code
        r"\$\$.*?\$\$|"  # $$ … $$   (after normalisation)
        r"\$.*?\$|"  # inline $ … $
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
        if line.lstrip().startswith(("```", "#")):
            return line  # leave code/heading intact

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

        # centre-pad to exactly 800 × 800 px
        img = Image.open(tmp).convert("RGB")
        canvas = Image.new("RGB", (TILE_PX, TILE_PX), "white")
        xoff = max((TILE_PX - img.width) // 2, 0)
        yoff = max((TILE_PX - img.height) // 2, 0)
        canvas.paste(img, (xoff, yoff))

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        out.seek(0)
        return out
