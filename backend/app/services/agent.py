import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import Conversation
from app.schemas import ToolCall
from app.services.tools import TOOLS, propose_action


@dataclass
class AgentDecision:
    answer_prefix: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


def _identifier(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def decide(db: Session, conversation: Conversation, query: str) -> AgentDecision:
    lowered = query.lower()
    order_id = _identifier(r"ORD-\d+", query)
    customer_id = _identifier(r"CUST-\d+", query)

    if "draft" in lowered or "reply" in lowered:
        arguments: dict[str, Any] = {
            "subject": "Follow-up requested by AtlasAgent",
            "customer_id": customer_id,
            "order_id": order_id,
        }
        action = propose_action(db, conversation.id, "create_support_draft", arguments)
        return AgentDecision(
            answer_prefix=(
                "I prepared a support-draft action. It must be approved before execution. "
            ),
            tool_calls=[
                ToolCall(
                    name="create_support_draft",
                    arguments=arguments,
                    status="approval_required",
                    action_id=action.id,
                )
            ],
        )

    calls: list[ToolCall] = []
    if order_id:
        result = TOOLS["get_order"].handler({"order_id": order_id})
        calls.append(
            ToolCall(
                name="get_order",
                arguments={"order_id": order_id},
                status="completed",
                result=result,
            )
        )
    if customer_id:
        result = TOOLS["get_customer"].handler({"customer_id": customer_id})
        calls.append(
            ToolCall(
                name="get_customer",
                arguments={"customer_id": customer_id},
                status="completed",
                result=result,
            )
        )
    prefix = "I retrieved the requested business record. " if calls else ""
    return AgentDecision(answer_prefix=prefix, tool_calls=calls)

