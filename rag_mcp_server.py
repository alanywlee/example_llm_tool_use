from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

HOST = os.getenv("RAG_MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("RAG_MCP_PORT", "8000"))

mcp = FastMCP("enterprise-rag-mcp-server", host=HOST, port=PORT)


@mcp.tool()
def rag_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Search enterprise KM documents and return raw search results.

    Demo behavior: fixed JSON array. Replace this with your real vector / hybrid / rerank search.
    """
    return [
        {
            "document_id": "POLICY-TRAVEL-001",
            "title": "差旅報銷政策",
            "source": "enterprise_km",
            "score": 0.92,
            "snippet": "住宿費需提供發票，每晚上限為新台幣 3500 元。餐費補助每日上限為新台幣 800 元。超過上限者需主管事前核准。",
            "metadata": {"department": "Finance", "tags": ["policy", "travel", "expense", "reimbursement"]},
        },
        {
            "document_id": "POLICY-IT-SEC-002",
            "title": "內部系統權限申請流程",
            "source": "enterprise_km",
            "score": 0.78,
            "snippet": "新系統權限申請需由直屬主管核准。高風險系統需額外經資安團隊審核。一般權限 SLA 為 2 個工作天。",
            "metadata": {"department": "IT", "tags": ["policy", "access", "security", "workflow"]},
        },
        {
            "document_id": "FAQ-PRODUCT-PRICING-003",
            "title": "產品方案與價格 FAQ",
            "source": "enterprise_km",
            "score": 0.71,
            "snippet": "方案 A：每月 1200 元。方案 B：每月 950 元。方案 C：每月 1500 元。以上價格未稅。",
            "metadata": {"department": "Product", "tags": ["faq", "pricing", "plan"]},
        },
    ][:top_k]


@mcp.tool()
def rag_search_and_summarize(query: str, top_k: int = 5, summarize_profile: str = "default") -> str:
    """
    Search enterprise KM documents, then return an integrated answer.

    Demo behavior: fixed integrated answer string. Replace with real search + summarizer LLM.
    """
    return (
        f"根據企業 KM 搜尋結果，這是一個使用 `{summarize_profile}` 摘要設定產生的整合回答。"
        "目前範例為固定回傳字串：差旅報銷政策指出住宿費每晚上限為新台幣 3500 元，"
        "餐費補助每日上限為新台幣 800 元；內部系統權限申請需主管核准，一般權限 SLA 為 2 個工作天。"
        "來源：POLICY-TRAVEL-001《差旅報銷政策》、POLICY-IT-SEC-002《內部系統權限申請流程》。"
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
