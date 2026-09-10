"""
Agentic core. Runs a Perceive -> Reason -> Act -> Respond loop against the
Claude API using tool calling (function calling). The model decides which
tool(s) to call, we execute them locally, feed results back, and repeat
until the model produces a final text answer or explicitly escalates.
"""

import os
import json
from typing import List, Dict, Any

from anthropic import Anthropic
from dotenv import load_dotenv

from tools import TOOL_DEFINITIONS, TOOL_IMPLEMENTATIONS

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_AGENT_STEPS = 6  # safety cap on tool-call loops per user turn
MAX_HISTORY_MESSAGES = 20  # trim conversation memory to control token usage

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are Aria, an AI customer support agent for an e-commerce store.

Your job is to resolve customer questions about orders, returns, shipping, and
products directly and accurately using the tools available to you. Follow these
rules:

1. Never guess at policy details (return windows, refund timelines, shipping
   costs, etc.) — always call `search_knowledge_base` first and answer only from
   what it returns.
2. Always call `get_order_status` before discussing a specific order's status,
   even if the customer describes what they think happened.
3. Only call `initiate_return` after you have confirmed the order is delivered
   and understood the customer's reason for the return.
4. If the customer is angry, mentions fraud, a legal issue, a billing dispute
   you cannot resolve, or explicitly asks for a human, call `escalate_to_human`
   immediately rather than continuing to try tools.
5. If you've made a reasonable attempt (2-3 tool calls) and still cannot resolve
   the issue, escalate rather than guessing.
6. Be concise, warm, and professional. Do not invent order IDs, tracking
   numbers, or policy terms that were not returned by a tool.
7. Ask a clarifying question (e.g. for an order ID) if you need it before you
   can call a tool — do not fabricate missing details.
"""


class AgentSession:
    """Holds conversation memory for a single chat session."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.escalated: bool = False

    def trim(self):
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            self.messages = self.messages[-MAX_HISTORY_MESSAGES:]


# In-memory session store. Swap for Redis/DB in production.
_sessions: Dict[str, AgentSession] = {}


def get_session(session_id: str) -> AgentSession:
    if session_id not in _sessions:
        _sessions[session_id] = AgentSession()
    return _sessions[session_id]


def reset_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def _execute_tool(name: str, tool_input: dict) -> dict:
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if impl is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return impl(**tool_input)
    except Exception as exc:  # tool failures shouldn't crash the agent
        return {"error": f"Tool '{name}' failed: {exc}"}


def handle_message(session_id: str, user_message: str) -> dict:
    """
    Runs one full agent turn: adds the user's message, loops through any
    tool calls the model makes, and returns the final natural-language
    reply plus a log of which tools were used and whether escalation occurred.
    """
    session = get_session(session_id)
    session.messages.append({"role": "user", "content": user_message})

    tool_call_log = []
    escalated_this_turn = False

    for _ in range(MAX_AGENT_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=session.messages,
        )

        # Append the assistant's turn (may contain text and/or tool_use blocks)
        session.messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # Model produced a final answer
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            session.trim()
            return {
                "reply": final_text.strip(),
                "escalated": escalated_this_turn or session.escalated,
                "tool_calls": tool_call_log,
            }

        # Handle every tool_use block in this response, then loop back to
        # the model with the results.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_call_log.append({"tool_name": block.name, "tool_input": block.input})

            if block.name == "escalate_to_human":
                escalated_this_turn = True
                session.escalated = True

            result = _execute_tool(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        session.messages.append({"role": "user", "content": tool_results})

    # Safety fallback if the loop cap is hit without a final answer
    session.trim()
    return {
        "reply": "I'm having trouble resolving this automatically — I've flagged it "
                 "for a human support agent to follow up with you shortly.",
        "escalated": True,
        "tool_calls": tool_call_log,
    }
