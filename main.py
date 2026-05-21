import asyncio
import os

from conversation_state import ConversationState
from llm_streaming import ask_llm_streaming
from mcp_registry import MCPToolRegistry
from trace_logger import TraceLogger


CONFIG_PATH = os.getenv("MCP_SERVERS_CONFIG", "mcp_servers.json")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))


async def main() -> None:
    trace = TraceLogger(log_dir="logs")

    print("Remote MCP RAG Tools + Skills + Streaming LLM demo")
    print("Conversation history is enabled.")
    print("Trace logging is enabled.")
    print(f"Trace log: {trace.log_path}")
    print("Type '/reset' to clear history.")
    print("Type 'exit' or 'quit' to stop.")
    print(f"MCP config: {CONFIG_PATH}")
    print(f"MAX_HISTORY_MESSAGES: {MAX_HISTORY_MESSAGES}")

    trace.event(
        "app_started",
        {
            "mcp_config_path": CONFIG_PATH,
            "max_history_messages": MAX_HISTORY_MESSAGES,
            "openai_base_url": os.getenv("OPENAI_BASE_URL"),
            "openai_model": os.getenv("OPENAI_MODEL"),
            "openai_model_name": os.getenv("OPENAI_MODEL_NAME"),
        },
    )

    state = ConversationState(max_history_messages=MAX_HISTORY_MESSAGES)

    async with MCPToolRegistry.from_config_file(CONFIG_PATH, trace=trace) as registry:
        tool_names = registry.get_all_tool_names()

        print("\nAvailable OpenAI-visible MCP tools:")
        for name in tool_names:
            print(f"  - {name}")

        trace.event("available_tools", {"tool_names": tool_names})

        while True:
            user_input = input("\nUser: ").strip()

            if user_input.lower() in {"exit", "quit"}:
                trace.event("app_exit_requested", {"command": user_input})
                break

            if user_input == "/reset":
                before_count = len(state.get_history())
                state.reset()
                trace.event(
                    "history_reset",
                    {
                        "history_messages_before_reset": before_count,
                    },
                )
                print("\n[system] conversation history cleared.")
                continue

            trace.event(
                "user_input",
                {
                    "text": user_input,
                    "history_messages_before_turn": len(state.get_history()),
                },
            )

            print("\nAssistant: ", end="", flush=True)
            await ask_llm_streaming(user_input, registry, state, trace=trace)

    trace.event("app_stopped")


if __name__ == "__main__":
    asyncio.run(main())
