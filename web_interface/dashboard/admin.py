"""
Django admin configuration for dashboard models.
"""

from django.contrib import admin
from .models import AgentConfig, ScheduledPost, TrendData, PostLog, EngagementStats


@admin.register(AgentConfig)
class AgentConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent_type', 'is_active', 'created_at']
    list_filter = ['agent_type', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = ['post_id', 'platform', 'status', 'scheduled_time', 'posted_at']
    list_filter = ['platform', 'status', 'scheduled_time']
    search_fields = ['post_id', 'platform']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'scheduled_time'


@admin.register(TrendData)
class TrendDataAdmin(admin.ModelAdmin):
    list_display = ['trend_name', 'platform', 'trend_type', 'volume', 'recorded_at']
    list_filter = ['platform', 'trend_type', 'recorded_at']
    search_fields = ['trend_name']
    readonly_fields = ['recorded_at']


@admin.register(PostLog)
class PostLogAdmin(admin.ModelAdmin):
    list_display = ['platform', 'log_type', 'message', 'created_at']
    list_filter = ['platform', 'log_type', 'created_at']
    search_fields = ['message']
    readonly_fields = ['created_at']


@admin.register(EngagementStats)
class EngagementStatsAdmin(admin.ModelAdmin):
    list_display = ['post_id', 'platform', 'likes', 'shares', 'engagement_rate', 'recorded_at']
    list_filter = ['platform', 'recorded_at']
    search_fields = ['post_id']
    readonly_fields = ['recorded_at', 'updated_at']


