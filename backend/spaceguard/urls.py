"""
SpaceGuard AI — Root URL Configuration

This is the project's master routing table. It maps incoming URL paths to
views by delegating to each app's own `urls.py` (include(...)). Think of it
as the "front door": Django strips the matching prefix and hands the rest
of the path to the included app's URL patterns.

Route map:
    admin/               -> Django's built-in admin site
    api/                 -> missions app API  (missions, spacecraft data)
    api/                 -> telemetry app API (telemetry readings ingest)
    api/                 -> alerts app API    (alert records)
    api/health/          -> health probe (spaceguard/health.py)
    ""  (root)           -> dashboard HTML pages (missions.dashboard_urls)

Note: several apps share the `api/` prefix. Django tries each pattern in
order, so the first app whose URLs match wins. For example `/api/missions/`
is matched by missions.urls before the others even get a look.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from spaceguard.health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    # /admin/ — Django's built-in admin site for editing data by hand
    path('api/', include('missions.urls')),
    # /api/missions/... — mission CRUD + AI actions (health, anomalies,
    # alerts, weather, analyze, assistant). See missions/urls.py.
    path('api/', include('telemetry.urls')),
    # /api/missions/{id}/telemetry/ and /api/missions/{id}/telemetry/upload/
    # — sensor reading ingest. See telemetry/urls.py.
    path('api/', include('alerts.urls')),
    # /api/alerts/ and /api/alerts/{id}/ — alert list/update. See alerts/urls.py.
    path('api/health/', health_check, name='health-check'),
    # /api/health/ — tiny JSON probe used by uptime/monitoring checks
    path('', include('missions.dashboard_urls')),
    # / , /missions/{id}/ , /missions/{id}/history/ , /spaceguard/
    # — the HTML dashboard pages (no /api/ prefix)
]

# In development (DEBUG=True) Django does not serve uploaded files or
# static assets itself in production mode, so we append extra URL patterns
# that serve MEDIA_*/STATIC_* files straight from disk. In production a
# real web server (nginx etc.) handles these instead, which is why this
# only happens when DEBUG is on.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
