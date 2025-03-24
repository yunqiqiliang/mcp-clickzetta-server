# Clickzetta MCP Server

[![smithery badge](https://smithery.ai/badge/mcp_clickzetta_server)](https://smithery.ai/server/mcp_clickzetta_server) [![PyPI - Version](https://img.shields.io/pypi/dm/mcp-clickzetta-server?color&logo=pypi&logoColor=white&label=PyPI%20downloads)](https://pypi.org/project/mcp-clickzetta-server/)


## Overview
A Model Context Protocol (MCP) server implementation that provides database interaction with Clickzetta. This server enables running SQL queries with tools and intereacting with a memo of data insights presented as a resource.

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

To install Clickzetta Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp_clickzetta_server):

```bash
npx -y @smithery/cli install mcp_clickzetta_server --client claude
```

### Installing via UVX

```python
# Add the server to your claude_desktop_config.json
"mcpServers": {
  "clickzetta_pip": {
      "command": "uvx",
      "args": [
          "mcp_clickzetta_server",
          "--service",
          "the_service",
          "--instance",
          "the_vcluster",
          "--instance",
          "the_vcluster",
          "--workspace",
          "the_workspace",
           "--schema",
          "the_schema",
          "--user",
          "the_user",
          "--password",
          "their_password",
          # Optionally: "--allow_write" (but not recommended)
          # Optionally: "--log_dir", "/absolute/path/to/logs"
          # Optionally: "--log_level", "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
          # Optionally: "--exclude_tools", "{tool name}", ["{other tool name}"]
      ]
  }
}
```

### Installing locally
```python
# Add the server to your claude_desktop_config.json
"mcpServers": {
  "clickzetta_local": {
      "command": "uv",
      "args": [
          "--directory",
          "/absolute/path/to/mcp_clickzetta_server",
          "run",
          "mcp_clickzetta_server",
          "mcp_clickzetta_server",
          "--service",
          "the_service",
          "--instance",
          "the_vcluster",
          "--instance",
          "the_vcluster",
          "--workspace",
          "the_workspace",
           "--schema",
          "the_schema",
          "--user",
          "the_user",
          "--password",
          "their_password",
          # Optionally: "--allow_write" (but not recommended)
          # Optionally: "--log_dir", "/absolute/path/to/logs"
          # Optionally: "--log_level", "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
          # Optionally: "--exclude_tools", "{tool name}", ["{other tool name}"]
      ]
  }
}
```
