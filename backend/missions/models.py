"""
Mission app models — Mission and MissionStatus definitions.
"""
from django.db import models


class MissionStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    STANDBY = 'STANDBY', 'Standby'
    COMPLETED = 'COMPLETED', 'Completed'
    LOST = 'LOST', 'Lost Contact'


class Mission(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    spacecraft_name = models.CharField(max_length=200)
    launch_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=MissionStatus.choices,
        default=MissionStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.spacecraft_name})'
