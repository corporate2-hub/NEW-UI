# Environment Configuration Setup

## Overview
This project uses **python-decouple** for managing environment variables from `.env` file. All sensitive configuration (database, email, API keys) is loaded from the environment.

## Quick Setup

### 1. Create `.env` file
Copy the provided `.env.example` to `.env` and update with your values:
```bash
cp .env.example .env
```

### 2. Database Configuration

#### Option A: SQLite (Development - Default)
```env
DB_TYPE=sqlite
```
This uses the default `db.sqlite3` file in the project root.

#### Option B: PostgreSQL (Production)
```env
DB_TYPE=postgresql
DB_NAME=skilltraining_db
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

To set up PostgreSQL:
```bash
# Create database
createdb skilltraining_db

# Run migrations
python manage.py migrate
```

### 3. Email Configuration (SMTP)

#### For Development (Console Backend - Default)
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```
Emails will be printed to the console instead of being sent.

#### For Gmail
1. Enable 2-factor authentication
2. Create an [App Password](https://support.google.com/accounts/answer/185833)
3. Configure `.env`:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
SERVER_EMAIL=your-email@gmail.com
```

#### For Other SMTP Providers
Configure the appropriate SMTP settings:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@yoursite.com
SERVER_EMAIL=noreply@yoursite.com
```

### 4. Django Security Settings

```env
# Generate a new secret key
SECRET_KEY=your-secret-key-here

# Set debug mode
DEBUG=True  # Only for development!

# Allowed hosts (comma-separated)
ALLOWED_HOSTS=localhost,127.0.0.1,.proto,yourdomain.com
```

### 5. Skill Jobs SSO Configuration

```env
SKILLJOBS_BASE_URL=http://localhost:3005
SKILLJOBS_API_BASE_URL=http://localhost:8000
SKILLJOBS_SSO_EXCHANGE_URL=http://localhost:8000/api/auth/sso/exchange/
SKILLJOBS_SSO_TIMEOUT=15
```

## Environment Variables Reference

### Core Django
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECRET_KEY` | string | Django insecure key | Django secret key for cryptographic operations |
| `DEBUG` | boolean | `True` | Enable debug mode (set to `False` in production) |
| `ALLOWED_HOSTS` | csv | `localhost,127.0.0.1,.proto` | Comma-separated list of allowed hosts |

### Database
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DB_TYPE` | string | `sqlite` | Database type: `sqlite` or `postgresql` |
| `DB_NAME` | string | `skilltraining_db` | PostgreSQL database name |
| `DB_USER` | string | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | string | empty | PostgreSQL password |
| `DB_HOST` | string | `localhost` | PostgreSQL host |
| `DB_PORT` | integer | `5432` | PostgreSQL port |

### Email (SMTP)
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EMAIL_BACKEND` | string | `console` | Email backend type |
| `EMAIL_HOST` | string | `smtp.gmail.com` | SMTP server host |
| `EMAIL_PORT` | integer | `587` | SMTP server port |
| `EMAIL_USE_TLS` | boolean | `True` | Use TLS encryption |
| `EMAIL_HOST_USER` | string | empty | SMTP authentication username |
| `EMAIL_HOST_PASSWORD` | string | empty | SMTP authentication password |
| `DEFAULT_FROM_EMAIL` | string | `noreply@skilljobstraining.com` | Default sender email |
| `SERVER_EMAIL` | string | `noreply@skilljobstraining.com` | Server error notification email |

### Skill Jobs SSO
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SKILLJOBS_BASE_URL` | string | `http://localhost:3005` | Skill Jobs frontend URL |
| `SKILLJOBS_API_BASE_URL` | string | `http://localhost:8000` | Skill Jobs API URL |
| `SKILLJOBS_SSO_EXCHANGE_URL` | string | derived | SSO token exchange endpoint |
| `SKILLJOBS_SSO_TIMEOUT` | integer | `15` | SSO request timeout (seconds) |

## Testing the Configuration

### Run migrations
```bash
./venv/Scripts/python.exe manage.py migrate
```

### Create a superuser
```bash
./venv/Scripts/python.exe manage.py createsuperuser
```

### Start development server
```bash
./venv/Scripts/python.exe manage.py runserver
```

### Test email configuration
```bash
./venv/Scripts/python.exe manage.py shell
```

In the shell:
```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'This is a test email from Django.',
    'noreply@skilljobstraining.com',
    ['test@example.com'],
    fail_silently=False,
)
```

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in `.env`
- [ ] Generate a secure `SECRET_KEY`
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Configure PostgreSQL database
- [ ] Set up SMTP credentials (don't use Gmail in production)
- [ ] Configure proper SSL/TLS certificates
- [ ] Set up backup strategy for database
- [ ] Configure proper logging
- [ ] Use environment-specific `.env` files

## Notes

- **Never commit `.env` to git** - it contains sensitive information
- The `.env.example` file is provided as a template for developers
- Use `decouple` throughout the codebase instead of `os.getenv()`
- All configuration is centralized in `settings.py`
