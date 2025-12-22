from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

# Decision actions (match OpenSpiel ActionType)
PASS = 0  # Pass: check (no bet yet) or fold (after someone bet)
BET = 1  # Bet: bet (if no bet yet) or call (after someone bet)

CHANCE_PLAYER = -1
TERMINAL_PLAYER = -2


@dataclass
class KuhnConfig:
    num_players: int = 2
    ante: int = 1
    bet_size: int = 1

    def __post_init__(self) -> None:
        if not (2 <= self.num_players <= 10):
            raise ValueError("num_players must be in [2, 10]")
        if self.ante != 1 or self.bet_size != 1:
            # OpenSpiel Kuhn is fixed at 1/1; keep it strict to avoid silent mismatch.
            raise ValueError(
                "This OpenSpiel-aligned implementation requires ante=1 and bet_size=1."
            )


@dataclass
class HistoryItem:
    player: int  # CHANCE_PLAYER for chance actions; otherwise 0..num_players-1
    action: int  # card_id for chance; PASS/BET for decision nodes


@dataclass
class KuhnState:
    cfg: KuhnConfig

    # OpenSpiel stores mapping card -> player (vector size num_players+1, init invalid)
    # card_dealt[card] = player who received it, or None if not dealt
    card_dealt: List[Optional[int]] = field(init=False)

    # bookkeeping
    first_bettor: Optional[int] = None  # player id of first bet, None if no one bet yet
    pot: int = field(init=False)  # starts at ante * num_players
    ante_contrib: List[int] = field(init=False)  # per player contributed amount, starts at 1 each

    # terminal bookkeeping
    winner: Optional[int] = None

    # full history includes chance deals and betting actions
    history: List[HistoryItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        n = self.cfg.num_players
        self.card_dealt = [None] * (n + 1)
        self.pot = self.cfg.ante * n
        self.ante_contrib = [self.cfg.ante] * n

    # ---------------- OpenSpiel-like core API ----------------

    def is_terminal(self) -> bool:
        return self.winner is not None

    def is_chance_node(self) -> bool:
        return (not self.is_terminal()) and (len(self.history) < self.cfg.num_players)

    def current_player(self) -> int:
        if self.is_terminal():
            return TERMINAL_PLAYER
        if self.is_chance_node():
            return CHANCE_PLAYER
        # after all cards dealt, players act in order 0..n-1 repeating
        return len(self.history) % self.cfg.num_players

    def legal_actions(self) -> List[int]:
        if self.is_terminal():
            return []
        if self.is_chance_node():
            # remaining cards
            return [c for c, p in enumerate(self.card_dealt) if p is None]
        # decision node: always PASS/BET
        return [PASS, BET]

    def chance_outcomes(self) -> List[Tuple[int, float]]:
        """OpenSpiel: uniform over remaining cards at this chance node."""
        if not self.is_chance_node():
            raise RuntimeError("Not a chance node")
        remaining = self.legal_actions()
        p = 1.0 / len(remaining)
        return [(c, p) for c in remaining]

    def apply_action(self, action: int) -> None:
        if self.is_terminal():
            raise RuntimeError("Cannot act in terminal state")

        if self.is_chance_node():
            self._apply_chance(action)
        else:
            self._apply_decision(action)

    # ---------------- Key mechanics (match kuhn_poker.cc) ----------------

    def _apply_chance(self, card: int) -> None:
        if not self.is_chance_node():
            raise RuntimeError("Not a chance node")
        if not (0 <= card < len(self.card_dealt)):
            raise ValueError("Invalid card")
        if self.card_dealt[card] is not None:
            raise ValueError("Card already dealt")

        dealing_to = len(self.history)  # player index 0..n-1
        self.card_dealt[card] = dealing_to
        # history stores chance action as the card id
        self.history.append(HistoryItem(CHANCE_PLAYER, card))
        # no terminal check during dealing

    def _apply_decision(self, move: int) -> None:
        if move not in (PASS, BET):
            raise ValueError("Decision move must be PASS(0) or BET(1)")

        p = self.current_player()

        # OpenSpiel bookkeeping on BET after dealing:
        if move == BET:
            if self.first_bettor is None:
                self.first_bettor = p
            self.pot += self.cfg.bet_size
            self.ante_contrib[p] += self.cfg.bet_size

        # Push to history (player, move)
        self.history.append(HistoryItem(p, move))

        # Terminal check exactly as OpenSpiel does
        self._maybe_set_terminal()

    def _maybe_set_terminal(self) -> None:
        n = self.cfg.num_players
        # number of betting actions (actions after dealing)
        num_actions = len(self.history) - n
        if num_actions < 0:
            return  # still dealing

        if self.first_bettor is None:
            # Nobody bet; terminal after everyone acted once.
            if num_actions == n:
                # Winner is holder of highest dealt card. Deck size n+1; top card index n.
                # If top card wasn't dealt, winner is holder of next-highest.
                winner = self.card_dealt[n]
                if winner is None:
                    winner = self.card_dealt[n - 1]
                if winner is None:
                    raise RuntimeError("No winner found in no-bet showdown")
                self.winner = winner
        else:
            # There was betting; terminal after num_actions == n + first_bettor
            if num_actions == n + self.first_bettor:
                # Winner is highest card among players who "DidBet" (bettor or caller).
                for card in range(n, -1, -1):
                    player = self.card_dealt[card]
                    if player is not None and self.did_bet(player):
                        self.winner = player
                        break
                if self.winner is None:
                    raise RuntimeError("No winner found in bet showdown")

    def did_bet(self, player: int) -> bool:
        """Replicates OpenSpiel DidBet() based on history indexing layout."""
        n = self.cfg.num_players
        fb = self.first_bettor
        if fb is None:
            return False
        if player == fb:
            return True

        # After dealing, betting actions are appended. Layout:
        # - First round actions: players 0..n-1 at indices [n .. n+(n-1)]
        # - Second round (only players 0..fb-1) at indices [2n .. 2n+fb-1]
        if player > fb:
            idx = n + player  # corresponds to that player's first-round action
        else:
            idx = 2 * n + player  # corresponds to that player's second action (response after bet)

        if idx < 0 or idx >= len(self.history):
            # Not yet reached that point in play.
            return False
        return self.history[idx].action == BET

    def returns(self) -> List[float]:
        """OpenSpiel Returns(): winner gets pot - bet, others -bet where bet is 2 if did_bet else 1."""
        n = self.cfg.num_players
        if not self.is_terminal():
            return [0.0] * n
        w = self.winner
        assert w is not None

        out = [0.0] * n
        for p in range(n):
            bet = 2 if self.did_bet(p) else 1
            out[p] = (self.pot - bet) if (p == w) else -bet
        return out

    # ---------------- OpenSpiel-aligned info-state string ----------------

    def information_state_string(self, player: int) -> str:
        """
        Matches the OpenSpiel info_state_observer string for perfect-recall, public+private:
        - First: the dealt card id for this player (decimal, no delimiter)
        - Then: public betting history as 'p'/'b' for actions after dealing
        """
        n = self.cfg.num_players
        if not (0 <= player < n):
            raise ValueError("player out of range")

        s = ""

        # Private card (history_[player].action is the card id) if it has been dealt
        if len(self.history) > player:
            s += str(self.history[player].action)

        # Public betting history from index n onward
        for i in range(n, len(self.history)):
            a = self.history[i].action
            s += "b" if a == BET else "p"
        return s


@dataclass
class KuhnGame:
    cfg: KuhnConfig

    def new_initial_state(self) -> KuhnState:
        return KuhnState(self.cfg)
