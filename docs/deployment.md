# WordPress Agent Deployment Guide

## Deployment Options

### 1. Coolify Deployment

#### Prerequisites
- Coolify server setup
- Git repository access
- Domain name (for production)

#### Steps

1. Create Production Environment:
```bash
cp .envsample.env .env
```

2. Configure Production Variables:
```env
FLASK_ENV=production
WORDPRESS_SITE_URL=https://your-domain.com
A2A_API_KEY=<strong-api-key>
CORS_ORIGINS=https://your-domain.com
```

3. Deploy using Coolify:
```bash
docker compose -f docker-compose.coolify.yml up -d
```

### 2. Manual Deployment

#### Prerequisites
- Docker and Docker Compose
- SSL certificates
- Domain name

#### Steps

1. Clone Repository:
```bash
git clone https://github.com/your-username/wp-agent.git
cd wp-agent
```

2. Configure Environment:
```bash
cp .envsample.env .env
# Edit .env with production values
```

3. Build and Deploy:
```bash
make build
make deploy
```

## Production Configuration

### Resource Limits

Configure container resources in docker-compose.coolify.yml:
```yaml
services:
  wp-agent:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

### SSL/TLS Setup

1. Configure SSL in your reverse proxy
2. Update WORDPRESS_SITE_URL to use https
3. Enable HSTS if needed

### Database Backups

1. Configure automated backups:
```bash
# Daily backup
0 0 * * * docker exec wp-agent-db mysqldump -u root -p wordpress > backup.sql
```

2. Setup backup rotation

### Monitoring Setup

1. Configure Prometheus:
```yaml
scrape_configs:
  - job_name: 'wp-agent'
    static_configs:
      - targets: ['wp-agent:5000']
```

2. Setup Grafana dashboards from /monitoring

### Security Checklist

- [ ] Strong API key configured
- [ ] Rate limiting enabled
- [ ] CORS origins restricted
- [ ] SSL/TLS enabled
- [ ] Database credentials secured
- [ ] File permissions checked
- [ ] Regular security updates enabled

## Maintenance

### Updates

1. Pull latest changes:
```bash
git pull origin main
```

2. Rebuild and restart:
```bash
make build
make deploy
```

### Backup and Restore

1. Backup:
```bash
# Database
docker exec wp-agent-db mysqldump -u root -p wordpress > backup.sql

# Files
docker cp wp-agent:/var/www/html ./backup
```

2. Restore:
```bash
# Database
cat backup.sql | docker exec -i wp-agent-db mysql -u root -p wordpress

# Files
docker cp ./backup wp-agent:/var/www/html
```

### Monitoring

1. Check logs:
```bash
docker compose logs wp-agent

# Follow logs
docker compose logs -f wp-agent
```

2. Monitor metrics:
- Access Grafana dashboard
- Check Prometheus alerts
- Review error rates

### Troubleshooting

1. Container Issues:
```bash
# Check status
docker compose ps

# Restart service
docker compose restart wp-agent
```

2. Common Problems:
- Database connection issues
- Permission problems
- Memory limits
- Rate limiting issues

## Scaling

### Horizontal Scaling

1. Configure load balancer
2. Add multiple agent instances
3. Setup shared storage
4. Configure session management

### Performance Tuning

1. Adjust Gunicorn workers:
```env
GUNICORN_WORKERS=4
MAX_REQUESTS=1000
```

2. Optimize PHP settings:
```env
PHP_MEMORY_LIMIT=512M
```

3. Configure caching:
- Enable WordPress object cache
- Setup Redis if needed