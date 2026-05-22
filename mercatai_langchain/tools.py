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
        description="Category: research, content, code_review, procurement, data_analysis, translation",
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
    result: str = Field(description="The completed deliverable as text, markdown, or JSON")


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
        )
        return f"Bid submitted — id: {bid['id']}, score: {bid.get('score', 'n/a')}"


class DeliverTaskTool(BaseTool):
    """Submit the completed deliverable for a task."""

    name: str = "mercatai_deliver_task"
    description: str = (
        "Submit your completed work for a Mercatai task. "
        "Provide the task_id and the result as text. "
        "Only call this when the task is in 'assigned' status."
    )
    args_schema: Type[BaseModel] = DeliverTaskInput
    client: Any

    def _run(self, task_id: str, result: str) -> str:
        task = self.client.deliver(task_id=task_id, result=result)
        return f"Delivered — task status is now '{task['status']}'"


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
