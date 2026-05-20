# 🧠 LLM-Powered Daily Intelligence System

A self-evolving knowledge graph system powered by LLM + embeddings.

It transforms raw news into structured, reusable knowledge using:

- LLM (Ollama / Gemini)
- Embedding-based memory
- Auto-merging & normalization
- Topic classification & clustering

---

# 🚀 Architecture

```
RSS → inbox → LLM → normalize (topic + insight)
        ↓
     daily
        ↓
   aggregation
        ↓
   insights / topics
        ↓
clean → merge → reindex
        ↓
ranking → clustering
        ↓
Obsidian Graph
```

---

# 🔄 Execution Flow

```
fetch → init → summarize → topic normalize → insight normalize → aggregate → clean → merge → reindex → ranking → cluster-topics
```

---

# 📊 Pipeline Steps

## 1. Fetch (`--fetch`)
- Collect RSS news
- Save to `inbox/YYYY-MM-DD.md`

---

## 2. Initialize (`--init`)
- Create `daily/YYYY-MM-DD.md`

---

## 3. Summarize (`--backend`)
- LLM generates:
  - Summary
  - Topics
  - Insights

---

## 4. Topic Normalization (Hybrid System)

- Match against existing topics (embedding)
- If matched → reuse
- If not → create new topic file

```
LLM → candidate topic
→ embedding match
→ reuse OR create
```

---

## 5. Insight Normalization

- Match against existing insights
- Prevent duplication
- Enforce canonical naming

---

## 6. Aggregation (`--agg`)

- Extract insights from daily
- Append to `insights/*.md`

---

## 7. Cleanup (`--clean`)

Remove invalid nodes:

- `summarized`
- `URL`
- `...`

---

## 8. Auto Merge (`--merge`)

- Detect similar insights
- Merge into canonical nodes

---

## 9. Reindex (`--reindex`)

Rebuild embedding memory:

- insights
- topics

---

## 10. Ranking (`--ranking`)

Score insights based on:

- frequency
- recency
- connections

Output:
```
reports/top_insights.md
```

---

## 11. Topic Clustering (`--cluster-topics`)

Group topics using embeddings:

```
reports/topic_clusters.md
```

---

# 🧪 Usage

## Full Pipeline

```bash
python3 src/run_pipeline.py \
  --fetch \
  --init \
  --backend ollama \
  --agg \
  --clean \
  --merge \
  --reindex \
  --ranking \
  --cluster-topics
```

---

## Partial Runs

### Only fetch
```bash
python3 src/run_pipeline.py --fetch
```

### Only summarize
```bash
python3 src/run_pipeline.py --backend ollama
```

### Rebuild memory
```bash
python3 src/run_pipeline.py --reindex
```

### Merge insights
```bash
python3 src/run_pipeline.py --merge --merge-apply
```

---

# 🧠 Hybrid Topic System

Topics are not fully manual or fully AI.

```
LLM → propose topics
→ embedding → match existing
→ no match → create new topic
```

---

# 🧠 Design Philosophy

- LLM proposes
- Embedding decides
- System enforces consistency
- Knowledge evolves over time

---

# 🎯 Key Insight

```
This is not a note-taking system.
It is a self-evolving knowledge graph.
```

---

# 🧠 Core Concepts

```
embedding = similarity engine
index = memory
merge = fix past
reindex = update memory
normalize = enforce naming
```

---

# 🏁 Summary

```
LLM → suggest
embedding → decide
system → evolve
```