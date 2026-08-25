# Deployment Guide

## Pre-Deployment Checklist

### Security
- [ ] Change SECRET_KEY in settings.py
- [ ] Set DEBUG = False
- [ ] Configure ALLOWED_HOSTS
- [ ] Enable HTTPS/SSL
- [ ] Configure CSRF_TRUSTED_ORIGINS
- [ ] Set secure cookies: SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE
- [ ] Enable HSTS: SECURE_HSTS_SECONDS
- [ ] Setup firewall rules
- [ ] Update database credentials
- [ ] Rotate API keys and secrets

### Performance
- [ ] Enable database connection pooling
- [ ] Configure caching (Redis recommended)
- [ ] Minify static assets
- [ ] Enable gzip compression
- [ ] Setup CDN for static files
- [ ] Configure database indexes
- [ ] Enable query optimization

### Infrastructure
- [ ] Setup PostgreSQL database
- [ ] Configure backup strategy
- [ ] Setup monitoring and logging
- [ ] Configure error tracking (Sentry)
- [ ] Setup email service
- [ ] Configure file storage (S3 or similar)
- [ ] Setup load balancer if needed
- [ ] Configure reverse proxy (Nginx)

### Testing
- [ ] Run full test suite
- [ ] Manual testing on staging
- [ ] Load testing
- [ ] Security testing
- [ ] Cross-browser testing
- [ ] Mobile responsiveness testing

## Deployment Options

### Option 1: Traditional VPS (AWS EC2, DigitalOcean, Linode)

#### Steps:
1. **SSH into server**
```bash
ssh root@your_server_ip
```

2. **Install system dependencies**
```bash
sudo apt update
sudo apt install python3-pip python3-venv postgresql postgresql-contrib nginx
```

3. **Setup PostgreSQL**
```bash
sudo -u postgres psql
CREATE DATABASE skilltraining;
CREATE USER skilluser WITH PASSWORD 'strong_password';
ALTER ROLE skilluser SET client_encoding TO 'utf8';
ALTER ROLE skilluser SET default_transaction_isolation TO 'read committed';
ALTER ROLE skilluser SET default_transaction_deferrable TO on;
ALTER ROLE skilluser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE skilltraining TO skilluser;
\q
```

4. **Clone repository and setup Django**
```bash
cd /var/www
sudo git clone https://github.com/your_repo/skilltraining.git
cd skilltraining
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install psycopg2-binary gunicorn
```

5. **Configure environment**
```bash
cp .env.example .env
nano .env  # Edit with production values
```

6. **Run migrations**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

7. **Setup Gunicorn**
```bash
gunicorn skilltraining.wsgi:application --bind 127.0.0.1:8000
```

8. **Create systemd service**
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

```ini
[Unit]
Description=Gunicorn application server for skilltraining
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/skilltraining
ExecStart=/var/www/skilltraining/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    skilltraining.wsgi:application

[Install]
WantedBy=multi-user.target
```

9. **Enable and start service**
```bash
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
```

10. **Configure Nginx**
```bash
sudo nano /etc/nginx/sites-available/skilltraining
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    client_max_body_size 10M;
    
    location /static/ {
        alias /var/www/skilltraining/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /var/www/skilltraining/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

11. **Enable Nginx site**
```bash
sudo ln -s /etc/nginx/sites-available/skilltraining /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

12. **Setup SSL (Let's Encrypt)**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Option 2: Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "skilltraining.wsgi:application"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=skilltraining
      - POSTGRES_USER=skilluser
      - POSTGRES_PASSWORD=strong_password
    ports:
      - "5432:5432"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - DATABASE_URL=postgres://skilluser:strong_password@db:5432/skilltraining
    depends_on:
      - db

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - web
```

#### Build and run:
```bash
docker-compose build
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Option 3: Platform as a Service (Heroku)

#### Procfile
```
web: gunicorn skilltraining.wsgi --log-file -
release: python manage.py migrate
```

#### runtime.txt
```
python-3.11.4
```

#### Deploy
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:standard-0
heroku config:set DEBUG=False
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### Option 4: Container Orchestration (Kubernetes)

#### Kubernetes deployment manifests available in `k8s/` directory

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/django.yaml
kubectl apply -f k8s/nginx.yaml
```

## Post-Deployment

### Monitoring
```bash
# Enable logging
python manage.py runserver --log-requests
```

### Backup Strategy
```bash
# Daily PostgreSQL backup
0 2 * * * pg_dump skilltraining > /backups/skilltraining_$(date +\%Y\%m\%d).sql

# S3 uploads
aws s3 sync /backups s3://your-backup-bucket/
```

### Performance Monitoring
- Setup New Relic or similar APM tool
- Monitor database performance
- Track application logs
- Setup uptime monitoring

### Scaling
- Horizontal scaling: Multiple Gunicorn workers, load balancer
- Vertical scaling: Upgrade server resources
- Database optimization: Read replicas, caching layers
- CDN for static files

## Troubleshooting Deployment

### Issue: 500 Error on production
```bash
# Check logs
tail -f /var/log/nginx/error.log
journalctl -u gunicorn -f

# Enable DEBUG temporarily to see error details
```

### Issue: Static files not loading
```bash
python manage.py collectstatic --clear --noinput
```

### Issue: Database connection issues
```bash
# Test connection
python manage.py dbshell
```

### Issue: Memory leaks
```bash
# Monitor process
htop
ps aux | grep gunicorn
```

## Maintenance

### Regular Updates
```bash
# Update dependencies
pip install --upgrade django
pip install --upgrade -r requirements.txt

# Apply security patches
sudo apt update && sudo apt upgrade
```

### Database Maintenance
```bash
# Vacuum and analyze (PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE;
```

### Clean up old sessions
```bash
python manage.py clearsessions
```

## Security Hardening

### Rate Limiting
```python
# In settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

### DDoS Protection
- Use Cloudflare or similar CDN
- Configure firewall rules
- Enable fail2ban

### SQL Injection Prevention
- Already handled by Django ORM (no explicit SQL needed)

### XSS Prevention
- Template auto-escaping (enabled by default)
- Content Security Policy headers

### CSRF Protection
- CSRF middleware active
- CSRF token in forms

## Monitoring & Alerts

### Email alerts for errors
```python
# In settings.py
ADMINS = [('Admin', 'admin@yourdomain.com')]
MANAGERS = ADMINS

# Configure email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```

### Uptime monitoring
- Set up with Uptime Robot or similar
- Configure alerts

### Performance alerts
- Database CPU > 80%
- Memory usage > 85%
- Response time > 2s

---

**For Production Deployments, always**:
- Follow Django deployment checklist
- Test thoroughly on staging
- Have a rollback plan
- Monitor application closely post-deployment
- Keep backups updated
