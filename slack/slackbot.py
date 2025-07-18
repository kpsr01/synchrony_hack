import os
import sqlite3
import asyncio
from datetime import datetime
from collections import defaultdict
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from google import genai
from google.genai import types
import logging
import dotenv

dotenv.load_dotenv()

# Initialize Slack app
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))


class StandupTracker:
    def __init__(self):
        self.db_path = "standup_messages.db"
        self.init_database()
        self.client = genai.Client()

    def init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create standup_channels table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS standup_channels (
                channel_id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                message_ts TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                date TEXT NOT NULL,
                attachments INTEGER DEFAULT 0
            )
        """
        )

        # Create index for faster queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_date_channel 
            ON messages (date, channel_id)
        """
        )

        conn.commit()
        conn.close()

    def get_standup_channels(self, team_id=None):
        """Get all standup channels, optionally filtered by team."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if team_id:
            cursor.execute(
                "SELECT channel_id FROM standup_channels WHERE team_id = ?",
                (team_id,),
            )
        else:
            cursor.execute("SELECT channel_id FROM standup_channels")

        channels = {row[0] for row in cursor.fetchall()}
        conn.close()
        return channels

    def add_standup_channel(self, channel_id, team_id, channel_name):
        """Add a channel to standup monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO standup_channels 
            (channel_id, team_id, channel_name) 
            VALUES (?, ?, ?)
        """,
            (channel_id, team_id, channel_name),
        )

        conn.commit()
        conn.close()

    def remove_standup_channel(self, channel_id):
        """Remove a channel from standup monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM standup_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()

    def store_message(self, message_data):
        """Store a message in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.fromtimestamp(float(message_data["ts"]))
        date_str = timestamp.strftime("%Y-%m-%d")

        cursor.execute(
            """
            INSERT INTO messages 
            (message_ts, channel_id, user_name, user_id, content, timestamp, date, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                message_data["ts"],
                message_data["channel"],
                message_data.get("user_name", "Unknown"),
                message_data["user"],
                message_data.get("text", ""),
                timestamp.isoformat(),
                date_str,
                len(message_data.get("files", [])),
            ),
        )

        conn.commit()
        conn.close()

    def get_messages_for_date(self, channel_id, date):
        """Get all messages for a specific date and channel."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_name, content, timestamp, attachments
            FROM messages 
            WHERE channel_id = ? AND date = ?
            ORDER BY timestamp ASC
        """,
            (channel_id, date),
        )

        messages = cursor.fetchall()
        conn.close()
        return messages

    def trim_messages_for_gemini(self, messages, max_tokens=900000):
        """Trim messages to fit within Gemini's context window."""
        max_chars = max_tokens * 3  # Conservative estimate

        if not messages:
            return []

        formatted_messages = []
        total_chars = 0

        # Group by author
        author_messages = defaultdict(list)
        for msg in messages:
            author_messages[msg[0]].append(msg)

        for author, msgs in author_messages.items():
            author_content = f"\n**{author}:**\n"
            author_chars = len(author_content)

            for msg in msgs:
                content = msg[1]
                timestamp = datetime.fromisoformat(msg[2]).strftime("%H:%M")

                # Add attachment info if present
                extra_info = f" ({msg[3]} attachments)" if msg[3] > 0 else ""
                msg_text = f"[{timestamp}] {content}{extra_info}\n"

                if total_chars + author_chars + len(msg_text) > max_chars:
                    if not formatted_messages:
                        formatted_messages.append(author_content + msg_text)
                    break

                author_content += msg_text
                author_chars += len(msg_text)

            if author_chars > len(f"\n**{author}:**\n"):
                formatted_messages.append(author_content)
                total_chars += author_chars

            if total_chars > max_chars:
                break

        return formatted_messages

    async def generate_ai_summary(self, messages, date, channel_name):
        """Generate AI summary using Gemini."""
        if not messages:
            return "No messages found for this date."

        trimmed_messages = self.trim_messages_for_gemini(messages)
        messages_text = "\n".join(trimmed_messages)

        prompt = f"""
        Please analyze the following standup messages from {channel_name} on {date} and provide **ONE** comprehensive summary.

        Focus on:
        1. Key updates and progress made by team members
        2. Blockers or challenges mentioned
        3. Plans for upcoming work
        4. Important decisions or discussions
        5. Overall team sentiment and productivity

        Format your response as a clear, organized summary that a manager could quickly read to understand the team's status.
        Please send Only One summary, do not send multiple summaries.

        Messages:
        {messages_text}
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error generating AI summary: {str(e)}"


# Initialize tracker
tracker = StandupTracker()


@app.command("/set_standup_channel")
async def set_standup_channel(ack, respond, command, client):
    """Set current channel for standup monitoring."""
    await ack()

    channel_id = command["channel_id"]
    team_id = command["team_id"]

    # Get channel info
    try:
        channel_info = await client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]
    except Exception as e:
        await respond(f"Error getting channel info: {str(e)}", response_type="in_channel")
        return

    standup_channels = tracker.get_standup_channels(team_id)
    if channel_id in standup_channels:
        await respond(
            "✅ This channel is already set as a standup channel!",
            response_type="in_channel",
        )
        return

    tracker.add_standup_channel(channel_id, team_id, channel_name)

    await respond(
        f"📋 *Standup Channel Set!*\n\nNow monitoring messages in <#{channel_id}>\n\n*What happens now:*\n• All messages in this channel will be tracked\n• Use `/ai_summary` to get AI-powered daily summaries\n• Use `/remove_standup_channel` to stop monitoring",
        response_type="in_channel",
    )


@app.command("/remove_standup_channel")
async def remove_standup_channel(ack, respond, command):
    """Remove standup monitoring from current channel."""
    await ack()

    channel_id = command["channel_id"]
    team_id = command["team_id"]

    standup_channels = tracker.get_standup_channels(team_id)
    if channel_id not in standup_channels:
        await respond("This channel is not set as a standup channel.", response_type="in_channel")
        return

    tracker.remove_standup_channel(channel_id)
    await respond("✅ Removed standup monitoring from this channel.", response_type="in_channel")


@app.command("/ai_summary")
async def ai_summary(ack, respond, command, client):
    """Generate AI-powered daily summary."""
    await ack()

    # Parse arguments
    args = command.get("text", "").strip().split()
    date = None
    channel_id = command["channel_id"]

    if args:
        # Try to parse date from first argument
        try:
            datetime.strptime(args[0], "%Y-%m-%d")
            date = args[0]
        except ValueError:
            await respond("Invalid date format. Use YYYY-MM-DD format.")
            return

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Check if channel is monitored
    standup_channels = tracker.get_standup_channels(command["team_id"])
    if channel_id not in standup_channels:
        await respond(
            "This channel is not set as a standup channel. Use `/set_standup_channel` first."
        )
        return

    # Get messages
    messages = tracker.get_messages_for_date(channel_id, date)

    if not messages:
        await respond(f"No messages found for {date} in this channel.")
        return

    # Get channel name
    try:
        channel_info = await client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]
    except Exception:
        channel_name = "Unknown"

    # Generate summary
    summary = await tracker.generate_ai_summary(messages, date, channel_name)

    # Format response
    response = f"🤖 *AI-Powered Daily Summary*\n\n*Date:* {date}\n*Channel:* <#{channel_id}>\n*Messages Analyzed:* {len(messages)}\n\n*Summary:*\n{summary}"

    await respond(response)


@app.command("/list_standup_channels")
async def list_standup_channels(ack, respond, command, client):
    """List all configured standup channels."""
    await ack()

    standup_channels = tracker.get_standup_channels(command["team_id"])

    if not standup_channels:
        await respond(
            "No standup channels configured. Use `/set_standup_channel` to add one.",
            response_type="in_channel",
        )
        return

    channel_list = []
    today = datetime.now().strftime("%Y-%m-%d")

    for channel_id in standup_channels:
        try:
            channel_info = await client.conversations_info(channel=channel_id)
            channel_name = channel_info["channel"]["name"]
            messages = tracker.get_messages_for_date(channel_id, today)
            msg_count = len(messages)
            channel_list.append(f"• <#{channel_id}> ({msg_count} messages today)")
        except Exception:
            channel_list.append(f"• Unknown channel (ID: {channel_id})")

    response = f"📋 *Standup Channels*\n\nChannels currently being monitored:\n\n" + "\n".join(
        channel_list
    )
    await respond(response, response_type="in_channel")


@app.event("message")
async def handle_message(event, client):
    """Track messages in standup channels."""
    # Skip bot messages and message subtypes
    if event.get("subtype") or event.get("bot_id"):
        return

    channel_id = event["channel"]
    team_id = event.get("team")

    # Check if channel is monitored
    standup_channels = tracker.get_standup_channels(team_id)
    if channel_id not in standup_channels:
        return

    # Get user info
    try:
        user_info = await client.users_info(user=event["user"])
        user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
    except Exception:
        user_name = "Unknown"

    # Prepare message data
    message_data = {
        "ts": event["ts"],
        "channel": channel_id,
        "user": event["user"],
        "user_name": user_name,
        "text": event.get("text", ""),
        "files": event.get("files", []),
    }

    # Store message
    tracker.store_message(message_data)


async def main():
    """Start the bot."""
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
