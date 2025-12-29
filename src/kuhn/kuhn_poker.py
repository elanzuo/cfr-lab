import enum
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


# --- 1. 常量与枚举定义 ---
class Action(enum.IntEnum):
    PASS = 0
    BET = 1


INVALID_PLAYER = -1
CHANCE_PLAYER = -1
TERMINAL_PLAYER = -2
DEFAULT_PLAYERS = 2
ANTE = 1.0
BET_SIZE = 1.0


@dataclass(frozen=True, slots=True)
class KuhnConfig:
    num_players: int = DEFAULT_PLAYERS
    ante: float = ANTE
    bet_size: float = BET_SIZE
    enable_checks: bool = False

    def __post_init__(self) -> None:
        if self.num_players < 2:
            raise ValueError("num_players 必须 >= 2")
        if self.ante <= 0 or self.bet_size <= 0:
            raise ValueError("ante 与 bet_size 必须为正数")


class KuhnState:
    """
    完全对应 OpenSpiel C++ 的 KuhnState 类
    """

    __slots__ = (
        "num_players",
        "history",
        "card_dealt",
        "first_bettor",
        "winner",
        "pot",
        "ante",
        "_bet_size",
        "_enable_checks",
        "_config",
        "_deck_size",
    )

    def __init__(
        self,
        num_players_or_config: Union[int, KuhnConfig],
        *,
        ante: float = ANTE,
        bet_size: float = BET_SIZE,
        enable_checks: bool = False,
    ):
        if isinstance(num_players_or_config, KuhnConfig):
            config = num_players_or_config
        else:
            config = KuhnConfig(
                num_players=num_players_or_config,
                ante=ante,
                bet_size=bet_size,
                enable_checks=enable_checks,
            )
        self._config = config
        self.num_players = config.num_players
        self._deck_size = self.num_players + 1
        self._bet_size = config.bet_size
        self._enable_checks = config.enable_checks

        # history: 存储动作序列 (int)。
        # 0..N-1 为 Chance 动作(发牌)，N..End 为玩家动作
        self.history: List[int] = []

        # card_dealt: 索引为牌面值(0..N)，值为持有该牌的 Player ID，未发出为 -1
        # card_dealt_(game->NumPlayers() + 1, kInvalidPlayer)
        self.card_dealt = [INVALID_PLAYER] * self._deck_size

        self.first_bettor = INVALID_PLAYER
        self.winner = INVALID_PLAYER
        self.pot = config.ante * self.num_players

        # 记录每个玩家的投入，索引为 Player ID
        self.ante = [config.ante] * self.num_players

    def current_player(self) -> int:
        """"""
        if self.is_terminal():
            return TERMINAL_PLAYER

        # 历史长度小于人数，处于发牌阶段 (Chance Node)
        if len(self.history) < self.num_players:
            return CHANCE_PLAYER

        # 玩家轮流行动
        return len(self.history) % self.num_players

    def is_chance_node(self) -> bool:
        return self.current_player() == CHANCE_PLAYER

    def is_terminal(self) -> bool:
        """"""
        return self.winner != INVALID_PLAYER

    def apply_action(self, action: int):
        """对应 C++ 的 DoApplyAction"""
        if self._enable_checks and self.is_terminal():
            raise RuntimeError("终局状态不可再行动")

        curr_player = self.current_player()

        # 1. 处理 Chance (发牌)
        if len(self.history) < self.num_players:
            # 此时 action 代表牌面值
            # C++ 逻辑: card_dealt_[move] = history_.size()
            # history_.size() 此时正好等于接下来要拿牌的 player id
            if self._enable_checks:
                if not (0 <= action < self._deck_size):
                    raise ValueError("发牌动作越界")
                if self.card_dealt[action] != INVALID_PLAYER:
                    raise ValueError("重复发牌")
            player_receiving_card = len(self.history)
            self.card_dealt[action] = player_receiving_card

        # 2. 处理 Betting
        else:
            if self._enable_checks and action not in (Action.PASS, Action.BET):
                raise ValueError("下注动作必须为 PASS(0) 或 BET(1)")
            if action == Action.BET:
                if self.first_bettor == INVALID_PLAYER:
                    self.first_bettor = curr_player
                self.pot += self._bet_size
                self.ante[curr_player] += self._bet_size

        # 将动作加入历史
        self.history.append(action)

        # 3. 检查终止条件
        # num_actions 指的是玩家产生的动作数（排除发牌动作）
        num_actions = len(self.history) - self.num_players

        # 情况 A: 无人下注 (Nobody bet)
        if self.first_bettor == INVALID_PLAYER and num_actions == self.num_players:
            # 赢家是拥有最高牌的人
            # 检查牌堆中最大的牌 (N)，看是谁拿的；如果没有，检查 N-1
            #
            if self.card_dealt[self.num_players] != INVALID_PLAYER:
                self.winner = self.card_dealt[self.num_players]
            else:
                self.winner = self.card_dealt[self.num_players - 1]

        # 情况 B: 有人下注 (Betting occurred)
        # 终止条件: 所有人在 first_bettor 之后都表态了
        # C++ 逻辑: num_actions == num_players + first_bettor_
        elif (
            self.first_bettor != INVALID_PLAYER
            and num_actions == self.num_players + self.first_bettor
        ):
            # 从最大牌开始向下检查，找拥有该牌且没有弃牌(DidBet)的玩家
            #
            for card in range(self.num_players, -1, -1):
                player = self.card_dealt[card]
                if player != INVALID_PLAYER and self.did_bet(player):
                    self.winner = player
                    break

    def did_bet(self, player: int) -> bool:
        """
        判断玩家是否进行了下注/跟注。

        """
        if self.first_bettor == INVALID_PLAYER:
            return False
        if player == self.first_bettor:
            return True

        # 根据 OpenSpiel 逻辑，通过历史索引判断动作
        # 玩家 P 的第一个动作索引是: N + P
        # 玩家 P 的第二个动作索引是: N + N + P (如果存在)

        if player > self.first_bettor:
            # 在 first_bettor 之后的玩家，只有一轮行动机会
            idx = self.num_players + player
            if idx >= len(self.history):
                return False
            return self.history[idx] == Action.BET
        else:
            # 在 first_bettor 之前的玩家，必须有第二轮行动
            idx = self.num_players * 2 + player
            # 需要检查索引越界，虽然在结算时应该都有
            if idx < len(self.history):
                return self.history[idx] == Action.BET
            return False

    def legal_actions(self) -> List[int]:
        """"""
        if self.is_terminal():
            return []

        if self.is_chance_node():
            # 返回所有未发出的牌
            actions = []
            for card, owner in enumerate(self.card_dealt):
                if owner == INVALID_PLAYER:
                    actions.append(card)
            return actions
        else:
            return [Action.PASS, Action.BET]

    def returns(self) -> List[float]:
        """"""
        if not self.is_terminal():
            return [0.0] * self.num_players

        outcomes = [0.0] * self.num_players
        for p in range(self.num_players):
            # 投入计算: ante 记录了玩家实际投入，能自然兼容不同 bet_size
            bet = float(self.ante[p])

            if p == self.winner:
                outcomes[p] = self.pot - bet
            else:
                outcomes[p] = -bet
        return outcomes

    def information_state_string(self, player: Optional[int] = None) -> str:
        """
        完全对齐 C++ 的字符串表示，用于 CFR 查表
        格式: {Card}{History}，例如 "0pb"

        """
        if player is None:
            player = self.current_player()
        if player < 0:
            return "Chance"
        if self._enable_checks and player >= self.num_players:
            raise ValueError("player 越界")

        result = ""
        # 1. 私有牌 (Private Card)
        # 只有一张牌，history 中前 N 个动作是发牌
        # 第 player 个动作就是发给该 player 的牌
        if len(self.history) > player:
            card_val = self.history[player]
            result += str(card_val)

        # 2. 下注序列 (Betting Sequence)
        # 从 index N 开始是下注动作
        for i in range(self.num_players, len(self.history)):
            act = self.history[i]
            result += "b" if act == Action.BET else "p"

        return result

    def chance_outcomes(self) -> List[Tuple[int, float]]:
        """"""
        if self._enable_checks and not self.is_chance_node():
            raise RuntimeError("当前不是 Chance 节点")
        actions = self.legal_actions()
        prob = 1.0 / len(actions)
        return [(a, prob) for a in actions]

    def clone(self):
        """深拷贝状态，用于搜索"""
        new_state = KuhnState(self._config)
        new_state.history = self.history[:]
        new_state.card_dealt = self.card_dealt[:]
        new_state.first_bettor = self.first_bettor
        new_state.winner = self.winner
        new_state.pot = self.pot
        new_state.ante = self.ante[:]
        return new_state


# --- 游戏入口类 ---
class KuhnPokerGame:
    def __init__(
        self,
        num_players: int = DEFAULT_PLAYERS,
        *,
        ante: float = ANTE,
        bet_size: float = BET_SIZE,
        enable_checks: bool = False,
    ):
        self.config = KuhnConfig(
            num_players=num_players,
            ante=ante,
            bet_size=bet_size,
            enable_checks=enable_checks,
        )
        self.num_players = self.config.num_players

    def new_initial_state(self) -> KuhnState:
        return KuhnState(self.config)
