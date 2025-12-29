import argparse
import sys

import numpy as np
from kuhn_poker import Action, KuhnPokerGame  # 引用之前写好的游戏逻辑
from loguru import logger

# 说明：这是全树遍历版的 vanilla CFR 实现（非 CFR+ / 非 MCCFR 采样）。
# 可能的非标准点 / 实现选择：
# - 动作数固定为 2（PASS/BET），是 Kuhn Poker 特例而非通用博弈。
# - 单次遍历同时更新双方 regret（不是 Alternating CFR）。
# - chance 节点完全枚举（不是采样式）。
# - 递归返回值统一为玩家 0 视角，玩家 1 分支通过取负号处理。


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


def _format_strategy(strategy: np.ndarray) -> str:
    return f"pass={strategy[0]:.3f}, bet={strategy[1]:.3f}"


def _log_snapshot(
    step: int,
    snapshot: dict[str, dict[str, np.ndarray]],
    focus: list[str],
    show_regret: bool,
    show_current: bool,
) -> None:
    keys = focus if focus else sorted(snapshot.keys())
    logger.info("step={} snapshot_keys={}", step, len(snapshot))
    for info_set in keys:
        if info_set not in snapshot:
            logger.info("  infoset={} missing", info_set)
            continue
        data = snapshot[info_set]
        avg_strategy = data["avg_strategy"]
        current_strategy = data["current_strategy"]
        regret = data["regret"]
        parts = [f"infoset={info_set}", f"avg=[{_format_strategy(avg_strategy)}]"]
        if show_current:
            parts.append(f"current=[{_format_strategy(current_strategy)}]")
        if show_regret:
            parts.append(f"regret=[{regret[0]:.3f}, {regret[1]:.3f}]")
        logger.info("  {}", " ".join(parts))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 vanilla CFR 并输出训练日志。")
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=20000,
        help="迭代次数（默认：20000）",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=1000,
        help="日志间隔（默认：1000，0 表示只输出最终结果）",
    )
    parser.add_argument(
        "--focus",
        nargs="*",
        default=[],
        help="仅输出指定 infoset（例：0 1 2 0b 1b 2b 1pb）",
    )
    parser.add_argument(
        "--show-regret",
        action="store_true",
        help="是否输出 regret",
    )
    parser.add_argument(
        "--show-current",
        action="store_true",
        help="是否输出当前策略（即时策略）",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="日志级别（默认：INFO）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logger.remove()
    logger.add(
        sys.stderr,
        level=args.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{level}</level> {message}",
    )

    solver = CFRSolver()

    if args.log_every > 0:
        _log_snapshot(
            step=0,
            snapshot=solver.get_snapshot(),
            focus=args.focus,
            show_regret=args.show_regret,
            show_current=args.show_current,
        )

    for step in range(1, args.iterations + 1):
        solver.train_step()
        if args.log_every > 0 and step % args.log_every == 0:
            _log_snapshot(
                step=step,
                snapshot=solver.get_snapshot(),
                focus=args.focus,
                show_regret=args.show_regret,
                show_current=args.show_current,
            )

    if args.log_every == 0 or args.iterations % args.log_every != 0:
        _log_snapshot(
            step=args.iterations,
            snapshot=solver.get_snapshot(),
            focus=args.focus,
            show_regret=args.show_regret,
            show_current=args.show_current,
        )


if __name__ == "__main__":
    main()
