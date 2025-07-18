import argparse
import asyncio
import logging
import os
import sys
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class StandupBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=["standup ", "Standup ", "STANDUP "],
            case_insensitive=True,
            strip_after_prefix=True,
            help_command=None,
            intents=intents,
        )

    async def setup_hook(self) -> None:
        print("Connected to bot: Standup Bot")
        print(f"Bot ID: {self.user.id}")

        # Load cogs
        cogs_dir = "cogs"
        if os.path.exists(cogs_dir):
            for cog_file in os.listdir(cogs_dir):
                if cog_file.endswith(".py") and not cog_file.startswith("__"):
                    cog_name = cog_file[:-3]
                    try:
                        cog_path = f"{cogs_dir}.{cog_name}"
                        await self.load_extension(cog_path)
                        print(f"Loaded cog: {cog_name}")
                    except Exception as e:
                        print(f"Error loading cog {cog_name}: {e}")
                        traceback.print_exc()

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

        self.boot_time = discord.utils.utcnow()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Standup Discord Bot")
    parser.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    log_level = getattr(logging, args.log_level.upper())

    # Simple logging setup
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("bot.log"), logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("bot")

    bot = StandupBot()
    token = os.getenv("TOKEN")

    if not token:
        logger.critical("Bot token is missing. Please set the TOKEN environment variable.")
        sys.exit(1)

    try:
        asyncio.run(bot.run(token))
    except KeyboardInterrupt:
        print("Bot shutting down...")
    except Exception:
        logger.exception("Exception during bot startup:")
    finally:
        print("Bot stopped.")


if __name__ == "__main__":
    main()
