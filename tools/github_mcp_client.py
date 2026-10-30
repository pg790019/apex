import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import (
    GITHUB_MCP_URL,
    GITHUB_PERSONAL_ACCESS_TOKEN,
)

logger = logging.getLogger(__name__)

ALLOWED_GITHUB_TOOLS = {
    "create_branch",
    "push_files",
}


async def get_github_mcp_tools():
    if not GITHUB_PERSONAL_ACCESS_TOKEN:
        raise ValueError(
            "GITHUB_PERSONAL_ACCESS_TOKEN is not configured"
        )

    client = MultiServerMCPClient({
        "github": {
            "transport": "streamable_http",
            "url": GITHUB_MCP_URL,
            "headers": {
                "Authorization": (
                    f"Bearer {GITHUB_PERSONAL_ACCESS_TOKEN}"
                )
            },
        }
    })

    tools = await client.get_tools()

    selected_tools = [
        tool for tool in tools
        if tool.name in ALLOWED_GITHUB_TOOLS
    ]

    discovered = {tool.name for tool in selected_tools}
    missing = ALLOWED_GITHUB_TOOLS - discovered

    if missing:
        raise RuntimeError(
            f"Missing GitHub MCP tools: {sorted(missing)}"
        )

    return selected_tools