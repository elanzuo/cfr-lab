import random

import numpy as np

# 游戏常量
# 0: J, 1: Q, 2: K
CARDS = [0, 1, 2]
NUM_ACTIONS = 2  # 0: Pass/Check, 1: Bet


class KuhnNode:
    def __init__(self, key):
        # 信息集标识，如 "1pb"（手牌1，动作过牌-下注）
        self.key = key

        # 累积遗憾值：每个动作在历史对局中相对最优动作的遗憾累计
        # 作为 Regret Matching 的权重来源
        self.regret_sum = np.zeros(NUM_ACTIONS)

        # 累积策略：对每次迭代得到的当前策略做加权累计
        # 用于计算平均策略（期望收敛到纳什均衡）
        self.strategy_sum = np.zeros(NUM_ACTIONS)

        # 当前策略：由本轮 regret_sum 经过归一化得到的动作概率分布
        self.strategy = np.zeros(NUM_ACTIONS)

    def get_strategy(self, realization_weight):
        """
        根据 Regret Matching (遗憾匹配) 计算当前策略：
        1) 仅保留正遗憾值作为动作权重；负遗憾视为 0
        2) 将正遗憾权重归一化为概率分布；若全为 0 则退化为均匀策略
        3) 用到达该信息集的概率权重 realization_weight 累加平均策略

        realization_weight 表示当前路径上该玩家到达此信息集的“实现概率”，（即前序动作所导致的到达权重），用于计算平均策略的加权累计。
            如果是玩家0的选择则传递p0，是玩家1就传递p1
        """
        normalizing_sum = 0

        for a in range(NUM_ACTIONS):
            self.strategy[a] = self.regret_sum[a] if self.regret_sum[a] > 0 else 0
            normalizing_sum += self.strategy[a]

        for a in range(NUM_ACTIONS):
            if normalizing_sum > 0:
                self.strategy[a] /= normalizing_sum
            else:
                # 如果没有遗憾值，则采用均匀分布
                self.strategy[a] = 1.0 / NUM_ACTIONS

            # 将当前策略累加到 strategy_sum，用于后续计算平均策略
            self.strategy_sum[a] += realization_weight * self.strategy[a]

        return self.strategy

    def get_average_strategy(self):
        """
        计算平均策略（用于逼近纳什均衡）：
        - 将累计策略 strategy_sum 归一化为概率分布
        - 若累计和为 0（尚未访问/更新），则退化为均匀策略
        说明：平均策略是 CFR 常用的输出，而非单次迭代的当前策略
        """
        avg_strategy = np.zeros(NUM_ACTIONS)
        normalizing_sum = np.sum(self.strategy_sum)
        for a in range(NUM_ACTIONS):
            if normalizing_sum > 0:
                avg_strategy[a] = self.strategy_sum[a] / normalizing_sum
            else:
                avg_strategy[a] = 1.0 / NUM_ACTIONS
        return avg_strategy


class KuhnCFRTrainer:
    def __init__(self):
        self.node_map = {}  # 存储所有的信息集节点

    def train(self, iterations=10):
        total_utility = 0
        for _ in range(iterations):
            cards = random.sample(CARDS, 2)  # 洗牌并为两名玩家发牌
            # 初始权重为 1, 1
            iteration_utility = self.cfr(cards, "", 1, 1)
            total_utility += iteration_utility

    def cfr(self, cards, history, reach_prob_p0, reach_prob_p1):
        """
        递归 CFR 函数
        cards: [玩家0手牌, 玩家1手牌]
        history: 动作历史，如 "p" (pass), "pb" (pass, bet)
        reach_prob_p0, reach_prob_p1: 到达该节点时，玩家0和玩家1的贡献概率 (Reach Probability)。
                训练从根节点开始，没有任何历史动作限制，因此两位玩家到达根节点的概率都是 1，所以调用 self.cfr(cards, "", 1, 1) 作为初始权重。
                随后在递归过程中，这两个权重会根据玩家的行动概率逐步乘上去，反映“沿着当前路径走到这里”的概率。这样在计算遗憾和平均策略时就能正确地按路径概率加权。
        """
        plays = len(history)
        player = plays % 2

        # 1. 检查是否为叶子节点（结算点）
        terminal_utility = self.get_terminal_utility(cards, history, player)
        if terminal_utility is not None:
            return terminal_utility

        # 2. 获当前信息集节点；如果 node_map 还不存在该信息集节点就新建
        info_set = str(cards[player]) + history
        if info_set not in self.node_map:
            self.node_map[info_set] = KuhnNode(info_set)
        node = self.node_map[info_set]

        # 3. 递归计算每个动作的收益
        # current_strategy 获取的当前策略
        current_strategy = node.get_strategy(reach_prob_p0 if player == 0 else reach_prob_p1)
        # action_utilities: 当前玩家在该信息集下，选择每个动作时对应的期望收益（含对手最优反应后的递归回报）
        action_utilities = np.zeros(NUM_ACTIONS)
        # node_utility: 按当前策略加权后的信息集期望收益（即节点价值/平均收益）
        node_utility = 0

        for action_ in range(NUM_ACTIONS):
            next_history = history + ("p" if action_ == 0 else "b")
            if player == 0:
                # 因为递归会切换玩家视角，所以这里取负号 - 把对手视角的收益翻回“当前玩家”的收益（零和博弈的对称性）
                # reach_prob_p0 * current_strategy[action_]：表示“玩家0到达下一节点的概率”，= 之前的到达概率 × 这次选择该动作的概率。
                # reach_prob_p1 保持不变，因为这一步是玩家0行动，玩家1的到达概率不受影响。
                action_utilities[action_] = -self.cfr(
                    cards,
                    next_history,
                    reach_prob_p0 * current_strategy[action_],
                    reach_prob_p1,
                )
            else:
                action_utilities[action_] = -self.cfr(
                    cards,
                    next_history,
                    reach_prob_p0,
                    reach_prob_p1 * current_strategy[action_],
                )
            # 把每个动作的收益按其发生概率加权相加，就是该信息集在当前策略下的期望收益（也叫节点价值/平均收益）。公式就是：node_utility = Σ_a π(a) * U(a)
            # current_strategy[action_] 是当前策略下选择该动作的概率；action_utilities[action_] 是“选择该动作后的收益”
            node_utility += current_strategy[action_] * action_utilities[action_]

        # 4. 更新遗憾值 (核心公式: 遗憾 = 动作收益 - 节点平均收益)
        opponent_reach_prob = reach_prob_p1 if player == 0 else reach_prob_p0
        for a in range(NUM_ACTIONS):
            # action_utilities[a] 是“如果当前行动者在该信息集选择动作 a 的收益”；node_utility 是“当前策略下的期望收益”
            # 两者之差就是“后悔值”：如果我当时选了动作 a，会比现在的策略好/差多少
            regret = action_utilities[a] - node_utility
            # CFR 更新遗憾时要乘上“对手到达该节点的概率”
            node.regret_sum[a] += opponent_reach_prob * regret

        return node_utility

    def get_terminal_utility(self, cards, history, player):
        """
        判断博弈是否结束，返回当前玩家的收益
        """
        plays = len(history)
        opponent = 1 - player
        if plays >= 2:
            is_player_card_higher = cards[player] > cards[opponent]

            # 动作序列: pp (过牌-过牌)
            if history == "pp":
                return 1 if is_player_card_higher else -1
            # 动作序列: pbb (过牌-下注-跟注) 或 bb (下注-跟注)
            if history in ["pbb", "bb"]:
                return 2 if is_player_card_higher else -2
            # 动作序列: pb p (过牌-下注-弃牌)
            if history == "pbp":
                return 1  # 对手(player)弃牌了，当前行动者赢1
            # 动作序列: bp (下注-弃牌)
            if history == "bp":
                return 1
        return None

    def print_results(self):
        print("\n--- 训练结果 (平均策略) ---")
        print("信息集\t过牌(P)\t下注(B)")
        for key in sorted(self.node_map.keys()):
            strat = self.node_map[key].get_average_strategy()
            print(f"{key}:\t{strat[0]:.3f}\t{strat[1]:.3f}")


if __name__ == "__main__":
    trainer = KuhnCFRTrainer()
    trainer.train(10)
    trainer.print_results()
