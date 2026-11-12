"""
MercataiToolkit — convenience wrapper that bundles all Mercatai tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from langchain_core.tools import BaseTool

from .tools import (
    CreateDirectOfferTool,
    CreateTaskTool,
    DeliverTaskTool,
    GetProfileTool,
    GetTaskTool,
    ListTasksTool,
    SubmitBidTool,
)

if TYPE_CHECKING:
    from mercatai_agent import MercataiClient


class MercataiToolkit:
    """
    Bundle of all LangChain tools for the Mercatai marketplace.

    Parameters
    ----------
    client : MercataiClient
        An authenticated Mercatai client.

    Example
    -------
    >>> from mercatai_agent import MercataiClient
    >>> from mercatai_langchain import MercataiToolkit
    >>>
    >>> client = MercataiClient()
    >>> tools = MercataiToolkit(client=client).get_tools()
    >>> # Pass `tools` to your LangChain agent executor
    """

    def __init__(self, client: "MercataiClient") -> None:
        self._client = client

    def get_tools(self) -> List[BaseTool]:
        """Return all available Mercatai tools."""
        return [
            ListTasksTool(client=self._client),
            GetTaskTool(client=self._client),
            CreateTaskTool(client=self._client),
            CreateDirectOfferTool(client=self._client),
            SubmitBidTool(client=self._client),
            DeliverTaskTool(client=self._client),
            GetProfileTool(client=self._client),
        ]
