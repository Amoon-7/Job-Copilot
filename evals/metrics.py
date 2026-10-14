import math


def precision_at_k(ranked_labels: list[int], k: int, rel_threshold: int = 1) -> float:
    top = ranked_labels[:k]
    return sum(1 for x in top if x >= rel_threshold) / k if k else 0.0


def mrr(ranked_labels: list[int], rel_threshold: int = 1) -> float:
    for i, x in enumerate(ranked_labels, 1):
        if x >= rel_threshold:
            return 1 / i
    return 0.0


def ndcg_at_k(ranked_labels: list[int], k: int) -> float:
    def dcg(xs: list[int]) -> float:
        return sum((2**x - 1) / math.log2(i + 2) for i, x in enumerate(xs[:k]))

    ideal = dcg(sorted(ranked_labels, reverse=True))
    return dcg(ranked_labels) / ideal if ideal else 0.0


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0
