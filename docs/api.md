# WordPress Agent API Reference

## Authentication

All API requests require authentication using the `X-API-KEY` header:
```bash
curl -H "X-API-KEY: your-key" http://localhost:5000/health
```

## Endpoints

### Health Check
```bash
GET /health
```
Returns the agent's health status.

### A2A Task Endpoint
```bash
POST /a2a/task
Content-Type: application/json
```

## Available Tools

### System Management

#### get_system_information
Gets system version information.
```json
{
  "tool": "get_system_information"
}
```

### Post Management

#### create_wordpress_post
Creates a new post or page.
```json
{
  "tool": "create_wordpress_post",
  "args": {
    "title": "Post Title",
    "content": "Post content",
    "status": "publish",
    "post_type": "post"
  }
}
```

### Plugin Management

#### install_wordpress_plugin
Installs a WordPress plugin.
```json
{
  "tool": "install_wordpress_plugin",
  "args": {
    "plugin_slug": "plugin-name",
    "version": "optional-version"
  }
}
```

#### activate_wordpress_plugin
Activates an installed plugin.
```json
{
  "tool": "activate_wordpress_plugin",
  "args": {
    "plugin_slug": "plugin-name"
  }
}
```

#### deactivate_wordpress_plugin
Deactivates an installed plugin.
```json
{
  "tool": "deactivate_wordpress_plugin",
  "args": {
    "plugin_slug": "plugin-name"
  }
}
```

### Theme Management

#### install_wordpress_theme
Installs a WordPress theme.
```json
{
  "tool": "install_wordpress_theme",
  "args": {
    "theme_slug": "theme-name",
    "version": "optional-version"
  }
}
```

#### activate_wordpress_theme
Activates an installed theme.
```json
{
  "tool": "activate_wordpress_theme",
  "args": {
    "theme_slug": "theme-name"
  }
}
```

### File Operations

#### read_file
Reads a file's contents.
```json
{
  "tool": "read_file",
  "args": {
    "file_path": "relative/path/to/file"
  }
}
```

#### edit_file
Modifies a file's contents.
```json
{
  "tool": "edit_file",
  "args": {
    "file_path": "relative/path/to/file",
    "content": "new file content"
  }
}
```

### WordPress Options

#### get_wordpress_option
Retrieves a WordPress option.
```json
{
  "tool": "get_wordpress_option",
  "args": {
    "option_name": "option_key"
  }
}
```

#### update_wordpress_option
Updates a WordPress option.
```json
{
  "tool": "update_wordpress_option",
  "args": {
    "option_name": "option_key",
    "option_value": "new value"
  }
}
```

## Error Handling

All endpoints return JSON responses with the following structure:
```json
{
  "status": "success|error",
  "message": "Description of result or error",
  "data": {} // Optional data object
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

## Rate Limiting

Requests are rate-limited based on the client IP address. The default limits are:
- Development: 200 requests per minute
- Production: 100 requests per minute

Rate limit headers are included in all responses:
- X-RateLimit-Limit
- X-RateLimit-Remaining
- X-RateLimit-Reset