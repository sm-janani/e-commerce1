"""
Backend "tools" the agent can call. In a real deployment these would call
your order management system, payment gateway, and ticketing system over
HTTP/gRPC. Here they operate on local JSON files so the project runs
out-of-the-box without external services.
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from rag import knowledge_base

DATA_DIR = Path(__file__).parent / "data"
ORDERS_FILE = DATA_DIR / "orders.json"
INVENTORY_FILE = DATA_DIR / "inventory.json"
TICKETS_FILE = DATA_DIR / "tickets.json"


def _load(path: Path) -> list:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tool: get_order_status
# ---------------------------------------------------------------------------
def get_order_status(order_id: str) -> dict:
    orders = _load(ORDERS_FILE)
    for order in orders:
        if order["order_id"].lower() == order_id.strip().lower():
            return {"found": True, "order": order}
    return {"found": False, "message": f"No order found with ID '{order_id}'. "
                                        f"Please double-check the order ID."}


# ---------------------------------------------------------------------------
# Tool: initiate_return
# ---------------------------------------------------------------------------
def initiate_return(order_id: str, reason: str, item_id: Optional[str] = None) -> dict:
    orders = _load(ORDERS_FILE)
    order = next((o for o in orders if o["order_id"].lower() == order_id.strip().lower()), None)

    if order is None:
        return {"success": False, "message": f"No order found with ID '{order_id}'."}

    if order["status"] != "delivered":
        return {
            "success": False,
            "message": f"Order {order_id} has status '{order['status']}'. "
                        f"Only delivered orders are eligible for return. "
                        f"If it hasn't shipped yet, it can be cancelled instead.",
        }

    return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    return {
        "success": True,
        "return_id": return_id,
        "order_id": order_id,
        "item_id": item_id or "all items",
        "reason": reason,
        "message": f"Return {return_id} has been initiated for order {order_id}. "
                    f"A pickup will be scheduled within 2-3 business days. "
                    f"Refund will be processed within 5-7 business days after quality "
                    f"check, per policy.",
    }


# ---------------------------------------------------------------------------
# Tool: check_inventory
# ---------------------------------------------------------------------------
def check_inventory(product_name: str) -> dict:
    inventory = _load(INVENTORY_FILE)
    query = product_name.strip().lower()
    matches = [
        p for p in inventory
        if query in p["name"].lower() or query == p["product_id"].lower()
    ]
    if not matches:
        return {"found": False, "message": f"No product found matching '{product_name}'."}
    return {"found": True, "products": matches}


# ---------------------------------------------------------------------------
# Tool: search_knowledge_base (RAG)
# ---------------------------------------------------------------------------
def search_knowledge_base(query: str) -> dict:
    context = knowledge_base.format_context(query, top_k=3)
    return {"context": context}


# ---------------------------------------------------------------------------
# Tool: escalate_to_human
# ---------------------------------------------------------------------------
def escalate_to_human(summary: str, reason: str, priority: str = "normal") -> dict:
    tickets = _load(TICKETS_FILE)
    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "summary": summary,
        "reason": reason,
        "priority": priority,
        "status": "open",
    }
    tickets.append(ticket)
    _save(TICKETS_FILE, tickets)
    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": f"Escalation ticket {ticket_id} created with priority '{priority}'. "
                    f"A human support agent will follow up shortly.",
    }


# ---------------------------------------------------------------------------
# Tool registry: JSON-schema definitions passed to the Claude API, mapped
# to their Python implementations.
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "get_order_status",
        "description": "Look up the current status, tracking number, and details of a "
                        "customer's order using its order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID, e.g. 'ORD-10234'."}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "initiate_return",
        "description": "Start a return/refund request for a delivered order. Only works "
                        "if the order status is 'delivered'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID to return."},
                "reason": {"type": "string", "description": "Customer's reason for the return."},
                "item_id": {"type": "string", "description": "Specific product SKU to return, "
                                                               "if not the whole order."},
            },
            "required": ["order_id", "reason"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Check stock availability, price, and variants for a product by "
                        "name or SKU.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product name or SKU to search for."}
            },
            "required": ["product_name"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "Search the store's return, shipping, and FAQ policy documents for "
                        "information relevant to the customer's question. Always use this "
                        "before answering policy questions instead of guessing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The customer's question or topic to search for."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand off the conversation to a human support agent. Use this for "
                        "fraud/legal/billing disputes, when the customer explicitly asks "
                        "for a human, or when you cannot resolve the issue confidently "
                        "after using the other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Short summary of the conversation and issue."},
                "reason": {"type": "string", "description": "Why this needs human attention."},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
            },
            "required": ["summary", "reason"],
        },
    },
]

TOOL_IMPLEMENTATIONS = {
    "get_order_status": get_order_status,
    "initiate_return": initiate_return,
    "check_inventory": check_inventory,
    "search_knowledge_base": search_knowledge_base,
    "escalate_to_human": escalate_to_human,
}


def _to_ollama_format(defs: list) -> list:
    """Convert Anthropic-style tool defs (name/description/input_schema) into
    the OpenAI-style {"type": "function", "function": {...}} shape Ollama expects."""
    converted = []
    for d in defs:
        converted.append({
            "type": "function",
            "function": {
                "name": d["name"],
                "description": d["description"],
                "parameters": d["input_schema"],
            },
        })
    return converted


# Same tools, reshaped for Ollama's OpenAI-compatible tool-calling format.
OLLAMA_TOOL_DEFINITIONS = _to_ollama_format(TOOL_DEFINITIONS)
