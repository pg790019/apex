# tools/plan_approval_tool.py
from langgraph.types import interrupt

def request_plan_approval(plan_summary: str) -> str:
    """Call this after the planner finishes and before delegating to the
    executor, to get human approval of the plan before execution begins."""
    decision = interrupt({
        "action_requests": [
            {
                "name": "request_plan_approval",
                "args": {"plan_summary": plan_summary},
                "description": "Approve this plan before the executor runs it?",
            }
        ],
        "review_configs": [
            {"action_name": "request_plan_approval", "allowed_decisions": ["approve", "reject"]}
        ],
    })
    decisions = decision.get("decisions", [{}])
    decision_type = decisions[0].get("type", "reject")
    return "approved" if decision_type == "approve" else "rejected"