# Django Web Interface for AI Agents

A modern web dashboard for managing and monitoring AI agents, scheduled posts, trends, and analytics.

## Features

- **Agent Management Panel** - Configure and control AI agents
- **Scheduler Configuration** - View, reschedule, and manage scheduled posts
- **Trend Dashboard** - Visualize trending topics with charts
- **Logs & Stats** - Monitor API usage, errors, and engagement statistics

## Setup

1. **Install Django dependencies:**
   ```bash
   pip install Django djangorestframework
   ```

2. **Navigate to web_interface directory:**
   ```bash
   cd web_interface
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

5. **Sync existing data (optional):**
   ```bash
   python manage.py sync_agents
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the dashboard:**
   - Open http://127.0.0.1:8000 in your browser
   - Login with your superuser credentials

## Pages

- `/` - Dashboard home with overview stats
- `/agents/` - Agent Management Panel
- `/scheduler/` - Scheduler Configuration
- `/trends/` - Trend Dashboard with charts
- `/logs/` - Logs & Statistics

## Data Sync

The web interface can sync data from your existing agent system:

- **Post Logs** - Syncs from `logs/post_log.json`
- **Trend Data** - Syncs from `data/trend_report.json`

Run `python manage.py sync_agents`` periodically to keep data up to date.

## Integration

The dashboard integrates with your existing agents by:
- Reading log files from the agent system
- Displaying scheduled posts from the scheduler
- Showing trend data from TrendScannerAgent
- Monitoring API usage and errors

## Authentication

The interface uses Django's built-in authentication. Create users via:
```bash
python manage.py createsuperuser
```

Or use Django admin at `/admin/` to manage users.


