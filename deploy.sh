#!/bin/bash

cd /home/skilljobs/trainingnew

echo "📥 Pulling latest code..."
git pull

echo "🐍 Activating venv..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🗄 Running migrations..."
python manage.py migrate

echo "📁 Collecting static..."
python manage.py collectstatic --noinput

echo "🔄 Restarting service..."
sudo systemctl restart training

echo "✅ Deployment complete!"