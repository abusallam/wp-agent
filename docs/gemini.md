# Gemini Model Integration

This document outlines the integration of the Gemini model with the WP-Agent.

## Configuration

The configuration for the Gemini model is managed through environment variables.

## Monitoring

Alerting rules for the Gemini model are defined in `monitoring/rules/gemini.yml`.

### Alerts

- **GeminiHighLatency**: Triggers when the average latency for Gemini API requests exceeds 1.5 seconds over the last 5 minutes.
- **GeminiHighErrorRate**: Triggers when the error rate for Gemini API requests is above 5% over the last 15 minutes.
