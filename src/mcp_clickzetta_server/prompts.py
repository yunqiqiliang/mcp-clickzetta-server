PROMPTS = {
    "create_table_prompt": {
        "name": "create_table_prompt",
        "description": "Create a new table by prompting the user for table name, columns, and their types.The columns and their types in the format 'column1:type1,column2:type2' (e.g., 'id:INTEGER,name:STRING').",
        "arguments": [
            {
                "name": "table_name",
                "description": "The name of the table to create.",
                "required": True
            },
            {
                "name": "columns",
                "description": "The columns and their types in the format 'column1:type1,column2:type2' (e.g., 'id:INTEGER,name:STRING').",
                "required": True
            },
        ],
    },
    "create_database_connection_and_query_table_prompt": {
        "name": "create_database_connection_and_query_table_prompt",
        "description": "Establish a connection to a database by providing the necessary connection parameters and query data from table.",
        "arguments": [
            {
                "name": "db_type",
                "description": "The type of the database (e.g., 'mysql', 'postgresql', 'sqlite', 'mssql', 'oracle').",
                "required": True
            },
            {
                "name": "host",
                "description": "The hostname or IP address of the database server. Not required for SQLite.",
                "required": False
            },
            {
                "name": "port",
                "description": "The port number of the database server. Not required for SQLite.",
                "required": False
            },
            {
                "name": "database",
                "description": "The name of the database to connect to. For SQLite, this is the file path to the database file.",
                "required": False
            },
            {
                "name": "username",
                "description": "The username for authentication. Not required for SQLite.",
                "required": False
            },
            {
                "name": "password",
                "description": "The password for authentication. Not required for SQLite.",
                "required": False
            },
            {
                "name": "source_table",
                "description": "The table(source table) to be queried.",
                "required": True
            },
            {
                "name": "dest_table",
                "description": "The table(destination table) to be write.",
                "required": True
            }
        ]
    },
   
}


    

