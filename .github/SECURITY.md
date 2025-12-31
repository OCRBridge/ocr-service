# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainers with details of the vulnerability
3. Include steps to reproduce the issue
4. Allow reasonable time for the issue to be addressed before public disclosure

## Security Best Practices for Deployment

### Authentication

- **Enable API key authentication** in production: Set `API_KEY_ENABLED=true`
- Use strong, randomly generated API keys (minimum 32 characters)
- Store API keys in environment variables, never in code

### Rate Limiting

- Rate limiting is enabled by default
- For multi-worker deployments, configure Redis: `RATE_LIMIT_STORAGE_URI=redis://host:port`
- In-memory rate limiting is per-worker and not shared across processes

### Network Security

- Run behind a reverse proxy (nginx, Traefik) in production
- Enable HTTPS/TLS termination at the proxy level
- Restrict CORS origins to known domains (avoid using `*`)

### Container Security

- Docker images run as non-root user (`appuser`)
- Temporary directories have restricted permissions (700)
- Use specific image tags, not `latest`

### File Handling

- Maximum upload size is configurable (default: 25MB, sync: 5MB)
- Only allowed file extensions are accepted (.jpg, .jpeg, .png, .pdf, .tiff, .tif)
- Uploaded files are automatically cleaned up after expiration

## Security Features

- Circuit breaker pattern for failing engines
- Request logging with correlation IDs
- Prometheus metrics for monitoring
- Health check endpoints for orchestration
