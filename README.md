# 🚀 Skill.jobs Training Platform

A production-ready Django SaaS platform for managing courses, batches, enrollments, live classes, and attendance.

---

# 🏗️ Tech Stack

* **Backend**: Django 4.2
* **Database**: PostgreSQL (SQLite for development)
* **Frontend**: Django Templates + Tailwind CSS + Alpine.js
* **API**: Django REST Framework
* **Server**: Gunicorn + Nginx
* **SSL**: Let’s Encrypt

---

# 🌐 Live Deployment

👉 https://lms.skill.jobs

---

# 🏗️ Architecture

```
Internet (HTTPS)
        ↓
     Nginx (80/443)
        ↓
 Gunicorn (127.0.0.1:8001)
        ↓
     Django App
        ↓
    PostgreSQL
```

---

# 📁 Project Structure

```
skilltraining/
├── accounts/
├── core/
├── courses/
├── enrollments/
├── classes/
├── attendance/
├── dashboard/
├── skilltraining/
├── templates/
├── static/
├── manage.py
```

---

# ⚙️ Local Development Setup

## 1️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

## 3️⃣ Configure Database

Edit `settings.py` or `.env`:

```env
DB_TYPE=sqlite
```

or PostgreSQL:

```env
DB_TYPE=postgresql
DB_NAME=training_db
DB_USER=training_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

---

## 4️⃣ Run Migrations

```bash
python manage.py migrate
```

---

## 5️⃣ Create Superuser

```bash
python manage.py createsuperuser
```

---

## 6️⃣ Run Server

```bash
python manage.py runserver
```

---

# 🚀 Production Deployment (Ubuntu)

> Full setup based on live production server 

---

## 📁 Project Path

```
/home/skilljobs/trainingnew
```

---

## 🔐 Environment (.env)

```env
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=lms.skill.jobs

DB_TYPE=postgresql
DB_NAME=training_db
DB_USER=training_user
DB_PASSWORD=StrongPassword123
DB_HOST=localhost
DB_PORT=5432
```

---

## 🗄️ PostgreSQL Setup

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE training_db;
CREATE USER training_user WITH PASSWORD 'StrongPassword123';
ALTER DATABASE training_db OWNER TO training_user;

\c training_db
ALTER SCHEMA public OWNER TO training_user;
GRANT ALL ON SCHEMA public TO training_user;
```

---

## 📦 Django Setup

```bash
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py collectstatic --noinput
```

---

## ⚙️ Gunicorn

```bash
gunicorn skilltraining.wsgi:application --bind 127.0.0.1:8001
```

---

## 🔄 systemd Service

`/etc/systemd/system/training.service`

```ini
[Unit]
Description=Django Training App
After=network.target

[Service]
User=skilljobs
Group=www-data
WorkingDirectory=/home/skilljobs/trainingnew
Environment="PATH=/home/skilljobs/trainingnew/venv/bin"

ExecStart=/home/skilljobs/trainingnew/venv/bin/gunicorn \
    skilltraining.wsgi:application \
    --bind 127.0.0.1:8001 \
    --workers 3

Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable training
sudo systemctl start training
```

---

## 🌐 Nginx Configuration

`/etc/nginx/sites-available/training`

```nginx
server {
    server_name lms.skill.jobs;

    client_max_body_size 50M;

    location /static/ {
        alias /home/skilljobs/trainingnew/staticfiles/;
    }

    location /media/ {
        alias /home/skilljobs/trainingnew/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8001;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/lms.skill.jobs/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lms.skill.jobs/privkey.pem;
}

server {
    listen 80;
    server_name lms.skill.jobs;
    return 301 https://$host$request_uri;
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/training /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔐 SSL (Let’s Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d lms.skill.jobs
```

---

## 📁 Static & Media

### Django settings

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

# 🔄 Deployment Workflow

After code update:

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart training
```

---

# 🧪 Features

## Public

* Homepage, course listing, course details
* Instructor profiles
* About page

## Student

* Dashboard
* Enrollment requests
* Class access & attendance

## Instructor

* Manage sessions
* Mark attendance

## Admin

* Full Django admin control
* Course, batch, enrollment management

---

# 🔐 Security (Production)

```python
DEBUG = False
ALLOWED_HOSTS = ['lms.skill.jobs']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

# ⚠️ Common Issues

### Static 404

```bash
python manage.py collectstatic
```

### Media not loading

Use Nginx `alias`, not `root`

### 413 Upload Error

```nginx
client_max_body_size 50M;
```

### PostgreSQL permission error

```sql
ALTER SCHEMA public OWNER TO training_user;
```

---

# 🔍 Useful Commands

```bash
sudo systemctl status training
journalctl -u training -f
sudo systemctl restart training
sudo systemctl reload nginx
```

---

# 📌 Future Improvements

* CI/CD auto deploy
* S3 media storage
* DB backups
* Monitoring & alerts
* Rate limiting

---

# 📄 License

For training and educational use.

---

**Status**: ✅ Production Ready
**Domain**: https://lms.skill.jobs
**Stack**: Django + PostgreSQL + Gunicorn + Nginx
