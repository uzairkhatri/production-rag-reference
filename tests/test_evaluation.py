from app.eval_runner import EvalCase,evaluate_cases,score_case
from app.ingestion import Chunk
from app.retrieval import Hit

def hit(doc,score=1):
    return Hit(Chunk(doc+":0",doc,doc,"local",doc),score)

def test_recall_and_mrr():
    recall,mrr=score_case([hit("other"),hit("wanted")],("wanted",))
    assert recall==1.0
    assert mrr==0.5

def test_dataset_aggregate():
    cases=[EvalCase("q1",("a",)),EvalCase("q2",("b",))]
    result=evaluate_cases(cases,lambda q:[hit("a")] if q=="q1" else [hit("b")])
    assert result.recall_at_k==1.0 and result.mrr==1.0
