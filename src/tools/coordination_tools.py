"""Coordination-Tools — Räume, Nachrichten und Kontextaustausch für Agents."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

DB_PATH = Path.home() / ".agent-coordination" / "coordination.db"


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            room_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (room_id, agent_id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)
    conn.commit()
    return conn


def register_coordination_tools(mcp: FastMCP):

    @mcp.tool()
    async def create_room(
        room_id: str, name: str, description: str = "", created_by: str = ""
    ) -> dict:
        """Create a coordination room for agents to collaborate.

        Rooms are persistent spaces where agents share context,
        coordinate tasks, and exchange results.

        Args:
            room_id: Unique room ID (e.g. "project-alpha", "data-pipeline")
            name: Display name for the room
            description: What this room is for
            created_by: Agent or user who created the room
        """
        conn = _get_db()
        existing = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if existing:
            return {"error": f"Room '{room_id}' already exists"}

        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO rooms (id, name, description, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (room_id, name, description, created_by, now)
        )
        # Ersteller automatisch beitreten lassen
        if created_by:
            conn.execute(
                "INSERT OR IGNORE INTO members (room_id, agent_id, joined_at) VALUES (?, ?, ?)",
                (room_id, created_by, now)
            )
        conn.commit()

        return {"status": "created", "room_id": room_id, "name": name}

    @mcp.tool()
    async def join_room(room_id: str, agent_id: str) -> dict:
        """Join a coordination room.

        Args:
            room_id: Room to join
            agent_id: Your agent identifier
        """
        conn = _get_db()
        room = conn.execute("SELECT id, name FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return {"error": f"Room '{room_id}' not found"}

        conn.execute(
            "INSERT OR IGNORE INTO members (room_id, agent_id, joined_at) VALUES (?, ?, ?)",
            (room_id, agent_id, datetime.utcnow().isoformat())
        )
        conn.commit()

        return {"status": "joined", "room": room["name"], "agent": agent_id}

    @mcp.tool()
    async def send_message(
        room_id: str, sender: str, message: str,
        message_type: str = "text", metadata: str = "{}"
    ) -> dict:
        """Send a message to a coordination room.

        Share context, results, status updates, or requests with
        other agents in the room.

        Args:
            room_id: Target room
            sender: Your agent identifier
            message: The message content
            message_type: Type: "text", "result", "request", "status", "context"
            metadata: Optional JSON metadata
        """
        conn = _get_db()
        room = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return {"error": f"Room '{room_id}' not found"}

        conn.execute("""
            INSERT INTO messages (room_id, sender, message, message_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (room_id, sender, message, message_type, metadata, datetime.utcnow().isoformat()))
        conn.commit()

        return {"status": "sent", "room": room_id, "type": message_type}

    @mcp.tool()
    async def read_messages(room_id: str, limit: int = 20, since: str = "") -> dict:
        """Read messages from a coordination room.

        Get the latest messages or messages since a specific time.

        Args:
            room_id: Room to read from
            limit: Max messages (default: 20)
            since: Only messages after this ISO timestamp (optional)
        """
        conn = _get_db()
        room = conn.execute("SELECT id, name FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return {"error": f"Room '{room_id}' not found"}

        if since:
            rows = conn.execute("""
                SELECT sender, message, message_type, metadata, created_at
                FROM messages WHERE room_id = ? AND created_at > ?
                ORDER BY created_at DESC LIMIT ?
            """, (room_id, since, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT sender, message, message_type, metadata, created_at
                FROM messages WHERE room_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (room_id, limit)).fetchall()

        messages = []
        for r in rows:
            msg = {
                "sender": r["sender"],
                "message": r["message"],
                "type": r["message_type"],
                "time": r["created_at"],
            }
            meta = r["metadata"]
            if meta and meta != "{}":
                msg["metadata"] = json.loads(meta)
            messages.append(msg)

        messages.reverse()  # Chronologisch
        return {"room": room["name"], "message_count": len(messages), "messages": messages}

    @mcp.tool()
    async def list_rooms(active_only: bool = True) -> dict:
        """List all coordination rooms.

        Args:
            active_only: Only show active rooms (default: True)
        """
        conn = _get_db()
        if active_only:
            rows = conn.execute("SELECT * FROM rooms WHERE is_active = 1 ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM rooms ORDER BY created_at DESC").fetchall()

        rooms = []
        for r in rows:
            member_count = conn.execute(
                "SELECT COUNT(*) FROM members WHERE room_id = ?", (r["id"],)
            ).fetchone()[0]
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE room_id = ?", (r["id"],)
            ).fetchone()[0]
            rooms.append({
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "members": member_count,
                "messages": msg_count,
                "created_by": r["created_by"],
                "created_at": r["created_at"],
            })

        return {"total_rooms": len(rooms), "rooms": rooms}

    @mcp.tool()
    async def share_context(room_id: str, sender: str, key: str, value: str) -> dict:
        """Share a piece of context/data with a room.

        Structured way to share results, findings, or data points
        that other agents in the room can reference.

        Args:
            room_id: Target room
            sender: Your agent identifier
            key: Context key (e.g. "api_results", "analysis", "decision")
            value: The context value (text or JSON string)
        """
        metadata = json.dumps({"context_key": key})
        conn = _get_db()
        room = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return {"error": f"Room '{room_id}' not found"}

        conn.execute("""
            INSERT INTO messages (room_id, sender, message, message_type, metadata, created_at)
            VALUES (?, ?, ?, 'context', ?, ?)
        """, (room_id, sender, value, metadata, datetime.utcnow().isoformat()))
        conn.commit()

        return {"status": "shared", "room": room_id, "context_key": key}
