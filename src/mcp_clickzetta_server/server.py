import datetime
import importlib.metadata
import json
import logging
import os
import time
import uuid
from functools import wraps
from typing import Any, Callable
import decimal
import pandas as pd


import mcp.server.stdio
import mcp.types as types
import yaml
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl, BaseModel
from clickzetta.zettapark.session import Session
import clickzetta.zettapark.types as T

from .write_detector import SQLWriteDetector
from .util import read_data_from_url_or_file_into_dataframe, generate_df_schema, get_embedding_hf,connect_to_database_and_read_data_from_table_into_dataframe
from .prompts import PROMPTS
from .knowledges import KNOWLEDGES
from .samples import SAMPLES

import dotenv
dotenv.load_dotenv()

# 加载 samples 数据
samples_sql = SAMPLES

table_name = os.getenv("Similar_table_name")
embedding_column_name = os.getenv("Similar_embedding_column_name")
content_column_name = os.getenv("Similar_content_column_name")
other_columns_name = os.getenv("Similar_other_columns_name")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp_clickzetta_server")

def convert_df_to_dict(data: pd.DataFrame) -> list[dict[str, Any]]:
    # Convert Timestamp, date, and Decimal objects to strings for JSON serialization compatibility
    # Convert the data to a pandas DataFrame for efficient processing
    df = pd.DataFrame(data)

    # Apply type-specific transformations
    df = df.applymap(
        lambda value: value.isoformat() if isinstance(value, (datetime.datetime, datetime.date))
        else str(value) if isinstance(value, (decimal.Decimal, float))
        else value
    )

    # Convert the DataFrame back to a list of dictionaries
    data = df.to_dict(orient="records")

    return data

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
        WHERE table_catalog = '{db.connection_config['workspace'].lower()}' AND table_schema = '{db.connection_config['schema'].lower()}'
    """
    data, data_id = db.execute_query(query)

    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)

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

    table_name = arguments["table_name"]
   
    query = f"""
        DESC TABLE EXTENDED {table_name};
    """
    data, data_id = db.execute_query(query)

    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)

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

    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)

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

    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)

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
    else:
        table_name = arguments["table_name"]
    if "embedding_column_name" not in arguments:
        embedding_column_name = os.getenv("Similar_embedding_column_name")
    else:
        embedding_column_name = arguments["embedding_column_name"]
    if "content_column_name" not in arguments:
        content_column_name = os.getenv("Similar_content_column_name")
    else:
        content_column_name = arguments["content_column_name"]
    if "partition_scope" not in arguments:
        partition_scope = os.getenv("Similar_partition_scope")
    else:
        partition_scope = arguments["partition_scope"]
    
    question = arguments["question"]
    embedded_question = get_embedding_hf(question)
    embedding_list = embedded_question.tolist()
    query = f"""
        SELECT {content_column_name},L2_DISTANCE({embedding_column_name}, CAST("{embedding_list}" as VECTOR(768))) AS distance, "vector_search_l2" as search_method,{other_columns_name},CONCAT('https://yunqi.tech/documents', CASE WHEN SUBSTRING_INDEX(SUBSTRING_INDEX(file_directory, 's3/', -1), '/', 1) <> '' THEN CONCAT('/', SUBSTRING_INDEX(SUBSTRING_INDEX(file_directory, 's3/', -1), '/', 1)) ELSE '' END, '/', LEFT(filename, LENGTH(filename) - LENGTH(SUBSTRING_INDEX(filename, '.', -1)) - 1)) AS doc_link
        FROM {table_name}
        WHERE L2_DISTANCE({embedding_column_name}, CAST("{embedding_list}" as VECTOR(768))) < 0.8
        ORDER BY 2
        LIMIT 10;
        """
    data, data_id = db.execute_query(query)

    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)

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

    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)

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
    df_loaded = read_data_from_url_or_file_into_dataframe(from_url)
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


async def handle_import_data_into_table_from_database(arguments, db, *_):
    """
    Handle importing data from a database table into another table in the workspace.

    Args:
        arguments (dict): A dictionary containing the connection parameters and table details.
        db: The database object for executing queries.
    """
    # Supported database types and their required parameters
    db_type_required_params = {
        "mysql": ["host", "port", "database", "username", "password", "source_table", "dest_table"],
        "postgresql": ["host", "port", "database", "username", "password", "source_table", "dest_table"],
        "sqlite": ["database", "source_table", "dest_table"],  # SQLite only requires the database file path
        "mssql": ["host", "port", "database", "username", "password", "source_table", "dest_table"],
        "oracle": ["host", "port", "database", "username", "password", "source_table", "dest_table"]
    }

    # Validate db_type
    if "db_type" not in arguments:
        raise ValueError("Missing required argument: 'db_type'")
    db_type = arguments["db_type"]
    if db_type not in db_type_required_params:
        raise ValueError(f"Unsupported database type '{db_type}'. Supported types are: {', '.join(db_type_required_params.keys())}")

    # Validate required arguments for the given db_type
    required_args = db_type_required_params[db_type]
    missing_args = [arg for arg in required_args if arg not in arguments]
    if missing_args:
        raise ValueError(f"Missing required arguments for database type '{db_type}': {', '.join(missing_args)}")

    # Extract connection parameters and table details based on db_type
    if db_type == "sqlite":
        # SQLite-specific parameters
        database = arguments["database"]
        source_table = arguments["source_table"]
        dest_table = arguments["dest_table"]
        host = port = username = password = None  # Not required for SQLite
    else:
        # Parameters for other database types (MySQL, PostgreSQL, MSSQL, Oracle)
        host = arguments["host"]
        port = arguments["port"]
        database = arguments["database"]
        username = arguments["username"]
        password = arguments["password"]
        source_table = arguments["source_table"]
        dest_table = arguments["dest_table"]

    # Connect to the source database and read data into a DataFrame
    try:
        query = f"SELECT * FROM {source_table};"
        df_loaded = connect_to_database_and_read_data_from_table_into_dataframe(
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            table_name=source_table,
        )
    except Exception as connection_error:
        raise RuntimeError(f"Failed to connect to the database or read data from table '{source_table}'. Error: {connection_error}")

    # Generate schema for the DataFrame
    df_schema = generate_df_schema(df_loaded)

    # Drop the destination table if it exists
    drop_query = f"DROP TABLE IF EXISTS {dest_table};"
    try:
        db.execute_query(drop_query)
    except Exception as drop_error:
        raise RuntimeError(f"Failed to drop table '{dest_table}'. Error: {drop_error}")

    # Save the DataFrame into the destination table
    try:
        zetta_df = db.session.create_dataframe(df_loaded, schema=df_schema)
        zetta_df.write.mode("overwrite").save_as_table(dest_table)
    except Exception as save_error:
        raise RuntimeError(f"Error loading data into table '{dest_table}': {save_error}")

    # Prepare success response
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
    
    # Convert the DataFrame back to a list of dictionaries
    data = convert_df_to_dict(data)
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
    # if not allow_write:
    #     raise ValueError("Write operations are not allowed for this data connection")
    if arguments["query"].strip().upper().startswith("SELECT"):
        raise ValueError("SELECT queries are not allowed for write_query")

    results, data_id = db.execute_query(arguments["query"])
    return [types.TextContent(type="text", text=str(results))]


async def handle_create_table(arguments, db, _, allow_write, __):
    # if not allow_write:
    #     raise ValueError("Write operations are not allowed for this data connection")
    if not arguments["query"].strip().upper().startswith("CREATE TABLE"):
        raise ValueError("Only CREATE TABLE statements are allowed")

    results, data_id = db.execute_query(arguments["query"])
    return [types.TextContent(type="text", text=f"Table created successfully. data_id = {data_id}")]

async def handle_get_knowledge_about_how_to_something(arguments, db, _, allow_write, __):
    if not arguments or "to_do_something" not in arguments:
        raise ValueError("Missing to_do_something argument to describe your purpose")

    data = [
        KNOWLEDGES[arguments["to_do_something"]],
    ]
    data_id = str(uuid.uuid4())
    return [types.TextContent(type="text", text=f"Get knowledge about how to analyze slow query as {data}, data_id = {data_id}")]


async def handle_create_table_with_prompt(arguments, db, _, allow_write, __):
    # if not allow_write:
    #     raise ValueError("Write operations are not allowed for this data connection")
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
            tags=["query"],
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
            tags=["query"],
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
            tags=["query"],
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
            tags=["query"],
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
            tags=["write"],
        ),
        Tool(
            name="import_data_into_table_from_database",
            description="Establish a connection to a database and execute a query, returning the results as a Pandas DataFrame then import data into clickzetta table. Supports MySQL, PostgreSQL, SQLite, and other common database types.",
            input_schema={
                "type": "object",
                "properties": {
                    "db_type": {
                        "type": "string",
                        "description": "The type of the database (e.g., 'mysql', 'postgresql', 'sqlite')."
                    },
                    "host": {
                        "type": "string",
                        "description": "The hostname or IP address of the database server. Not required for SQLite."
                    },
                    "port": {
                        "type": "integer",
                        "description": "The port number of the database server. Not required for SQLite."
                    },
                    "database": {
                        "type": "string",
                        "description": "The name of the database to connect to. For SQLite, this is the file path to the database file."
                    },
                    "username": {
                        "type": "string",
                        "description": "The username for authentication. Not required for SQLite."
                    },
                    "password": {
                        "type": "string",
                        "description": "The password for authentication. Not required for SQLite."
                    },
                    "source_table": {
                        "type": "string",
                        "description": "The source table name."
                    },
                    "dest_table": {
                        "type": "string",
                        "description": "The destination table name."
                    }
                },
                "required": ["db_type", "database", "source_table", "dest_table"]
                },

        handler=handle_import_data_into_table_from_database,
        tags=["write"]
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
            description="Execute a SELECT query. Date and time functions that are compatible with Spark SQL.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SELECT SQL query to execute"}},
                "required": ["query"],
            },
            handler=handle_read_query,
            tags=["query"],
            samples=samples_sql.get("read_query", []),  # 从 samples 加载样例 SQL
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
            description=("Execute an INSERT INTO, INSERT OVERWRITE, MERGE INTO, UPDATE, DELETE, or TRUNCATE query on the Clickzetta workspace/database."
                         "While update date or timestamp column, need type cast to date or timestamp, like date '2023-10-01' or timestamp '2023-10-02 12:00:00'"),
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
                "required": ["query"],
            },
            handler=handle_write_query,
            tags=["write"],
            samples=samples_sql.get("write_query", []),  # 从 samples 加载样例 SQL
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
            tags=["write"],
            samples=samples_sql.get("create_table", []),  # 从 samples 加载样例 SQL
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
            tags=["write"],
            samples=samples_sql.get("create_table", []),  # 从 samples 加载样例 SQL
        ),
        Tool(
            name="get_knowledge_about_how_to_do_something",
            description=("guide on how to something, like how to analyze slow query,"
                        "analyze table with small file,how to create table syntax, "
                        "how to create vcluster, how to create index, how to alter table and column, "
                        "how to create storage connection, how to create external volume,"
                        "how to alter vcluster, partition table guide,cluster table guide, etc."),
            input_schema={
                "type": "object",
                "properties": {
                    "to_do_something": {
                        "type": "string",
                        "description": "The thing you want to do, should be one of the following: analyze_slow_query, analyze_table_with_small_file,create_table_syntax,how_to_create_vcluster, how_to_create_index, how_to_alter_table_and_column,how_to_create_storage_connection, how_to_create_external_volume, how_to_alter_vcluster,partition_table_guide,cluster_table_guide, etc."
                    },
                },
            },
            handler=handle_get_knowledge_about_how_to_something,
            tags=["knowledge_based"],
        ),
        Tool(
            name="get_clickzetta_product_knowledge_from_embedded_documents",
            description=(f"Before use your own knowledge about clickzetta, please always use this tool to get knowledge not metioned in get_knowledge_about_how_to_do_something."
                         "Similar search on clickzetta product knowledge base, handler's parametes as: table_name = {table_name},embedding_column_name = {embedding_column_name},content_column_name = {content_column_name},"
                         "While get user question, this tool will execute vector search to retrieve documents about the question"
                         "You could organize retrieve documents."
                         "If doc_link is not NULL,YOU MUST SHOW doc_link at last to user to refer and get source information."
                         "If the knowledge is not enough, please continue to query to get knowledge(filename is in handle_vector_search results): select text from {table_name} where filename = '{filename}';."),
            input_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "user question to search"
                    },
                },
            },
            handler=handle_vector_search,
            tags=["knowledge_based"],
        )
    ]
    server.prompts = {
        "create_table_with_prompt": PROMPTS["create_table_prompt"],
    }

    exclude_tags = []
    if not allow_write:
        # exclude_tags.append("write")
        exclude_tags.append("create")
    if prefetch:
        exclude_tags.append("description")
    allowed_tools = [
        tool for tool in all_tools if tool.name not in exclude_tools and not any(tag in exclude_tags for tag in tool.tags)
    ]

    logger.info("Allowed tools: %s", [tool.name for tool in allowed_tools])
    logger.info("exclude_tags: %s", exclude_tags)

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
        
        if name == "create_table_prompt":
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

        if name == "create_database_connection_and_query_table_prompt":
            # Define required parameters for each database type
            db_type_required_params = {
                "mysql": ["host", "port", "database", "username", "password", "source_table", "dest_table"],
                "postgresql": ["host", "port", "database", "username", "password", "source_table", "dest_table"],
                "sqlite": ["database", "source_table", "dest_table"],  # SQLite only requires database file, source table, and target table
                "mssql": ["host", "port", "database", "username", "password", "source_table", "dest_table"],
                "oracle": ["host", "port", "database", "username", "password", "source_table", "dest_table"]
            }

            # Extract db_type and validate it
            db_type = arguments.get("db_type") if arguments else None
            if not db_type:
                raise ValueError("Missing required argument: 'db_type'")
            if db_type not in db_type_required_params:
                raise ValueError(f"Unsupported database type '{db_type}'. Supported types are: {', '.join(db_type_required_params.keys())}")

            # Check for missing required arguments
            required_params = db_type_required_params[db_type]
            missing_params = [param for param in required_params if not arguments or param not in arguments]
            if missing_params:
                raise ValueError(f"Missing required arguments for database type '{db_type}': {', '.join(missing_params)}")

            # Extract arguments
            host = arguments.get("host", "")
            port = arguments.get("port", "")
            database = arguments.get("database", "")
            username = arguments.get("username", "")
            password = arguments.get("password", "")
            source_table = arguments.get("source_table", "")
            dest_table = arguments.get("dest_table", "")

            # Generate the prompt message
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"Connect to a {db_type} database with the following details:\n"
                                f"Host: {host}\n"
                                f"Port: {port}\n"
                                f"Database: {database}\n"
                                f"Username: {username}\n"
                                f"Password: {password}\n\n"
                                f"Query the table named '{source_table}' and save the results into the target table '{dest_table}'."
                            )
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
        logger.info(f"Allowed tools: {allowed_tools}")
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
