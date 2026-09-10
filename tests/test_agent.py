"""
Unit tests that don't require an Anthropic API key — they test the
deterministic building blocks (tools + RAG retrieval) directly.

Run with:  pytest tests/test_agent.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from tools import get_order_status, initiate_return, check_inventory  # noqa: E402
from rag import knowledge_base  # noqa: E402


def test_get_order_status_found():
    result = get_order_status("ORD-10234")
    assert result["found"] is True
    assert result["order"]["status"] == "shipped"


def test_get_order_status_not_found():
    result = get_order_status("ORD-99999")
    assert result["found"] is False


def test_initiate_return_on_delivered_order():
    result = initiate_return("ORD-10236", reason="Item too small")
    assert result["success"] is True
    assert result["return_id"].startswith("RET-")


def test_initiate_return_blocked_when_not_delivered():
    result = initiate_return("ORD-10235", reason="Changed my mind")
    assert result["success"] is False


def test_check_inventory_out_of_stock():
    result = check_inventory("Smart Fitness Watch")
    assert result["found"] is True
    assert result["products"][0]["stock"] == 0


def test_knowledge_base_retrieves_return_policy():
    context = knowledge_base.format_context("How long do I have to return an item?")
    assert "return_policy" in context
    assert "15" in context


def test_knowledge_base_retrieves_shipping_policy():
    context = knowledge_base.format_context("free shipping minimum order")
    assert "999" in context
