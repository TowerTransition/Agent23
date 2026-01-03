"""
API views for AJAX requests.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from datetime import datetime, timedelta
from .models import ScheduledPost, TrendData, PostLog, EngagementStats


@login_required
def posts_list(request):
    """API endpoint for posts list."""
    platform = request.GET.get('platform')
    status = request.GET.get('status')
    
    posts = ScheduledPost.objects.all()
    if platform:
        posts = posts.filter(platform=platform)
    if status:
        posts = posts.filter(status=status)
    
    posts_data = [{
        'id': post.id,
        'post_id': post.post_id,
        'platform': post.platform,
        'status': post.status,
        'scheduled_time': post.scheduled_time.isoformat(),
        'posted_at': post.posted_at.isoformat() if post.posted_at else None,
    } for post in posts[:50]]
    
    return JsonResponse({'posts': posts_data})


@login_required
def trends_list(request):
    """API endpoint for trends list."""
    platform = request.GET.get('platform')
    days = int(request.GET.get('days', 7))
    
    trends = TrendData.objects.all()
    if platform:
        trends = trends.filter(platform=platform)
    
    date_from = datetime.now() - timedelta(days=days)
    trends = trends.filter(recorded_at__gte=date_from)
    
    trends_data = [{
        'id': trend.id,
        'platform': trend.platform,
        'trend_name': trend.trend_name,
        'trend_type': trend.trend_type,
        'volume': trend.volume,
        'relevance_score': trend.relevance_score,
        'recorded_at': trend.recorded_at.isoformat(),
    } for trend in trends[:100]]
    
    return JsonResponse({'trends': trends_data})


@login_required
def logs_list(request):
    """API endpoint for logs list."""
    platform = request.GET.get('platform')
    log_type = request.GET.get('log_type')
    
    logs = PostLog.objects.all()
    if platform:
        logs = logs.filter(platform=platform)
    if log_type:
        logs = logs.filter(log_type=log_type)
    
    logs_data = [{
        'id': log.id,
        'platform': log.platform,
        'log_type': log.log_type,
        'message': log.message,
        'created_at': log.created_at.isoformat(),
    } for log in logs[:100]]
    
    return JsonResponse({'logs': logs_data})


@login_required
def stats_summary(request):
    """API endpoint for statistics summary."""
    platform = request.GET.get('platform')
    
    posts = ScheduledPost.objects.all()
    stats = EngagementStats.objects.all()
    
    if platform:
        posts = posts.filter(platform=platform)
        stats = stats.filter(platform=platform)
    
    summary = {
        'total_posts': posts.count(),
        'posted': posts.filter(status='posted').count(),
        'scheduled': posts.filter(status='scheduled').count(),
        'failed': posts.filter(status='failed').count(),
        'avg_engagement': round(stats.aggregate(avg=Avg('engagement_rate'))['avg'] or 0.0, 2),
        'total_likes': stats.aggregate(total=Count('likes'))['total'] or 0,
        'total_shares': stats.aggregate(total=Count('shares'))['total'] or 0,
    }
    
    return JsonResponse(summary)


