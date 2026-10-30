import asyncio
from tools.github_mcp_client import get_github_mcp_tools


async def main():
    tools = await get_github_mcp_tools()

    for tool in tools:
        print(f"\n{'=' * 50}")
        print(f"Tool: {tool.name}")
        print(f"Description: {tool.description}")
        print("Input Schema:")
        print(tool.args_schema)


if __name__ == "__main__":
    asyncio.run(main())