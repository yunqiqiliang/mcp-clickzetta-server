import importlib.metadata
import json
import logging
import os
import time
import uuid
from functools import wraps
from typing import Any, Callable

import mcp.server.stdio
import mcp.types as types
import yaml
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl, BaseModel
from clickzetta.zettapark.session import Session
import clickzetta.zettapark.types as T

from .write_detector import SQLWriteDetector
from .util import read_data_to_dataframe, generate_df_schema, get_embedding_xin

import dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp_clickzetta_server")



# Define available prompts
PROMPTS = {
    "create_table_with_prompt": types.Prompt(
        name="create_table_with_prompt",
        description="Create a new table by prompting the user for table name, columns, and their types.",
        arguments=[
            types.PromptArgument(
                name="table_name",
                description="The name of the table to create.",
                required=True
            ),
            types.PromptArgument(
                name="columns",
                description="The columns and their types in the format 'column1:type1,column2:type2' (e.g., 'id:INTEGER,name:STRING').",
                required=True
            ),
        ],
    ),
}


def data_to_yaml(data: Any) -> str:
    return yaml.dump(data, indent=2, sort_keys=False)


class ClickzettaDB:
    AUTH_EXPIRATION_TIME = 1800

    def __init__(self, connection_config: dict):
        self.connection_config = connection_config
        self.session = None
        self.insights: list[str] = []
        self.auth_time = 0
        self.connection_config["hints"] = {
            "sdk.job.timeout": 300,
            "query_tag": "Query from MCP Server",
            "cz.storage.parquet.vector.index.read.memory.cache": "true",
            "cz.storage.parquet.vector.index.read.local.cache": "false",
            "cz.sql.table.scan.push.down.filter": "true",
            "cz.sql.table.scan.enable.ensure.filter": "true",
            "cz.storage.always.prefetch.internal": "true",
            "cz.optimizer.generate.columns.always.valid": "true",
            "cz.sql.index.prewhere.enabled": "true",
            "cz.storage.parquet.enable.io.prefetch": "false"
        }

    def _init_database(self):
        """Initialize connection to the Clickzetta database"""
        try:
            # logger.info(f"self.connection_config: {self.connection_config}")
            self.session = Session.builder.configs(self.connection_config).create()
            for component in [ "schema"]:
                self.session.sql(f"USE {component.upper()} {self.connection_config[component].upper()}")
            self.auth_time = time.time()
        except Exception as e:
            raise ValueError(f"Failed to connect to Clickzetta workspace/database: {e}")

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries"""
        if not self.session or time.time() - self.auth_time > self.AUTH_EXPIRATION_TIME:
            self._init_database()

        logger.debug(f"Executing query: {query}")
        try:
            result = self.session.sql(query).to_pandas()
            result_rows = result.to_dict(orient="records")
            data_id = str(uuid.uuid4())

            return result_rows, data_id

        except Exception as e:
            logger.error(f'Database error executing "{query}": {e}')
            raise

    def add_insight(self, insight: str) -> None:
        """Add a new insight to the collection"""
        self.insights.append(insight)

    def get_memo(self) -> str:
        """Generate a formatted memo from collected insights"""
        if not self.insights:
            return "No data insights have been discovered yet."

        memo = "📊 Data Intelligence Memo 📊\n\n"
        memo += "Key Insights Discovered:\n\n"
        memo += "\n".join(f"- {insight}" for insight in self.insights)

        if len(self.insights) > 1:
            memo += f"\n\nSummary:\nAnalysis has revealed {len(self.insights)} key data insights that suggest opportunities for strategic optimization and growth."

        return memo


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator to standardize tool error handling"""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> list[types.TextContent]:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    return wrapper


class Tool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[str, dict[str, Any] | None], list[types.TextContent | types.ImageContent | types.EmbeddedResource]]
    tags: list[str] = []


# Tool handlers
async def handle_list_tables(arguments, db, *_):
    query = f"""
        SELECT table_catalog, table_schema, table_name, comment 
        FROM {db.connection_config['workspace']}.information_schema.tables 
        WHERE table_schema = '{db.connection_config['schema'].upper()}'
    """
    data, data_id = db.execute_query(query)

    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]


async def handle_describe_table(arguments, db, *_):
    if not arguments or "table_name" not in arguments:
        raise ValueError("Missing table_name argument")

    split_identifier = arguments["table_name"].split(".")
    table_name = split_identifier[-1].upper()
    schema_name = (split_identifier[-2] if len(split_identifier) > 1 else db.connection_config["schema"]).upper()
    workspace_name = (split_identifier[-3] if len(split_identifier) > 2 else db.connection_config["table_catalog"]).upper()

    query = f"""
        SELECT column_name, column_default, is_nullable, data_type, comment 
        FROM {workspace_name}.information_schema.columns 
        WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
    """
    data, data_id = db.execute_query(query)

    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]

async def handle_show_object_list(arguments, db, *_):
    if not arguments or "object_type" not in arguments:
        raise ValueError("Missing object_type argument")
    object_type = arguments["object_type"]
    query = f"""
       SHOW {object_type};
    """
    data, data_id = db.execute_query(query)

    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]

async def handle_desc_object(arguments, db, *_):
    if not arguments or "object_type" not in arguments or "object_name" not in arguments:
        raise ValueError("Missing object_type argument")
    object_type = arguments["object_type"]
    object_name = arguments["object_name"]
    query = f"""
       desc {object_type} extended {object_name};
    """
    data, data_id = db.execute_query(query)

    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]

async def handle_vector_search(arguments, db, *_):
    if not arguments or "question" not in arguments:
        raise ValueError("Missing object_type argument")
    dotenv.load_dotenv()
    if "table_name" not in arguments:
        table_name = os.getenv("Similar_table_name")
    elif "table_name" in arguments:
        table_name = arguments["table_name"]
    if "embedding_column_name" not in arguments:
        embedding_column_name = os.getenv("Similar_embedding_column_name")
    elif "embedding_column_name" in arguments:
        embedding_column_name = arguments["embedding_column_name"]
    if "content_column_name" not in arguments:
        content_column_name = os.getenv("Similar_content_column_name")
    elif "content_column_name" in arguments:
        content_column_name = arguments["content_column_name"]
    if "partition_scope" not in arguments:
        partition_scope = os.getenv("Similar_partition_scope")
    elif "partition_scope" in arguments:
        partition_scope = arguments["partition_scope"]
    
    question = arguments["question"]
    embedded_question = get_embedding_xin(question)
    query = f"""
        SELECT {content_column_name},L2_DISTANCE({embedding_column_name}, CAST({embedded_question} as VECTOR(512))) AS distance, "vector_search_l2" as search_method
        FROM {table_name}
        WHERE {partition_scope}
        ORDER BY 2
        LIMIT 5;
        """
    data, data_id = db.execute_query(query)

    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]

async def handle_match_all(arguments, db, *_):
    if not arguments or "question" not in arguments:
        raise ValueError("Missing object_type argument")
    dotenv.load_dotenv()
    if "table_name" not in arguments:
        table_name = os.getenv("Similar_table_name")
    elif "table_name" in arguments:
        table_name = arguments["table_name"]
    if "content_column_name" not in arguments:
        content_column_name = os.getenv("Similar_content_column_name")
    elif "content_column_name" in arguments:
        content_column_name = arguments["content_column_name"]
    if "partition_scope" not in arguments:
        partition_scope = os.getenv("Similar_partition_scope")
    elif "partition_scope" in arguments:
        partition_scope = arguments["partition_scope"]
    question = arguments["question"]
    query = f"""
        SELECT  {content_column_name}, 0 AS distance, "match_all_search" as search_method
        FROM {table_name}
        WHERE {partition_scope} and (MATCH_ALL({content_column_name}, '{question}' ))
        ORDER BY 2
        LIMIT 5;
        """
    data, data_id = db.execute_query(query)

    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]

async def handle_import_data_into_table_from_url(arguments, db, *_):
    if not arguments or "from_url" not in arguments or "dest_table" not in arguments:
        raise ValueError("Missing object_type argument")
    from_url = arguments["from_url"]
    dest_table = arguments["dest_table"]
    df_loaded = read_data_to_dataframe(from_url)
    df_schema = generate_df_schema(df_loaded)
    
    query = f"""
       drop table if exists {dest_table};
    """
    data, data_id = db.execute_query(query)
    try:
        zetta_df = db.session.create_dataframe(df_loaded, schema=df_schema)
        zetta_df.write.mode("overwrite").save_as_table(dest_table)
    except Exception as save_error:
        print(f"Error load data to table {dest_table}: {save_error}")

    # query = f"""
    #    desc table extended {dest_table};
    # """
    # data, data_id = db.execute_query(query)
    data = [
        {"Result": "Successfully imported data into table", "Table": dest_table},
    ]
    data_id = str(uuid.uuid4())
    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]


async def handle_read_query(arguments, db, write_detector, *_):
    if write_detector.analyze_query(arguments["query"])["contains_write"]:
        raise ValueError("Calls to read_query should not contain write operations")
    data, data_id = db.execute_query(arguments["query"])
    output = {
        "type": "data",
        "data_id": data_id,
        "data": data,
    }
    yaml_output = data_to_yaml(output)
    json_output = json.dumps(output)
    return [
        types.TextContent(type="text", text=yaml_output),
        types.EmbeddedResource(
            type="resource",
            resource=types.TextResourceContents(uri=f"data://{data_id}", text=json_output, mimeType="application/json"),
        ),
    ]


async def handle_append_insight(arguments, db, _, __, server):
    if not arguments or "insight" not in arguments:
        raise ValueError("Missing insight argument")

    db.add_insight(arguments["insight"])
    await server.request_context.session.send_resource_updated(AnyUrl("memo://insights"))
    return [types.TextContent(type="text", text="Insight added to memo")]


async def handle_write_query(arguments, db, _, allow_write, __):
    if not allow_write:
        raise ValueError("Write operations are not allowed for this data connection")
    if arguments["query"].strip().upper().startswith("SELECT"):
        raise ValueError("SELECT queries are not allowed for write_query")

    results, data_id = db.execute_query(arguments["query"])
    return [types.TextContent(type="text", text=str(results))]


async def handle_create_table(arguments, db, _, allow_write, __):
    if not allow_write:
        raise ValueError("Write operations are not allowed for this data connection")
    if not arguments["query"].strip().upper().startswith("CREATE TABLE"):
        raise ValueError("Only CREATE TABLE statements are allowed")

    results, data_id = db.execute_query(arguments["query"])
    return [types.TextContent(type="text", text=f"Table created successfully. data_id = {data_id}")]

async def handle_create_table_with_prompt(arguments, db, _, allow_write, __):
    if not allow_write:
        raise ValueError("Write operations are not allowed for this data connection")
    if not arguments["query"].strip().upper().startswith("CREATE TABLE"):
        raise ValueError("Only CREATE TABLE statements are allowed")
    # 检查用户输入的参数
    if not arguments or "table_name" not in arguments or "columns" not in arguments:
        raise ValueError("Missing required arguments: 'table_name' or 'columns'")

    table_name = arguments["table_name"]
    columns_input = arguments["columns"]

    # 解析列定义
    try:
        columns = ", ".join(
            [f"{col.split(':')[0]} {col.split(':')[1]}" for col in columns_input.split(",")]
        )
    except IndexError:
        raise ValueError("Invalid columns format. Use 'column1:type1,column2:type2'.")

    # 构造 CREATE TABLE 语句
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns});"

    # 执行建表语句
    results, data_id = db.execute_query(query)

    # 返回结果
    return [
        types.TextContent(type="text", text=f"Table '{table_name}' created successfully. data_id = {data_id}")
    ]

async def prefetch_tables(db: ClickzettaDB, credentials: dict) -> dict:
    """Prefetch table and column information"""
    try:
        logger.info("Prefetching table descriptions")
        table_results, data_id = db.execute_query(
            f"""SELECT table_name, comment 
                FROM {credentials['workspace']}.information_schema.tables 
                WHERE table_schema = '{credentials['schema'].upper()}'"""
        )

        column_results, data_id = db.execute_query(
            f"""SELECT table_name, column_name, data_type, comment 
                FROM {credentials['workspace']}.information_schema.columns 
                WHERE table_schema = '{credentials['schema'].upper()}'"""
        )

        tables_brief = {}
        for row in table_results:
            tables_brief[row["TABLE_NAME"]] = {**row, "COLUMNS": {}}

        for row in column_results:
            row_without_table_name = row.copy()
            del row_without_table_name["TABLE_NAME"]
            tables_brief[row["TABLE_NAME"]]["COLUMNS"][row["COLUMN_NAME"]] = row_without_table_name

        return tables_brief

    except Exception as e:
        logger.error(f"Error prefetching table descriptions: {e}")
        return f"Error prefetching table descriptions: {e}"


async def main(
    allow_write: bool = False,
    connection_args: dict = None,
    log_dir: str = None,
    prefetch: bool = False,
    log_level: str = "INFO",
    exclude_tools: list[str] = [],
):
    # Setup logging
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        logger.handlers.append(logging.FileHandler(os.path.join(log_dir, "mcp_clickzetta_server.log")))
    if log_level:
        logger.setLevel(log_level)

    logger.info("Starting Clickzetta MCP Server")
    logger.info("Allow write operations: %s", allow_write)
    logger.info("Prefetch table descriptions: %s", prefetch)
    logger.info("Excluded tools: %s", exclude_tools)

    db = ClickzettaDB(connection_args)
    server = Server("clickzetta-manager")
    write_detector = SQLWriteDetector()

    tables_info = (await prefetch_tables(db, connection_args)) if prefetch else {}
    tables_brief = data_to_yaml(tables_info) if prefetch else ""

    all_tools = [
        Tool(
            name="list_tables",
            description="List all tables in the Clickzetta workspace/database",
            input_schema={
                "type": "object",
                "properties": {},
            },
            handler=handle_list_tables,
            tags=["description"],
        ),
        Tool(
            name="describe_table",
            description="Get the schema information for a specific table",
            input_schema={
                "type": "object",
                "properties": {"table_name": {"type": "string", "description": "Name of the table to describe"}},
                "required": ["table_name"],
            },
            handler=handle_describe_table,
            tags=["description"],
        ),
        Tool(
            name="show_object_list",
            description="Get the list of specific object type in current workspace, supported objects list such as catalogs,vclusters, connections,volumes,schemas,tables,tables history, table streams,users,jobs,functions, etc.",
            input_schema={
                "type": "object",
                "properties": {"object_type": {"type": "string", "description": "Type of the object to show"}},
                "required": ["object_type"],
            },
            handler=handle_show_object_list,
            tags=["show"],
        ),
        Tool(
            name="desc_object",
            description="Get the information of specific object, supported object type such as catalog,vcluster, connection,volume,schema,table, table stream,view, history, share, job, etc.",
            input_schema={
                "type": "object",
                "properties": {"object_type": {"type": "string", "description": "Type of the object to desc"},"object_name": {"type": "string", "description": "Name of the object to desc"}},
                "required": ["object_type", "object_name"],
            },
            handler=handle_desc_object,
            tags=["description"],
        ),
        Tool(
            name="import_data_into_table_from_url",
            description="From url(include file path or https/http url) import data into table, if dest_table not exists, handler will auto create table before data import.",
            input_schema={
                "type": "object",
                "properties": {"from_url": {"type": "string", "description": "data source url"},"dest_table": {"type": "string", "description": "Table tobe imported"}},
                "required": ["from_url", "dest_table"],
            },
            handler=handle_import_data_into_table_from_url,
            tags=["import-data"],
        ),
        Tool(
            name="vector_search",
            description="Perform vector search on a table using a question and return the top 5 closest answers",
            input_schema={
                "type": "object",
                "properties": {"table_name": {"type": "string", "description": "table name"},"content_column_name": {"type": "string", "description": "column which stored content"},"embedding_column_name": {"type": "string", "description": "column which stored embedding"},"partition_scope": {"type": "string", "description": "sql code to define the partiion scope as part of where condition"} },
                "required": ["question"],
            },
            handler=handle_vector_search,
            tags=["query"],
        ),
        Tool(
            name="match_all",
            description="Perform search via match all function on a table using a question and return the top 5 answers",
            input_schema={
                "type": "object",
                "properties": {"table_name": {"type": "string", "description": "table name"},"content_column_name": {"type": "string", "description": "column which stored content"},"question": {"type": "string", "description": "question to search"},"partition_scope": {"type": "string", "description": "sql code to define the partiion scope as part of where condition"}},
                "required": ["question"],
            },
            handler=handle_match_all,
            tags=["query"],
        ),
        Tool(
            name="read_query",
            description="Execute a SELECT query.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SELECT SQL query to execute"}},
                "required": ["query"],
            },
            handler=handle_read_query,
        ),
        Tool(
            name="append_insight",
            description="Add a data insight to the memo",
            input_schema={
                "type": "object",
                "properties": {"insight": {"type": "string", "description": "Data insight discovered from analysis"}},
                "required": ["insight"],
            },
            handler=handle_append_insight,
            tags=["resource_based"],
        ),
        Tool(
            name="write_query",
            description="Execute an INSERT, UPDATE, or DELETE query on the Clickzetta workspace/database",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
                "required": ["query"],
            },
            handler=handle_write_query,
            tags=["write"],
        ),
        Tool(
            name="create_table",
            description="Create a new table in the Clickzetta workspace/database",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "CREATE TABLE SQL statement"}},
                "required": ["query"],
            },
            handler=handle_create_table,
            tags=["create"],
        ),
        Tool(
            name="create_table_with_prompt",
            description="Create a new table by prompting the user for table name, columns, and their types.",
            input_schema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "The name of the table to create."
                    },
                    "columns": {
                        "type": "string",
                        "description": "The columns and their types in the format 'column1:type1,column2:type2' (e.g., 'id:INT,name:VARCHAR(255)')."
                    },
                },
                "required": ["table_name", "columns"],
            },
            handler=handle_create_table_with_prompt,
            tags=["create"],
        )
    ]

    exclude_tags = []
    if not allow_write:
        exclude_tags.append("write")
    if prefetch:
        exclude_tags.append("description")
    allowed_tools = [
        tool for tool in all_tools if tool.name not in exclude_tools and not any(tag in exclude_tags for tag in tool.tags)
    ]

    logger.info("Allowed tools: %s", [tool.name for tool in allowed_tools])

    # Register handlers
    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        resources = [
            types.Resource(
                uri=AnyUrl("memo://insights"),
                name="Data Insights Memo",
                description="A living document of discovered data insights",
                mimeType="text/plain",
            )
        ]
        table_brief_resources = [
            types.Resource(
                uri=AnyUrl(f"context://table/{table_name}"),
                name=f"{table_name} table",
                description=f"Description of the {table_name} table",
                mimeType="text/plain",
            )
            for table_name in tables_info.keys()
        ]
        resources += table_brief_resources
        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        if str(uri) == "memo://insights":
            return db.get_memo()
        elif str(uri).startswith("context://table"):
            table_name = str(uri).split("/")[-1]
            if table_name in tables_info:
                return data_to_yaml(tables_info[table_name])
            else:
                raise ValueError(f"Unknown table: {table_name}")
        else:
            raise ValueError(f"Unknown resource: {uri}")
    

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        return list(PROMPTS.values())

    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        if name not in PROMPTS:
            raise ValueError(f"Prompt not found: {name}")
        
        if name == "create_table_with_prompt":
            table_name = arguments.get("table_name") if arguments else ""
            columns = arguments.get("columns") if arguments else ""
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"Create a table named '{table_name}' with the following columns:\n\n{columns}"
                        )
                    )
                ]
            )

        raise ValueError("Prompt implementation not found")

    @server.call_tool()
    @handle_tool_errors
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name in exclude_tools:
            return [types.TextContent(type="text", text=f"Tool {name} is excluded from this data connection")]

        handler = next((tool.handler for tool in allowed_tools if tool.name == name), None)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(arguments, db, write_detector, allow_write, server)

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        logger.info("Listing tools")
        logger.error(f"Allowed tools: {allowed_tools}")
        tools = [
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema,
            )
            for tool in allowed_tools
        ]
        return tools

    # Start server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="clickzetta",
                server_version=importlib.metadata.version("mcp_clickzetta_server"),
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
