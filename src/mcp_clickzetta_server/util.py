import pandas as pd
import requests
import zipfile
import gzip
from io import StringIO, BytesIO
from typing import Union
import clickzetta.zettapark.types as T

from sqlalchemy import create_engine, text

import os,json

from sentence_transformers import SentenceTransformer


embedding_provider = "huggingface"
embedding_model_name_768 = "BAAI/bge-base-zh-v1.5"
embedding_model_name_1024 = "BAAI/bge-m3"
embedding_dim = 1024
embedding_max_tokens = 2048
if embedding_dim == 768:
    embedding_model_name = embedding_model_name_768
elif embedding_dim == 1024:
    embedding_model_name = embedding_model_name_1024


def get_embedding_hf(query):
    model = SentenceTransformer(embedding_model_name)
    return model.encode(query, normalize_embeddings=True)


def read_data_from_url_or_file_into_dataframe(source: str, **kwargs) -> pd.DataFrame:
    """
    Reads data from a file hosted at a URL or a local file (CSV, TXT, Excel, Parquet, etc.) into a Pandas DataFrame.
    Automatically detects compressed files (e.g., ZIP, GZ) based on the file extension.
    Pre-reads data to automatically set parameters like delimiter, skiprows, etc.

    Args:
        source (str): The URL or local file path of the data source.
        **kwargs: Additional arguments to pass to the Pandas read function.

    Returns:
        pd.DataFrame: The data loaded into a Pandas DataFrame.

    Raises:
        ValueError: If the file type is unsupported or the file cannot be read.
    """
    # Determine if the source is a URL or a local file
    is_url = source.startswith("http://") or source.startswith("https://")

    # Infer file type and compression type from the source
    if source.endswith('.zip'):
        compression = 'zip'
    elif source.endswith('.gz'):
        compression = 'gz'
    else:
        compression = None

    file_type = source.split('.')[-1].lower()
    if compression in ['zip', 'gz']:
        file_type = source.split('.')[-2].lower()  # Get the actual file type before the compression extension

    try:
        if is_url:
            # Handle URL source
            response = requests.get(source)
            response.raise_for_status()  # Raise an error for HTTP issues
            file_content = BytesIO(response.content)
        else:
            # Handle local file source
            if not os.path.exists(source):
                raise ValueError(f"Local file does not exist: {source}")
            file_content = open(source, 'rb')  # Open the local file in binary mode

        # Pre-read data for parameter inference
        def infer_parameters(file_obj, file_type):
            if file_type in ['csv', 'txt']:
                # Read a small sample to infer delimiter
                sample = file_obj.read(1024).decode('utf-8')
                file_obj.seek(0)  # Reset file pointer
                delimiter = ',' if ',' in sample else '\t' if '\t' in sample else None
                if delimiter:
                    kwargs.setdefault('delimiter', delimiter)
            elif file_type in ['xls', 'xlsx']:
                # For Excel, no additional inference needed
                kwargs.setdefault('skiprows', 0)
                kwargs.setdefault('sheet_name', 0)

        if compression == 'zip':
            # Handle ZIP compressed files
            with zipfile.ZipFile(file_content) as z:
                file_name = z.namelist()[0]
                with z.open(file_name) as f:
                    infer_parameters(f, file_name.split('.')[-1].lower())
                    if file_name.endswith('.csv'):
                        return pd.read_csv(f, **kwargs)
                    elif file_name.endswith('.txt'):
                        return pd.read_csv(f, **kwargs)
                    elif file_name.endswith(('.xls', '.xlsx')):
                        return pd.read_excel(f, **kwargs)
                    elif file_name.endswith('.json'):
                        return pd.read_json(f, **kwargs)
                    elif file_name.endswith('.parquet'):
                        return pd.read_parquet(f, **kwargs)
                    else:
                        raise ValueError(f"Unsupported file type in ZIP: {file_name}")
        elif compression == 'gz':
            # Handle GZ compressed files
            with gzip.GzipFile(fileobj=file_content) as f:
                infer_parameters(f, file_type)
                if file_type == 'csv':
                    return pd.read_csv(f, **kwargs)
                elif file_type == 'txt':
                    return pd.read_csv(f, **kwargs)
                elif file_type == 'parquet':
                    return pd.read_parquet(f, **kwargs)
                else:
                    raise ValueError(f"Unsupported file type for GZ: {file_type}")
        else:
            # Handle regular files
            if file_type in ['csv', 'txt']:
                file_obj = StringIO(file_content.read().decode('utf-8')) if is_url else open(source, 'r', encoding='utf-8')
                infer_parameters(file_obj, file_type)
                return pd.read_csv(file_obj, **kwargs)
            elif file_type in ['xls', 'xlsx']:
                return pd.read_excel(file_content if is_url else source, **kwargs)
            elif file_type == 'json':
                return pd.read_json(StringIO(file_content.read().decode('utf-8')) if is_url else source, **kwargs)
            elif file_type == 'parquet':
                return pd.read_parquet(file_content if is_url else source, **kwargs)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
    except Exception as e:
        raise ValueError(f"Failed to read file from source {source}: {e}")
    finally:
        if not is_url and 'file_content' in locals():
            file_content.close()  # Ensure local file is closed
    

def generate_df_schema(df: pd.DataFrame) -> T.StructType:
    """
    Generate a schema definition for a DataFrame in the format of T.StructType.

    Args:
        df (pd.DataFrame): The DataFrame for which to generate the schema.

    Returns:
        T.StructType: The schema definition.
    """
    type_mapping = {
        "int64": T.IntegerType(),
        "float64": T.FloatType(),
        "object": T.StringType(),
        "bool": T.BooleanType(),
        "datetime64[ns]": T.TimestampType(),
    }

    fields = []
    for column_name, dtype in df.dtypes.items():
        field_type = type_mapping.get(str(dtype), T.StringType())  # Default to StringType if type is unknown
        fields.append(T.StructField(column_name, field_type))

    return T.StructType(fields)


def connect_to_database_and_read_data_from_table_into_dataframe(
    db_type: str,
    host: str = None,
    port: int = None,
    database: str = None,
    username: str = None,
    password: str = None,
    table_name: str = None
) -> pd.DataFrame:
    """
    Establish a connection to a database and execute a query, returning the results as a Pandas DataFrame.

    Args:
        db_type (str): The type of the database (e.g., 'mysql', 'postgresql', 'sqlite').
        host (str): The hostname or IP address of the database server. Not required for SQLite.
        port (int): The port number of the database server. Not required for SQLite.
        database (str): The name of the database to connect to. For SQLite, this is the file path to the database file.
        username (str): The username for authentication. Not required for SQLite.
        password (str): The password for authentication. Not required for SQLite.
        query (str): The SQL query to execute.

    Returns:
        pd.DataFrame: A DataFrame containing the query results.

    Raises:
        ValueError: If the provided db_type is not supported or query is not provided.
        ConnectionError: If the connection to the database fails.
        RuntimeError: If the query execution fails.
    """
    # Supported database types
    supported_db_types = ["mysql", "postgresql", "sqlite", "mssql", "oracle"]

    if db_type not in supported_db_types:
        raise ValueError(f"Unsupported database type '{db_type}'. Supported types are: {', '.join(supported_db_types)}")

    if not table_name:
        raise ValueError("A valid table name must be provided.")

    # Construct the connection URL
    if db_type == "sqlite":
        # SQLite uses a file path instead of host/port
        connection_url = f"sqlite:///{database}"
    else:
        connection_url = f"{db_type}://{username}:{password}@{host}:{port}/{database}"

    # Create the SQLAlchemy engine
    try:
        engine = create_engine(connection_url)
        print(f"Connecting to the {db_type} database '{database}' at {host}:{port}...")
    except Exception as e:
        raise ConnectionError(f"Failed to connect to the {db_type} database. Error: {e}")

    # Execute the query and return results as a DataFrame
    try:
        with engine.connect() as connection:
            df = pd.read_sql(f"select * from {table_name}", connection)
            print("Query executed successfully.")
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to execute query. Error: {e}")