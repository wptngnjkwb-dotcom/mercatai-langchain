import json
from unittest.mock import MagicMock

from mercatai_langchain import (
    CreateDirectOfferTool,
    CreateTaskTool,
    DeliverTaskTool,
    MercataiToolkit,
    SubmitBidTool,
)


def test_create_task_forwards_retry_safe_agent_request():
    client = MagicMock()
    client.create_task.return_value = {"id": "task-1", "human_approval_required": True}
    tool = CreateTaskTool(client=client)
    result = json.loads(tool._run(
        title="Validate an API",
        description="Run the checks and return an evidence-backed report.",
        category="code_review",
        budget_max_eur=30,
        deadline_hours=24,
        bidding_window_hours=6,
        required_capabilities=["api_testing"],
        required_languages=["en"],
        idempotency_key="langchain-task-0001",
    ))
    assert result["id"] == "task-1"
    assert client.create_task.call_args.kwargs["idempotency_key"] == "langchain-task-0001"


def test_direct_offer_never_adds_a_buyer_credential():
    client = MagicMock()
    client.create_direct_offer.return_value = {"direct_offer_id": "offer-1"}
    tool = CreateDirectOfferTool(client=client)
    result = json.loads(tool._run(
        provider_agent_id="specialist",
        title="Analyze data",
        scope="Analyze the supplied dataset and explain anomalies.",
        category="data_analysis",
        price_eur=25,
        delivery_hours=12,
        deliverables=["Report"],
        required_inputs=["CSV"],
        output_formats=["markdown"],
        idempotency_key="langchain-offer-0001",
        listing_id=None,
    ))
    assert result["direct_offer_id"] == "offer-1"
    assert client.create_direct_offer.call_args.args == ("specialist",)
    assert "buyer_email" not in client.create_direct_offer.call_args.kwargs


def test_delivery_uses_canonical_field_and_bid_keeps_sample():
    client = MagicMock()
    client.deliver.return_value = {"status": "review"}
    DeliverTaskTool(client=client)._run("task-1", "Completed report")
    client.deliver.assert_called_once_with(task_id="task-1", delivery_note="Completed report")

    client.bid.return_value = {"id": "bid-1", "score": 1}
    SubmitBidTool(client=client)._run("task-1", 9, 2, "Approach", "Sample")
    assert client.bid.call_args.kwargs["sample_preview"] == "Sample"


def test_toolkit_includes_requester_tools_but_no_payment_execution_tool():
    names = [tool.name for tool in MercataiToolkit(client=MagicMock()).get_tools()]
    assert "mercatai_create_task" in names
    assert "mercatai_create_direct_offer" in names
    assert all("payment" not in name for name in names)
