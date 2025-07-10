# Claude Model Integration

This document outlines the integration of the Claude model with the WP-Agent.

## Configuration

The configuration for the Claude model is managed through environment variables.

## Monitoring

Alerting rules for the Claude model are defined in `monitoring/rules/claude.yml`.

### Alerts

- **ClaudeHighLatency**: Triggers when the average latency for Claude API requests exceeds 2.0 seconds over the last 5 minutes.
- **ClaudeHighErrorRate**: Triggers when the error rate for Claude API requests is above 3% over the last 15 minutes.
