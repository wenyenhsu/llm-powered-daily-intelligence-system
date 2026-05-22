# 🧠 LLM-Powered Daily Intelligence System — AKB (Automatic Knowledge Base)

![logo.png](images/logo.png)

A self-evolving knowledge graph powered by LLMs + embeddings.

AKB continuously transforms raw information into structured, reusable, and evolving intelligence.

Instead of generating temporary AI outputs, the system builds persistent semantic memory through:

- LLM reasoning (Ollama / Gemini)
- Embedding-based memory
- Topic normalization
- Semantic deduplication
- Auto-merging
- Knowledge clustering
- Graph-based organization

```text
Raw Information
        ↓
LLM Extraction
        ↓
Semantic Normalization
        ↓
Embedding Memory
        ↓
Knowledge Graph Evolution
```

AKB is not just an AI summarization tool.

It is a long-term intelligence and memory system.

---

# ❓ Why Use This?

Tired of spending hours reading endless news and articles just to keep up with trends?

AKB is built for that.

Most AI tools generate temporary answers.

AKB builds persistent intelligence.

Instead of producing one-time summaries, the system continuously transforms raw information into a self-evolving semantic knowledge graph powered by LLMs + embeddings.

It can:

- summarize massive information streams
- normalize concepts over time
- merge duplicated knowledge
- preserve semantic relationships
- cluster related ideas
- accumulate long-term intelligence

```text
RSS / Information
        ↓
LLM Extraction
        ↓
Embedding Memory
        ↓
Semantic Knowledge Graph
```

This is not just AI summarization.

It is an evolving intelligence system.

---

# 🚀 Architecture

![architect.png](images/architect.png)

---

# 🧠 Design Philosophy

- LLM proposes
- Embeddings decide
- The system enforces consistency
- Knowledge evolves over time

---
# 🚀 Quick Start

## 1. Clone Project

```bash
git clone <your-repo-url>

cd llm-powered-daily-intelligence-system
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Setup `.env`

Create a `.env` file in the project root:

```env
# Ollama host
OLLAMA_HOST=http://localhost:11434

# Embedding model
OLLAMA_EMBED_MODEL=nomic-embed-text

```

---

## 4. Configure RSS Sources

Edit:

```text
configs/sources.yaml
```

Example:

```yaml
tech:
  - name: The Verge
    type: rss
    url: https://www.theverge.com/rss/index.xml

  - name: TechCrunch
    type: rss
    url: https://techcrunch.com/feed/

finance:
  - name: Reuters Business
    type: rss
    url: https://feeds.reuters.com/reuters/businessNews
```

---

## 5. Start Ollama

Start Ollama server:

```bash
ollama serve
```

Pull embedding model:

```bash
ollama pull nomic-embed-text
```

(Optional) Pull report model:

```bash
ollama pull llama3
```

---

# ⚡ Run Pipeline

## Full Pipeline

```bash
python3 -m src.run_pipeline \
  --fetch \
  --init \
  --execution-analysis-backend ollama \
  --agg \
  --clean \
  --merge \
  --reindex \
  --ranking \
  --cluster-topics \
  --reports-backend ollama
```

---

## Generate Reports Only

```bash
python3 -m src.run_pipeline \
  --reports-backend ollama \
  --reports-granularity all
```

Supported granularities:

```text
day
week
month
all
```

---

# 🧩 Pipeline Commands

## Fetch RSS News

```bash
python3 -m src.run_pipeline --fetch
```

---

## Initialize Daily Notes

```bash
python3 -m src.run_pipeline --init
```

---

## Run LLM Analysis

```bash
python3 -m src.run_pipeline \
  --execution-analysis-backend ollama
```

---

## Aggregate Insights

```bash
python3 -m src.run_pipeline --agg
```

---

## Clean Daily Output

```bash
python3 -m src.run_pipeline --clean
```

---

## Merge Similar Insights

Dry run:

```bash
python3 -m src.run_pipeline --merge
```

Apply merge:

```bash
python3 -m src.run_pipeline \
  --merge \
  --merge-apply
```

---

## Rebuild Embedding Memory

```bash
python3 -m src.run_pipeline --reindex
```

---

## Build Insight Ranking

```bash
python3 -m src.run_pipeline --ranking
```

---

## Cluster Topics

```bash
python3 -m src.run_pipeline --cluster-topics
```

---

# 📊 Report Generation

## Generate Daily Report

```bash
python3 -m src.run_pipeline \
  --reports-backend ollama \
  --reports-granularity day
```

---

## Generate Weekly Report

```bash
python3 -m src.run_pipeline \
  --reports-backend ollama \
  --reports-granularity week
```

---

## Generate Monthly Report

```bash
python3 -m src.run_pipeline \
  --reports-backend ollama \
  --reports-granularity month
```

---

## Generate All Reports

```bash
python3 -m src.run_pipeline \
  --reports-backend ollama \
  --reports-granularity all
```

---

# 📅 Custom Date Ranges

## Run Specific Date

```bash
python3 -m src.run_pipeline \
  --target-date 2026-05-21
```

---

## Generate Reports for Custom Range

```bash
python3 -m src.run_pipeline \
  --reports-backend ollama \
  --reports-granularity custom \
  --reports-start-date 2026-05-01 \
  --reports-end-date 2026-05-21
```

---

# 🧩 Direct Script Usage

## Fetch News Directly

```bash
python3 -m src.fetch_news \
  --date 2026-05-21
```

Output:

```text
inbox/2026-05-21.md
```

---

## Aggregate Insights Directly

```bash
python3 -m src.aggregate_insights \
  --date 2026-05-21
```

Generates:

```text
insights/*.md
topics/*.md
```

---

## Generate Reports Directly

### Template Provider

```bash
python3 -m src.generate_reports \
  --granularity day \
  --date 2026-05-21 \
  --provider template
```

---

### Ollama Provider

```bash
python3 -m src.generate_reports \
  --granularity month \
  --provider ollama
```

---

# 🧪 Testing

Run all tests:

```bash
pytest
```

Run specific test file:

```bash
pytest tests/test_run_pipeline.py
```

---

# 📁 Generated Output

After execution, the system generates:

```text
inbox/
daily/
insights/
topics/
reports/
state/
```
---

# 📂 Output Files

## Inbox

Raw RSS ingestion:

```text
inbox/YYYY-MM-DD.md
```

Example:

```text
inbox/2026-05-21.md
```

---

## Daily Notes

LLM-generated daily analysis:

```text
daily/YYYY-MM-DD.md
```

Example:

```text
daily/2026-05-21.md
```

---

## Insight Nodes

Reusable semantic knowledge:

```text
insights/*.md
```

Example:

```text
insights/openai-launches-new-model.md
```

---

## Topic Nodes

Canonical topic entities:

```text
topics/*.md
```

Example:

```text
topics/artificial-intelligence.md
```

---

## State Files

Embedding memory indexes:

```text
state/insight_index.json
state/topic_index.json
```

---

## Reports

Generated summaries and rankings:

```text
reports/
```

Structure:

```text
reports/daily/
reports/weekly/
reports/monthly/
reports/all/
```

Examples:

```text
reports/daily/2026-05-21.md

reports/weekly/2026-W21.md

reports/monthly/2026-05.md

reports/all/global_summary.md
```

---

## Ranking Outputs

Generated ranking files:

```text
reports/top_insights.md
reports/topic_clusters.md
```

---

## Obsidian Knowledge Graph

Final semantic structure:

```text
daily/  ↔  insights/  ↔  topics/
```

Using wiki-links:

```text
[[insights/example]]
[[topics/example]]
```

---

# 🧠 Persistent Knowledge Flow

```text
daily/
    ↓
insights/
    ↓
topics/
    ↓
embedding memory
    ↓
semantic clustering
    ↓
long-term intelligence

This transforms isolated information into persistent semantic intelligence.
```
---

# 🧠 Hybrid Topic System

Topics are neither fully manual nor fully AI-generated.

```text
LLM
  ↓
propose topics
  ↓
embedding similarity matching
  ↓
existing topic found?
      ├─ yes → reuse topic
      └─ no  → create new topic
```

---

# 🧠 Core Concepts

```text
embedding = semantic similarity engine

index = long-term memory

merge = repair duplicated knowledge

reindex = rebuild semantic memory

normalize = enforce canonical naming
```

---

# 🧩 Core Responsibilities

| Layer | Responsibility |
|---|---|
| fetch_news | RSS ingestion |
| aggregate_insights | LLM extraction & normalization |
| embedding_memory | Semantic similarity memory |
| auto_merge_insights | Deduplication & canonicalization |
| topic_clustering | Topic relationship discovery |
| ranking | Insight importance scoring |
| generate_reports | Intelligence synthesis |
| run_pipeline | End-to-end orchestration |

---

# 📌 Final Vision

```text
Raw Information
        ↓
Structured Knowledge
        ↓
Persistent Memory
        ↓
Semantic Intelligence
        ↓
Self-Evolving Knowledge Graph
```