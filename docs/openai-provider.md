# Optional OpenAI generator

Local mode remains the default and requires no external API.

To use the optional OpenAI generator:

```bash
python -m pip install -e ".[openai]"
export RAG_GENERATOR_PROVIDER=openai
export OPENAI_API_KEY=...
uvicorn app.main:app --reload
```

The adapter implements the same generation boundary as the local extractive generator. Retrieval, reranking, citation construction and the HTTP contract do not depend on the OpenAI SDK.

Before calling the provider, it runs the same [value evidence guard](evidence-check.md) as local generation. Only positive-score, word-bounded source text is checked and sent. Missing value evidence produces abstention with no citations and no provider request. Offline fake-client tests verify call suppression and the exact bounded context; they do not verify live answer quality. An allowed request still uses the existing Responses API call and may incur charges. See the [official OpenAI quickstart](https://developers.openai.com/api/docs/quickstart) for that API pattern.

Provider calls use the bounded transient-failure retry policy. Authentication/configuration errors are not silently converted into local answers. CI uses an injected fake client and never needs a real API key.

The prompt instructs the model to answer only from retrieved context. This is a guardrail, not proof of groundedness; production deployments should evaluate groundedness and citation correctness against representative data.
