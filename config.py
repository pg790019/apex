"""
Central configuration for the Jira -> Deep Agents demo.

All values are read from environment variables (loaded from a .env file via
python-dotenv if present, which mirrors how AgentCore Runtime / ECS / Lambda
would inject them in a real deployment). Nothing here should be hardcoded --
copy .env.example to .env and fill in real values before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---- Azure OpenAI ----
AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "")
AZURE_OPENAI_MODEL_ID: str = os.getenv("AZURE_OPENAI_MODEL_ID", "")
AZURE_OPENAI_EMBEDDING_MODEL_ID: str = os.getenv(
    "AZURE_OPENAI_EMBEDDING_MODEL_ID", ""
)

# ---- AWS (used only by the optional AgentCore checkpointer) ----
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

# ---- Persistence ----
# "memory"    -> in-process MemorySaver, zero AWS dependency, 
# "agentcore" -> Bedrock AgentCore Memory-backed checkpointer (needs a provisioned
#                Memory resource)
CHECKPOINTER_BACKEND: str = os.getenv("CHECKPOINTER_BACKEND", "memory").lower()
AGENTCORE_MEMORY_ID: str = os.getenv("AGENTCORE_MEMORY_ID", "REPLACE_WITH_AGENTCORE_MEMORY_ID")

# ---- Jira ----
JIRA_BASE_URL: str = os.getenv("JIRA_BASE_URL", "https://rishugupta9417.atlassian.net")
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "rishugupta9417@gmail.com")
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")

# ---- GitHub Remote MCP ----
GITHUB_MCP_URL = os.getenv(
    "GITHUB_MCP_URL",
    "https://api.githubcopilot.com/mcp/"
)

GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv(
    "GITHUB_PERSONAL_ACCESS_TOKEN", ""
)

GITHUB_OWNER = os.getenv("GITHUB_OWNER", "pg790019")
GITHUB_REPO = os.getenv("GITHUB_REPO", "apex")
GITHUB_BASE_BRANCH = os.getenv("GITHUB_BASE_BRANCH", "main")

# ---- Webhook listener ----
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))

# ---- Loop safety net ----
# Routing is intentionally LLM-driven (the orchestrator decides when to retry
# the executor) rather than a hardcoded graph edge, per requirements. We still
# tell the orchestrator its retry ceiling in its own prompt so a confused model
# doesn't loop forever and burn tokens -- this is guidance, not code-enforced.
MAX_EXECUTOR_RETRIES: int = int(os.getenv("MAX_EXECUTOR_RETRIES", "3"))

# After this many CONSECUTIVE failed validations, the orchestrator is
# instructed to call request_human_review instead of retrying the executor
# again. This is also guidance enforced via the prompt, not code -- the
# request_human_review tool itself is what actually pauses the graph.
MAX_CONSECUTIVE_VALIDATION_FAILURES_BEFORE_REVIEW: int = int(
    os.getenv("MAX_CONSECUTIVE_VALIDATION_FAILURES_BEFORE_REVIEW", "2")
)

# ---- Workspace / filesystem backend ----
# Base directory (in the current working directory by default) under which
# per-ticket workspace folders (agent-work-{ticket_id}[-vN]) are created,
# and where the shared skills/ folder actually lives on disk.
WORKSPACE_BASE_DIR: str = os.getenv("WORKSPACE_BASE_DIR", ".")

# On-disk folder name (relative to WORKSPACE_BASE_DIR) containing ALL skill
# subfolders, e.g. skills/salesforce-dynamics-migration/SKILL.md.
# IMPORTANT: point this at the PARENT "skills" folder, not at one specific
# skill's own subfolder -- deep agents expects a directory that *contains*
# skill folders, and discovers each skill inside it.
SKILLS_DIR_NAME: str = os.getenv("SKILLS_DIR_NAME", "skills")

# Route prefix used inside the agent's virtual filesystem to reach skills.
# This is NOT a disk path -- it's the key the CompositeBackend in
# orchestrator.py uses to route skill reads to a backend rooted at the real
# on-disk skills/ folder, independently of whatever per-ticket workspace
# folder the rest of the agent's files are scoped to. Passed as-is to
# create_deep_agent(skills=[...]) and to each subagent's "skills" list.
SKILLS_ROUTE_PREFIX: str = "/skills/"

# migrate_component's success/partial outcome is normally random (~25% partial
# chance per call). If DEMO_FORCE_FAILURE_COMPONENT is set to a component name
# (e.g. "Custom_Object__c"), that component will deterministically report a
# partial failure for the first DEMO_FORCE_FAILURE_COUNT times it is migrated
# in this process run, then succeed -- letting you reliably trigger N
# validation failures (and, with MAX_CONSECUTIVE_VALIDATION_FAILURES_BEFORE_
# REVIEW set to the same number, a human-review escalation. Leave empty ("") to use pure random behavior for every
# component, as before.
DEMO_FORCE_FAILURE_COMPONENT: str = os.getenv("DEMO_FORCE_FAILURE_COMPONENT", "")
DEMO_FORCE_FAILURE_COUNT: int = int(os.getenv("DEMO_FORCE_FAILURE_COUNT", "2"))