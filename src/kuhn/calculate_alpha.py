import argparse
import os
import sys

# 将 src/kuhn 加入路径以便导入
sys.path.append(os.path.join(os.getcwd(), "src", "kuhn"))

from vanilla_cfr import CFRSolver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 CFR 迭代并估算 Kuhn Poker 的 alpha 参数。")
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=200000,
        help="迭代次数（默认：200000）",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=0,
        help="进度日志间隔（默认：0 表示不输出）",
    )
    return parser.parse_args()


def calculate_alpha(iterations: int, log_every: int) -> None:
    solver = CFRSolver()
    print(f"开始运行 {iterations} 次迭代...")

    if log_every and log_every > 0:
        for i in range(1, iterations + 1):
            solver.train_step()
            if i % log_every == 0:
                print(f"进度：{i}/{iterations}")
    else:
        for _ in range(iterations):
            solver.train_step()

    snapshot = solver.get_snapshot()

    # 提取 alpha: P0 持 J (Card 0) 的 Bet 概率
    # InfoSet "0" -> avg_strategy[1]
    if "0" in snapshot:
        alpha = snapshot["0"]["avg_strategy"][1]
        print(f"\n计算得到 alpha（P0 持 0 号牌下注概率）：{alpha:.4f}（{alpha * 100:.2f}%）")

        # 验证关联数据
        # P0 Card 2 (K) Bet 应该是 3 * alpha
        if "2" in snapshot:
            k_bet = snapshot["2"]["avg_strategy"][1]
            print(f"P0 持 2 号牌下注概率：{k_bet:.4f}（期望约 {3 * alpha:.4f}）")

        # P0 Card 1 (Q) Pass-Bet Call 应该是 alpha + 1/3
        if "1pb" in snapshot:
            q_call = snapshot["1pb"]["avg_strategy"][1]
            print(f"P0 持 1 号牌跟注概率：{q_call:.4f}（期望约 {alpha + 1 / 3:.4f}）")

    else:
        print("错误：快照中未找到 InfoSet '0'。")


if __name__ == "__main__":
    args = parse_args()
    calculate_alpha(args.iterations, args.log_every)
