from . import server
import asyncio
import argparse
import dotenv
import os


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="Snowflake MCP Server")
    parser.add_argument(
        "--allow_write", required=False, default=False, action="store_true", help="Allow write operations on the database"
    )
    parser.add_argument("--log_dir", required=False, default=None, help="Directory to log to")
    parser.add_argument("--log_level", required=False, default="INFO", help="Logging level")
    parser.add_argument(
        "--prefetch",
        required=False,
        default=True,
        action="store_true",
        help="Prefetch table descriptions (when enabled, list_tables and describe_table are disabled)",
    )
    parser.add_argument(
        "--exclude_tools",
        required=False,
        default=[],
        nargs="+",
        help="List of tools to exclude",
    )

    dotenv.load_dotenv()

    required = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
    }

    parser.add_argument("--account", required=not required["account"], default=required["account"])
    parser.add_argument("--password", required=not required["password"], default=required["password"])
    parser.add_argument("--database", required=not required["database"], default=required["database"])
    parser.add_argument("--user", required=not required["user"], default=required["user"])
    parser.add_argument("--schema", required=not required["schema"], default=required["schema"])
    parser.add_argument("--warehouse", required=not required["warehouse"], default=required["warehouse"])
    parser.add_argument("--role", required=not required["role"], default=required["role"])

    args = parser.parse_args()
    credentials = {
        "account": args.account,
        "password": args.password,
        "database": args.database,
        "user": args.user,
        "schema": args.schema,
        "warehouse": args.warehouse,
        "role": args.role,
    }
    asyncio.run(
        server.main(
            allow_write=args.allow_write,
            credentials=credentials,
            log_dir=args.log_dir,
            prefetch=args.prefetch,
            log_level=args.log_level,
            exclude_tools=args.exclude_tools,
        )
    )


# Optionally expose other important items at package level
__all__ = ["main", "server", "write_detector"]

if __name__ == "__main__":
    main()
