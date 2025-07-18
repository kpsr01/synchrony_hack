import discord
from discord.ext import commands
from datetime import datetime, timedelta
import sqlite3
import os
import asyncio
from collections import defaultdict
from google import genai
from google.genai import types


class MessageTrackerCog(commands.Cog):
    """Tracks messages in designated standup channels and provides AI-powered daily summaries."""

    def __init__(self, bot):
        self.bot = bot
        self.db_path = "standup_messages.db"
        self.init_database()

        # Configure Gemini API
        # genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.client = genai.Client()

    def init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create standup_channels table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS standup_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
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
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                date TEXT NOT NULL,
                attachments INTEGER DEFAULT 0,
                embeds INTEGER DEFAULT 0,
                FOREIGN KEY (channel_id) REFERENCES standup_channels (channel_id)
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

    def get_standup_channels(self, guild_id=None):
        """Get all standup channels, optionally filtered by guild."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if guild_id:
            cursor.execute(
                "SELECT channel_id FROM standup_channels WHERE guild_id = ?",
                (guild_id,),
            )
        else:
            cursor.execute("SELECT channel_id FROM standup_channels")

        channels = {row[0] for row in cursor.fetchall()}
        conn.close()
        return channels

    def add_standup_channel(self, channel_id, guild_id, channel_name):
        """Add a channel to standup monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO standup_channels 
            (channel_id, guild_id, channel_name) 
            VALUES (?, ?, ?)
        """,
            (channel_id, guild_id, channel_name),
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

    def store_message(self, message):
        """Store a message in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        date_str = message.created_at.strftime("%Y-%m-%d")

        cursor.execute(
            """
            INSERT INTO messages 
            (message_id, channel_id, author_name, author_id, content, timestamp, date, attachments, embeds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                message.id,
                message.channel.id,
                message.author.display_name,
                message.author.id,
                message.content,
                message.created_at.isoformat(),
                date_str,
                len(message.attachments),
                len(message.embeds),
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
            SELECT author_name, content, timestamp, attachments, embeds
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
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 3  # Conservative estimate

        if not messages:
            return []

        # Format messages with priorities
        formatted_messages = []
        total_chars = 0

        # Group by author for better organization
        author_messages = defaultdict(list)
        for msg in messages:
            author_messages[msg[0]].append(msg)

        # Add messages by author, ensuring we get representation from everyone
        for author, msgs in author_messages.items():
            author_content = f"\n**{author}:**\n"
            author_chars = len(author_content)

            for msg in msgs:
                content = msg[1]
                timestamp = datetime.fromisoformat(msg[2]).strftime("%H:%M")

                # Add attachment/embed info if present
                extras = []
                if msg[3] > 0:  # attachments
                    extras.append(f"{msg[3]} attachments")
                if msg[4] > 0:  # embeds
                    extras.append(f"{msg[4]} embeds")

                extra_info = f" ({', '.join(extras)})" if extras else ""
                msg_text = f"[{timestamp}] {content}{extra_info}\n"

                if total_chars + author_chars + len(msg_text) > max_chars:
                    if not formatted_messages:  # Ensure at least one message
                        formatted_messages.append(author_content + msg_text)
                    break

                author_content += msg_text
                author_chars += len(msg_text)

            if author_chars > len(f"\n**{author}:**\n"):  # Has content
                formatted_messages.append(author_content)
                total_chars += author_chars

            if total_chars > max_chars:
                break

        return formatted_messages

    async def generate_ai_summary(self, messages, date, channel_name):
        """Generate AI summary using Gemini."""
        if not messages:
            return "No messages found for this date."

        # Trim messages to fit context window
        trimmed_messages = self.trim_messages_for_gemini(messages)
        messages_text = "\n".join(trimmed_messages)

        prompt = f"""
        Please analyze the following standup messages from {channel_name} on {date} and provide a comprehensive summary.

        Focus on:
        1. Key updates and progress made by team members
        2. Blockers or challenges mentioned
        3. Plans for upcoming work
        4. Important decisions or discussions
        5. Overall team sentiment and productivity

        Format your response as a clear, organized summary that a manager could quickly read to understand the team's status.

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

    @discord.app_commands.command(
        name="set_standup_channel",
        description="Set this channel for standup message monitoring",
    )
    async def set_standup_channel(self, interaction: discord.Interaction):
        """Set the current channel as a standup channel to monitor."""
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "You need 'Manage Channels' permission to set standup channels.",
                ephemeral=True,
            )
            return

        channel_id = interaction.channel_id
        guild_id = interaction.guild_id
        channel_name = interaction.channel.name

        standup_channels = self.get_standup_channels(guild_id)
        if channel_id in standup_channels:
            await interaction.response.send_message(
                "✅ This channel is already set as a standup channel!", ephemeral=True
            )
            return

        self.add_standup_channel(channel_id, guild_id, channel_name)

        embed = discord.Embed(
            title="📋 Standup Channel Set!",
            description=f"Now monitoring messages in {interaction.channel.mention}",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="What happens now:",
            value="• All messages in this channel will be tracked\n• Use `/ai_summary` to get AI-powered daily summaries\n• Use `/remove_standup_channel` to stop monitoring",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(
        name="remove_standup_channel",
        description="Remove standup monitoring from this channel",
    )
    async def remove_standup_channel(self, interaction: discord.Interaction):
        """Remove standup monitoring from the current channel."""
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "You need 'Manage Channels' permission to modify standup channels.",
                ephemeral=True,
            )
            return

        channel_id = interaction.channel_id
        standup_channels = self.get_standup_channels(interaction.guild_id)

        if channel_id not in standup_channels:
            await interaction.response.send_message(
                "This channel is not set as a standup channel.", ephemeral=True
            )
            return

        self.remove_standup_channel(channel_id)

        await interaction.response.send_message(
            "✅ Removed standup monitoring from this channel.", ephemeral=True
        )

    @discord.app_commands.command(
        name="ai_summary", description="Get AI-powered daily summary of messages"
    )
    @discord.app_commands.describe(
        date="Date to summarize (YYYY-MM-DD format, default: today)",
        channel="Channel to summarize (default: current channel)",
    )
    async def ai_summary(
        self,
        interaction: discord.Interaction,
        date: str = None,
        channel: discord.TextChannel = None,
    ):
        """Generate an AI-powered daily summary of messages from a standup channel."""
        await interaction.response.defer()  # This might take a while

        target_channel = channel or interaction.channel
        standup_channels = self.get_standup_channels(interaction.guild_id)

        if target_channel.id not in standup_channels:
            await interaction.followup.send(
                f"{target_channel.mention} is not set as a standup channel. Use `/set_standup_channel` first.",
                ephemeral=True,
            )
            return

        # Parse date
        if date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
                target_date = date
            except ValueError:
                await interaction.followup.send(
                    "Invalid date format. Use YYYY-MM-DD format.", ephemeral=True
                )
                return

        # Get messages for the date and channel
        messages = self.get_messages_for_date(target_channel.id, target_date)

        if not messages:
            await interaction.followup.send(
                f"No messages found for {target_date} in {target_channel.mention}",
                ephemeral=True,
            )
            return

        # Generate AI summary
        summary = await self.generate_ai_summary(messages, target_date, target_channel.name)

        # Create embed
        embed = discord.Embed(
            title="🤖 AI-Powered Daily Summary",
            description=f"**Date:** {target_date}\n**Channel:** {target_channel.mention}\n**Messages Analyzed:** {len(messages)}",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        # Split summary if it's too long for Discord
        if len(summary) > 1024:
            # Split into chunks
            chunks = [summary[i : i + 1020] for i in range(0, len(summary), 1020)]
            for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks
                embed.add_field(
                    name=f"Summary {i + 1}" if len(chunks) > 1 else "Summary",
                    value=chunk + ("..." if i < len(chunks) - 1 else ""),
                    inline=False,
                )
        else:
            embed.add_field(name="Summary", value=summary, inline=False)

        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(
        name="list_standup_channels", description="List all configured standup channels"
    )
    async def list_standup_channels(self, interaction: discord.Interaction):
        """List all channels configured for standup monitoring."""
        standup_channels = self.get_standup_channels(interaction.guild_id)

        if not standup_channels:
            await interaction.response.send_message(
                "No standup channels configured. Use `/set_standup_channel` to add one.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📋 Standup Channels",
            description="Channels currently being monitored:",
            color=discord.Color.blue(),
        )

        channel_list = []
        today = datetime.now().strftime("%Y-%m-%d")

        for channel_id in standup_channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                # Get message count for today
                messages = self.get_messages_for_date(channel_id, today)
                msg_count = len(messages)
                channel_list.append(f"• {channel.mention} ({msg_count} messages today)")
            else:
                channel_list.append(f"• Unknown channel (ID: {channel_id})")

        embed.add_field(name="Monitored Channels:", value="\n".join(channel_list), inline=False)

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Track messages in standup channels."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Only track messages in standup channels
        standup_channels = self.get_standup_channels(message.guild.id)
        if message.channel.id not in standup_channels:
            return

        # Store message in database
        self.store_message(message)


async def setup(bot):
    await bot.add_cog(MessageTrackerCog(bot))
