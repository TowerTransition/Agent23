"""
URL configuration for web_interface project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard pages
    path('', views.dashboard_home, name='home'),
    path('agents/', views.agent_management, name='agent_management'),
    path('scheduler/', views.scheduler_config, name='scheduler_config'),
    path('trends/', views.trend_dashboard, name='trend_dashboard'),
    path('logs/', views.logs_stats, name='logs_stats'),
    
    # API endpoints
    path('api/', include('dashboard.api_urls')),
]


