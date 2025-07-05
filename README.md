# Intelligent WordPress Agent

This project provides a containerized WordPress environment with a Python-based agent that allows for programmatic control over the WordPress site. The agent uses the Agent2Agent (A2A) protocol to receive commands and can manage posts, plugins, themes, and more.

## Features

*   **Containerized Environment:** A self-contained WordPress site running in a Docker container.
*   **Intelligent Agent:** A Python-based agent that can manage the WordPress site.
*   **A2A Protocol:** The agent uses the A2A protocol to receive commands from external systems.
*   **Programmatic Control:** The agent can manage posts, plugins, themes, and other aspects of the site.
*   **File Editing:** The agent can read, write, and append to files within the WordPress installation.

## Getting Started

### Prerequisites

*   Docker
*   Docker Compose

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/intelligent-wordpress-agent.git
    ```
2.  Navigate to the project directory:
    ```bash
    cd intelligent-wordpress-agent
    ```
3.  Create a `.env` file and add the following environment variables:
    ```
    AGENT_API_KEY=your-secret-api-key
    ```
4.  Build and run the containers:
    ```bash
    docker-compose up --build -d
    ```

### Interacting with the Agent

The agent listens for requests on port `5000`. You can interact with it by sending POST requests to the `/a2a/task` endpoint.

**Example:**
```bash
curl -X POST -H "Content-Type: application/json" \
-H "X-API-KEY: your-secret-api-key" \
-d '{ "tool": "create_wordpress_post", "args": { "title": "My Agent Post", "content": "This post was created by the agent." } }' \
http://localhost:5000/a2a/task
```

## API Reference

### System Tools

*   `get_system_information`: Retrieves version information for the OS, Python, PHP, WordPress, and WP-CLI.

### Post Tools

*   `create_wordpress_post`: Creates a new post or page.

### Plugin Tools

*   `install_wordpress_plugin`: Installs a plugin.
*   `activate_wordpress_plugin`: Activates a plugin.
*   `deactivate_wordpress_plugin`: Deactivates a plugin.
*   `delete_wordpress_plugin`: Deletes a plugin.

### Theme Tools

*   `install_wordpress_theme`: Installs a theme.
*   `activate_wordpress_theme`: Activates a theme.
*   `list_wordpress_themes`: Lists installed themes.
*   `get_active_wordpress_theme`: Gets the active theme.
*   `delete_wordpress_theme`: Deletes a theme.

### File Tools

*   `read_file`: Reads the content of a file.
*   `edit_file`: Edits or overwrites a file.
*   `append_to_file`: Appends content to a file.

### Option Tools

*   `get_wordpress_option`: Retrieves a WordPress option.
*   `update_wordpress_option`: Updates a WordPress option.

## Security

The agent uses an API key to authenticate requests. The API key is passed in the `X-API-KEY` header of each request.

The agent also includes a security measure to prevent directory traversal attacks. The `_validate_file_path` function ensures that all file operations are restricted to the `/var/www/html` directory.
