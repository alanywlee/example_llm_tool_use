# enterprise_km_search

## Purpose

Use this skill for enterprise knowledge management search, policy lookup, SOP lookup, FAQ lookup, and document-grounded answering.

## When to use

Use this skill when:
- The user asks about company policy, SOP, FAQ, internal process, product docs, support docs, or enterprise knowledge.
- The user asks to find, compare, summarize, or explain information from the knowledge base.
- The answer should be grounded in internal documents.
- The user asks broad questions where search results need to be summarized.
- The user asks a follow-up question referring to earlier KM search results.

## Available tools

- rag__rag_search
- rag__rag_search_and_summarize

## Tool choice policy

Use `rag__rag_search` when:
- The user asks for a specific fact.
- You need raw evidence before deciding how to answer.
- The question is high-risk or policy-related and exact wording matters.
- You need citations / document IDs.

Use `rag__rag_search_and_summarize` when:
- The user asks for a summary.
- The user asks to compare multiple policies, products, SOPs, or FAQ entries.
- The user asks a broad KM question.
- The user explicitly asks for key points, overview, digest, or executive summary.

## Summarize profile selection

When using `rag__rag_search_and_summarize`, choose `summarize_profile` carefully:

- `default`: general KM summary.
- `policy_lookup`: policies, limits, reimbursement, access rules, SLA, compliance.
- `comparison`: compare plans, policies, options, teams, workflows.
- `troubleshooting`: support SOP, incidents, escalation, RCA, severity handling.

## Grounding

- Use only retrieved evidence.
- If evidence is insufficient, say what is missing.
- Cite document_id and title for important claims.
