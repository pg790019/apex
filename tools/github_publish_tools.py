
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from tools.validation_gate import (
    is_github_publishing_allowed,
    reset_validation_gate,
)


def create_guarded_github_tools(mcp_tools):
    """Wrap GitHub MCP tools with a validation gate."""

    tools_by_name = {tool.name: tool for tool in mcp_tools}

    create_branch_mcp = tools_by_name.get("create_branch")
    push_files_mcp = tools_by_name.get("push_files")

    if not create_branch_mcp or not push_files_mcp:
        raise RuntimeError(
            "Required GitHub MCP tools are not available."
        )

    @tool
    def reset_github_publish_gate(
        runtime_config: RunnableConfig,
    ) -> str:
        """Reset GitHub publishing permission at the start of a new Jira run."""

        reset_validation_gate(runtime_config)

        return "GitHub publishing gate reset. Publishing is blocked until validation passes."

    @tool
    async def github_create_branch_guarded(
        owner: str,
        repo: str,
        branch: str,
        from_branch: str,
        runtime_config: RunnableConfig,
    ) -> str:
        """Create a GitHub branch only after successful validation."""

        if not is_github_publishing_allowed(runtime_config):
            raise PermissionError(
                "GitHub publishing blocked: validation has not passed."
            )

        result = await create_branch_mcp.ainvoke(
            {
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "from_branch": from_branch,
            },
            config=runtime_config,
        )

        return str(result)

    @tool
    async def github_push_files_guarded(
        owner: str,
        repo: str,
        branch: str,
        files: list[dict],
        message: str,
        runtime_config: RunnableConfig,
    ) -> str:
        """Push files to GitHub only after successful validation."""

        if not is_github_publishing_allowed(runtime_config):
            raise PermissionError(
                "GitHub publishing blocked: validation has not passed."
            )

        result = await push_files_mcp.ainvoke(
            {
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "files": files,
                "message": message,
            },
            config=runtime_config,
        )

        return str(result)

    return [
        reset_github_publish_gate,
        github_create_branch_guarded,
        github_push_files_guarded,
    ]
