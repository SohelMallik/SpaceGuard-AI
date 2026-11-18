from django.shortcuts import render

# Create your views here.

# The anomaly app does not define its own API views — AIAnalysis records are
# created by the AI pipeline (ai/pipeline.py) and read through the Mission
# API, e.g. GET /api/missions/{id}/health/ in missions/views.py.
