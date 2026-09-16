from .retrieval import tokens
def citation_coverage(answer:str,source_texts:list[str])->float:
    answer_tokens=set(tokens(answer))
    if not answer_tokens:return 1.0
    source=set()
    for text in source_texts:source.update(tokens(text))
    return len(answer_tokens.intersection(source))/len(answer_tokens)
