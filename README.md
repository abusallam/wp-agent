# Intelligent WordPress Agent Project

This project delivers a powerful, all-in-one containerized WordPress solution integrated with an intelligent Python-based Agent. The agent is designed for external communication via the Agent2Agent (A2A) protocol, enabling programmatic control over the WordPress site, including file editing, content management, and advanced administrative tasks using WP-CLI.

## Table of Contents

1.  [Project Overview](#1-project-overview)
2.  [Key Features](#2-key-features)
3.  [Core Technologies](#3-core-technologies)
4.  [Project Structure](#4-project-structure)
5.  [Setup & Local Deployment](#5-setup--local-deployment)
6.  [Interacting with the Agent (A2A Tasks)](#6-interacting-with-the-agent-a2a-tasks)
7.  [Production Readiness & Flexibility Enhancements](#7-production-readiness--flexibility-enhancements)
8.  [Further Enhancements & Future Directions](#8-further-enhancements--future-directions)
9.  [Stopping and Cleaning Up](#9-stopping-and-cleaning-up)

## 1. Project Overview

This project provides a highly efficient and intelligent WordPress environment. It bundles a WordPress installation powered by the high-performance FrankenPHP PHP application server within a Docker container. Crucially, this container also houses a Python-based Agent. This agent acts as the "brain" of your WordPress instance, capable of receiving commands via the A2A protocol, executing actions using `wp-cli` and direct file system manipulations, and providing detailed system insights.

The architecture supports easy deployment with Docker Compose and is designed with future integration with the broader Model Context Protocol (MCP) ecosystem in mind, allowing the agent to leverage external tools and context.

## 2. Key Features

*   **Containerized WordPress:** A self-contained WordPress site running efficiently within a Docker container.
*   **FrankenPHP Integration:** Utilizes FrankenPHP for superior PHP performance and a modern application server.
*   **Intelligent Python Agent:** A Python-based agent (using Flask) embedded within the WordPress container.
*   **A2A Communication:** Enables external systems or other agents to send structured commands to the WordPress agent via HTTP POST requests to the `/a2a/task` endpoint.
*   **Programmatic Site Control:** The agent can manage WordPress core functionalities (posts, plugins, options) using `wp-cli`.
*   **Direct File Editing:** The agent has the ability to read and modify files directly within the WordPress installation (within `/var/www/html`), enabling advanced customization and configuration.
*   **System Information Retrieval:** The agent can gather and report detailed information about its operating environment (OS, Python, PHP, WordPress, WP-CLI versions).
*   **Persistent Storage:** Docker Compose with named volumes ensures all WordPress files, themes, plugins, and database data persist across container restarts.
*   **MCP Compatibility Foundation:** Designed to be easily extended for Model Context Protocol (MCP) integration.

## 3. Core Technologies

*   **FrankenPHP:** A modern PHP application server built on Caddy. It serves WordPress, replacing traditional setups like Apache/Nginx + PHP-FPM for enhanced performance.
*   **Python Agent (Flask):** The intelligent component, a Python application running within the WordPress container. It uses Flask for its web server and `subprocess` for `wp-cli` interaction and `os` for file operations.
*   **Agent2Agent (A2A) Protocol:** The agent exposes an HTTP endpoint (`/a2a/task`) that receives JSON payloads, defining the tool to execute and its arguments. This is a conceptual implementation based on A2A principles.
*   **Model Context Protocol (MCP):** While not fully implemented, the agent's design allows for future extension to become an MCP client, enabling it to query external MCP servers for context or to use external tools.
*   **WP-CLI:** The command-line interface for WordPress. The Python agent leverages `wp-cli` to manage WordPress.
*   **Docker & Docker Compose:**
    *   **Docker:** Platform for running applications in containers.
    *   **Docker Compose:** Tool for defining and running multi-container Docker applications using `docker-compose.yml`.
*   **Git & GitHub:** Version control and collaboration platform (this project is intended to be hosted on GitHub).

## 4. Project Structure

```
.
├── docker-compose.yml
├── README.md
└── wordpress/
    ├── Dockerfile
    ├── entrypoint.sh
    └── agent/
        ├── __init__.py
        ├── agent.py
        └── requirements.txt
```

*   **`docker-compose.yml`**: Defines the `wordpress` (FrankenPHP + Python Agent) and `mariadb` services, volumes, and network configuration.
*   **`README.md`**: This file.
*   **`wordpress/`**: Directory containing files related to the WordPress service.
    *   **`Dockerfile`**: Builds the custom WordPress image. It starts from a FrankenPHP image, adds `wp-cli`, Python, copies the agent code and entrypoint script, and sets up user permissions.
    *   **`entrypoint.sh`**: Script executed when the WordPress container starts. It waits for the database, installs WordPress (if not already installed), installs Python dependencies, starts the Python agent in the background, and then starts FrankenPHP.
    *   **`agent/`**: Directory for the Python Agent.
        *   **`__init__.py`**: Makes the `agent` directory a Python package.
        *   **`agent.py`**: The core Python code for the Agent. It includes a Flask web server for the A2A endpoint and tool implementations that interact with `wp-cli` and the file system.
        *   **`requirements.txt`**: Lists Python dependencies for the agent (e.g., Flask).

## 5. Setup & Local Deployment

To get this project running on your local machine:

### Prerequisites

*   **Docker Desktop:** Ensure Docker Desktop (or Docker Engine with Docker Compose V2) is installed and running. (See [Docker Desktop](https://www.docker.com/products/docker-desktop/))
*   **Git:** Install Git if you haven't already (for cloning, though you can also manually create files). (See [Git SCM](https://git-scm.com/downloads))

### Cloning the Repository (Recommended)

If the project is hosted on GitHub (e.g., `https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git`):
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
cd YOUR_REPOSITORY_NAME
```

### Manual File Creation

If you are creating files manually:
1.  Create a root directory (e.g., `intelligent-wordpress-agent`).
2.  Create the subdirectories: `wordpress`, `wordpress/agent`.
3.  Copy the content for each file (as provided or from your project source) into the corresponding file paths listed in the [Project Structure](#4-project-structure) section.

### Building and Running Containers

1.  Open your terminal in the project's root directory (where `docker-compose.yml` is located).
2.  Run the following command:
    ```bash
    docker compose up --build -d
    ```
    *   `--build`: Builds the custom `wordpress` Docker image using `wordpress/Dockerfile`. Required on first run or after changes to `Dockerfile`, `entrypoint.sh`, or agent files.
    *   `-d`: Runs containers in detached mode (in the background).

### Verification

*   **WordPress Installation:** The `entrypoint.sh` script handles the initial WordPress setup. This may take a few minutes. Monitor logs:
    ```bash
    docker compose logs -f wordpress
    ```
    (Press `Ctrl+C` to stop.) Look for messages like "WordPress installation complete" and "Agent A2A server starting...".
*   **WordPress Site:** Access at `http://localhost`. Default admin credentials (from `docker-compose.yml`):
    *   User: `admin`
    *   Pass: `password`
*   **Agent Health:** Check `http://localhost:5000/health`.

## 6. Interacting with the Agent (A2A Tasks)

The Agent listens for A2A tasks on port `5000` at the `/a2a/task` endpoint. Send HTTP POST requests with a JSON payload.

**JSON Payload Structure:**
```json
{
    "tool": "tool_name_to_execute",
    "args": {
        "argument1": "value1",
        "argument2": "value2"
    }
}
```

### Example Tasks (using `curl`)

1.  **Get System Information:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "get_system_information", "args": {} }' \
         http://localhost:5000/a2a/task
    ```

2.  **Create a WordPress Post:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "create_wordpress_post", "args": { "title": "My Agent Post", "content": "Content by AI Agent.", "status": "publish", "post_type": "post" } }' \
         http://localhost:5000/a2a/task
    ```
    *   Other `args` for `create_wordpress_post`:
        *   `post_type`: "page" (for creating pages)
        *   `status`: "draft", "pending"

3.  **Activate a WordPress Plugin:**
    (Assumes plugin is already installed, e.g., "akismet")
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "activate_wordpress_plugin", "args": { "plugin_slug": "akismet" } }' \
         http://localhost:5000/a2a/task
    ```

4.  **Read a File:**
    (Reads a file relative to `/var/www/html` inside the container)
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "read_file", "args": { "file_path": "wp-config.php" } }' \
         http://localhost:5000/a2a/task
    ```

5.  **Edit a File (Overwrite):**
    **Caution:** This overwrites the entire file content. Use with care.
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "edit_file", "args": { "file_path": "agent-test-file.txt", "content": "Hello from the agent!\nThis is a new line." } }' \
         http://localhost:5000/a2a/task
    ```
    *(For critical files like `wp-config.php`, it's safer to read, modify content externally, then write back the full modified content.)*

6.  **Get a WordPress Option:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "get_wordpress_option", "args": { "option_name": "blogname" } }' \
         http://localhost:5000/a2a/task
    ```

7.  **Update a WordPress Option:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{ "tool": "update_wordpress_option", "args": { "option_name": "blogdescription", "option_value": "Managed by an Intelligent Agent" } }' \
         http://localhost:5000/a2a/task
    ```

## 7. Production Readiness & Flexibility Enhancements

While this project provides a solid foundation, consider these for production:

*   **Security Enhancements:**
    *   **A2A Endpoint Authentication:** Implement API keys, OAuth2/JWT, or mTLS for the `/a2a/task` endpoint.
    *   **Non-Root User:** Ensure agent and web server processes run as non-root users with minimal privileges (Dockerfile attempts this with `frankie` user).
    *   **Input Validation & Sanitization:** Rigorously validate all inputs to agent tools.
    *   **File Operation Safeguards:** Enhance checks for file operations (e.g., restrict writes to specific subdirectories).
*   **Scalability & Architecture:**
    *   **Agent Decoupling:** Consider running the agent in a separate container for independent scaling.
    *   **Load Balancing:** Use a load balancer for multiple WordPress instances.
    *   **Managed Database:** Use a managed database service (e.g., AWS RDS, Google Cloud SQL).
*   **Observability:**
    *   **Structured Logging:** Implement JSON logging in `agent.py`.
    *   **Centralized Logging:** Integrate with services like ELK Stack, Splunk, or Cloud Logging.
    *   **Monitoring & Alerting:** Monitor container health, application metrics (agent tasks, errors), and WordPress performance.
*   **Robustness & Reliability:**
    *   **Error Handling & Retries:** Implement more sophisticated error handling and retry mechanisms in the agent.
    *   **Health Checks:** Utilize Docker health checks for services.
    *   **Backup & Disaster Recovery:** Implement regular backups for WordPress files and the database.
*   **Continuous Integration/Continuous Deployment (CI/CD):**
    *   **Automated Testing:** Add unit tests for `agent.py` and integration tests.
    *   **GitOps Workflow:** Automate deployments from Git (e.g., using GitHub Actions, Coolify).
*   **LLM Integration (Future):**
    *   Integrate an LLM (e.g., Google Gemini) to interpret natural language requests and orchestrate tool usage.
    *   Use `get_system_information` to provide context to the LLM.

## 8. Further Enhancements & Future Directions

*   **Expanding Ecosystem Adoption:** Develop industry-specific templates, contribute to Agent Card/MCP tool marketplaces.
*   **Advanced Operational Capabilities:** Multi-agent debugging tools, LLM explainability, centralized governance.
*   **Community-Driven Growth:** Training programs, community engagement, simplified onboarding.

## 9. Stopping and Cleaning Up

*   **To stop the running containers:**
    ```bash
    docker compose down
    ```
*   **To stop and remove containers, networks, AND aLL DATA in volumes** (WordPress files, database):
    **Use with caution as this will delete your WordPress site and database content.**
    ```bash
    docker compose down --volumes
    ```

---
This README provides a comprehensive guide to understanding, setting up, and using the Intelligent WordPress Agent project.
