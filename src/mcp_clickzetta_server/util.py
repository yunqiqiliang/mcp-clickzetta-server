import pandas as pd
import requests
import zipfile
import gzip
from io import StringIO, BytesIO
from typing import Union
import clickzetta.zettapark.types as T

import pandas as pd
import requests
import zipfile
import gzip
import os
from io import StringIO, BytesIO

from xinference.client import Client as Xinference_Client
import dotenv
dotenv.load_dotenv()
xinference_base_url = os.getenv("XINFERENCE_BASE_URL")
xinference_embedding_model_512 = os.getenv("XINFERENCE_EMBEDDING_MODEL_512")

def get_embedding_xin(
    input_text: str,
    base_url: str = xinference_base_url,
    model_name: str = xinference_embedding_model_512
) -> list:
    """
    获取文本的嵌入向量
    
    参数:
    input_text (str): 要生成嵌入向量的文本
    base_url (str): Xinference服务器地址，默认为本地服务
    model_name (str): 要使用的模型名称，默认为bge-m3
    
    返回:
    list: 文本的嵌入向量
    """
    # 使用别名创建客户端连接
    client = Xinference_Client(base_url)  # 修改类名调用
    
    # 获取指定模型
    model = client.get_model(model_name)
    embedding = model.create_embedding(input_text)
    # 生成并返回嵌入向量
    return embedding['data'][0]['embedding']

def read_data_to_dataframe(source: str, **kwargs) -> pd.DataFrame:
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