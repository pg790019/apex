from langchain_core.runnables import RunnableConfig

from tools.validation_gate import (
    reset_validation_gate,
    record_validation_verdict,
    is_github_publishing_allowed,
)


runtime_config: RunnableConfig = {
    "configurable": {
        "thread_id": "github-gate-test-001"
    }
}

# Initially blocked
reset_validation_gate(runtime_config)
assert not is_github_publishing_allowed(runtime_config)

# Failed validation must remain blocked
record_validation_verdict(runtime_config, False)
assert not is_github_publishing_allowed(runtime_config)

# Successful validation allows publishing
record_validation_verdict(runtime_config, True)
assert is_github_publishing_allowed(runtime_config)

# A new run reset must close the gate again
reset_validation_gate(runtime_config)
assert not is_github_publishing_allowed(runtime_config)

print("All validation gate tests passed!")