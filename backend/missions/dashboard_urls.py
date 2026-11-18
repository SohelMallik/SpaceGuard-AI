"""
Missions dashboard URL configuration (template views).

These serve HTML pages (included at the site root by spaceguard/urls.py,
i.e. WITHOUT the /api/ prefix).
"""
from django.urls import path
from missions.views import dashboard_home, mission_dashboard, history_view, spaceguard_dashboard

urlpatterns = [
    path('', dashboard_home, name='dashboard-home'),
    #                              ^ redirects to the first active mission's
    #                                dashboard, or shows a mission list
    path('spaceguard/', spaceguard_dashboard, name='spaceguard-dashboard'),
    #                    ^ standalone Space Weather Intelligence SPA
    path('missions/<int:pk>/', mission_dashboard, name='mission-dashboard'),
    #                           ^ dashboard for one mission, e.g. /missions/1/
    path('missions/<int:pk>/history/', history_view, name='mission-history'),
    #                                   ^ historical analytics, e.g. /missions/1/history/
]
