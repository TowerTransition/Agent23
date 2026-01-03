"""
Models for the dashboard app.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class AgentConfig(models.Model):
    """Configuration for AI agents."""
    AGENT_TYPES = [
        ('trend_scanner', 'Trend Scanner Agent'),
        ('content_creator', 'Content Creator Agent'),
        ('scheduler', 'Scheduler Agent'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    agent_type = models.CharField(max_length=50, choices=AGENT_TYPES)
    is_active = models.BooleanField(default=True)
    config_data = models.JSONField(default=dict, help_text="Agent-specific configuration")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()})"


class ScheduledPost(models.Model):
    """Scheduled social media posts."""
    PLATFORMS = [
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('posted', 'Posted'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    post_id = models.CharField(max_length=100, unique=True)
    platform = models.CharField(max_length=50, choices=PLATFORMS)
    content = models.JSONField(help_text="Post content (text, images, etc.)")
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    posted_at = models.DateTimeField(null=True, blank=True)
    result_data = models.JSONField(default=dict, help_text="Post result data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_time']
        indexes = [
            models.Index(fields=['platform', 'status']),
            models.Index(fields=['scheduled_time']),
        ]
    
    def __str__(self):
        return f"{self.platform} - {self.post_id} - {self.status}"


class TrendData(models.Model):
    """Trending topics and hashtags data."""
    PLATFORMS = [
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
    ]
    
    platform = models.CharField(max_length=50, choices=PLATFORMS)
    trend_name = models.CharField(max_length=200)
    trend_type = models.CharField(max_length=50, help_text="hashtag, topic, article, etc.")
    volume = models.IntegerField(default=0, help_text="Tweet volume, engagement, etc.")
    relevance_score = models.FloatField(default=0.0)
    trend_data = models.JSONField(default=dict, help_text="Additional trend metadata")
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at', '-volume']
        indexes = [
            models.Index(fields=['platform', 'recorded_at']),
            models.Index(fields=['trend_name']),
        ]
    
    def __str__(self):
        return f"{self.platform}: {self.trend_name} ({self.volume})"


class PostLog(models.Model):
    """Logs of posted content and API interactions."""
    PLATFORMS = [
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
    ]
    
    LOG_TYPES = [
        ('post', 'Post'),
        ('api_call', 'API Call'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ]
    
    platform = models.CharField(max_length=50, choices=PLATFORMS)
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    message = models.TextField()
    log_data = models.JSONField(default=dict, help_text="Additional log data")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['platform', 'log_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.platform} - {self.log_type} - {self.created_at}"


class EngagementStats(models.Model):
    """Post engagement statistics."""
    post_id = models.CharField(max_length=100)
    platform = models.CharField(max_length=50)
    likes = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)
    stats_data = models.JSONField(default=dict)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-recorded_at']
        unique_together = ['post_id', 'platform']
        indexes = [
            models.Index(fields=['platform', 'recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.platform} - {self.post_id} - {self.engagement_rate}%"


