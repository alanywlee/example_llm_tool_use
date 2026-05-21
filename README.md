# example_llm_tool_use

A Python example project for:

```text
OpenAI-compatible LLM tool calling
  +
streaming chat completions
  +
remote MCP tools
  +
enterprise KM / RAG tool patterns
  +
skill-based dynamic tool allowlisting
  +
conversation history with /reset
  +
JSONL trace logging under logs/
```

## Features

- Remote MCP RAG tools
- `rag_search` and `rag_search_and_summarize` exposed by `rag_mcp_server.py`
- OpenAI-compatible streaming tool loop
- vLLM-compatible environment variables
- Qwen3.5-compatible single system message construction
- Multi-turn conversation history
- `/reset` command to clear history
- Skill-based dynamic tool allowlist
- JSON Lines trace logs under `logs/YYYYMMDD-HHMMSS-trace.log`

## Project structure

```text
example_llm_tool_use/
  main.py
  llm_streaming.py
  conversation_state.py
  mcp_registry.py
  mcp_servers.json
  prompts.py
  rag_mcp_server.py
  skill_loader.py
  skill_router.py
  test_rag_mcp.py
  trace_logger.py
  requirements.txt
  skills/
    enterprise_km_search/
      SKILL.md
      tools.json
    calculator/
      SKILL.md
      tools.json
```

## Remote RAG MCP server

Run the RAG MCP server in one terminal:

```bash
python rag_mcp_server.py
```

Default bind:

```text
0.0.0.0:8000
```

Default client URL:

```text
http://localhost:8000/mcp
```

`0.0.0.0` is a server bind address. Clients should connect through `localhost`, `127.0.0.1`, or a real server IP.

## MCP tools

The RAG MCP server exposes:

```text
rag_search
rag_search_and_summarize
```

The client namespaces them as OpenAI-compatible tools:

```text
rag__rag_search
rag__rag_search_and_summarize
```

`rag_search` currently returns a fixed JSON array of search results.

`rag_search_and_summarize` currently returns a fixed integrated answer string.

Replace the bodies of these functions in `rag_mcp_server.py` with your real RAG implementation.

## MCP config

`mcp_servers.json`:

```json
{
  "servers": [
    {
      "name": "rag",
      "transport": "streamable_http",
      "url": "http://localhost:8000/mcp",
      "enabled": true,
      "tool_allowlist": [
        "rag_search",
        "rag_search_and_summarize"
      ]
    },
    {
      "name": "calculator",
      "transport": "streamable_http",
      "url": "http://localhost:8001/mcp",
      "enabled": false,
      "tool_allowlist": ["calculate"]
    }
  ]
}
```

The calculator MCP server is disabled by default to avoid startup failure when only the RAG MCP server is running.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Test MCP server

Terminal 1:

```bash
python rag_mcp_server.py
```

Terminal 2:

```bash
python test_rag_mcp.py
```

Expected tools:

```text
rag__rag_search
rag__rag_search_and_summarize
```

## Run with OpenAI API

Terminal 1:

```bash
python rag_mcp_server.py
```

Terminal 2:

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-5.5"
python main.py
```

## Run with vLLM

```bash
export OPENAI_BASE_URL="http://localhost:8001/v1"
export OPENAI_API_KEY="dummy"
export OPENAI_MODEL_NAME="Qwen/Qwen3.5-122B-A10B"
python main.py
```

The code reads model variables in this order:

```text
OPENAI_MODEL
OPENAI_MODEL_NAME
gpt-5.5
```

## Conversation history

The CLI keeps multi-turn conversation history until you type:

```text
/reset
```

History stores only:

```text
user messages
final assistant messages
```

Intermediate tool-call messages are used inside a single turn but are not stored permanently. This avoids stale tool state and improves compatibility with strict chat templates.

## Qwen3.5 compatibility

Some Qwen-style chat templates reject multiple system messages:

```text
system message must be at the beginning.
```

This project avoids that by merging the base prompt and selected skill instructions into a single first system message.

## Trace logging

Each `main.py` startup creates:

```text
logs/YYYYMMDD-HHMMSS-trace.log
```

Example:

```text
logs/20260519-111850-trace.log
```

Trace logs use JSON Lines format.

Inspect logs:

```bash
tail -f logs/*-trace.log
```

Find tool calls:

```bash
grep '"event": "tool_call_requested"' logs/*-trace.log
```

Find completed turns:

```bash
grep '"event": "turn_completed"' logs/*-trace.log
```

## Example prompts

```text
請整理內部系統權限申請流程
```

```text
剛剛提到的一般權限 SLA 是多久？
```

```text
/reset
```

```text
差旅報銷政策的餐費補助上限是多少？請列出文件來源
```

## Notes

This is a teaching/demo project. The RAG server currently returns fixed mock data. Replace `rag_search` and `rag_search_and_summarize` with production retrieval, reranking, summarization, and permission filtering.
