# mysql-mcp-server

mysql-mcp-server is a Model Context Protocol (MCP) server for connecting to MySQL Server.

## Installation

```
git clone https://github.com/leopeng1995/mysql-mcp-server.git
cd mysql-mcp-server

uv sync
uv run mysql-mcp-server
```

## Configuration in Cline

```json
{
  "mysql-mcp-server": {
    "command": "uv",
    "args": [
      "--directory",
      "H:/workspaces/leopeng1995/mysql-mcp-server",
      "run",
      "mysql-mcp-server"
    ],
    "env": {
      "MYSQL_HOST": "localhost",
      "MYSQL_PORT": "3306",
      "MYSQL_USER": "username",
      "MYSQL_PASSWORD": "password",
      "MYSQL_DATABASE": "database"
    },
    "disabled": false,
    "autoApprove": []
  }
}
```
