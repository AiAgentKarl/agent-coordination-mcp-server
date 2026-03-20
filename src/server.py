"""Agent Coordination — Slack for AI agents."""

from mcp.server.fastmcp import FastMCP
from src.tools.coordination_tools import register_coordination_tools

mcp = FastMCP(
    "Agent Coordination",
    instructions=(
        "Multi-agent coordination hub. Create rooms, share context, "
        "and coordinate tasks between multiple AI agents. "
        "Like Slack, but for AI agents working together."
    ),
)

register_coordination_tools(mcp)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
