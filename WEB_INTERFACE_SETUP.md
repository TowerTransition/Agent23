# Django Web Interface Setup Guide

## Quick Start

1. **Install Django dependencies:**
   ```bash
   pip install Django djangorestframework
   ```

2. **Navigate to web interface directory:**
   ```bash
   cd web_interface
   ```

3. **Create database and migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create a superuser account:**
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create your admin account.

5. **Sync existing data from agents (optional):**
   ```bash
   python manage.py sync_agents
   ```
   This will import posts and trends from your existing log files.

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the dashboard:**
   - Open http://127.0.0.1:8000
   - Login with your superuser credentials

## Features

### 1. Dashboard Home (`/`)
- Overview statistics
- Recent posts
- Recent trends
- Recent errors

### 2. Agent Management (`/agents/`)
- View all agents (TrendScanner, ContentCreator, Scheduler)
- Toggle agents active/inactive
- Edit agent configurations
- Update scheduling parameters

### 3. Scheduler Configuration (`/scheduler/`)
- View all scheduled posts
- Filter by platform and status
- Reschedule posts
- Cancel or delete posts
- See posting history

### 4. Trend Dashboard (`/trends/`)
- View trending topics per platform
- Interactive charts showing trend evolution
- Filter by platform and date
- Top trends by volume and relevance

### 5. Logs & Stats (`/logs/`)
- API usage logs
- Error and warning tracking
- Post engagement statistics
- Filter by platform and log type

## Data Integration

The web interface reads data from:
- `logs/post_log.json` - Scheduled and posted content
- `data/trend_report.json` - Trend data from TrendScannerAgent

To keep data synchronized, run:
```bash
python manage.py sync_agents
```

You can set this up as a cron job or scheduled task to run periodically.

## Customization

### Change Time Zone
Edit `web_interface/settings.py`:
```python
TIME_ZONE = 'America/New_York'  # Change to your timezone
```

### Add Custom Styling
Edit `templates/base.html` to customize the Bootstrap theme.

### Add More Agents
Edit `dashboard/models.py` to add new agent types or fields.

## Production Deployment

For production:
1. Set `DEBUG = False` in `settings.py`
2. Set a secure `SECRET_KEY` environment variable
3. Configure proper database (PostgreSQL recommended)
4. Set up static file serving
5. Use a production WSGI server (gunicorn, uwsgi)

## Troubleshooting

**Issue: "No module named 'dashboard'"**
- Make sure you're in the `web_interface` directory
- Run `python manage.py` from the `web_interface` folder

**Issue: Database errors**
- Run `python manage.py migrate` to create tables

**Issue: No data showing**
- Run `python manage.py sync_agents` to import data
- Check that log files exist in the parent directory

**Issue: Login not working**
- Create a superuser: `python manage.py createsuperuser`
- Or use Django admin at `/admin/` to manage users


