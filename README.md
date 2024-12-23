# Snowflake MCP Server

[![smithery badge](https://smithery.ai/badge/mcp_snowflake_server)](https://smithery.ai/server/mcp_snowflake_server)

## Overview
A Model Context Protocol (MCP) server implementation that provides database interaction with Snowflake. This server enables running SQL queries with tools and intereacting with a memo of data insights presented as a resource.

## Components

### Resources
The server exposes a single dynamic resource:
- `memo://insights`: A continuously updated data insights memo that aggregates discovered insights during analysis
  - Auto-updates as new insights are discovered via the append-insight tool

### Tools
The server offers six core tools:

#### Query Tools
- `read_query`
   - Execute SELECT queries to read data from the database
   - Input:
     - `query` (string): The SELECT SQL query to execute
   - Returns: Query results as array of objects

- `write_query` (with `--allow-write` flag)
   - Execute INSERT, UPDATE, or DELETE queries
   - Input:
     - `query` (string): The SQL modification query
   - Returns: `{ affected_rows: number }`

- `create_table` (with `--allow-write` flag)
   - Create new tables in the database
   - Input:
     - `query` (string): CREATE TABLE SQL statement
   - Returns: Confirmation of table creation

#### Schema Tools
- `list_tables`
   - Get a list of all tables in the database
   - No input required
   - Returns: Array of table names

- `describe-table`
   - View column information for a specific table
   - Input:
     - `table_name` (string): Name of table to describe (can be fully qualified)
   - Returns: Array of column definitions with names and types

#### Analysis Tools
- `append_insight`
   - Add new data insights to the memo resource
   - Input:
     - `insight` (string): data insight discovered from analysis
   - Returns: Confirmation of insight addition
   - Triggers update of memo://insights resource


## Usage with Claude Desktop

### Installing via Smithery

To install Snowflake Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp_snowflake_server):

```bash
npx -y @smithery/cli install mcp_snowflake_server --client claude
```

This server can be run without cloning or installing the repository.

```python
# Add the server to your claude_desktop_config.json
"mcpServers": {
  "snowflake": {
      "command": "uvx",
      "args": [
          "mcp_snowflake_server"
          # Optionally: "--allow-write" (but not recommended)
      ],
      "env": {
          "SNOWFLAKE_WAREHOUSE": "your_warehouse",
          "SNOWFLAKE_DATABASE": "your_database",
          "SNOWFLAKE_ACCOUNT": "your_account_identifier",
          "SNOWFLAKE_USER": "your_username",
          "SNOWFLAKE_ROLE": "your_role",
          "SNOWFLAKE_SCHEMA": "your_schema",
          "SNOWFLAKE_PASSWORD": "your_password"
      }
  }
}
```
