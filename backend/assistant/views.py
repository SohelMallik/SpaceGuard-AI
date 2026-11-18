from django.shortcuts import render
from django.contrib import admin


# Assistant app has no additional views — handled in missions/views.py assistant action
#
# How the assistant works: the frontend POSTs {"question": "..."} to
# /api/missions/{id}/assistant/. The MissionViewSet.assistant action gathers
# real facts from the database (latest telemetry, latest AI analysis, open
# alerts, space weather) into a context dict and passes it, along with the
# question, to the Granite LLM (ai/pipeline.py -> ask_assistant).
# This module is intentionally a placeholder that keeps the app importable.
