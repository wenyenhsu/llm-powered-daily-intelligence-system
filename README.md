# AI Second Brain System

## Overview

This project is an AI-powered personal knowledge system that automatically collects, processes, and organizes tech and financial news into structured insights.

It helps transform daily information into long-term knowledge.

---

## Features

* Automated news ingestion (RSS feeds)
* Daily note generation
* AI-powered summarization
* Trend extraction and insights
* Markdown-based knowledge storage (Obsidian compatible)

---

## Architecture

RSS Sources → Fetch Script → Markdown Inbox → AI Processing → Structured Notes → Insights

---

## Tech Stack

* Python (RSS parsing)
* Bash (automation & scheduling)
* Gemini API (LLM processing)
* Obsidian (knowledge management)

---

## Workflow

1. Fetch news from RSS sources
2. Save raw news into `inbox/YYYY-MM-DD.md`
3. Generate daily note template
4. Process content using AI (Gemini)
5. Extract insights and trends

---

## Example Output

See `examples/sample_output.md`

---

## Why This Project?

Most people consume information passively.
This system converts information into structured knowledge and actionable insights.

---

## Future Improvements

* Web dashboard for visualization
* Trend tracking over time
* Multi-source aggregation
* Embedding-based search

---

## Author

Built as a personal AI productivity system.
