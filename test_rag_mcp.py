import asyncio
import os

from mcp_registry import MCPToolRegistry


CONFIG_PATH = os.getenv("MCP_SERVERS_CONFIG", "mcp_servers.json")


async def main() -> None:
    async with MCPToolRegistry.from_config_file(CONFIG_PATH) as registry:
        print("Connected OpenAI-visible MCP tools:")
        for tool_name in registry.get_all_tool_names():
            print(f"  - {tool_name}")

        allowed = {"rag__rag_search", "rag__rag_search_and_summarize"}

        search_result = await registry.call_tool(
            openai_tool_name="rag__rag_search",
            arguments={
                "query": "差旅報銷政策 餐費 上限",
                "top_k": 3,
            },
            allowed_tool_names=allowed,
        )

        print("\nrag__rag_search result:")
        print(search_result)

        summarize_result = await registry.call_tool(
            openai_tool_name="rag__rag_search_and_summarize",
            arguments={
                "query": "整理內部權限申請流程",
                "top_k": 3,
                "summarize_profile": "policy_lookup",
            },
            allowed_tool_names=allowed,
        )

        print("\nrag__rag_search_and_summarize result:")
        print(summarize_result)


if __name__ == "__main__":
    asyncio.run(main())
