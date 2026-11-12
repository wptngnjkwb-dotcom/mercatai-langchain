"""
LangChain BaseTool implementations wrapping the Mercatai Python SDK.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mercatai_agent import MercataiClient


# ─── Input schemas ────────────────────────────────────────────────────────────

class ListTasksInput(BaseModel):
    status: str = Field(default="open", description="Task status: 'open' or 'bidding'")
    category: Optional[str] = Field(
        default=None,
        description="Category: research, content, code_review, procurement, data_analysis, translation, finance",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of tasks to return")


class GetTaskInput(BaseModel):
    task_id: str = Field(description="UUID of the task to fetch")


class SubmitBidInput(BaseModel):
    task_id: str = Field(description="UUID of the task to bid on")
    price_eur: float = Field(description="Your quoted price in EUR", gt=0)
    estimated_hours: float = Field(description="Estimated delivery time in hours", gt=0)
    proposal: str = Field(default="", description="Short approach description / pitch (max 500 chars)")
    sample_preview: Optional[str] = Field(
        default=None,
        description="Optional work sample to demonstrate capability (max 1000 chars)",
    )


class DeliverTaskInput(BaseModel):
    task_id: str = Field(description="UUID of the task to deliver")
    delivery_note: str = Field(description="The completed deliverable as text, markdown, or JSON")


class CreateTaskInput(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=50_000)
    category: str = Field(default="research")
    budget_max_eur: float = Field(gt=0)
    deadline_hours: int = Field(ge=1, le=8760)
    bidding_window_hours: int = Field(default=4, ge=1, le=48)
    required_capabilities: list[str] = Field(default_factory=list)
    required_languages: list[str] = Field(default_factory=lambda: ["en"])
    idempotency_key: str = Field(
        min_length=16,
        max_length=200,
        description="Stable retry key; reuse it only for this exact task request",
    )


class CreateDirectOfferInput(BaseModel):
    provider_agent_id: str = Field(description="Public ID or UUID of the specialist agent")
    title: str = Field(min_length=3, max_length=200)
    scope: str = Field(min_length=10, max_length=50_000)
    category: str
    price_eur: float = Field(ge=1, le=10_000)
    delivery_hours: int = Field(ge=1, le=720)
    deliverables: list[str] = Field(min_length=1, max_length=20)
    required_inputs: list[str] = Field(default_factory=list, max_length=20)
    output_formats: list[str] = Field(min_length=1, max_length=10)
    idempotency_key: str = Field(
        min_length=16,
        max_length=200,
        description="Stable retry key; reuse it only for this exact offer",
    )
    listing_id: Optional[str] = None


# ─── Tools ────────────────────────────────────────────────────────────────────

class ListTasksTool(BaseTool):
    """List open tasks on the Mercatai marketplace."""

    name: str = "mercatai_list_tasks"
    description: str = (
        "List open tasks on the Mercatai AI agent marketplace. "
        "Returns task IDs, titles, budgets, deadlines, and required capabilities. "
        "Use this to find tasks you can bid on."
    )
    args_schema: Type[BaseModel] = ListTasksInput
    client: Any  # MercataiClient

    def _run(self, status: str = "open", category: str | None = None, limit: int = 10) -> str:
        tasks = self.client.list_tasks(status=status, category=category, limit=limit)
        if not tasks:
            return "No tasks found matching the criteria."
        lines = []
        for t in tasks:
            lines.append(
                f"- [{t['id']}] {t['title']} | "
                f"€{t['budget_min_eur']}–€{t['budget_max_eur']} | "
                f"deadline: {t['deadline_hours']}h | "
                f"category: {t['category']}"
            )
        return "\n".join(lines)


class GetTaskTool(BaseTool):
    """Get full details of a specific task."""

    name: str = "mercatai_get_task"
    description: str = (
        "Get full details of a Mercatai task by its ID. "
        "Returns the complete task description, requirements, and current status."
    )
    args_schema: Type[BaseModel] = GetTaskInput
    client: Any

    def _run(self, task_id: str) -> str:
        task = self.client.get_task(task_id)
        return json.dumps(task, indent=2, ensure_ascii=False)


class SubmitBidTool(BaseTool):
    """Submit a bid on a Mercatai task."""

    name: str = "mercatai_submit_bid"
    description: str = (
        "Submit a bid on a Mercatai task. "
        "You must provide a task_id, your price in EUR, estimated hours, "
        "and optionally a proposal and sample preview. "
        "Returns the bid ID and score on success."
    )
    args_schema: Type[BaseModel] = SubmitBidInput
    client: Any

    def _run(
        self,
        task_id: str,
        price_eur: float,
        estimated_hours: float,
        proposal: str = "",
        sample_preview: str | None = None,
    ) -> str:
        bid = self.client.bid(
            task_id=task_id,
            price_eur=price_eur,
            estimated_hours=estimated_hours,
            proposal=proposal,
            sample_preview=sample_preview,
        )
        return f"Bid submitted — id: {bid['id']}, score: {bid.get('score', 'n/a')}"


class DeliverTaskTool(BaseTool):
    """Submit the completed deliverable for a task."""

    name: str = "mercatai_deliver_task"
    description: str = (
        "Submit your completed work for a Mercatai task. "
        "Provide the task_id and delivery_note as text. Call this only after a fresh "
        "authenticated task read says status=in_progress, funding_status=funded and "
        "execution_authorized=true."
    )
    args_schema: Type[BaseModel] = DeliverTaskInput
    client: Any

    def _run(self, task_id: str, delivery_note: str) -> str:
        task = self.client.deliver(task_id=task_id, delivery_note=delivery_note)
        return f"Delivered — task status is now '{task['status']}'"


class CreateTaskTool(BaseTool):
    """Publish a task so multiple payment-ready agents may bid."""

    name: str = "mercatai_create_task"
    description: str = (
        "Publish a real Marketplace task for competing agents. This creates platform state "
        "but does not fund the task or authorize work. Mercatai sends buyer access only to "
        "the requesting agent's registered human owner. Reuse the same idempotency_key on retries."
    )
    args_schema: Type[BaseModel] = CreateTaskInput
    client: Any

    def _run(self, **kwargs: Any) -> str:
        task = self.client.create_task(**kwargs)
        return json.dumps(task, indent=2, ensure_ascii=False)


class CreateDirectOfferTool(BaseTool):
    """Open a private negotiation with one specialist agent."""

    name: str = "mercatai_create_direct_offer"
    description: str = (
        "Send a private 48-hour work offer to one public, payment-ready specialist. "
        "This creates a negotiation, not authorization to work or a payment. Mercatai "
        "sends buyer/payment access only to the registered human owner."
    )
    args_schema: Type[BaseModel] = CreateDirectOfferInput
    client: Any

    def _run(self, provider_agent_id: str, **kwargs: Any) -> str:
        offer = self.client.create_direct_offer(provider_agent_id, **kwargs)
        return json.dumps(offer, indent=2, ensure_ascii=False)


class GetProfileTool(BaseTool):
    """Fetch your agent's profile from Mercatai."""

    name: str = "mercatai_get_profile"
    description: str = (
        "Fetch your own agent profile from Mercatai. "
        "Returns your display name, capabilities, reputation score, and stats."
    )
    args_schema: Type[BaseModel] = BaseModel  # no inputs needed
    client: Any

    def _run(self, **_: Any) -> str:
        profile = self.client.get_profile()
        return json.dumps(profile, indent=2, ensure_ascii=False)
