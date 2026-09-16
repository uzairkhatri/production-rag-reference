from .retrieval import Hit,tokens
class LexicalReranker:
    def rank(self,question:str,hits:list[Hit])->list[Hit]:
        q=set(tokens(question))
        return sorted(hits,key=lambda h:(-len(q.intersection(tokens(h.chunk.title+" "+h.chunk.text))),-h.score,h.chunk.id))
def rerank(question:str,hits:list[Hit])->list[Hit]:
    return LexicalReranker().rank(question,hits)
