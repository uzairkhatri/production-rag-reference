import os
from .generation import Generated
from .evidence import ABSTENTION, select_evidence
from .providers import ProviderPolicy,with_retries

class OpenAIGenerator:
    def __init__(self,client=None,model=None,policy=None):
        if client is None:
            from openai import OpenAI
            client=OpenAI(api_key=os.environ.get("OPENAI_API_KEY"),timeout=float(os.getenv("RAG_PROVIDER_TIMEOUT","15")))
        self.client=client
        self.model=model or os.getenv("RAG_OPENAI_MODEL","gpt-5-mini")
        self.policy=policy or ProviderPolicy(timeout_seconds=float(os.getenv("RAG_PROVIDER_TIMEOUT","15")),max_retries=int(os.getenv("RAG_PROVIDER_RETRIES","2")))

    def generate(self,question,hits,max_words):
        evidence = select_evidence(question, hits, max_words)
        if not evidence.passages:
            return Generated(ABSTENTION, (), evidence.reason)
        context="\n\n".join(f"[{i+1}] {p.text}" for i,p in enumerate(evidence.passages))
        prompt=("Answer only from the supplied context. If the context is insufficient, say so. "
                "Do not invent sources.\n\nQuestion: "+question+"\n\nContext:\n"+context)
        def call():
            response=self.client.responses.create(model=self.model,input=prompt,max_output_tokens=max(64,min(1200,max_words*2)))
            return response.output_text
        text=with_retries(call,self.policy)
        return Generated(text,tuple(p.hit for p in evidence.passages),evidence.reason)
