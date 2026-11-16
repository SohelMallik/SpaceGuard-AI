"""
Missions app serializers.

A DRF serializer converts Mission objects (Python) into JSON for the API,
and validates incoming JSON before it is saved to the database.
"""
from rest_framework import serializers
from missions.models import Mission


class MissionSerializer(serializers.ModelSerializer):
    """
    Exposes every field of the Mission model as JSON.

    Exposed fields: id, name, description, spacecraft_name, launch_date,
    status, created_at.
    Validation: 'status' must be one of the MissionStatus choices
    (Django enforces this automatically because of choices= on the model).
    """
    class Meta:
        model = Mission
        # '__all__' = every model field is included in the JSON output
        fields = '__all__'
        # Clients cannot set these — the DB/Django fills them in
        # (id comes from the database, created_at is auto_now_add).
        read_only_fields = ('id', 'created_at')
