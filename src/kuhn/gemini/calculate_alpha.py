import os
import sys

# 将 src/kuhn/gemini 加入路径以便导入
sys.path.append(os.path.join(os.getcwd(), "src", "kuhn", "gemini"))

from cfr_backend import CFRSolver


def calculate_alpha():
    solver = CFRSolver()
    iterations = 10000000
    print(f"Running {iterations} iterations...")

    for i in range(iterations):
        solver.train_step()

    snapshot = solver.get_snapshot()

    # 提取 alpha: P0 持 J (Card 0) 的 Bet 概率
    # InfoSet "0" -> avg_strategy[1]
    if "0" in snapshot:
        alpha = snapshot["0"]["avg_strategy"][1]
        print(f"\nCalculated alpha (P0 Card 0 Bet): {alpha:.4f} ({alpha * 100:.2f}%)")

        # 验证关联数据
        # P0 Card 2 (K) Bet 应该是 3 * alpha
        if "2" in snapshot:
            k_bet = snapshot["2"]["avg_strategy"][1]
            print(f"P0 Card 2 (K) Bet: {k_bet:.4f} (Expected ~{3 * alpha:.4f})")

        # P0 Card 1 (Q) Pass-Bet Call 应该是 alpha + 1/3
        if "1pb" in snapshot:
            q_call = snapshot["1pb"]["avg_strategy"][1]
            print(f"P0 Card 1 (Q) Call: {q_call:.4f} (Expected ~{alpha + 1 / 3:.4f})")

    else:
        print("Error: InfoSet '0' not found in snapshot.")


if __name__ == "__main__":
    calculate_alpha()
