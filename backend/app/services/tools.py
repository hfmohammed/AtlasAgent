import hashlib
import hmac
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, PendingAction

CUSTOMERS = {
    "CUST-1001": {"id": "CUST-1001", "name": "Northwind Health", "tier": "enterprise"},
    "CUST-1002": {"id": "CUST-1002", "name": "Acme Retail", "tier": "standard"},
}
ORDERS = {
    "ORD-2048": {"id": "ORD-2048", "customer_id": "CUST-1001", "status": "shipped"},
    "ORD-4096": {"id": "ORD-4096", "customer_id": "CUST-1002", "status": "processing"},
}


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    mutating: bool
    handler: Callable[[dict[str, Any]], dict[str, Any]]


def _get_customer(arguments: dict[str, Any]) -> dict[str, Any]:
    customer_id = str(arguments.get("customer_id", "")).upper()
    return CUSTOMERS.get(customer_id, {"error": "customer not found", "id": customer_id})


def _get_order(arguments: dict[str, Any]) -> dict[str, Any]:
    order_id = str(arguments.get("order_id", "")).upper()
    return ORDERS.get(order_id, {"error": "order not found", "id": order_id})


def _create_support_draft(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_id": f"DRAFT-{hashlib.sha1(str(arguments).encode()).hexdigest()[:8].upper()}",
        "status": "created",
        "subject": arguments.get("subject", "Customer follow-up"),
    }


TOOLS = {
    "get_customer": ToolDefinition("get_customer", False, _get_customer),
    "get_order": ToolDefinition("get_order", False, _get_order),
    "create_support_draft": ToolDefinition("create_support_draft", True, _create_support_draft),
}


def approval_token(action_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), action_id.encode(), hashlib.sha256).hexdigest()


def verify_approval(action_id: str, token: str, secret: str) -> bool:
    return hmac.compare_digest(approval_token(action_id, secret), token)


def propose_action(
    db: Session, conversation_id: str, tool_name: str, arguments: dict[str, Any]
) -> PendingAction:
    if tool_name not in TOOLS or not TOOLS[tool_name].mutating:
        raise ValueError("only registered mutating tools require proposals")
    action = PendingAction(
        conversation_id=conversation_id,
        tool_name=tool_name,
        arguments=arguments,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def execute_approved(db: Session, action: PendingAction) -> dict[str, Any]:
    if not action.approved:
        raise PermissionError("action has not been approved")
    if action.executed:
        raise ValueError("action has already been executed")
    result = TOOLS[action.tool_name].handler(action.arguments)
    action.executed = True
    db.add(
        AuditEvent(
            conversation_id=action.conversation_id,
            event_type="tool_executed",
            payload={"tool": action.tool_name, "action_id": action.id, "result": result},
        )
    )
    db.commit()
    return result

