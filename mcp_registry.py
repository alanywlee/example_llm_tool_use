from __future__ import annotations

import json
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from trace_logger import TraceLogger


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    transport: str
    url: str
    enabled: bool = True
    tool_allowlist: list[str] | None = None


@dataclass(frozen=True)
class ToolRoute:
    openai_tool_name: str
    server_name: str
    mcp_tool_name: str


class RemoteMCPServerConnection:
    def __init__(self, config: MCPServerConfig, trace: TraceLogger | None = None) -> None:
        self.config = config
        self.trace = trace
        self._exit_stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def connect(self) -> None:
        if self.config.transport != "streamable_http":
            raise ValueError(f"Unsupported transport: {self.config.transport}")

        if self.trace:
            self.trace.event(
                "mcp_server_connecting",
                {
                    "server_name": self.config.name,
                    "transport": self.config.transport,
                    "url": self.config.url,
                    "tool_allowlist": self.config.tool_allowlist,
                },
            )

        streams = await self._exit_stack.enter_async_context(streamablehttp_client(self.config.url))
        read_stream = streams[0]
        write_stream = streams[1]

        self._session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self._session.initialize()

        if self.trace:
            self.trace.event("mcp_server_connected", {"server_name": self.config.name, "url": self.config.url})

    async def close(self) -> None:
        if self.trace:
            self.trace.event("mcp_server_closing", {"server_name": self.config.name, "url": self.config.url})
        await self._exit_stack.aclose()

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError(f"MCP server is not connected: {self.config.name}")
        return self._session

    async def list_tools(self):
        response = await self.session.list_tools()
        if self.trace:
            self.trace.event(
                "mcp_server_tools_listed",
                {
                    "server_name": self.config.name,
                    "tools": [{"name": tool.name, "description": tool.description} for tool in response.tools],
                },
            )
        return response

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.trace:
            self.trace.event(
                "mcp_tool_call_started",
                {"server_name": self.config.name, "mcp_tool_name": name, "arguments": arguments},
            )

        result = await self.session.call_tool(name, arguments=arguments)
        text_parts = []
        raw_content = []

        for content in result.content:
            if isinstance(content, TextContent):
                text_parts.append(content.text)
                raw_content.append({"type": "text", "text": content.text})
            else:
                raw_content.append({"type": getattr(content, "type", "unknown"), "repr": repr(content)})

        payload = {
            "server_name": self.config.name,
            "mcp_tool_name": name,
            "arguments": arguments,
            "text": "\n".join(text_parts).strip(),
            "content": raw_content,
        }

        if self.trace:
            self.trace.event(
                "mcp_tool_call_finished",
                {
                    "server_name": self.config.name,
                    "mcp_tool_name": name,
                    "result_preview": json.dumps(payload, ensure_ascii=False, default=repr)[:4000],
                },
            )
        return payload


class MCPToolRegistry:
    def __init__(self, server_configs: list[MCPServerConfig], trace: TraceLogger | None = None) -> None:
        self.server_configs = [config for config in server_configs if config.enabled]
        self.trace = trace
        self.connections: dict[str, RemoteMCPServerConnection] = {}
        self.tool_routes: dict[str, ToolRoute] = {}
        self.openai_tools: list[dict[str, Any]] = []

    @classmethod
    def from_config_file(cls, path: str | Path, trace: TraceLogger | None = None) -> "MCPToolRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        server_configs = [
            MCPServerConfig(
                name=item["name"],
                transport=item.get("transport", "streamable_http"),
                url=item["url"],
                enabled=item.get("enabled", True),
                tool_allowlist=item.get("tool_allowlist"),
            )
            for item in data.get("servers", [])
        ]

        if trace:
            trace.event(
                "mcp_config_loaded",
                {
                    "path": str(path),
                    "enabled_servers": [
                        {
                            "name": config.name,
                            "transport": config.transport,
                            "url": config.url,
                            "tool_allowlist": config.tool_allowlist,
                        }
                        for config in server_configs
                        if config.enabled
                    ],
                },
            )
        return cls(server_configs, trace=trace)

    async def __aenter__(self) -> "MCPToolRegistry":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def connect(self) -> None:
        for config in self.server_configs:
            connection = RemoteMCPServerConnection(config, trace=self.trace)
            await connection.connect()
            self.connections[config.name] = connection
        await self.refresh_tools()

    async def close(self) -> None:
        for connection in self.connections.values():
            await connection.close()

    async def refresh_tools(self) -> None:
        self.openai_tools.clear()
        self.tool_routes.clear()

        for config in self.server_configs:
            connection = self.connections[config.name]
            response = await connection.list_tools()

            for tool in response.tools:
                if config.tool_allowlist and tool.name not in config.tool_allowlist:
                    continue

                openai_tool_name = f"{config.name}__{tool.name}"
                input_schema = getattr(tool, "inputSchema", None) or {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                }

                self.openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": openai_tool_name,
                            "description": f"[MCP server: {config.name}] " + (tool.description or f"MCP tool: {tool.name}"),
                            "parameters": input_schema,
                        },
                    }
                )

                self.tool_routes[openai_tool_name] = ToolRoute(
                    openai_tool_name=openai_tool_name,
                    server_name=config.name,
                    mcp_tool_name=tool.name,
                )

        if self.trace:
            self.trace.event("openai_tools_refreshed", {"tool_names": list(self.tool_routes.keys())})

    def get_all_tool_names(self) -> list[str]:
        return list(self.tool_routes.keys())

    def select_tools(self, allowed_tool_names: set[str]) -> list[dict[str, Any]]:
        return [tool for tool in self.openai_tools if tool["function"]["name"] in allowed_tool_names]

    async def call_tool(
        self,
        openai_tool_name: str,
        arguments: dict[str, Any],
        allowed_tool_names: set[str],
        trace: TraceLogger | None = None,
    ) -> dict[str, Any]:
        active_trace = trace or self.trace

        if openai_tool_name not in allowed_tool_names:
            result = {"error": f"MCP tool not allowed in this turn: {openai_tool_name}"}
            if active_trace:
                active_trace.event(
                    "mcp_tool_call_rejected",
                    {
                        "openai_tool_name": openai_tool_name,
                        "arguments": arguments,
                        "allowed_tool_names": sorted(allowed_tool_names),
                        "result": result,
                    },
                )
            return result

        route = self.tool_routes.get(openai_tool_name)
        if route is None:
            result = {"error": f"Unknown MCP tool: {openai_tool_name}"}
            if active_trace:
                active_trace.event(
                    "mcp_tool_call_unknown",
                    {"openai_tool_name": openai_tool_name, "arguments": arguments, "result": result},
                )
            return result

        if active_trace:
            active_trace.event(
                "mcp_tool_route_resolved",
                {
                    "openai_tool_name": openai_tool_name,
                    "server_name": route.server_name,
                    "mcp_tool_name": route.mcp_tool_name,
                    "arguments": arguments,
                },
            )

        return await self.connections[route.server_name].call_tool(route.mcp_tool_name, arguments)
