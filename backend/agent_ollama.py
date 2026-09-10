"""
Agentic core — Ollama (local LLM) backend.

Same Perceive -> Reason -> Act -> Respond loop as agent.py, but talks to a
locally running Ollama server instead of the Claude API. Exposes the same
handle_message() / reset_session() interface so main.py can swap providers
via the LLM_PROVIDER env var without any other code changes.

Requires:
  - Ollama running locally (https://ollama.com) — `ollama serve`
  - A tool-calling-capable model pulled, e.g. `ollama pull llama3.1`
    or `ollama pull qwen2.5`
"""

import os
from typing import List, Dict, Any

from ollama import chat
from dotenv import load_dotenv

from tools import OLLAMA_TOOL_DEFINITIONS, TOOL_IMPLEMENTATIONS

load_dotenv()

MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
MAX_AGENT_STEPS = 6
MAX_HISTORY_MESSAGES = 20

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
8. You may call a tool at most once per turn for a given purpose — don't repeat
   an identical tool call.
"""


class AgentSession:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.escalated: bool = False

    def trim(self):
        # Keep the system message plus the most recent turns
        if len(self.messages) > MAX_HISTORY_MESSAGES + 1:
            self.messages = [self.messages[0]] + self.messages[-MAX_HISTORY_MESSAGES:]


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
    except Exception as exc:
        return {"error": f"Tool '{name}' failed: {exc}"}


def handle_message(session_id: str, user_message: str) -> dict:
    session = get_session(session_id)
    session.messages.append({"role": "user", "content": user_message})

    tool_call_log = []
    escalated_this_turn = False

    for _ in range(MAX_AGENT_STEPS):
        response = chat(
            model=MODEL,
            messages=session.messages,
            tools=OLLAMA_TOOL_DEFINITIONS,
        )

        session.messages.append(response.message)

        tool_calls = response.message.tool_calls or []
        if not tool_calls:
            session.trim()
            return {
                "reply": (response.message.content or "").strip(),
                "escalated": escalated_this_turn or session.escalated,
                "tool_calls": tool_call_log,
            }

        for call in tool_calls:
            name = call.function.name
            args = dict(call.function.arguments or {})
            tool_call_log.append({"tool_name": name, "tool_input": args})

            if name == "escalate_to_human":
                escalated_this_turn = True
                session.escalated = True

            result = _execute_tool(name, args)
            session.messages.append({
                "role": "tool",
                "tool_name": name,
                "content": str(result),
            })

    session.trim()
    return {
        "reply": "I'm having trouble resolving this automatically — I've flagged it "
                 "for a human support agent to follow up with you shortly.",
        "escalated": True,
        "tool_calls": tool_call_log,
    }
