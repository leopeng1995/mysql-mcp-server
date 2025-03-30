import os
import logging
import mcp.types as types
from typing import Dict, Any, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
from mcp.server.stdio import stdio_server
import pymysql


app_name = "mysql-mcp-server"
app_version = "0.1.0"
logger = logging.getLogger(app_name)
logger.setLevel(logging.INFO)
server = Server(app_name)


def get_db_config():
    """Get database configuration from environment variables."""
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE")
    }
    
    if not all([config["user"], config["password"], config["database"]]):
        logger.error("Missing required database configuration. Please check environment variables:")
        logger.error("MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DATABASE are required")
        raise ValueError("Missing required database configuration")
    
    return config


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available MySQL tools."""
    query_tool = types.Tool(
        name="execute_sql",
        description="Execute an SQL query on the MySQL server",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SQL query to execute"
                },
            },
            "required": ["query"],
        },
    )
    return [query_tool]


@server.list_resources()
async def list_resources() -> List[types.Resource]:
    """List MySQL tables as resources."""
    config = get_db_config()
    try:
        conn = pymysql.connect(**config)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                logger.info(f"Found tables: {tables}")

                resources = []
                for table in tables:
                    resources.append(
                        types.Resource(
                            uri=f"mysql://{table[0]}/data",
                            name=f"Table: {table[0]}",
                            mimeType="text/plain",
                            description=f"Data in table: {table[0]}"
                        )
                    )
                return resources
    except Exception as e:
        logger.error(f"Failed to list resources: {str(e)}")
        return []


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Execute SQL commands."""
    logger.debug(f"Calling tool {name} with arguments {arguments}")
    config = get_db_config()

    if name != "execute_sql":
        raise ValueError(f"Unknown tool: {name}")
    
    query = arguments.get("query")
    if not query:
        raise ValueError("Query is required")
    
    try:
        conn = pymysql.connect(**config)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(query)

                # Handling different types of SQL commands
                query_upper = query.strip().upper()
                
                # SHOW TABLES
                if query_upper.startswith("SHOW TABLES"):
                    tables = cursor.fetchall()
                    # Header
                    result = [config["database"] + " tables:"]
                    result.extend([table[0] for table in tables])
                    return [types.TextContent(type="text", text="\n".join(result))]
                
                # SELECT query
                elif query_upper.startswith("SELECT"):
                    rows = cursor.fetchall()
                    if not rows:
                        return [types.TextContent(type="text", text="Query executed successfully. No results returned.")]
                    
                    # Get column names
                    field_names = [i[0] for i in cursor.description]
                    
                    # Constructing tabular results
                    result = []
                    # Add a header
                    result.append(" | ".join(field_names))
                    result.append("-" * (sum(len(name) for name in field_names) + 3 * (len(field_names) - 1)))
                    
                    # Adding Data Row
                    for row in rows:
                        result.append(" | ".join(str(value) for value in row))
                    
                    return [types.TextContent(type="text", text="\n".join(result))]
                
                # SHOW DATABASES
                elif query_upper.startswith("SHOW DATABASES"):
                    databases = cursor.fetchall()
                    result = ["Available databases:"]
                    result.extend([db[0] for db in databases])
                    return [types.TextContent(type="text", text="\n".join(result))]
                
                # DESCRIBE 或 DESC (Table Structure)
                elif query_upper.startswith("DESCRIBE") or query_upper.startswith("DESC"):
                    columns = cursor.fetchall()
                    if not columns:
                        return [types.TextContent(type="text", text="No columns found or table doesn't exist.")]
                    
                    # Get column names
                    field_names = [i[0] for i in cursor.description]
                    
                    # Constructing tabular results
                    result = []
                    # Add a header
                    result.append(" | ".join(field_names))
                    result.append("-" * (sum(len(name) for name in field_names) + 3 * (len(field_names) - 1)))
                    
                    # Adding Data Row
                    for column in columns:
                        result.append(" | ".join(str(value) for value in column))
                    
                    return [types.TextContent(type="text", text="\n".join(result))]
                
                # SHOW COLUMNS
                elif query_upper.startswith("SHOW COLUMNS"):
                    columns = cursor.fetchall()
                    if not columns:
                        return [types.TextContent(type="text", text="No columns found or table doesn't exist.")]
                    
                    # Get column names
                    field_names = [i[0] for i in cursor.description]
                    
                    # Constructing tabular results
                    result = []
                    # Add a header
                    result.append(" | ".join(field_names))
                    result.append("-" * (sum(len(name) for name in field_names) + 3 * (len(field_names) - 1)))
                    
                    # Adding Data Row
                    for column in columns:
                        result.append(" | ".join(str(value) for value in column))
                    
                    return [types.TextContent(type="text", text="\n".join(result))]
                
                # INSERT, UPDATE, DELETE
                elif any(query_upper.startswith(cmd) for cmd in ["INSERT", "UPDATE", "DELETE"]):
                    affected_rows = cursor.rowcount
                    conn.commit()  # Make sure the changes are committed
                    return [types.TextContent(type="text", text=f"Query executed successfully. Affected rows: {affected_rows}")]
                
                # DDL statements such as CREATE, ALTER, DROP, TRUNCATE, etc.
                elif any(query_upper.startswith(cmd) for cmd in ["CREATE", "ALTER", "DROP", "TRUNCATE"]):
                    conn.commit()  # Make sure the changes are committed
                    return [types.TextContent(type="text", text="DDL statement executed successfully.")]
                
                # Other queries
                else:
                    try:
                        rows = cursor.fetchall()
                        if not rows:
                            return [types.TextContent(type="text", text="Query executed successfully. No results returned.")]
                        
                        # Get column names
                        field_names = [i[0] for i in cursor.description]
                        
                        # Constructing tabular results
                        result = []
                        # Add a header
                        result.append(" | ".join(field_names))
                        result.append("-" * (sum(len(name) for name in field_names) + 3 * (len(field_names) - 1)))
                        
                        # Adding Data Row
                        for row in rows:
                            result.append(" | ".join(str(value) for value in row))
                        
                        return [types.TextContent(type="text", text="\n".join(result))]
                    except:
                        # May be a query with no result set
                        conn.commit()
                        return [types.TextContent(type="text", text="Query executed successfully.")]

    except Exception as e:
        logger.error(f"Error executing SQL '{query}': {e}")
        return [types.TextContent(type="text", text=f"Error executing query: {str(e)}")]


async def start_server():
    """Run the server async context."""
    async with stdio_server() as streams:
        await server.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name=app_name,
                server_version=app_version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(resources_changed=True),
                    experimental_capabilities={},
                ),
            ),
        )
