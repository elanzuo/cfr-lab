# cfr_backend.py
import copy

import numpy as np
from kuhn_poker import Action, KuhnPokerGame  # 引用之前写好的游戏逻辑


class CFRNode:
    def __init__(self, num_actions):
        self.regret_sum = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)
        self.strategy = np.zeros(num_actions)

    def get_strategy(self, realization_weight):
        # Regret Matching
        positive_regret = np.maximum(self.regret_sum, 0)
        sum_pos_regret = np.sum(positive_regret)
        if sum_pos_regret > 0:
            strategy = positive_regret / sum_pos_regret
        else:
            strategy = np.ones(len(self.regret_sum)) / len(self.regret_sum)

        self.strategy_sum += strategy * realization_weight
        self.strategy = strategy
        return strategy

    def get_average_strategy(self):
        # 计算平均策略 (用于最终策略)
        strategy_sum = np.sum(self.strategy_sum)
        if strategy_sum > 0:
            return self.strategy_sum / strategy_sum
        return np.ones(len(self.strategy_sum)) / len(self.strategy_sum)


class CFRSolver:
    def __init__(self):
        self.game = KuhnPokerGame()
        self.nodes = {}  # Map: InfoSet -> CFRNode

    def _get_node(self, info_set, num_actions):
        if info_set not in self.nodes:
            self.nodes[info_set] = CFRNode(num_actions)
        return self.nodes[info_set]

    def train_step(self):
        """执行一次完整的 CFR 迭代"""
        state = self.game.new_initial_state()
        self._cfr(state, 1.0, 1.0)

    def _cfr(self, state, p0, p1):
        if state.is_terminal():
            return state.returns()[0]

        if state.is_chance_node():
            strategy = state.chance_outcomes()
            expected_util = 0
            for action, prob in strategy:
                next_state = state.clone()
                next_state.apply_action(action)
                expected_util += prob * self._cfr(next_state, p0, p1)
            return expected_util

        # 玩家节点
        info_set = state.information_state_string()
        node = self._get_node(info_set, 2)

        realization_weight = p0 if state.current_player() == 0 else p1
        strategy = node.get_strategy(realization_weight)

        util = np.zeros(2)
        node_util = 0

        for i, action in enumerate([Action.PASS, Action.BET]):
            next_state = state.clone()
            next_state.apply_action(action)

            if state.current_player() == 0:
                util[i] = self._cfr(next_state, p0 * strategy[i], p1)
            else:
                util[i] = -self._cfr(next_state, p0, p1 * strategy[i])

            node_util += strategy[i] * util[i]

        for i in range(2):
            regret = util[i] - node_util
            node.regret_sum[i] += regret * (p1 if state.current_player() == 0 else p0)

        return node_util if state.current_player() == 0 else -node_util

    def get_snapshot(self):
        """
        创建当前训练状态的轻量级快照
        仅保存用于展示的数据，不需要保存对象方法
        """
        snapshot = {}
        for info_set, node in self.nodes.items():
            avg_strat = node.get_average_strategy()
            # 保存关键数据：平均策略、当前Regret、当前Strategy
            snapshot[info_set] = {
                "avg_strategy": avg_strat.copy(),
                "regret": node.regret_sum.copy(),
                "current_strategy": node.strategy.copy(),
            }
        return snapshot
