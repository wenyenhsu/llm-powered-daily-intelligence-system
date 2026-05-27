# REQUIRED EXTRACTION BLOCK (CRITICAL)

The Extraction Block is parsed automatically by downstream systems.

Formatting errors will break the pipeline.

Your response MUST end with this EXACT structure.

Do NOT omit it.

Do NOT add prose after it.

---

## Extraction Block

Insights
[[insights/example-insight]]
[[insights/example-insight]]

Topics
[[topics/example-topic]]
[[topics/example-topic]]

HighValue
[[insights/example-high-value]]

<!-- END EXTRACTION -->

---

# Extraction Rules

- Include ALL unique insights
- Include ALL unique topics
- HighValue must contain only importance >= 4 insights
- Minimum:
  - 5 insights
  - 5 topics
- One link per line
- No duplicate links
- No prose inside Extraction Block
- No commentary after END EXTRACTION

Forbidden inside Extraction Block:

- Explanations
- Sentences
- Markdown tables
- Numbered lists
- Commentary
- Extra headings

If the Extraction Block is missing, the output is invalid.