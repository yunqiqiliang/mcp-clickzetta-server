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

### Installing as local MCP Server(This way has been tested and verified on MacOS)

#### Clone this repository:

```bash
git clone https://github.com/yunqiqiliang/mcp-clickzetta-server.git
cd mcp-clickzetta-server
```

#### Install the package:

```bash
uv pip install -e .

#### Config credentials
Create a .env file based on .env.example with your Clickzetta Lakehouse credentials:
```
```json
CLICKZETTA_USERNAME = ""
CLICKZETTA_PASSWORD = ""
CLICKZETTA_SERVICE = "api.clickzetta.com"
CLICKZETTA_INSTANCE = ""
CLICKZETTA_WORKSPACE = ""
CLICKZETTA_SCHEMA = ""
CLICKZETTA_VCLUSTER = ""
```

##### Usage

##### Running with uv

After installing the package, you can run the server directly with:

```bash
uv run mcp_clickzetta_server
```

If this is the first time you are running the server, you could run the following command to acclerate the package installation:

```bash
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ uv run mcp-clickzetta-server
```

This will start the stdio-based MCP server, which can be connected to Claude Desktop or any MCP client that supports stdio communication.

You should see output similar to:

```bash

uv run mcp_clickzetta_server

2025-03-25 10:11:20,799 - mcp_clickzetta_server - INFO - Starting Clickzetta MCP Server
2025-03-25 10:11:20,799 - mcp_clickzetta_server - INFO - Allow write operations: False
2025-03-25 10:11:20,799 - mcp_clickzetta_server - INFO - Prefetch table descriptions: True
2025-03-25 10:11:20,799 - mcp_clickzetta_server - INFO - Excluded tools: []
2025-03-25 10:11:20,799 - mcp_clickzetta_server - INFO - Prefetching table descriptions
2025-03-25 10:11:21,726 - clickzetta.zettapark.session - INFO - Zettapark Session information: 
"version" : 0.1.3,
"python.version" : 3.12.2,
"python.connector.version" : 0.8.89.0,
"python.connector.session.id" : dd46bd27-920d-4760-94a6-6f994d31e63e,
"os.name" : Darwin

2025-03-25 10:11:21,728 - clickzetta.connector.v0.client - INFO - clickzetta connector submitting job,  id:2025032510112172821098301
2025-03-25 10:11:23,059 - clickzetta.connector.v0.client - INFO - clickzetta connector submitting job,  id:2025032510112305897947697
2025-03-25 10:11:23,728 - mcp_clickzetta_server - INFO - Allowed tools: ['read_query', 'append_insight']
2025-03-25 10:11:23,732 - mcp_clickzetta_server - INFO - Server running with stdio transport
```

##### Claude Desktop Integration
- In Claude Desktop, go to Settings → MCP Servers
- Add a new server with the full path to your uv executable:

```json
{
   "mcpServers": {
      "clickzetta-mcp-server" : {
         "command": "/Users/******/anaconda3/bin/uv",
         "args": [
            "--directory",
            "/Users/******/Documents/GitHub/mcp-clickzetta-server",
            "run",
            "mcp_clickzetta_server"
         ]
      }
   }
}
```

- You can find your uv path by running which uv in your terminal
- Save the server configuration

##### Example Queries

When using with Claude, you can ask questions like:

- "Can you list all the schemas in my Clickzetta account?"
- "List all views in the PUBLIC schema"
- "Describe the structure of the CUSTOMER_ANALYTICS view in the SALES schema"
- "Show me sample data from the REVENUE_BY_REGION view in the FINANCE schema"
- "Run this SQL query: SELECT customer_id, SUM(order_total) as total_spend FROM SALES.ORDERS GROUP BY customer_id ORDER BY total_spend DESC LIMIT 10"
- "Query the MARKETING database to find the top 5 performing campaigns by conversion rate"
- "帮我从Clickzetta中读取数据，分析下在public这个schema下github_users表里每个公司的用户数。请用中文返回结果，并对结果进行数据可视化展现"
- "帮我从Clickzetta中读取数据，分析下在public这个schema下github_event_issuesevent表里有多少条记录？"

##### Example Result

![alt text](result1_image.png)

#### Security Considerations
This server:

- Enforces read-only operations (only SELECT statements are allowed)
- Automatically adds LIMIT clauses to prevent large result sets
- Uses service account authentication for secure connections
- Validates inputs to prevent SQL injection
- ⚠️ Important: Keep your .env file secure and never commit it to version control. The .gitignore file is configured to exclude it.


### Installing via Smithery(This way is tobe tested and verified)

To install Clickzetta Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp_clickzetta_server):

```bash
npx -y @smithery/cli install mcp_clickzetta_server --client claude
```

### Installing via UVX(This way is tobe tested and verified)

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
          "the_instance",
          "--vcluster",
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


