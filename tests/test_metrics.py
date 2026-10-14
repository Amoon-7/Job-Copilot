import pytest

from evals.metrics import mrr, ndcg_at_k, precision_at_k


def test_precision_and_mrr():
    ranked = [0, 2, 1, 0, 2]
    assert precision_at_k(ranked, 2) == 0.5
    assert precision_at_k(ranked, 5) == 0.6
    assert mrr(ranked) == 0.5
    assert mrr([0, 0]) == 0.0


def test_ndcg_perfect_and_worse():
    assert ndcg_at_k([2, 1, 0], 3) == pytest.approx(1.0)
    assert ndcg_at_k([0, 1, 2], 3) < 1.0
