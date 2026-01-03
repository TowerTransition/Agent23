"""
Views for the dashboard app.
"""

import os
import json
import sys
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Avg
from datetime import datetime, timedelta
from .models import AgentConfig, ScheduledPost, TrendData, PostLog, EngagementStats

# Add parent directory to path to import agents
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


@login_required
def dashboard_home(request):
    """Main dashboard home page."""
    # Get recent stats
    recent_posts = ScheduledPost.objects.filter(status='posted').order_by('-posted_at')[:5]
    recent_trends = TrendData.objects.all().order_by('-recorded_at')[:10]
    recent_logs = PostLog.objects.filter(log_type='error').order_by('-created_at')[:5]
    
    # Count stats
    stats = {
        'total_posts_today': ScheduledPost.objects.filter(
            scheduled_time__date=timezone.now().date()
        ).count(),
        'pending_posts': ScheduledPost.objects.filter(status='scheduled').count(),
        'active_agents': AgentConfig.objects.filter(is_active=True).count(),
        'trends_today': TrendData.objects.filter(
            recorded_at__date=timezone.now().date()
        ).count(),
    }
    
    context = {
        'recent_posts': recent_posts,
        'recent_trends': recent_trends,
        'recent_logs': recent_logs,
        'stats': stats,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def agent_management(request):
    """Agent Management Panel."""
    agents = AgentConfig.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        agent_id = request.POST.get('agent_id')
        
        if action == 'toggle_active':
            agent = get_object_or_404(AgentConfig, id=agent_id)
            agent.is_active = not agent.is_active
            agent.save()
            messages.success(request, f"{agent.name} is now {'active' if agent.is_active else 'inactive'}")
        elif action == 'update_config':
            agent = get_object_or_404(AgentConfig, id=agent_id)
            # Update config data
            config_key = request.POST.get('config_key')
            config_value = request.POST.get('config_value')
            if config_key:
                agent.config_data[config_key] = config_value
                agent.save()
                messages.success(request, f"Updated {config_key} for {agent.name}")
    
    context = {
        'agents': agents,
    }
    return render(request, 'dashboard/agents.html', context)


@login_required
def scheduler_config(request):
    """Scheduler Configuration Panel."""
    posts = ScheduledPost.objects.all()
    
    # Filtering
    platform_filter = request.GET.get('platform')
    status_filter = request.GET.get('status')
    
    if platform_filter:
        posts = posts.filter(platform=platform_filter)
    if status_filter:
        posts = posts.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(posts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        post_id = request.POST.get('post_id')
        
        if action == 'delete':
            post = get_object_or_404(ScheduledPost, id=post_id)
            post.delete()
            messages.success(request, f"Deleted post {post.post_id}")
            return redirect('scheduler_config')
        elif action == 'reschedule':
            post = get_object_or_404(ScheduledPost, id=post_id)
            new_time = request.POST.get('new_time')
            if new_time:
                try:
                    post.scheduled_time = datetime.fromisoformat(new_time)
                    post.save()
                    messages.success(request, f"Rescheduled post to {post.scheduled_time}")
                except ValueError:
                    messages.error(request, "Invalid date format")
        elif action == 'cancel':
            post = get_object_or_404(ScheduledPost, id=post_id)
            post.status = 'cancelled'
            post.save()
            messages.success(request, f"Cancelled post {post.post_id}")
    
    context = {
        'page_obj': page_obj,
        'platform_filter': platform_filter,
        'status_filter': status_filter,
        'platforms': ScheduledPost.PLATFORMS,
        'statuses': ScheduledPost.STATUS_CHOICES,
    }
    return render(request, 'dashboard/scheduler.html', context)


@login_required
def trend_dashboard(request):
    """Trend Dashboard with charts and filters."""
    trends = TrendData.objects.all()
    
    # Filtering
    platform_filter = request.GET.get('platform')
    date_filter = request.GET.get('date')
    
    if platform_filter:
        trends = trends.filter(platform=platform_filter)
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            trends = trends.filter(recorded_at__date=filter_date)
        except ValueError:
            pass
    
    # Get top trends by platform
    top_trends_by_platform = {}
    for platform_code, platform_name in TrendData.PLATFORMS:
        top_trends_by_platform[platform_code] = trends.filter(
            platform=platform_code
        ).order_by('-volume')[:10]
    
    # Prepare chart data (last 7 days)
    chart_data = {}
    for platform_code, platform_name in TrendData.PLATFORMS:
        last_7_days = timezone.now() - timedelta(days=7)
        platform_trends = trends.filter(
            platform=platform_code,
            recorded_at__gte=last_7_days
        ).order_by('recorded_at')
        
        # Group by date and sum volumes
        daily_data = {}
        for trend in platform_trends:
            date_key = trend.recorded_at.strftime('%Y-%m-%d')
            if date_key not in daily_data:
                daily_data[date_key] = {'volume': 0, 'count': 0}
            daily_data[date_key]['volume'] += trend.volume
            daily_data[date_key]['count'] += 1
        
        dates = sorted(daily_data.keys())
        volumes = [daily_data[d]['volume'] for d in dates]
        
        chart_data[platform_code] = {
            'dates': dates,
            'volumes': volumes,
        }
    
    context = {
        'trends': trends[:50],  # Show latest 50
        'top_trends_by_platform': top_trends_by_platform,
        'chart_data': chart_data,
        'platform_filter': platform_filter,
        'date_filter': date_filter,
        'platforms': TrendData.PLATFORMS,
    }
    return render(request, 'dashboard/trends.html', context)


@login_required
def logs_stats(request):
    """Logs & Stats page."""
    logs = PostLog.objects.all()
    stats = EngagementStats.objects.all()
    
    # Filtering
    platform_filter = request.GET.get('platform')
    log_type_filter = request.GET.get('log_type')
    
    if platform_filter:
        logs = logs.filter(platform=platform_filter)
        stats = stats.filter(platform=platform_filter)
    if log_type_filter:
        logs = logs.filter(log_type=log_type_filter)
    
    # Pagination for logs
    log_paginator = Paginator(logs, 50)
    log_page_number = request.GET.get('log_page')
    log_page_obj = log_paginator.get_page(log_page_number)
    
    # Pagination for stats
    stats_paginator = Paginator(stats, 20)
    stats_page_number = request.GET.get('stats_page')
    stats_page_obj = stats_paginator.get_page(stats_page_number)
    
    # Aggregate stats
    total_errors = logs.filter(log_type='error').count()
    total_warnings = logs.filter(log_type='warning').count()
    avg_engagement = stats.aggregate(
        avg=Avg('engagement_rate')
    )['avg'] or 0.0
    
    context = {
        'log_page_obj': log_page_obj,
        'stats_page_obj': stats_page_obj,
        'platform_filter': platform_filter,
        'log_type_filter': log_type_filter,
        'platforms': PostLog.PLATFORMS,
        'log_types': PostLog.LOG_TYPES,
        'total_errors': total_errors,
        'total_warnings': total_warnings,
        'avg_engagement': round(avg_engagement, 2),
    }
    return render(request, 'dashboard/logs.html', context)

