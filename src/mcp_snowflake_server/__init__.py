from . import server
import asyncio
import argparse


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="Snowflake MCP Server")
    parser.add_argument("--allow-write", default=False, action="store_true", help="Allow write operations on the database")

    args = parser.parse_args()
    asyncio.run(server.main(allow_write=args.allow_write))


# Optionally expose other important items at package level
__all__ = ["main", "server"]
