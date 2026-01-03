# Daily Automation Setup - 8:00 AM Eastern

This document explains how to set up the automated daily cycle that runs at 8:00 AM Eastern time, searches for AI articles, and posts to all social media platforms.

## Overview

The system follows the schedule from `data.mdc` - **all tasks complete between 8:00 AM and 8:15 AM Eastern**:
- **8:00 AM Eastern** - Fetch latest trends and articles about AI solving real-world problems
- **8:05 AM Eastern** - Generate draft posts for all platforms (Twitter, Instagram, LinkedIn, Facebook)
- **8:06 AM Eastern** - Generate images (automatic during content creation)
- **8:10 AM Eastern** - Content ready for review (optional human step)
- **8:15 AM Eastern** - Post to all platforms immediately and log results

## How It Works

### 1. Daily Schedule
The orchestrator runs an endless loop following the `data.mdc` timeline - **all tasks must complete by 8:15 AM Eastern**:
- **8:00 AM** - Scans for trends on social media and searches for 2 articles about AI solving real-world problems
- **8:05 AM** - Generates platform-specific content for all platforms (Twitter, Instagram, LinkedIn, Facebook)
- **8:06 AM** - Generates images (automatic during content creation)
- **8:10 AM** - Content ready for human review (if enabled)
- **8:15 AM** - Posts to all platforms immediately and logs results
- **15-minute timeout** - All tasks must complete within this window (8:00-8:15 AM)

### 2. Article Search
The system searches for articles using:
- **NewsAPI** (if `NEWSAPI_KEY` is set)
- **Google News** (RSS or Custom Search API)
- **Fallback methods** if APIs are unavailable

Articles are about: **"AI solving real-world problems"**

### 3. Content Generation
For each platform, the system:
- Uses the trend report and articles as input
- Generates platform-specific content following brand guidelines
- Creates appropriate text, hashtags, and image descriptions

### 4. Posting
Content is posted immediately to all platforms at **8:15 AM Eastern**:
- **Twitter**
- **Instagram**
- **LinkedIn**
- **Facebook**

All posts go out simultaneously after the 15-minute preparation window.

## Setup Instructions

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Required for article search (optional but recommended)
NEWSAPI_KEY=your_newsapi_key  # Get from https://newsapi.org/
GOOGLE_NEWS_API_KEY=your_google_api_key  # Optional
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id  # Optional

# Timezone (defaults to America/New_York)
TIME_ZONE=America/New_York
```

### 2. Run the Orchestrator

Start the orchestrator in daemon mode:

```bash
python orchestrator.py --daemon
```

Or with custom settings:

```bash
python orchestrator.py \
  --daemon \
  --platforms twitter instagram linkedin facebook \
  --keywords "AI" "artificial intelligence" "machine learning" \
  --time-zone "America/New_York"
```

### 3. Verify It's Running

Check the logs:

```bash
tail -f orchestrator.log
```

You should see:
```
Orchestrator scheduled to run daily at 8:00 AM Eastern
All tasks must complete by 8:15 AM Eastern:
  08:00 AM - Fetch trends and articles
  08:05 AM - Generate content
  08:06 AM - Generate images
  08:10 AM - Review content (optional)
  08:15 AM - Post to all platforms immediately
Next run: 2025-01-XX 08:00:00 EST-0500
Orchestrator started - waiting for scheduled time
```

## Configuration Options

### Change the Run Time

Edit `orchestrator.py` line ~472:
```python
schedule.every().day.at("08:00").do(run_daily_at_8am)
```

Change `"08:00"` to your desired time (24-hour format).

### Change Timeout

Edit `orchestrator.py` in the `run_daily_cycle` method:
```python
def run_daily_cycle(self, timeout_minutes: int = 15):
```

Change `15` to your desired timeout in minutes.

### Change Article Search Query

Edit `agents/trend_scanner/article_searcher.py`:
```python
def __init__(self, search_query: str = "AI solving real world problems"):
```

Or pass it when initializing:
```python
self.article_searcher = ArticleSearcher(search_query="your custom query")
```

## Monitoring

### Log Files
- `orchestrator.log` - Main orchestrator logs
- `logs/post_log.json` - Post history and results

### Check Status
The orchestrator logs:
- When it starts waiting for 8 AM
- When the daily cycle begins
- Progress through each step
- Success/failure of each post
- Total time taken

## Troubleshooting

### Articles Not Found
- Check if `NEWSAPI_KEY` is set correctly
- Verify internet connection
- Check article searcher logs for errors

### Posts Not Going Out
- Verify API credentials for each platform
- Check `logs/post_log.json` for error details
- Ensure `--dry-run` is not enabled

### Timezone Issues
- Ensure `pytz` is installed: `pip install pytz`
- Verify timezone string is correct (e.g., "America/New_York")

## Manual Testing

Test the daily cycle manually:

```bash
python orchestrator.py --platforms twitter instagram linkedin facebook
```

This runs the cycle once immediately (without waiting for 8 AM).

## Stopping the Orchestrator

Press `Ctrl+C` to stop the orchestrator gracefully. It will:
- Finish any in-progress operations
- Stop the scheduler thread
- Save current state

