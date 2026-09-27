"""Interactive game loop: menus, turns, animation, undo, results."""

from __future__ import annotations

import argparse
import random
import sys
import time
from typing import Dict, List, Optional, Tuple

from . import __version__, ai, ui
from .game import Game, MoveResult, NORTH, SOUTH, STORE, pits_of

Highlight = Dict[int, Tuple[int, int, int]]


class Session:
    """One match between two seats (human or computer)."""

    def __init__(
        self,
        names: Dict[int, str],
        ai_levels: Dict[int, Optional[str]],
        animate: bool = True,
        seeds: int = 4,
        first: int = SOUTH,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.names = names
        self.ai_levels = ai_levels
        self.animate = animate
        self.game = Game.new(seeds_per_pit=seeds, first=first)
        self.history: List[Game] = []
        self.rng = rng or random.Random()
        self.status: List[Tuple[str, str]] = []
        self.last_highlight: Highlight = {}

    # ---------------------------------------------------------------- helpers
    def is_ai(self, player: int) -> bool:
        return self.ai_levels.get(player) is not None

    def name(self, player: int) -> str:
        return ui.player_color(self.names[player], player, bold=True)

    def label_for(self, pit: int, player: int) -> str:
        return str(pit - pits_of(player).start + 1)

    def pit_from_label(self, label: int, player: int) -> int:
        return pits_of(player).start + label - 1

    # --------------------------------------------------------------- drawing
    def draw(self, highlight: Optional[Highlight] = None, hints: bool = True) -> None:
        ui.clear()
        print(ui.title_block())
        print()
        g = self.game
        hint_pits = g.legal_moves() if hints and not g.is_over() and not self.is_ai(g.current) else ()
        print(ui.render_board(g, self.names, highlight, hint_pits))
        print()
        for text, tone in self.status[-3:]:
            print(ui.message(text, tone))
        if self.status:
            print()

    def flash(self, text: str, tone: str = "info") -> None:
        self.status.append((text, tone))

    # ------------------------------------------------------------- animation
    def animate_move(self, before: Game, result: MoveResult) -> None:
        """Replay the sow seed by seed on a scratch copy of ``before``."""
        if not self.animate:
            return
        g = before.copy()
        seeds = g.board[result.pit]
        g.board[result.pit] = 0
        # Temporarily swap in the scratch board for drawing.
        real = self.game
        self.game = g
        try:
            self.draw({result.pit: ui.GOLD}, hints=False)
            time.sleep(0.25)
            for idx in result.sow_path:
                g.board[idx] += 1
                self.draw({idx: ui.GOLD, result.pit: ui.GREY}, hints=False)
                time.sleep(0.11 if seeds < 12 else 0.05)
            if result.captured:
                cp = result.capture_pit
                opp = 12 - cp
                self.draw({cp: ui.RED, opp: ui.RED}, hints=False)
                time.sleep(0.45)
        finally:
            self.game = real

    # ------------------------------------------------------------------ turns
    def human_turn(self) -> Optional[str]:
        """Return 'quit' to abort, 'undo' to undo, or None after a move."""
        g = self.game
        player = g.current
        while True:
            self.draw(self.last_highlight)
            legal = [self.label_for(p, player) for p in g.legal_moves()]
            choice = ui.prompt(f"{self.names[player]}, choose a pit [{'/'.join(legal)}] ›")
            if choice in ("q", "quit", "exit"):
                return "quit"
            if choice in ("r", "rules", "h", "help", "?"):
                self.show_rules()
                continue
            if choice in ("u", "undo"):
                return "undo"
            if choice.isdigit() and 1 <= int(choice) <= 6:
                pit = self.pit_from_label(int(choice), player)
                if g.board[pit] == 0:
                    self.flash("That pit is empty. Pick another.", "bad")
                    continue
                self.make_move(pit)
                return None
            self.flash("Type a pit number 1-6, or u / r / q.", "dim")

    def ai_turn(self) -> None:
        g = self.game
        player = g.current
        level = self.ai_levels[player]
        assert level is not None
        self.draw(self.last_highlight, hints=False)
        sys.stdout.write(ui.center(ui.rgb(f"{self.names[player]} is thinking", *ui.GREY)))
        sys.stdout.flush()
        t0 = time.time()
        pit = ai.choose_move(g, level, self.rng)
        # A small pause so the human can follow along.
        if self.animate:
            time.sleep(max(0.0, 0.6 - (time.time() - t0)))
        self.make_move(pit)

    def make_move(self, pit: int) -> None:
        g = self.game
        player = g.current
        self.history.append(g.copy())
        before = g.copy()
        result = g.play(pit)
        self.animate_move(before, result)

        label = self.label_for(pit, player)
        who = self.names[player]
        hl: Highlight = {p: ui.GOLD for p in result.sow_path}
        parts = [f"{who} sowed pit {label}."]
        tone = "info"
        if result.captured:
            hl[result.capture_pit] = ui.RED
            hl[12 - result.capture_pit] = ui.RED
            parts.append(f"Captured {result.captured} seeds!")
            tone = "gold"
        if result.extra_turn and not g.is_over():
            parts.append("Landed in the store: extra turn!")
            tone = "good"
        self.flash(" ".join(parts), tone)
        self.last_highlight = hl

    def undo(self) -> None:
        """Rewind to the human's previous decision point."""
        target = None
        while self.history:
            snap = self.history.pop()
            if not self.is_ai(snap.current):
                target = snap
                break
        if target is None:
            self.flash("Nothing to undo.", "dim")
            return
        self.game = target
        self.last_highlight = {}
        self.flash("Undid the last move.", "dim")

    def show_rules(self) -> None:
        ui.clear()
        print(ui.title_block())
        print()
        for line in ui.rules_text():
            print("    " + line)
        print()
        ui.prompt("Press Enter to return ›")

    # ------------------------------------------------------------------- loop
    def run(self) -> bool:
        """Play until the game ends. Returns False if the player quit."""
        while not self.game.is_over():
            if self.is_ai(self.game.current):
                self.ai_turn()
            else:
                action = self.human_turn()
                if action == "quit":
                    return False
                if action == "undo":
                    self.undo()
        self.show_result()
        return True

    def show_result(self) -> None:
        g = self.game
        self.draw({}, hints=False)
        s, n = g.score()
        w = g.winner()
        print(ui.hr(heavy=True))
        if w is None:
            print(ui.center(ui.rgb("  It's a draw!  ", *ui.GOLD, bold=True)))
        else:
            print(ui.center(ui.player_color(f"  {self.names[w]} wins!  ", w, bold=True)))
        print(
            ui.center(
                ui.player_color(f"{self.names[SOUTH]} {s}", SOUTH, True)
                + ui.rgb(f"  {ui.G['dash']}  ", *ui.GREY)
                + ui.player_color(f"{n} {self.names[NORTH]}", NORTH, True)
            )
        )
        print(ui.hr(heavy=True))
        print()


# ------------------------------------------------------------------------ menus
def _menu(title: str, options: List[Tuple[str, str, str]], allow_back: bool = True) -> str:
    """Show a numbered menu; return the key of the chosen option or 'q'."""
    while True:
        ui.clear()
        print(ui.title_block())
        print()
        print(ui.center(ui.rgb(title, *ui.WHITE, bold=True)))
        print()
        width = max(len(ui.strip_ansi(label)) for _, label, _ in options)
        for i, (_, label, desc) in enumerate(options, 1):
            line = ui.rgb(f"[{i}] ", *ui.GOLD, bold=True) + f"{label:<{width}}   " + ui.rgb(desc, *ui.GREY)
            print(ui.center(line))
        print()
        if allow_back:
            print(ui.center(ui.rgb("[q] quit", *ui.GREY)))
            print()
        choice = ui.prompt("›")
        if choice in ("q", "quit", "exit"):
            return "q"
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][0]


def configure_match(rng: random.Random) -> Optional[Tuple[Dict[int, str], Dict[int, Optional[str]], int]]:
    """Walk through the menus. Returns (names, ai_levels, first_player) or None."""
    mode = _menu(
        "Choose a game mode",
        [
            ("pve", "Play vs Computer", "one player against the machine"),
            ("pvp", "Two Players", "pass the keyboard, hot-seat"),
            ("rules", "How to play", "the rules in a nutshell"),
        ],
    )
    if mode == "q":
        return None
    if mode == "rules":
        ui.clear()
        print(ui.title_block())
        print()
        for line in ui.rules_text():
            print("    " + line)
        print()
        ui.prompt("Press Enter to return ›")
        return configure_match(rng)

    if mode == "pvp":
        names = {SOUTH: "South", NORTH: "North"}
        return names, {SOUTH: None, NORTH: None}, SOUTH

    level = _menu(
        "Pick your opponent",
        [(lvl, ui.rgb(ai.LEVEL_INFO[lvl][0], *ui.GOLD if lvl == "hard" else ui.WHITE, bold=(lvl == "hard")), ai.LEVEL_INFO[lvl][1]) for lvl in ai.LEVELS],
    )
    if level == "q":
        return None

    first = _menu(
        "Who moves first?",
        [
            ("me", "You", "take the opening move"),
            ("cpu", "Computer", "let the machine open"),
            ("random", "Flip a coin", "leave it to chance"),
        ],
    )
    if first == "q":
        return None
    if first == "random":
        first = rng.choice(["me", "cpu"])

    names = {SOUTH: "You", NORTH: ai.LEVEL_INFO[level][0]}
    ai_levels: Dict[int, Optional[str]] = {SOUTH: None, NORTH: level}
    return names, ai_levels, SOUTH if first == "me" else NORTH


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mancala", description="Play Mancala (Kalah) in your terminal.")
    parser.add_argument("--no-anim", action="store_true", help="disable sowing animation")
    parser.add_argument("--no-color", action="store_true", help="disable colours")
    parser.add_argument("--ascii", action="store_true", help="draw with plain ASCII instead of Unicode box characters")
    parser.add_argument("--seeds", type=int, default=4, choices=(3, 4, 5, 6), help="seeds per pit (default 4)")
    parser.add_argument("--seed", type=int, default=None, help="random seed for the computer player")
    parser.add_argument("--version", action="version", version=f"mancala {__version__}")
    args = parser.parse_args(argv)

    if args.no_color:
        ui.set_color(False)
    if args.ascii:
        ui.set_ascii(True)
    rng = random.Random(args.seed)

    try:
        while True:
            cfg = configure_match(rng)
            if cfg is None:
                break
            names, levels, first = cfg
            session = Session(names, levels, animate=not args.no_anim, seeds=args.seeds, first=first, rng=rng)
            finished = session.run()
            if not finished:
                break
            again = ui.prompt("Play again? [Y/n] ›")
            if again in ("n", "no", "q"):
                break
    except KeyboardInterrupt:
        print()
    print(ui.center(ui.rgb("Thanks for playing!", *ui.GOLD, bold=True)))
    return 0
