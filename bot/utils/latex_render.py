from __future__ import annotations

import io
import re
import shutil
import textwrap
from typing import List, Tuple

import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image

# --- GLOBAL CONSTANTS ---
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
    Escape LaTeX special chars in NON-MATH parts ONLY.
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
    # Split text into segments: math ($...$ or $$...$$) and non-math
    pattern = re.compile(r"(\$\$.*?\$\$|\$.*?\$)", re.DOTALL)
    result = []
    last = 0
    for m in pattern.finditer(text):
        non_math = text[last:m.start()]
        for char, escape in escape_chars.items():
            non_math = non_math.replace(char, escape)
        result.append(non_math)
        # math part, untouched
        result.append(m.group(0))
        last = m.end()
    non_math = text[last:]
    for char, escape in escape_chars.items():
        non_math = non_math.replace(char, escape)
    result.append(non_math)
    return ''.join(result)


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
    Convert mixed Markdown + LaTeX into 800x800 PNG images for Telegram.
    Handles long Markdown, headings, and robust LaTeX math.
    """

    def render(self, markdown: str) -> List[io.BytesIO]:
        """
        Return list of 800x800 PNG image buffers from the markdown string.
        """
        cleaned = self._normalise_delimiters(markdown)
        if FULL_LATEX:
            cleaned = md_heading_to_latex(cleaned)
            cleaned = escape_latex(cleaned)
        blocks = self._split_blocks(cleaned)
        chunks = self._pack_blocks(blocks)
        return [self._draw_tile(chunk, is_math) for chunk, is_math in chunks]

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

    # ---------- STEP B : block splitter & tagging math -----------------
    _BLOCK_RE = re.compile(
        r"(```.*?```|"  # fenced code
        r"\$\$.*?\$\$|"  # display math
        r"\$.*?\$|"  # inline math
        r"^\s*#{1,6} .*?$|"  # Markdown heading
        r"\s*---\s*$|"  # horizontal rule
        r"[^\n]*?(?:\n|$))",  # one normal line
        re.DOTALL | re.MULTILINE
    )

    def _split_blocks(self, text: str) -> List[Tuple[str, bool]]:
        """
        Return list of (block, is_math).
        """
        blocks = []
        for m in self._BLOCK_RE.finditer(text):
            block = m.group(0).rstrip("\n")
            if not block.strip():
                continue
            # Math: starts/ends with $$...$$ or $...$ and is not a code block or heading
            block_stripped = block.strip()
            is_math = (
                    (block_stripped.startswith("$$") and block_stripped.endswith("$$")) or
                    (block_stripped.startswith("$") and block_stripped.endswith("$") and len(block_stripped) > 2)
            )
            blocks.append((block, is_math))
        return blocks

    # ---------- STEP C : greedy packer ---------------------------------
    def _pack_blocks(self, blocks: List[Tuple[str, bool]]) -> List[Tuple[str, bool]]:
        tiles, current, current_is_math = [], "", None
        for blk, is_math in blocks:
            candidate = f"{current}\n\n{blk}" if current and current_is_math == is_math else blk
            if len(candidate) > CHAR_LIMIT or (current and current_is_math != is_math):
                if current:
                    tiles.append((current.strip(), current_is_math))
                current, current_is_math = blk, is_math
            else:
                current, current_is_math = candidate, is_math
        if current:
            tiles.append((current.strip(), current_is_math))
        return tiles

    # ---------- STEP D : soft-wrap for text only -----------------------
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
                wrapped += textwrap.fill(part, WRAP_WIDTH, subsequent_indent="")
        return wrapped

    # ---------- STEP E : drawing one tile ------------------------------
    def _draw_tile(self, chunk: str, is_math: bool) -> io.BytesIO:
        """
        Draw one tile. For math chunks, strip $$ and render with ismath=True.
        For text, wrap lines and render as ismath=False.
        """
        if is_math:
            # Support both $$...$$ and $...$
            content = chunk.strip()
            if content.startswith("$$") and content.endswith("$$"):
                content = content[2:-2].strip()
            elif content.startswith("$") and content.endswith("$"):
                content = content[1:-1].strip()
            # Replace double-backslash with newline for multiline equations
            content = content.replace("\\\\", "\n")
            fig = plt.figure()
            fig.patch.set_facecolor("white")
            fig.subplots_adjust(left=0.03, right=0.97, top=0.97, bottom=0.03)
            # Math is centered
            fig.text(0.5, 0.5, content, ha="center", va="center", wrap=True, ismath=True)
        else:
            # Wrap each line
            wrapped = "\n".join(self._wrap_line(l) for l in chunk.splitlines())
            fig = plt.figure()
            fig.patch.set_facecolor("white")
            fig.subplots_adjust(left=0.03, right=0.97, top=0.97, bottom=0.03)
            fig.text(0.03, 0.97, wrapped, ha="left", va="top", wrap=True, ismath=False)

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
