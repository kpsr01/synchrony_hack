import argparse
import asyncio
import logging
import os
import pathlib
import sys
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv
import Me.logging
from core.tree import MeTree

load_dotenv()


class StandupBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # TODO: change prefixx
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

        # Set up command tree
        self.tree = MeTree(self)

        # Load core modules
        core_dir = "core"
        if os.path.exists(core_dir):
            for module_file in os.listdir(core_dir):
                if module_file.endswith(".py") and not module_file.startswith("__"):
                    module_name = module_file[:-3]
                    try:
                        module_path = f"{core_dir}.{module_name}"
                        await self.load_extension(module_path)
                        print(f"Loaded core module: {module_name}")
                    except Exception as e:
                        print(f"Error loading core module {module_name}: {e}")
                        traceback.print_exc()

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
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "VERBOSE",
            "TRACE",
        ],
        help="Set the logging level",
    )
    parser.add_argument(
        "--rich-logging",
        dest="rich_logging",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable rich logging (requires terminal)",
    )
    parser.add_argument(
        "--rich-traceback-extra-lines",
        dest="rich_traceback_extra_lines",
        type=int,
        default=3,
        help="Extra lines to show in rich tracebacks",
    )
    parser.add_argument(
        "--rich-traceback-show-locals",
        dest="rich_traceback_show_locals",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Show locals in rich tracebacks",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    log_level_str = args.log_level.upper()
    log_level = getattr(logging, log_level_str)
    log_location = pathlib.Path("./logs")

    Me.logging.init_logging(log_level, log_location, args)
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
