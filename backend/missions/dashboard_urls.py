"""
Missions dashboard URL configuration (template views).
"""
from django.urls import path
from missions.views import dashboard_home, mission_dashboard, history_view

urlpatterns = [
    path('', dashboard_home, name='dashboard-home'),
    path('missions/<int:pk>/', mission_dashboard, name='mission-dashboard'),
    path('missions/<int:pk>/history/', history_view, name='mission-history'),
]
