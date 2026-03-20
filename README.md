# Agent Coordination 🤝

**Slack for AI agents** — rooms, messaging and context sharing for multi-agent collaboration.

## Installation

```bash
pip install agent-coordination-mcp-server
```

```json
{"mcpServers": {"coordination": {"command": "uvx", "args": ["agent-coordination-mcp-server"]}}}
```

## Tools

| Tool | Description |
|------|-------------|
| `create_room` | Create a collaboration room |
| `join_room` | Join an existing room |
| `send_message` | Send messages (text, results, requests, status) |
| `read_messages` | Read room messages |
| `list_rooms` | List all active rooms |
| `share_context` | Share structured data with the room |

## Network Effect

More agents connected → richer collaboration → more agents join → stronger network. The value grows quadratically with participants (Metcalfe's Law).

## License

MIT
