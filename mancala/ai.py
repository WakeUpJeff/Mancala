"""Computer opponents at three difficulty levels.

* ``easy``   – mostly random, with a soft spot for obvious extra turns.
* ``medium`` – one-ply greedy: picks the move that maximises immediate gain,
               including chained extra turns, with a little randomness.
* ``hard``   – depth-limited minimax with alpha-beta pruning and a
               positional evaluation function.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .game import Game, NORTH, SOUTH, STORE, pits_of

LEVELS = ("easy", "medium", "hard")

LEVEL_INFO: Dict[str, Tuple[str, str]] = {
    "easy": ("Novice", "Plays mostly at random. Good for learning the rules."),
    "medium": ("Tactician", "Grabs captures and extra turns. Thinks one move ahead."),
    "hard": ("Grandmaster", "Searches several moves deep. Bring your A-game."),
}

_SEARCH_DEPTH = {"hard": 8}


def choose_move(game: Game, level: str, rng: Optional[random.Random] = None) -> int:
    """Return a legal pit index for the current player of ``game``."""
    rng = rng or random.Random()
    moves = game.legal_moves()
    if not moves:
        raise ValueError("no legal moves")
    if len(moves) == 1:
        return moves[0]
    if level == "easy":
        return _easy(game, moves, rng)
    if level == "medium":
        return _medium(game, moves, rng)
    if level == "hard":
        return _hard(game, moves, rng)
    raise ValueError(f"unknown level {level!r}")


# ------------------------------------------------------------------------ easy
def _easy(game: Game, moves: List[int], rng: random.Random) -> int:
    # 30% of the time take a free extra turn if one exists, else random.
    extra = [m for m in moves if _lands_in_store(game, m)]
    if extra and rng.random() < 0.3:
        return rng.choice(extra)
    return rng.choice(moves)


def _lands_in_store(game: Game, pit: int) -> bool:
    seeds = game.board[pit]
    # Distance to own store ignoring the skipped opponent store (13 positions per lap).
    dist = (STORE[game.current] - pit) % 14
    return seeds % 13 == dist


# ---------------------------------------------------------------------- medium
def _medium(game: Game, moves: List[int], rng: random.Random) -> int:
    player = game.current
    scored = []
    for m in moves:
        g = game.copy()
        gain = _greedy_line(g, m, player)
        scored.append((gain + rng.random() * 0.5, m))
    scored.sort(reverse=True)
    return scored[0][1]


def _greedy_line(g: Game, pit: int, player: int) -> float:
    """Play ``pit`` and, on extra turns, keep greedily playing. Return store gain."""
    before = g.store(player)
    res = g.play(pit)
    depth = 0
    while res.extra_turn and not g.is_over() and depth < 6:
        best = None
        for m in g.legal_moves():
            gg = g.copy()
            gg.play(m)
            v = gg.store(player)
            if best is None or v > best[0]:
                best = (v, m)
        if best is None:
            break
        res = g.play(best[1])
        depth += 1
    gain = g.store(player) - before
    # Slightly prefer leaving fewer seeds exposed to capture.
    exposure = sum(g.board[i] for i in pits_of(player) if g.board[12 - i] == 0)
    return gain - 0.05 * exposure


# ------------------------------------------------------------------------ hard
def _hard(game: Game, moves: List[int], rng: random.Random) -> int:
    player = game.current
    depth = _SEARCH_DEPTH["hard"]
    best_val = float("-inf")
    best_moves: List[int] = []
    # Order moves: extra turns first, then by seed count, improves pruning.
    ordered = sorted(moves, key=lambda m: (not _lands_in_store(game, m), -game.board[m]))
    for m in ordered:
        g = game.copy()
        g.play(m)
        val = _minimax(g, depth - 1, float("-inf"), float("inf"), player)
        if val > best_val + 1e-9:
            best_val, best_moves = val, [m]
        elif abs(val - best_val) <= 1e-9:
            best_moves.append(m)
    return rng.choice(best_moves)


def _evaluate(g: Game, me: int) -> float:
    them = 1 - me
    if g.is_over():
        diff = g.store(me) - g.store(them)
        return 1000.0 * (1 if diff > 0 else -1 if diff < 0 else 0) + diff
    store_diff = g.store(me) - g.store(them)
    side_diff = g.side_seeds(me) - g.side_seeds(them)
    # Seeds sitting in my empty-opposite pits are safe; seeds across from my
    # empties are capture targets for me, and vice versa.
    my_threat = sum(g.board[12 - i] for i in pits_of(me) if g.board[i] == 0)
    their_threat = sum(g.board[12 - i] for i in pits_of(them) if g.board[i] == 0)
    return store_diff * 1.0 + side_diff * 0.25 + (my_threat - their_threat) * 0.15


def _minimax(g: Game, depth: int, alpha: float, beta: float, me: int) -> float:
    if depth == 0 or g.is_over():
        return _evaluate(g, me)
    moves = g.legal_moves()
    maximizing = g.current == me
    if maximizing:
        value = float("-inf")
        for m in sorted(moves, key=lambda m: not _lands_in_store(g, m)):
            gg = g.copy()
            gg.play(m)
            value = max(value, _minimax(gg, depth - 1, alpha, beta, me))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    value = float("inf")
    for m in sorted(moves, key=lambda m: not _lands_in_store(g, m)):
        gg = g.copy()
        gg.play(m)
        value = min(value, _minimax(gg, depth - 1, alpha, beta, me))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value
