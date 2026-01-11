# ==========================================
# 1. 核心参数与动作编码 (kuhn-rule-2p.md)
# ==========================================
PASS = 0
BET = 1
ACTIONS = [PASS, BET]
NUM_ACTIONS = len(ACTIONS)


class KuhnPokerNode:
    """
    对应流程图中的 [决策节点] 数据结构
    存储特定信息集(InfoSet)下的策略和悔恨值
    """

    def __init__(self, info_set):
        self.info_set = info_set
        self.regret_sum = [0.0] * NUM_ACTIONS
        self.strategy_sum = [0.0] * NUM_ACTIONS
        self.strategy = [0.0] * NUM_ACTIONS  # 当前策略

    def compute_strategy(self):
        """
        [Mermaid: Regret Matching (计算策略)]
        根据正悔恨值比例决定动作概率 (无副作用)
        """
        strategy = [0.0] * NUM_ACTIONS
        normalizing_sum = 0.0
        for a in range(NUM_ACTIONS):
            strategy[a] = self.regret_sum[a] if self.regret_sum[a] > 0 else 0
            normalizing_sum += strategy[a]

        for a in range(NUM_ACTIONS):
            if normalizing_sum > 0:
                strategy[a] /= normalizing_sum
            else:
                # 若无正悔恨值，采用均匀随机策略
                strategy[a] = 1.0 / NUM_ACTIONS

        return strategy

    def get_average_strategy(self):
        """
        [Mermaid: 计算最终平均策略]
        """
        avg_strategy = [0.0] * NUM_ACTIONS
        normalizing_sum = sum(self.strategy_sum)
        for a in range(NUM_ACTIONS):
            if normalizing_sum > 0:
                avg_strategy[a] = self.strategy_sum[a] / normalizing_sum
            else:
                avg_strategy[a] = 1.0 / NUM_ACTIONS
        return avg_strategy


class VanillaCFR:
    def __init__(self):
        # [Mermaid: 初始化仓库]
        self.node_map = {}

    def get_node(self, card, history):
        """获取或创建节点，key 为 '牌+历史'，例如 '1pb'"""
        key = f"{card}{history}"
        if key not in self.node_map:
            self.node_map[key] = KuhnPokerNode(key)
        return self.node_map[key]

    def train(self, iterations):
        """
        主训练循环
        对应 [Mermaid: IterLoop] 及其外层逻辑
        """
        print(f"[Start] 开始训练 {iterations} 次迭代...")

        for i in range(iterations):
            # [Mermaid: ForPlayer - 轮流选择更新方]
            # 这里的 learner 就是流程图中的 "Updater"
            for learner in [0, 1]:
                # [Mermaid: RootCall - 进入游戏树根节点]
                # Chance 节点在递归内处理，根节点只传入空手牌与起始概率
                util_sum = self.cfr(
                    cards=None,
                    history="",
                    p0_reach=1.0,
                    p1_reach=1.0,
                    chance_reach=1.0,
                    learner_id=learner,
                )

                # 优化 2: 在 learner 循环内打印，区分 Learner 0 和 Learner 1
                if (i + 1) % 1000 == 0:
                    print(
                        f"Iteration {i + 1:5d} | Learner {learner} | Expected Value = {util_sum:8.6f}"
                    )

        print("[End] 训练结束，生成策略。")
        self.display_results()

    def cfr(self, cards, history, p0_reach, p1_reach, chance_reach, learner_id):
        """
        [Mermaid: CFR 递归核心逻辑]
        Args:
            cards: 双方手牌；若为 None 表示 Chance 发牌节点
            history: 历史动作
            p0_reach: P0 到达该节点的概率 (不含 Chance)
            p1_reach: P1 到达该节点的概率 (不含 Chance)
            chance_reach: Chance 到达该节点的累计概率
            learner_id: 当前更新策略的玩家
        """
        # --- [Mermaid: 机会节点 -> 发牌] ---
        if cards is None:
            cards_deck = [0, 1, 2]
            chance_prob = 1.0 / 6.0
            util_sum = 0.0
            for c1 in cards_deck:
                for c2 in cards_deck:
                    if c1 == c2:
                        continue
                    util_sum += chance_prob * self.cfr(
                        cards=[c1, c2],
                        history=history,
                        p0_reach=p0_reach,
                        p1_reach=p1_reach,
                        chance_reach=chance_reach * chance_prob,
                        learner_id=learner_id,
                    )
            return util_sum

        plays = len(history)
        player = plays % 2
        # --- [Mermaid: 结局节点 -> 返回游戏胜负收益] ---
        if self.is_terminal(history):
            return self.get_payoff(cards, history, learner_id)

        # --- [Mermaid: 决策节点 -> 识别当前玩家与局面] ---
        my_card = cards[player]
        node = self.get_node(my_card, history)

        # 确定当前的到达概率
        if player == 0:
            my_reach = p0_reach
            opp_reach = p1_reach
        else:
            my_reach = p1_reach
            opp_reach = p0_reach

        # --- [Mermaid: Regret Matching -> 决定动作概率] ---
        # 使用无副作用的 compute_strategy
        strategy = node.compute_strategy()
        node.strategy = strategy  # Optional: store for debugging

        # --- [Mermaid: 向下递归 -> 探索每个动作分支] ---
        util_actions = [0.0] * NUM_ACTIONS
        node_util = 0.0

        for a in ACTIONS:
            action_char = "p" if a == PASS else "b"
            next_history = history + action_char

            # 更新到达率
            next_p0 = p0_reach * strategy[a] if player == 0 else p0_reach
            next_p1 = p1_reach * strategy[a] if player == 1 else p1_reach

            # 递归获取 v(a)（固定更新方视角）
            # chance_reach 直接向下传递
            util_actions[a] = self.cfr(
                cards, next_history, next_p0, next_p1, chance_reach, learner_id
            )

            # --- [Mermaid: 计算局面均值] ---
            node_util += strategy[a] * util_actions[a]

        # --- [Mermaid: IsUpdater (当前玩家 P 是更新方吗?)] ---
        if player == learner_id:
            # --- [Mermaid: 执行更新] ---
            # 1. 累加策略 (Average Strategy)
            # 权重 = pi_i = my_reach * chance_reach
            for a in range(NUM_ACTIONS):
                node.strategy_sum[a] += strategy[a] * my_reach * chance_reach

            # 2. 累加悔恨值 (Regret)
            # 权重 = pi_-i = opp_reach * chance_reach
            for a in range(NUM_ACTIONS):
                regret = util_actions[a] - node_util
                node.regret_sum[a] += regret * opp_reach * chance_reach

        # --- [Mermaid: 向上层返回当前局面价值] ---
        return node_util

    def is_terminal(self, history):
        """判断是否终局"""
        if len(history) < 2:
            return False
        last_two = history[-2:]
        if last_two == "pp":
            return True  # Pass, Pass
        if last_two == "bb":
            return True  # Bet, Bet (or Pass, Bet, Bet)
        if last_two == "bp":
            return True  # Bet, Pass (or Pass, Bet, Pass)
        return False

    def get_payoff(self, cards, history, learner_id):
        """
        [规则文档 section 4]
        返回对于 **更新方(learner_id)** 的收益。
        """
        p0_card, p1_card = cards[0], cards[1]

        pot = 0
        # 分析历史计算底池
        # 初始各下 1
        p0_contrib = 1
        p1_contrib = 1

        # 按照 history 重演
        if len(history) > 0:
            if history[0] == "b":
                p0_contrib += 1
        if len(history) > 1:
            if history[1] == "b":
                p1_contrib += 1
        if len(history) > 2:
            if history[2] == "b":
                p0_contrib += 1

        pot = p0_contrib + p1_contrib

        winner = -1

        # 规则 6: 摊牌与胜负
        if history == "pp":
            winner = 0 if p0_card > p1_card else 1
        elif history == "pbp":
            winner = 1
        elif history == "pbb":
            winner = 0 if p0_card > p1_card else 1
        elif history == "bp":
            winner = 0
        elif history == "bb":
            winner = 0 if p0_card > p1_card else 1

        p0_profit = (pot - p0_contrib) if winner == 0 else -p0_contrib

        if learner_id == 0:
            return p0_profit
        return -p0_profit  # P1 的收益

    def display_results(self):
        """格式化输出结果，展示近似纳什均衡策略"""
        print(f"\n{'=' * 40}")
        print(f"{'InfoSet':^10} | {'Pass (%)':^10} | {'Bet (%)':^10}")
        print(f"{'-' * 40}")

        sorted_keys = sorted(self.node_map.keys())

        for key in sorted_keys:
            node = self.node_map[key]
            avg_strat = node.get_average_strategy()
            card = key[0]
            hist = key[1:] if len(key) > 1 else "(root)"
            if hist == "(root)":
                hist_display = "Start"
            else:
                hist_display = hist.replace("p", "Pass,").replace("b", "Bet,").rstrip(",")

            display_key = f"{card} | {hist_display}"

            print(f"{display_key:<15} {avg_strat[PASS] * 100:6.1f}     {avg_strat[BET] * 100:6.1f}")
        print(f"{'=' * 40}")


# ==========================================
# 运行
# ==========================================
if __name__ == "__main__":
    trainer = VanillaCFR()
    # 训练 10000 次 (对于 Kuhn Poker 足够收敛)
    trainer.train(iterations=10000)
