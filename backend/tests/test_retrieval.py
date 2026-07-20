from types import SimpleNamespace

from app.services.retrieval import RankedChunk, relevant_results


def result(score: float) -> RankedChunk:
    return RankedChunk(chunk=SimpleNamespace(), document=SimpleNamespace(), score=score)


def test_relevant_results_remove_weak_top_k_matches():
    ranked = [result(0.8), result(0.5), result(0.39), result(0.02)]

    assert relevant_results(ranked) == ranked[:2]


def test_relevant_results_handle_empty_search():
    assert relevant_results([]) == []
