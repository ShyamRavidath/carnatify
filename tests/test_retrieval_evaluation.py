from scripts.benchmark_melody_retrieval import retrieval_summary


def test_failed_query_is_not_removed_from_known_denominator():
    rows=[dict(answerable=True,rank=1),dict(answerable=True,rank=None),
          dict(answerable=False,rank=None)]
    result=retrieval_summary(rows)
    assert result['n_answerable']==2
    assert result['top1']==result['top5']==result['mrr']==.5


def test_no_answerable_queries_has_no_fabricated_accuracy():
    assert retrieval_summary([dict(answerable=False,rank=None)])['top1'] is None
