"""ANSI terminal rendering: colours, the board, banners and prompts.

Zero dependencies — plain escape codes and Unicode box drawing. Colour is
disabled automatically when stdout is not a TTY or ``NO_COLOR`` is set.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Dict, Iterable, List, Optional, Sequence

from .game import Game, NORTH, SOUTH, STORE, pits_of

# ----------------------------------------------------------------------- colour
_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


def set_color(enabled: bool) -> None:
    global _USE_COLOR
    _USE_COLOR = enabled


def _sgr(*codes: int) -> str:
    if not _USE_COLOR:
        return ""
    return "\x1b[" + ";".join(str(c) for c in codes) + "m"


RESET = "\x1b[0m"
BOLD = 1
DIM = 2
ITALIC = 3


def paint(text: str, *codes: int) -> str:
    if not _USE_COLOR or not codes:
        return text
    return _sgr(*codes) + text + RESET


def rgb(text: str, r: int, g: int, b: int, bold: bool = False, bg: Optional[Sequence[int]] = None) -> str:
    if not _USE_COLOR:
        return text
    seq = f"\x1b[38;2;{r};{g};{b}m"
    if bg:
        seq += f"\x1b[48;2;{bg[0]};{bg[1]};{bg[2]}m"
    if bold:
        seq += "\x1b[1m"
    return seq + text + RESET


# Palette -------------------------------------------------------------------
WOOD = (173, 120, 66)
WOOD_DARK = (120, 80, 40)
SAND = (232, 210, 160)
SOUTH_RGB = (86, 196, 255)      # sky blue
NORTH_RGB = (255, 140, 105)     # coral
GOLD = (255, 204, 77)
GREEN = (120, 220, 120)
RED = (255, 105, 97)
GREY = (140, 140, 140)
WHITE = (240, 240, 240)

PLAYER_RGB = {SOUTH: SOUTH_RGB, NORTH: NORTH_RGB}
PLAYER_NAME_DEFAULT = {SOUTH: "South", NORTH: "North"}


def player_color(text: str, player: int, bold: bool = False) -> str:
    return rgb(text, *PLAYER_RGB[player], bold=bold)


# ------------------------------------------------------------------ terminal io
def clear() -> None:
    if _USE_COLOR:
        sys.stdout.write("\x1b[2J\x1b[H")
    else:
        sys.stdout.write("\n" * 2)
    sys.stdout.flush()


def term_width(default: int = 80) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:  # pragma: no cover
        return default


def center(line: str, width: Optional[int] = None) -> str:
    width = width or term_width()
    visible = len(strip_ansi(line))
    pad = max(0, (width - visible) // 2)
    return " " * pad + line


def strip_ansi(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        if s[i] == "\x1b":
            j = s.find("m", i)
            if j == -1:
                break
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


# ------------------------------------------------------------------------ board
PIT_W = 5  # inner width of a pit cell
GAP = " "  # between pit cells

UNICODE_GLYPHS = {
    "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│",
    "TL": "╔", "TR": "╗", "BL": "╚", "BR": "╝", "H": "═", "V": "║",
    "seed": "●", "empty": "·", "more": "+", "left": "◀", "right": "▶",
    "check": "✔", "cross": "✘", "star": "★", "dot": "•", "dash": "—",
}
ASCII_GLYPHS = {
    "tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|",
    "TL": "+", "TR": "+", "BL": "+", "BR": "+", "H": "=", "V": "|",
    "seed": "o", "empty": ".", "more": "+", "left": "<", "right": ">",
    "check": "+", "cross": "x", "star": "*", "dot": "*", "dash": "-",
}
G = dict(UNICODE_GLYPHS)


def set_ascii(enabled: bool) -> None:
    """Switch every drawing glyph to plain ASCII (for terminals without Unicode)."""
    G.clear()
    G.update(ASCII_GLYPHS if enabled else UNICODE_GLYPHS)


def _seed_glyphs(n: int) -> str:
    """A tiny pictogram of ``n`` seeds, capped so it fits the cell."""
    if n == 0:
        return G["empty"]
    if n <= PIT_W:
        return G["seed"] * n
    return G["seed"] * (PIT_W - 1) + G["more"]


def _cell_lines(count: int, hl: Optional[Sequence[int]], player: int) -> List[str]:
    """Three rendered lines for one pit (top border, number, bottom border)."""
    top = G["tl"] + G["h"] * PIT_W + G["tr"]
    bot = G["bl"] + G["h"] * PIT_W + G["br"]
    num = f"{count:^{PIT_W}d}"
    seeds = f"{_seed_glyphs(count):^{PIT_W}}"
    frame_rgb = hl or WOOD
    body_rgb = GOLD if hl else PLAYER_RGB[player]
    return [
        rgb(top, *frame_rgb),
        rgb(G["v"], *frame_rgb) + rgb(num, *body_rgb, bold=True) + rgb(G["v"], *frame_rgb),
        rgb(G["v"], *frame_rgb) + rgb(seeds, *(GOLD if hl else SAND)) + rgb(G["v"], *frame_rgb),
        rgb(bot, *frame_rgb),
    ]


def _store_lines(count: int, player: int, active: bool, height: int) -> List[str]:
    w = 7
    top = G["tl"] + G["h"] * w + G["tr"]
    bot = G["bl"] + G["h"] * w + G["br"]
    frame = PLAYER_RGB[player] if active else WOOD
    lines = [rgb(top, *frame)]
    body = height - 2
    mid = body // 2
    for i in range(body):
        if i == mid - 1:
            inner = rgb(f"{PLAYER_NAME_DEFAULT[player][0]:^{w}}", *GREY)
        elif i == mid:
            inner = rgb(f"{count:^{w}d}", *GOLD, bold=True)
        elif i == mid + 1:
            inner = rgb(f"{'store':^{w}}", *GREY)
        else:
            inner = " " * w
        lines.append(rgb(G["v"], *frame) + inner + rgb(G["v"], *frame))
    lines.append(rgb(bot, *frame))
    return lines


def render_board(
    game: Game,
    names: Optional[Dict[int, str]] = None,
    highlight: Optional[Dict[int, Sequence[int]]] = None,
    hint_pits: Iterable[int] = (),
) -> str:
    """Return the whole board as a multi-line string.

    ``highlight`` maps pit index -> RGB tuple to accent a cell (e.g. the path
    of the last sow, or a capture). ``hint_pits`` are legal moves to mark.
    """
    names = names or PLAYER_NAME_DEFAULT
    highlight = highlight or {}
    hint_pits = set(hint_pits)

    # North row: pits 12..7 left-to-right, labelled 6..1
    north_pits = list(range(12, 6, -1))
    south_pits = list(range(0, 6))

    def row(pits: List[int], player: int) -> List[str]:
        cells = [_cell_lines(game.board[p], highlight.get(p), player) for p in pits]
        return [GAP.join(c[i] for c in cells) for i in range(4)]

    def labels(pits: List[int], player: int) -> str:
        parts = []
        for p in pits:
            lab = str(p - pits_of(player).start + 1)  # 1..6
            if p in hint_pits:
                parts.append(rgb(f"{lab:^{PIT_W + 2}}", *GOLD, bold=True))
            else:
                parts.append(rgb(f"{lab:^{PIT_W + 2}}", *GREY))
        return GAP.join(parts)

    north_rows = row(north_pits, NORTH)
    south_rows = row(south_pits, SOUTH)
    mid_gap = " " * len(strip_ansi(north_rows[0]))

    # Centre column: label row, north cells, spacer, south cells, label row
    centre: List[str] = [labels(north_pits, NORTH)] + north_rows + [mid_gap] + south_rows + [labels(south_pits, SOUTH)]
    height = len(centre)

    left_store = _store_lines(game.store(NORTH), NORTH, game.current == NORTH, height)
    right_store = _store_lines(game.store(SOUTH), SOUTH, game.current == SOUTH, height)

    margin = "  "
    inner_w = len(strip_ansi(centre[0])) + 2 * 9 + 4 * len(margin)
    top = rgb(G["TL"] + G["H"] * inner_w + G["TR"], *WOOD_DARK)
    bot = rgb(G["BL"] + G["H"] * inner_w + G["BR"], *WOOD_DARK)
    side = rgb(G["V"], *WOOD_DARK)

    lines = []
    n_title = player_color(f" {names[NORTH]} ", NORTH, bold=True) + rgb(G["left"] + " sows this way", *GREY)
    s_title = rgb("sows this way " + G["right"], *GREY) + player_color(f" {names[SOUTH]} ", SOUTH, bold=True)
    lines.append(top)
    lines.append(side + " " + n_title + " " * (inner_w - 1 - len(strip_ansi(n_title))) + side)
    for i in range(height):
        body = margin + left_store[i] + margin + centre[i] + margin + right_store[i] + margin
        lines.append(side + body + side)
    lines.append(side + " " * (inner_w - 1 - len(strip_ansi(s_title))) + s_title + " " + side)
    lines.append(bot)

    w = term_width()
    return "\n".join(center(l, w) for l in lines)


# ---------------------------------------------------------------------- banners
TITLE = r"""
 __  __                        _
|  \/  | __ _ _ __   ___ __ _ | | __ _
| |\/| |/ _` | '_ \ / __/ _` || |/ _` |
| |  | | (_| | | | | (_| (_| || | (_| |
|_|  |_|\__,_|_| |_|\___\__,_||_|\__,_|
"""


def title_block() -> str:
    lines = TITLE.strip("\n").splitlines()
    out = []
    steps = len(lines)
    for i, l in enumerate(lines):
        # gradient sky-blue -> coral
        t = i / max(1, steps - 1)
        r = int(SOUTH_RGB[0] + (NORTH_RGB[0] - SOUTH_RGB[0]) * t)
        g = int(SOUTH_RGB[1] + (NORTH_RGB[1] - SOUTH_RGB[1]) * t)
        b = int(SOUTH_RGB[2] + (NORTH_RGB[2] - SOUTH_RGB[2]) * t)
        out.append(center(rgb(l, r, g, b, bold=True)))
    out.append(center(rgb("the ancient game of seeds and stores", *GREY)))
    return "\n".join(out)


def hr(heavy: bool = False, width: Optional[int] = None) -> str:
    width = width or min(term_width(), 75)
    return center(rgb((G["H"] if heavy else G["h"]) * width, *WOOD_DARK))


def message(text: str, tone: str = "info") -> str:
    icon, colour = {
        "info": (G["dot"], WHITE),
        "good": (G["check"], GREEN),
        "bad": (G["cross"], RED),
        "gold": (G["star"], GOLD),
        "dim": (G["empty"], GREY),
    }[tone]
    return center(rgb(f"{icon} {text}", *colour))


def prompt(text: str) -> str:
    """Read a line with a coloured prompt; returns stripped lowercase text."""
    sys.stdout.write(center(rgb(text, *WHITE, bold=True)).rstrip("\n"))
    sys.stdout.flush()
    try:
        return input(" ").strip().lower()
    except EOFError:
        return "q"
    except KeyboardInterrupt:
        print()
        return "q"


def rules_text() -> List[str]:
    return [
        rgb("How to play Mancala (Kalah rules)", *GOLD, bold=True),
        "",
        "Each player owns the six pits on their side and the store to their right.",
        f"{player_color('South', SOUTH, True)} sits at the bottom and sows to the right; "
        f"{player_color('North', NORTH, True)} sits at the top and sows to the left.",
        "",
        "On your turn pick one of your pits (1-6). All its seeds are lifted and",
        "sown one at a time, counter-clockwise, into every following pit and your",
        "own store. The opponent's store is skipped.",
        "",
        rgb("Extra turn: ", *GREEN, bold=True) + "if the last seed lands in your store, you move again.",
        rgb("Capture:    ", *GREEN, bold=True) + "if the last seed lands in an empty pit on your side and the",
        "            opposite pit has seeds, you take both into your store.",
        "",
        "The game ends when one side is empty. The other player sweeps all the",
        "seeds left on their side into their store. Most seeds wins.",
        "",
        rgb("Keys during a game: ", *GREY) + "1-6 pick a pit · u undo · r rules · q quit",
    ]
