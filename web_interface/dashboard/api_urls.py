"""
API URL patterns for dashboard app.
"""

from django.urls import path
from . import api_views

urlpatterns = [
    path('posts/', api_views.posts_list, name='api_posts'),
    path('trends/', api_views.trends_list, name='api_trends'),
    path('logs/', api_views.logs_list, name='api_logs'),
    path('stats/', api_views.stats_summary, name='api_stats'),
]


