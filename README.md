


# Grounded Review RAG Agents

**Five specialized agents. One supervisor. Zero unverified claims.**

![Architecture](docs/img/architecture-overview.png)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit_Cloud-FF4B4B?logo=streamlit)](https://ecommerce-intel-copilot-u3hzffazrtbv4ayzfqhzet.streamlit.app/)
[![AWS Verified](https://img.shields.io/badge/AWS-Deployed_%26_Verified-FF9900?logo=amazonwebservices)](docs/aws-deployment.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A multi-agent RAG system that answers natural-language questions over 441,857 Amazon
appliance reviews — structured SQL, semantic retrieval, deterministic analytics, and a
groundedness critic, orchestrated behind a single supervisor.

**Live demo:** https://ecommerce-intel-copilot-u3hzffazrtbv4ayzfqhzet.streamlit.app/

![Agent path on AWS](docs/img/03-app-running-hybrid-query.png)

## Architecture

```
user ──> SUPERVISOR ──> { SQL ANALYST │ KNOWLEDGE (RAG) │ MARKET ANALYST │ HYBRID } ──> CRITIC ──> answer
              ^                                                                           │ (retry ≤ 1)
              └───────────────────────────────────────────────────────────────────────────┘
```

| Agent | Responsibility | Backing |
|---|---|---|
| Supervisor | Classifies the question (sql / rag / analyst / hybrid / reject), synthesizes the final answer | LLM |
| SQL Analyst | Text-to-SQL over a read-only connection, hard-guarded to single SELECTs | LLM + SQLite |
| Knowledge (RAG) | Top-k semantic retrieval; answers strictly from context with `[asin]` citations | LLM + Chroma |
| Market Analyst | Deterministic analytics (rating trends, review volume, top movers) — the LLM only narrates numbers it never computes | Python |
| Critic | Runtime groundedness gate; unverified claims trigger one retry, then an honest fallback | LLM |

## Evaluation

Measured on a 30-question held-out set (never leaked into prompts or the index);
the harness bypasses the answer cache.

Measured 2026-07-11 on Groq Llama 3.3 70B (since retired); faithfulness and relevance
were judged by the same model. Re-measurement on gpt-oss-20b with a cross-family judge
is planned. Source: [`eval_results/baseline.json`](eval_results/baseline.json).

| Metric | n | Score | Threshold |
|---|---|---|---|
| SQL execution accuracy | 12 | 92% (11/12) | ≥ 80% |
| Trajectory accuracy (routing; 3-class router: sql/rag/reject, component-level) | 30 | 100% (30/30) | ≥ 85% |
| Faithfulness (LLM-as-judge) | 12 | 1.00 | ≥ 0.80 |
| Answer relevance (LLM-as-judge) | 12 | 0.87 | ≥ 0.75 |
| Out-of-scope rejection | 6 | 6/6 | 100% |

The single SQL failure is an analyzed false negative (the model returned `parent_asin`
instead of the product title — same product, same count); the strict matcher was kept
rather than loosened. Details in [docs/DECISIONS.md](docs/DECISIONS.md).

## Safety & honesty properties

- **SQL guard** (test-first, 11 tests): SELECT-only allowlist, destructive-keyword
  rejection, multi-statement injection blocking, read-only URI, 50-row cap.
- **Grounded answering:** the RAG agent cites `[asin]` sources and refuses when the
  corpus lacks an answer; the Critic verifies claims before they reach the user.
- **Deterministic numbers:** all statistics come from SQL/Python, never from an LLM.

## Data

[Amazon Reviews 2023](https://amazon-reviews-2023.github.io/) (McAuley Lab) —
`Appliances` category, filtered to products with 300–999 ratings: 5,006 products /
441,857 reviews (2003–2023). Citation: Hou et al., 2024, *Bridging Language and Items
for Retrieval and Recommendation* (arXiv:2403.03952).

## Stack

Python 3.11 · LangGraph · litellm · Chroma + sentence-transformers (local embeddings) ·
SQLite (read-only) · OpenTelemetry traces to self-hosted Langfuse (Docker Compose) ·
custom LLM-as-judge eval harness · Streamlit · pytest.

One model, two profiles, selected by `COPILOT_PROFILE`:

| Profile | Model | Fallback | Use |
|---|---|---|---|
| `cloud` (default) | gpt-oss-20b on Groq | Gemini 2.5 Flash | development, demo |
| `local` | gpt-oss-20b on Ollama | none | data never leaves the machine |

The `local` profile fails closed: the app refuses to start unless `OLLAMA_NO_CLOUD=1`,
the endpoint is a loopback address and the model is a local Ollama model.

## Run locally

```bash
git clone https://github.com/R7Murat/grounded-review-rag-agents && cd grounded-review-rag-agents
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"
# .env with GROQ_API_KEY and GEMINI_API_KEY (cloud profile)
streamlit run src/copilot/ui/app.py
```

Local profile (needs [Ollama](https://ollama.com) with `gpt-oss:20b` pulled; about 16 GB of memory):

```bash
COPILOT_PROFILE=local OLLAMA_NO_CLOUD=1 streamlit run src/copilot/ui/app.py
```

Tracing (optional): start Langfuse and the app exports OpenTelemetry spans to it.

```bash
python infra/langfuse/init_env.py      # generates secrets into .env files; prints names only
cd infra/langfuse && docker compose up -d   # UI on http://localhost:3000
```
Without `LANGFUSE_*` variables tracing is a no-op.
On first launch the app downloads the prepared dataset (~2 GB) from the companion
dataset repo [R7Murat/ecommerce-intel-data](https://huggingface.co/datasets/R7Murat/ecommerce-intel-data).

Tests: `python -m pytest -m "not llm"` (fast) · `python -m pytest` (includes live-LLM tests).

## Project documentation

- [docs/DECISIONS.md](docs/DECISIONS.md) — every significant decision with rationale and rejected alternatives
- [SYSTEM_CARD.md](SYSTEM_CARD.md) — capabilities, limitations, and development notes
- [notebooks/01_data_pipeline.ipynb](notebooks/01_data_pipeline.ipynb) — EDA, schema design, and a reproduced type-integrity bug (pandas nullable Int64 → SQLite BLOB)
- [docs/aws-deployment.md](docs/aws-deployment.md) — AWS App Runner deployment evidence (provision-validate-destroy cycle); diagram: [docs/img/deployment_architecture.png](docs/img/deployment_architecture.png)