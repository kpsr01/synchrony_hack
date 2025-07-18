# Slack Standup Bot

A lightweight, AI‑powered Slack (and Discord) stand-up bot to collect daily team updates, store them locally, and generate summarized reports via the Gemini API.

## <<<<<<< HEAD

## Features

- **Channel Monitoring:** Easily set up and manage stand-up channels with slash commands.
- **Message Storage:** Persist all stand-up messages in a local SQLite database (user, message, timestamp).
- **AI Summarization:** Generate concise summaries of the day's stand-up using the Gemini API.
- **Multi‑Platform:** Supports both Slack and Discord with a shared codebase.

---

## Prerequisites

- A Slack workspace (and/or a Discord server)
- Slack Bot Token & App Token (for Slack)
- Discord Bot Token (for Discord)
- Gemini API key

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/kpsr01/synchrony_hack.git
   cd synchrony_hack
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Inside the `Slack/` and `Discord/` directories, create a `.env` file with the following variables:

### Slack (`Slack/.env`)

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///standup.db
```

### 1. Launch the Bot

- **Slack**

  ```bash
  python3 Slack/slackbot.py
  ```

- **Discord**

  ```bash
  python3 Discord/main.py
  ```

### 2. Slash Commands (Slack)

| Command                            | Description                                       |
| ---------------------------------- | ------------------------------------------------- |
| `/set_standup_channel #channel`    | Start tracking messages in the specified channel. |
| `/list_standup_channels`           | List all configured stand-up channels.            |
| `/remove_standup_channel #channel` | Stop tracking the specified channel.              |
| `/ai_summary [#channel]`           | Generate and post a summary of today's stand-ups. |

> **Tip:** If no channel is provided to `/ai_summary`, it summarizes all active stand-up channels.

### 3. Slash Commands (Discord)

| Command                            | Description                                       |
| ---------------------------------- | ------------------------------------------------- |
| `!set_standup_channel #channel`    | Start tracking messages in the specified channel. |
| `!list_standup_channels`           | List all configured stand-up channels.            |
| `!remove_standup_channel #channel` | Stop tracking the specified channel.              |
| `!ai_summary [#channel]`           | Generate and post a summary of today's stand-ups. |

---

## Database Schema

| Table      | Columns                                                         |
| ---------- | --------------------------------------------------------------- |
| `channels` | `id` (PK), `platform` (slack/discord), `channel_id`             |
| `standups` | `id` (PK), `user_id`, `channel_id` (FK), `message`, `timestamp` |
