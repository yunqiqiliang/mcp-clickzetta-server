# -*- coding: utf-8 -*-
KNOWLEDGES = {
    "analyze_slow_query": {
        "title": "How to Analyze Slow Queries",
        "description": "Guidelines and best practices for analyzing and optimizing slow queries.",
        "steps": [
            "Get the top 1 slow queries using excute sql query: SELECT workspace_name, job_creator, job_type, job_text, status, virtual_cluster, job_priority, CAST(execution_time AS INTEGER) AS execution_time_seconds, cast(pt_date as STRING) AS job_date FROM information_schema.job_history WHERE pt_date >= CURRENT_DATE - INTERVAL '1 days' ORDER BY execution_time_seconds DESC LIMIT 1;. job_text column is the slow query sql statement.",
            "Excute explain query to understand the query execution plan using excute sql query: EXPLAIN <slow_query>.",
            "Give optimization suggestions based on the execution plan."
        ],
        "references": [
            "https://yunqi.tech/documents/worksapce-informaiton_schema-views",
            "https://yunqi.tech/documents/instance-informaiton-schema"
        ]
    },
    "analyze_table_with_small_file": {
        "title": "How to Analyze Partitioned Table with Small Files",
        "description": "Guidelines and best practices for analyzing and optimizing partitioned table with small files.",
        "steps": [
            "Get the partitioned table list using excute sql query: select * from information_schema.tables where is_partitioned;.",
            "If the list is empty,please report No partitioned table with small files found, Then STOP analyze.",
            "If the list is not empty, Get each table's partition information using excute sql query: show  partitions extended <table_name>.",
            "Anlyze the partition information to find table with small files. If total_files>1, bytes/total_files < 10MB, you should compact the small files.",
            "If found table with small files, introduce the table",
            "Give optimization suggestions: list all General Type VCluster then tell user you could use a Genaral type VCluster(sql query: USE VCLUSTER <General type VCluster>;), and excute sql query to compact the small files: OPTIMIZE  <table_name>;."
        ],
        "references": [
            "https://yunqi.tech/documents/small_file_optimization"
        ]
    },
    "create_table_syntax": {
        "title": "How to Create Table",
        "description": "The syntax for creating a table DDL.",
        "basic_syntax": [
                "CREATE TABLE [ IF NOT EXISTS ] table_name ("
                "    column_definition  [column_definition ,...],"
                "    index_definition_list"
                ") "
                "[ PARTITIONED BY (column_name column_type | column_name | transform_function) ] "
                "[ CLUSTERED BY (column_name,...) "
                "    [SORTED BY (column_name [ ASC | DESC ])] "
                "    [INTO num_buckets BUCKETS] "
                "] "
                "[ COMMENT 'table_comment' ] "
                "[PROPERTIES('data_lifecycle'='day_num')];"
        ],
         "column_definition_syntax": [
                "column_name column_type "
                "{ NOT NULL |"
                "PRIMARY KEY|"
                "IDENTITY[(seed)]|"
                "GENERATED ALWAYS AS ( expr ) |"
                "DEFAULT default_expression |"
                "COMMENT column_comment |"
                "}"
         ],
         "column_type": [
                "TINYINT: 1-byte integer, range -128 to 127.",
                "SMALLINT: 2-byte integer, range -32,768 to 32,767.",
                "INT: 4-byte integer, range -2,147,483,648 to 2,147,483,647.",
                "BIGINT: 8-byte integer, range -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807.",
                "FLOAT: 4-byte floating-point number.",
                "DOUBLE: 8-byte floating-point number.",
                "DECIMAL: Variable-length precise numeric type, supports specified precision and scale,  e.g., DECIMAL(10, 2).",
                "VARCHAR: Variable-length string, max length 65,533 characters.",
                "CHAR: Fixed-length string, length range 1 to 255 characters.",
                "DATE: Date, format YYYY-MM-DD.",
                "TIMESTAMP: Date and time, local time format YYYY-MM-DD HH:MM:SS.",
                "TIMESTAMP_NTZ: Date and time without timezone, format YYYY-MM-DD HH:MM:SS.",
                "BINARY: Fixed-length binary string.",
                "BOOLEAN: Boolean value, true or false.",
                "ARRAY: Ordered collection of elements of the same type, e.g., ARRAY<INT>.",
                "MAP: Key-value pair collection, keys must be the same type, values can differ, e.g., MAP<STRING,INT>.",
                "STRUCT: Record type with fields of different types, e.g., struct<company_name:string,employee_count:int>.",
                "JSON: Lightweight data interchange format.",
                "VECTOR: Numeric vector type for storing a series of numbers, e.g., VECTOR(float, 1024)."
        ],
        "key_tips": [
            "Primary Key: Don't use until user asked. Use primary key in table definition only while you are processing data through real-time data interfaces, data cannot be written to the primary key table via the SQL interface. Default interface is SQL.",
            "Default Value: Default values are not supported for partitioning columns. Generated Column: Values can be generated for partitioning columns.",
            "Default Value: Conversion of column values from other columns is not supported.",
            "自增列,Identity Column (IDENTITY): Only the BIGINT type is supported; the INT type is not supported.",
            "IDENTITY[(seed)]: Supports specifying auto-increment. It does not guarantee that the values in the sequence are continuous (without gaps), nor does it guarantee that the sequence values are assigned in a specific order.",
            "Partitioning Column: The TIMESTAMP type cannot be used directly as a partitioning column; it needs to be converted to an integer type (such as YEAR, MONTH, DAY) using a generated column.",
        ],
        "references": [
            "https://www.yunqi.tech/documents/create-table-ddl",
            "https://www.yunqi.tech/documents/data-type"
        ]
    },

    "alter_table_and_column": {
            "alter_table_operations": {
                "rename_table": {
                "syntax": "ALTER TABLE name RENAME TO new_table_name",
                "description": "Renames a table to a new name"
                },
                "set_table_comment": {
                "syntax": "ALTER TABLE tbname SET COMMENT 'New Comments'",
                "description": "Sets or changes the comment for a table"
                },
                "set_table_properties": {
                "syntax": "ALTER TABLE table_name SET PROPERTIES(\"key\"=\"value\")",
                "description": "Sets custom properties for a table"
                },
                "table_properties": {
                "data_lifecycle": {
                    "description": "Data lifecycle setting",
                    "value_range": "Positive integers (>0), -1 means disabled"
                },
                "data_retention_days": {
                    "description": "Time Travel retention period in days (determines how far back you can access historical data)",
                    "value_range": "0-90 days, storage fees apply"
                }
                },
                "alter_column_operations": {
                "add_column": {
                    "syntax": "ALTER TABLE table_name ADD COLUMN column1_name_identifier data_type [COMMENT comment] [FIRST | AFTER column1_name_identifier]",
                    "description": "Adds one or more columns to a table",
                    "parameters": {
                    "column_name_identifier": {
                        "description": "Field identifier specifying the column to add",
                        "types": [
                        "regular_column: column_name",
                        "struct_type: column_name.struct_column_name",
                        "array_of_struct: column_name.ELEMENT.struct_column_name",
                        "map_key_struct: column_name.KEY.struct_column_name",
                        "map_value_struct: column_name.VALUE.struct_column_name"
                        ]
                    },
                    "position": {
                        "options": ["FIRST", "AFTER column_name"],
                        "description": "Specifies the position of the new column"
                    }
                    }
                },
                "drop_column": {
                    "syntax": "ALTER TABLE table_name DROP COLUMN column_name_identifier [, column_name_identifier ... ]",
                    "description": "Removes one or more columns from a table"
                },
                "rename_column": {
                    "syntax": "ALTER TABLE my_table RENAME COLUMN old_name TO new_name",
                    "description": "Renames an existing column"
                },
                "modify_column": {
                    "operations": [
                    {
                        "type": "change_position",
                        "syntax": "ALTER TABLE table_name CHANGE COLUMN column_name_identifier { FIRST | AFTER column_identifier }",
                        "description": "Changes the position of a column"
                    },
                    {
                        "type": "change_data_type",
                        "syntax": "ALTER TABLE table_name CHANGE COLUMN column_name_identifier TYPE data_type",
                        "description": "Changes the data type of a column"
                    },
                    {
                        "type": "change_comment",
                        "syntax": "ALTER TABLE table_name CHANGE COLUMN column_name_identifier COMMENT 'comment'",
                        "description": "Changes the comment of a column"
                    }
                    ]
                }
                }
            },
        "references": [
            "https://www.yunqi.tech/documents/ALTERTABLE",
            "https://www.yunqi.tech/documents/ALTER-TABLE-COLUMN"
        ]
    },

    "how_to_create_and_build_index": {
        "create_index_types": [
            {
            "index_name": "BLOOMFILTER",
            "references": [
                "https://www.yunqi.tech/documents/CREATE-BLOOMFILTER-INDEX",
            ],
            "description": "A Bloom Filter is a probabilistic data structure used to test whether an element is a member of a set. This feature allows users to create Bloom Filter indexes on tables to improve query efficiency.",
            "syntax": {
                "create": "CREATE BLOOMFILTER INDEX [IF NOT EXISTS] index_name ON TABLE [schema].table_name(column_name) [COMMENT 'comment'] [PROPERTIES ('key'='value')]",
                "parameters": [
                {
                    "name": "bloomfilter",
                    "description": "Index type using Bloom Filter algorithm"
                },
                {
                    "name": "index_name",
                    "description": "Name of the index to be created, must be under specified schema and unique within that schema"
                },
                {
                    "name": "schema",
                    "description": "Optional parameter specifying the schema name of the table"
                },
                {
                    "name": "table_name",
                    "description": "Name of the table to create index on"
                },
                {
                    "name": "column_name",
                    "description": "Column name to create index on (currently only single-column indexes are supported)"
                },
                {
                    "name": "COMMENT",
                    "description": "Optional parameter for adding descriptive information about the index"
                },
                {
                    "name": "PROPERTIES",
                    "description": "Optional parameter, Lakehouse reserved properties for future extension"
                }
                ]
            }
            },
            {
            "index_name": "INVERTED",
            "references": [
                "https://www.yunqi.tech/documents/create-inverted-index",
            ],
            "description": "Inverted index for efficient text searching",
            "syntax": {
                "create": "CREATE TABLE table_name(columns_definition, INDEX index_name (column_name) INVERTED [COMMENT ''] PROPERTIES('analyzer'='english|chinese|keyword|unicode'), ...)",
                "parameters": [
                {
                    "name": "columns_definition",
                    "description": "Defines table field information, the last field must be separated by a comma"
                },
                {
                    "name": "INDEX",
                    "description": "Keyword"
                },
                {
                    "name": "index_name",
                    "description": "Custom name for the index"
                },
                {
                    "name": "column_name",
                    "description": "Field name to which the index should be added"
                },
                {
                    "name": "INVERTED",
                    "description": "Keyword indicating inverted index"
                },
                {
                    "name": "COMMENT",
                    "description": "Specifies explanatory information for the index"
                },
                {
                    "name": "PROPERTIES",
                    "description": "Specifies INDEX parameters, currently supports specifying tokenizer"
                },
                {
                    "name": "analyzer",
                    "description": "Tokenizer strategy for text processing",
                    "options": [
                    {
                        "value": "keyword",
                        "description": "Fields of this type are not tokenized. The entire string is treated as a single term for exact matching."
                    },
                    {
                        "value": "english",
                        "description": "Tokenizer designed for English text, recognizes consecutive ASCII letters and numbers, converts text to lowercase."
                    },
                    {
                        "value": "chinese",
                        "description": "Chinese text tokenizer, recognizes Chinese and English characters while filtering out punctuation, converts English letters to lowercase."
                    },
                    {
                        "value": "unicode",
                        "description": "Tokenizer based on Unicode text segmentation algorithm, capable of recognizing text boundaries in multiple languages, converts letters to lowercase."
                    }
                    ]
                }
                ]
            }
            },
            {
            "index_name": "VECTOR",
            "references": [
                "https://www.yunqi.tech/documents/create-vector-index",
            ],
            "description": "Vector index for similarity search",
            "syntax": {
                "create": "CREATE TABLE table_name(columns_definition, INDEX index_name (column_name) USING VECTOR PROPERTIES(\"property1\" = \"value1\", \"property2\" = \"value2\"))",
                "parameters": [
                {
                    "name": "columns_definition",
                    "description": "Defines table field information, the last field must be separated by a comma"
                },
                {
                    "name": "INDEX",
                    "description": "Keyword"
                },
                {
                    "name": "index_name",
                    "description": "Custom name for the index"
                },
                {
                    "name": "column_name",
                    "description": "Field name to which the index should be added"
                },
                {
                    "name": "VECTOR",
                    "description": "Keyword indicating vector index"
                },
                {
                    "name": "COMMENT",
                    "description": "Specifies explanatory information for the index"
                },
                {
                    "name": "PROPERTIES",
                    "description": "Specifies vector INDEX parameters",
                    "properties": [
                    {
                        "name": "distance.function",
                        "options": ["l2_distance", "cosine_distance", "negative_dot_product", "jaccard_distance", "hamming_distance"],
                        "default": "cosine_distance",
                        "description": "For convenience, use negative_dot_product for dot product scenarios"
                    },
                    {
                        "name": "scalar.type",
                        "options": ["f32", "f16", "i8", "b1"],
                        "default": "f32",
                        "description": "Vector element type in vector index, can be different from vector column"
                    },
                    {
                        "name": "m",
                        "default": "16",
                        "recommendation": "Not exceeding 1000",
                        "description": "Maximum number of neighbors in HNSW algorithm"
                    },
                    {
                        "name": "ef.construction",
                        "default": "128",
                        "recommendation": "Not exceeding 5000",
                        "description": "Candidate set size when building index with HNSW algorithm"
                    },
                    {
                        "name": "reuse.vector.column",
                        "options": ["false", "true"],
                        "default": "false",
                        "description": "Whether to reuse vector column data to save storage space"
                    },
                    {
                        "name": "compress.codec",
                        "options": ["uncompressed", "zstd", "lz4"],
                        "default": "uncompressed",
                        "description": "Compression algorithm for vector index; doesn't take effect when reusing column"
                    },
                    {
                        "name": "compress.level",
                        "options": ["fastest", "default", "best"],
                        "default": "default",
                        "description": "Compression algorithm level"
                    },
                    {
                        "name": "compress.byte.stream.split",
                        "options": ["false", "true"],
                        "default": "true",
                        "description": "Rearrange float bits before compression"
                    },
                    {
                        "name": "compress.block.size",
                        "default": "16777216",
                        "minimum": "1048576",
                        "description": "Compression block size"
                    },
                    {
                        "name": "conversion.rule",
                        "options": ["default", "as_bits"],
                        "default": "default",
                        "description": "Use 'as_bits' when needing to build index by bits for vector(tinyint, N) type"
                    }
                    ]
                }
                ],
                "type_mapping": {
                "b1": {
                    "supported_types": ["tinyint", "int", "float"],
                    "notes": "When \"conversion.rule\" = \"bits\", treats each bit in vector(tinyint, N) as a vector element. When \"default\", performs binarization."
                },
                "i8": {
                    "supported_types": ["tinyint", "int", "float"],
                    "notes": "Performs cast when types don't match (watch for overflow)"
                },
                "f16": {
                    "supported_types": ["int", "float"],
                    "notes": "Performs cast when types don't match"
                },
                "f32": {
                    "supported_types": ["int", "float"],
                    "notes": "Performs cast when types don't match"
                }
                }
            }
            }
        ],
        "build_index_operation": {
            "description": "Operation to create indexes on existing data",
            "supported_index_types": ["vector_index", "inverted_index"],
            "unsupported_types": ["bloom_filter"],
            "syntax": [
                {
                "type": "default",
                "format": "BUILD INDEX index_name ON [schema].table_name",
                "description": "Creates index on all existing data in the table"
                },
                {
                "type": "partition_specific",
                "format": "BUILD INDEX index_name ON table_name WHERE partition_name1 = '1' and partition_name2 = '2'",
                "description": "Creates index on specified partition(s) with support for operators: =, !=, >, >=, <, <="
                }
            ],
            "parameters": {
                "index_name": {
                "description": "Name of the index to be created",
                "required": "TRUE"
                },
                "partition_specification": {
                "description": "Optional partition filter conditions",
                "operators": ["=", "!=", ">", ">=", "<", "<="],
                "multiple_partitions": "TRUE"
                }
            },
            "execution_properties": {
                "synchronous": "TRUE",
                "resource_intensive": "TRUE",
                "monitoring": "Progress can be checked via Job Profile",
                "recommendation": "For large partitioned tables, it's recommended to build indexes partition by partition sequentially"
            }
            },
        },

  "how_to_create_vcluster": {
    "title": "How to Create Virtual Cluster",
    "description": "The syntax and parameters for creating different types of virtual clusters in Yunqi.",
    
    "steps": [
      {
        "step": 1,
        "description": "首先识别purpose是哪种类型(通用型、分析型、同步型)",
        "english": "Identify the purpose type (General, Analytics, or Integration)"
      },
      {
        "step": 2,
        "description": "然后识别需要如何配置参数",
        "english": "Determine how to configure parameters based on the cluster type"
      },
      {
        "step": 3,
        "description": "根据语法生成创建VCluster的SQL DDL语句",
        "english": "Generate the CREATE VCLUSTER SQL DDL statement according to the syntax"
      },
      {
        "step": 4,
        "description": "检查后并执行",
        "english": "Review and verify the statement before execution"
      },
      {
        "step": 5,
        "description": "执行创建语句",
        "english": "Execute the statement to create the virtual cluster"
      },
      {
        "step": 6,
        "description": "验证集群创建是否成功",
        "english": "Verify that the cluster was created successfully"
      }
    ],
    
    "syntax": [
        "-- 创建计算集群",
        "CREATE VCLUSTER [IF NOT EXISTS] <name>",
        "objectProperties",
        "[COMMENT '']",
        "",
        "--参数说明",
        "--创建分析型计算集群（ANALYTICS PURPOSE VIRTUAL CLUSTER）适用属性",
        "objectProperties ::=",
        "VCLUSTER_SIZE = num --1至256之间的整数,must be a power of 2",
        "VCLUSTER_TYPE = ANALYTICS",
        "MIN_REPLICAS = num",
        "MAX_REPLICAS = num",
        "AUTO_SUSPEND_IN_SECOND = num",
        "AUTO_RESUME = TRUE| FALSE",
        "MAX_CONCURRENCY = num",
        "QUERY_RUNTIME_LIMIT_IN_SECOND = num",
        "PRELOAD_TABLES = \"<schema_name>.<table_name>[,<schema_name>.<table_name>,...]\"",
        "",
        "--创建通用型计算集群（GENERAL PURPOSE VIRTUAL CLUSTER）适用属性",
        "objectProperties ::=",
        "[VCLUSTER_SIZE = num | MIN_VCLUSTER_SIZE=num MAX_VCLUSTER_SIZE=num] --1至256的整数",
        "VCLUSTER_TYPE = GENERAL",
        "AUTO_SUSPEND_IN_SECOND = num",
        "AUTO_RESUME = TRUE| FALSE",
        "QUERY_RUNTIME_LIMIT_IN_SECOND = num",
        "QUERY_RESOURCE_LIMIT_RATIO=num;",
        "",
        "--创建同步型计算集群（INTEGRATION VIRTUAL CLUSTER）适用属性",
        "objectProperties ::=",
        "[VCLUSTER_SIZE = num | MIN_VCLUSTER_SIZE=num MAX_VCLUSTER_SIZE=num] --1至256的整数",
        "VCLUSTER_TYPE = INTEGRATION",
        "AUTO_SUSPEND_IN_SECOND = num",
        "AUTO_RESUME = TRUE| FALSE",
        "QUERY_RUNTIME_LIMIT_IN_SECOND = num",
        "QUERY_RESOURCE_LIMIT_RATIO=num;"
        ],

    "cluster_types": {
      "ANALYTICS": {
        "description": "分析型计算集群，适合于ad-hoc查询、BI分析、Serving等场景",
        "english": "Analytics Purpose Virtual Cluster",
        "parameters": [
          {"name": "VCLUSTER_SIZE", "description": "集群大小，1至256之间的整数,must be a power of 2", "english": "Cluster size (1-256)"},
          {"name": "MIN_REPLICAS", "description": "最小副本数", "english": "Minimum number of replicas"},
          {"name": "MAX_REPLICAS", "description": "最大副本数", "english": "Maximum number of replicas"}
        ]
      },
      "GENERAL": {
        "description": "通用型计算集群，适合于批量离线数据处理",
        "english": "General Purpose Virtual Cluster",
        "parameters": [
          {"name": "VCLUSTER_SIZE/MIN_VCLUSTER_SIZE/MAX_VCLUSTER_SIZE", "description": "集群大小或大小范围，1至256的整数", "english": "Cluster size or range (1-256)"}
        ]
      },
      "INTEGRATION": {
        "description": "同步型计算集群，仅适合数据集成场景",
        "english": "Integration Virtual Cluster",
        "parameters": [
          {"name": "VCLUSTER_SIZE/MIN_VCLUSTER_SIZE/MAX_VCLUSTER_SIZE", "description": "集群大小或大小范围，1至256的整数", "english": "Cluster size or range (1-256)"}
        ]
      }
    },
    "operational_notes": [
        "Clusters bill per-second with 60-second minimum charge",
        "Suspended clusters retain metadata but incur no compute charges",
        "Auto-resume typically completes within 5-15 seconds",
        "Concurrent query limits apply per cluster type",
        "Preloaded tables persist through suspend/resume cycles"
    ],
    "performance_tips": [
        "For mixed workloads, consider separate ANALYTICS and GENERAL clusters",
        "Monitor QUERY_TIMEOUT events to identify optimization opportunities",
        "Scale down during maintenance windows via MAX_REPLICAS adjustment",
        "Use PRELOAD_TABLES for frequently accessed reference data"
    ],
    "references": [
        "https://www.yunqi.tech/documents/create_cluster",
        "https://www.yunqi.tech/documents/virtual-clusters"
    ],
    "recommended_vcluster_configuration_samples": {
        "etl_scheduling": {
        "business_scenario": "ETL scheduling jobs",
        "workload_type": "Near-real-time offline processing",
        "execution_frequency": "Hourly",
        "job_concurrency": 1,
        "data_volume": "1 TB",
        "vcluster_type": "GENERAL",
        "latency_sla": "15 minutes",
        "recommended_size": 4,
        "configuration": {
            "auto_suspend": 3600,
            "auto_resume": "TRUE",
            "query_timeout": 900,
            "resource_limit_ratio": 0.8
        }
        },
        "tplus1_processing": {
        "business_scenario": "T+1 offline processing",
        "workload_type": "Daily batch processing",
        "execution_frequency": "Daily",
        "job_concurrency": 1,
        "data_volume": "10 TB",
        "vcluster_type": "GENERAL",
        "latency_sla": "4 hours",
        "recommended_size": 8,
        "configuration": {
            "auto_suspend": 86400,
            "auto_resume": "TRUE",
            "query_timeout": 14400,
            "resource_limit_ratio": 0.9
        }
        },
        "bi_ad_hoc": {
        "business_scenario": "Tableau/FineBI Ad-Hoc Analytics",
        "workload_type": "Interactive analytics",
        "execution_frequency": "Ad-Hoc",
        "job_concurrency": 8,
        "data_volume": "1 TB",
        "vcluster_type": "GENERAL",
        "latency_sla": "<1 minute (TP90 <5 seconds)",
        "recommended_size": 16,
        "configuration": {
            "auto_suspend": 300,
            "auto_resume": "TRUE",
            "query_timeout": 60,
            "resource_limit_ratio": 0.7,
            "max_concurrency": 16
        }
        },
        "data_applications": [
        {
            "scenario": "Data application products",
            "workload_type": "Operational analytics",
            "execution_frequency": "On-demand",
            "job_concurrency": 8,
            "data_volume": "100 GB",
            "vcluster_type": "ANALYTICS",
            "latency_sla": "<1 second",
            "recommended_size": 4,
            "configuration": {
                "min_replicas": 2,
                "max_replicas": 4,
                "preload_tables": ["schema1.table1", "schema2.table2"]
            }
        },
        {
            "scenario": "Data application products",
            "workload_type": "Operational analytics",
            "execution_frequency": "On-demand",
            "job_concurrency": 96,
            "data_volume": "100 MB",
            "vcluster_type": "ANALYTICS",
            "latency_sla": "<1 second",
            "recommended_size": 4,
            "configuration": {
                "min_replicas": 2,
                "max_replicas": 4,
                "preload_tables": ["schema3.table3"]
            }
        }
        ],
        "clickzetta_webui": {
            "business_scenario": "ClickZetta Web-UI (Data development testing)",
            "workload_type": "Interactive analytics",
            "execution_frequency": "Ad-Hoc",
            "job_concurrency": 8,
            "data_volume": "3 TB",
            "vcluster_type": "GENERAL",
            "latency_sla": "<1 minute (TP90 <15 seconds)",
            "recommended_size": 16,
            "configuration": {
                "auto_suspend": 600,
                "auto_resume": "TRUE",
                "query_timeout": 60,
                "resource_limit_ratio": 0.75,
                "max_concurrency": 16
            }
        }
    },
  },
    "how_to_create_storage_connection":{
        "title": "how_to_create_storage_connection",
        "description": "Provides step-by-step guidance on how to create various types of storage connections in the Clickzetta workspace. Supported storage types include Alibaba Cloud, Tencent Cloud, Amazon S3, Kafka, and HDFS.",
        "steps": [
            {
            "step_number": 1,
            "title": "Select the storage type",
            "description": "Choose the type of storage connection you want to create. Supported types include Alibaba Cloud, Tencent Cloud, Amazon S3, Kafka, and HDFS.",
            "options": [
                "Alibaba Cloud OSS",
                "Tencent Cloud COS",
                "Amazon S3",
                "Kafka",
                "HDFS"
            ]
            },
            {
            "step_number": 2,
            "title": "Provide connection details",
            "description": "Fill in the required configuration details based on the selected storage type.",
            "storage_types": {
                "Alibaba Cloud OSS": {
                "syntax": "CREATE STORAGE CONNECTION if not exists hz_conn_ak TYPE oss ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com' ACCESS_ID = 'LTAI5tMmbq1Ty1xxxxxxxxx' ACCESS_KEY = '0d7Ap1VBuFTzNg7gxxxxxxxxxxxx';",                },
                "Tencent Cloud COS": {
                "syntax": "CREATE STORAGE CONNECTION my_conn TYPE COS ACCESS_KEY = '<access_key>' SECRET_KEY = '<secret_key>' REGION = 'ap-shanghai' APP_ID = '1310000503';",
                },
                "Amazon S3": {
                "syntax": "CREATE STORAGE CONNECTION aws_bj_conn TYPE S3 ACCESS_KEY = 'AKIAQNBSBP6EIJE33***' SECRET_KEY = '7kfheDrmq***************************' ENDPOINT = 's3.cn-north-1.amazonaws.com.cn' REGION = 'cn-north-1';",
                },
                "Kafka": {
                "syntax": "CREATE STORAGE CONNECTION connection_name TYPE kafka BOOTSTRAP_SERVERS = ['server1:port1', 'server2:port2', ...] SECURITY_PROTOCOL = 'PLAINTEXT';",
                },
                "HDFS": {
                "syntax": "CREATE STORAGE CONNECTION <connection_name> TYPE HDFSNAME_NODE='<nameservice_id>'NAME_NODE_RPC_ADDRESSES=['<rpc_address>']",
                }
            }
            },
            {
            "step_number": 3,
            "title": "Submit the connection",
            "description": "Use the provided SQL statement to submit the storage connection details to the Clickzetta workspace.",
            },
            {
            "step_number": 4,
            "title": "Verify the connection",
            "description": "Check the status of the storage connection to ensure it was created successfully. Use the SQL to verify the connection if in list or not.",
            "sql_query": "show connections;",
            }
        ],
        "notes": [
            "Ensure that the provided credentials (e.g., access key and secret key) have the necessary permissions to access the storage system.",
            "For Kafka connections, ensure that the Kafka cluster is reachable from the Clickzetta workspace.",
            "For HDFS connections, the 'user' field may be required depending on the HDFS configuration."
        ],
        "references": [
            {
            "title": "Create Storage Connection Documentation",
            "url": "https://yunqi.tech/documents/create-storage-connection"
            }
        ]
    },
  "how_to_create_external_volume":{
    "title": "how_to_create_external_volume",
    "description": "Provides step-by-step guidance on how to create external volumes in the Clickzetta workspace. Supported external volume types include Alibaba Cloud OSS, Tencent Cloud COS, and Amazon S3.",
    "steps": [
        {
        "step_number": 1,
        "title": "Select the external volume type",
        "description": "Choose the type of external volume you want to create. Supported types include Alibaba Cloud OSS, Tencent Cloud COS, and Amazon S3.",
        "options": [
            "Alibaba Cloud OSS",
            "Tencent Cloud COS",
            "Amazon S3"
        ]
        },
        {
        "step_number": 2,
        "title": "Provide volume details",
        "description": "Fill in the required configuration details based on the selected external volume type.",
        "volume_types": {
            "Alibaba Cloud OSS": {
            "syntax": "CREATE VOLUME volume_name TYPE 'OSS' OPTIONS(endpoint='endpoint_url', access_key='access_key', secret_key='secret_key', bucket_name='bucket_name', region='region');",
            "example": "CREATE VOLUME my_oss_volume TYPE 'OSS' OPTIONS(endpoint='https://oss-cn-shanghai.aliyuncs.com', access_key='your-access-key', secret_key='your-secret-key', bucket_name='my-bucket', region='cn-shanghai');"
            },
            "Tencent Cloud COS": {
            "syntax": "CREATE VOLUME volume_name TYPE 'COS' OPTIONS(endpoint='endpoint_url', access_key='access_key', secret_key='secret_key', bucket_name='bucket_name', region='region');",
            "example": "CREATE VOLUME my_cos_volume TYPE 'COS' OPTIONS(endpoint='https://cos.ap-guangzhou.myqcloud.com', access_key='your-access-key', secret_key='your-secret-key', bucket_name='my-bucket', region='ap-guangzhou');"
            },
            "Amazon S3": {
            "syntax": "CREATE VOLUME volume_name TYPE 'S3' OPTIONS(endpoint='endpoint_url', access_key='access_key', secret_key='secret_key', bucket_name='bucket_name', region='region');",
            "example": "CREATE VOLUME my_s3_volume TYPE 'S3' OPTIONS(endpoint='https://s3.amazonaws.com', access_key='your-access-key', secret_key='your-secret-key', bucket_name='my-bucket', region='us-east-1');"
            }
        }
        },
        {
        "step_number": 3,
        "title": "Submit the volume creation request",
        "description": "Use the provided SQL statement to submit the external volume creation request to the Clickzetta workspace.",
        "example_submission": {
            "sql": "CREATE VOLUME my_s3_volume TYPE 'S3' OPTIONS(endpoint='https://s3.amazonaws.com', access_key='your-access-key', secret_key='your-secret-key', bucket_name='my-bucket', region='us-east-1');"
        }
        },
        {
        "step_number": 4,
        "title": "Verify the volume creation",
        "description": "Verify the created volume by checking its details and listing files in the specified volume path.",
        "verification_methods": [
            {
            "method": "Check volume details",
            "sql": "DESC VOLUME volume_name;",
            "example_sql": "DESC VOLUME my_s3_volume;",
            },
            {
            "method": "List files in the volume path",
            "sql": "SHOW VOLUME DIRECTORY volume_name;",
            "example_sql": "SHOW VOLUME DIRECTORY my_s3_volume;",
            }
        ]
        }
    ],
    "notes": [
        "Ensure that the provided credentials (e.g., access key and secret key) have the necessary permissions to access the external storage system.",
        "The 'region' field is optional for some storage types but mandatory for others like S3.",
        "For Alibaba Cloud OSS and Tencent Cloud COS, ensure that the endpoint URL matches the region of the bucket."
    ],
    "references": [
        {
        "title": "OSS Volume Creation Documentation",
        "url": "https://yunqi.tech/documents/oss_volume_creation"
        },
        {
        "title": "COS Volume Creation Documentation",
        "url": "https://yunqi.tech/documents/cos_volume_creation"
        },
        {
        "title": "S3 Volume Creation Documentation",
        "url": "https://yunqi.tech/documents/s3_volume_creation"
        }
    ]
    },
     "how_to_query_semi_structured_data_on_volume":{
        "title": "how_to_query_semi_structured_data_on_volume",
        "description": "Provides step-by-step guidance on how to query semi-structured data (e.g., JSON, Parquet, CSV) stored on external volumes in the Clickzetta workspace. This includes loading the data, defining schemas, and querying the data using SQL.",
        "syntax":"SELECT { <column_name>,... | * } FROM VOLUME <volume_name>(<column_name> <column_type>, ...) USING CSV|PARQUET|ORC|BSON OPTIONS(FileFormatParams) FILES|SUBDIRECTORY|REGEXP <pattern>;",
        "steps": [
            {
            "step_number": 1,
            "title": "Identify the volume and file path",
            "description": "Determine the external volume and the file path where the semi-structured data is stored. Ensure that the volume has been created and is accessible.",
            "syntax": "VOLUME_NAME:FILE_PATH",
            "example": {
                "volume_name": "my_s3_volume",
                "file_path": "/data/sample.json",
                "full_path": "my_s3_volume:/data/sample.json"
            }
            },
            {
            "step_number": 2,
            "title": "Load the semi-structured data",
            "description": "Use the `LOAD DATA` statement to load the semi-structured data from the volume into a table or directly query the file using SQL.",
            "methods": [
                {
                "method": "Load data into a table",
                "syntax": "LOAD DATA INFILE 'volume_name:file_path' INTO TABLE table_name;",
                "example": "LOAD DATA INFILE 'my_s3_volume:/data/sample.json' INTO TABLE my_table;"
                },
                {
                "method": "Query the file directly",
                "syntax": "SELECT * FROM EXTERNAL 'volume_name:file_path' FORMAT 'file_format';",
                "example": "SELECT * FROM EXTERNAL 'my_s3_volume:/data/sample.json' FORMAT 'json';"
                }
            ]
            },
            {
            "step_number": 3,
            "title": "Define the schema for the data",
            "description": "If querying directly, define the schema for the semi-structured data to enable SQL-based querying. Use the `WITH SCHEMA` clause to specify the structure.",
            "syntax": "SELECT * FROM EXTERNAL 'volume_name:file_path' FORMAT 'file_format' WITH SCHEMA (column1 type1, column2 type2, ...);",
            "example": "SELECT * FROM EXTERNAL 'my_s3_volume:/data/sample.json' FORMAT 'json' WITH SCHEMA (id INT, name STRING, details STRUCT<age: INT, city: STRING>);"
            },
            {
            "step_number": 4,
            "title": "Query the semi-structured data",
            "description": "Use SQL to query the semi-structured data. You can filter, aggregate, and transform the data using standard SQL syntax.",
            "syntax": "SELECT column1, column2 FROM table_name WHERE condition;",
            "example": "SELECT id, details.city FROM EXTERNAL 'my_s3_volume:/data/sample.json' FORMAT 'json' WITH SCHEMA (id INT, name STRING, details STRUCT<age: INT, city: STRING>) WHERE details.age > 30;"
            },
            {
            "step_number": 5,
            "title": "Optimize the query performance",
            "description": "For large datasets, consider optimizing query performance by using partitioning, indexing, or caching mechanisms. Ensure that the file format (e.g., Parquet) is optimized for analytical queries.",
            "notes": [
                "Partition the data by frequently queried columns to reduce the amount of data scanned.",
                "Use Parquet or ORC formats for better performance compared to JSON or CSV.",
                "Leverage caching mechanisms if supported by the workspace."
            ],
            "example": {
                "optimization_techniques": [
                "CREATE TABLE my_table PARTITIONED BY (region STRING) AS SELECT * FROM EXTERNAL 'my_s3_volume:/data/sample.parquet' FORMAT 'parquet';",
                "CACHE TABLE my_table;"
                ]
            }
            }
        ],
        "notes": [
            "Ensure that the volume and file path are accessible and that the user has the necessary permissions to query the data.",
            "For JSON files, ensure that the data is well-formed and follows a consistent structure.",
            "For Parquet files, schema inference is typically automatic, but you can override it using the `WITH SCHEMA` clause."
        ],
        "references": [
            {
            "title": "Structure Data Analysis Documentation",
            "url": "https://yunqi.tech/documents/structure_data_analysis"
            }
        ]
        }
}