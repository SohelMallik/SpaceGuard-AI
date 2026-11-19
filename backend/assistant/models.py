from django.db import models

# Create your models here.

# Assistant app has no database models of its own.
# The assistant reuses Mission / Telemetry / AIAnalysis / Alert data that
# lives in the other apps — see missions/views.py (assistant action).
