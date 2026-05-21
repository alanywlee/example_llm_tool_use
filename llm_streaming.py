from __future__ import annotations

import json
import os
from typing import Any

from openai import AsyncOpenAI

from conversation_state import ConversationState
from mcp_registry import MCPToolRegistry
from prompts import BASE_SYSTEM_PROMPT
from skill_loader import build_skill_instruction_block, collect_allowed_tools_from_skills
from skill_router import select_skills_for_turn
from trace_logger import TraceLogger, compact_messages_for_trace


def make_openai_client() -> AsyncOpenAI:
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY", "dummy")

    if base_url:
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    return AsyncOpenAI(api_key=api_key)


client = make_openai_client()

DEFAULT_MODEL = (
    os.getenv("OPENAI_MODEL")
    or os.getenv("OPENAI_MODEL_NAME")
    or "gpt-5.5"
)


def _new_tool_call_state() -> dict[str, Any]:
    return {
        "id": None,
        "type": "function",
        "function": {"name": "", "arguments": ""},
    }


def _build_single_system_prompt(selected_skills: list[str]) -> str:
    """
    Qwen3.5-style chat templates may reject multiple system messages.

    Therefore all system-level instructions are merged into the first and
    only system message.
    """
    skill_block = build_skill_instruction_block(selected_skills)

    return (
        BASE_SYSTEM_PROMPT
        + "\n\n"
        + "本輪動態載入的 skill instructions：\n"
        + skill_block
    )


async def ask_llm_streaming(
    user_input: str,
    registry: MCPToolRegistry,
    state: ConversationState,
    trace: TraceLogger | None = None,
) -> str:
    selected_skills = select_skills_for_turn(user_input)
    allowed_tool_names = collect_allowed_tools_from_skills(selected_skills)

    available_tool_names = set(registry.get_all_tool_names())
    allowed_tool_names = allowed_tool_names & available_tool_names

    selected_tools = registry.select_tools(allowed_tool_names)

    debug_payload = {
        "selected_skills": selected_skills or [],
        "allowed_tools": sorted(allowed_tool_names),
        "history_messages": len(state.get_history()),
        "model": DEFAULT_MODEL,
    }

    print(f"\n[debug] selected skills: {debug_payload['selected_skills']}", flush=True)
    print(f"[debug] allowed tools: {debug_payload['allowed_tools']}", flush=True)
    print(f"[debug] history messages: {debug_payload['history_messages']}", flush=True)

    if trace:
        trace.event("turn_policy_selected", debug_payload)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _build_single_system_prompt(selected_skills),
        },
        *state.get_history(),
        {
            "role": "user",
            "content": user_input,
        },
    ]

    if trace:
        trace.event(
            "llm_messages_prepared",
            {
                "message_count": len(messages),
                "messages": compact_messages_for_trace(messages),
                "selected_tool_names": [tool["function"]["name"] for tool in selected_tools],
            },
        )

    final_text_parts: list[str] = []
    round_index = 0

    while True:
        round_index += 1

        request_kwargs: dict[str, Any] = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "stream": True,
        }

        if selected_tools:
            request_kwargs["tools"] = selected_tools
            request_kwargs["tool_choice"] = "auto"

        if trace:
            trace.event(
                "llm_stream_request",
                {
                    "round_index": round_index,
                    "model": DEFAULT_MODEL,
                    "message_count": len(messages),
                    "tool_count": len(selected_tools),
                    "tool_names": [tool["function"]["name"] for tool in selected_tools],
                },
            )

        streamed_content_parts: list[str] = []
        streamed_tool_calls: dict[int, dict[str, Any]] = {}

        stream = await client.chat.completions.create(**request_kwargs)

        async for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                print(delta.content, end="", flush=True)
                streamed_content_parts.append(delta.content)
                final_text_parts.append(delta.content)

            if delta.tool_calls:
                for tool_delta in delta.tool_calls:
                    index = tool_delta.index

                    if index not in streamed_tool_calls:
                        streamed_tool_calls[index] = _new_tool_call_state()

                    state_for_tool = streamed_tool_calls[index]

                    if tool_delta.id:
                        state_for_tool["id"] = tool_delta.id

                    if tool_delta.type:
                        state_for_tool["type"] = tool_delta.type

                    if tool_delta.function:
                        if tool_delta.function.name:
                            state_for_tool["function"]["name"] += tool_delta.function.name

                        if tool_delta.function.arguments:
                            state_for_tool["function"]["arguments"] += tool_delta.function.arguments

        if trace:
            trace.event(
                "llm_stream_finished",
                {
                    "round_index": round_index,
                    "content_length": len("".join(streamed_content_parts)),
                    "has_tool_calls": bool(streamed_tool_calls),
                    "tool_calls": [streamed_tool_calls[index] for index in sorted(streamed_tool_calls.keys())],
                },
            )

        if not streamed_tool_calls:
            print()
            final_answer = "".join(final_text_parts)

            state.add_user_message(user_input)
            state.add_assistant_message(final_answer)

            if trace:
                trace.event(
                    "turn_completed",
                    {
                        "final_answer_preview": final_answer[:2000],
                        "final_answer_length": len(final_answer),
                        "history_messages_after_turn": len(state.get_history()),
                    },
                )

            return final_answer

        messages.append({
            "role": "assistant",
            "content": "".join(streamed_content_parts) or None,
            "tool_calls": [streamed_tool_calls[index] for index in sorted(streamed_tool_calls.keys())],
        })

        print("\n\n[tool phase] executing remote MCP tool call(s)...", flush=True)

        if trace:
            trace.event(
                "tool_phase_started",
                {"round_index": round_index, "tool_call_count": len(streamed_tool_calls)},
            )

        for index in sorted(streamed_tool_calls.keys()):
            tool_call = streamed_tool_calls[index]
            tool_call_id = tool_call["id"]
            tool_name = tool_call["function"]["name"]
            raw_arguments = tool_call["function"]["arguments"] or "{}"

            print(f"[tool phase] {tool_name}({raw_arguments})", flush=True)

            if trace:
                trace.event(
                    "tool_call_requested",
                    {
                        "round_index": round_index,
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "raw_arguments": raw_arguments,
                    },
                )

            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                tool_result = {
                    "error": f"Invalid JSON arguments: {str(exc)}",
                    "tool_name": tool_name,
                    "raw_arguments": raw_arguments,
                }
            else:
                tool_result = await registry.call_tool(
                    openai_tool_name=tool_name,
                    arguments=arguments,
                    allowed_tool_names=allowed_tool_names,
                    trace=trace,
                )

            if trace:
                trace.event(
                    "tool_call_completed",
                    {
                        "round_index": round_index,
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "result_preview": json.dumps(tool_result, ensure_ascii=False, default=repr)[:4000],
                    },
                )

            print(f"[tool phase] result: {json.dumps(tool_result, ensure_ascii=False)}", flush=True)
            print("\n[assistant continues]\n", flush=True)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": json.dumps(tool_result, ensure_ascii=False),
            })
