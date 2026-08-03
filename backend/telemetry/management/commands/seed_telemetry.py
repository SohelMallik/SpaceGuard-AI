"""
Django management command: seed_telemetry
Seeds the database with the demo mission and 200 sample telemetry records.
"""
import os
import csv
import logging
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seeds the database with the SpaceGuard AI demo mission and sample telemetry data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo mission before seeding.',
        )

    def handle(self, *args, **options):
        from missions.models import Mission
        from telemetry.models import Telemetry

        if options['reset']:
            Mission.objects.filter(spacecraft_name='ISS-Alpha').delete()
            self.stdout.write('Deleted existing demo mission.')

        # Create or retrieve demo mission
        mission, created = Mission.objects.get_or_create(
            spacecraft_name='ISS-Alpha',
            defaults={
                'name': 'Demo Mission Alpha',
                'description': 'SpaceGuard AI demonstration mission for hackathon evaluation.',
                'launch_date': '2024-01-15',
                'status': 'ACTIVE',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created mission: {mission}'))
        else:
            self.stdout.write(f'Using existing mission: {mission}')

        # Load CSV — path: commands/ -> management/ -> telemetry/ -> backend/ -> SpaceGuard-AI/ -> data/
        csv_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'sample_telemetry.csv'
        ))

        if not os.path.exists(csv_path):
            self.stderr.write(f'CSV not found at {csv_path}. Run data/generate_sample.py first.')
            return

        records_created = 0
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            bulk = []
            for row in reader:
                ts = datetime.fromisoformat(row['timestamp'])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                bulk.append(Telemetry(
                    mission=mission,
                    timestamp=ts,
                    temperature=float(row['temperature']),
                    battery_voltage=float(row['battery_voltage']),
                    battery_current=float(row['battery_current']),
                    fuel_level=float(row['fuel_level']),
                    radiation=float(row['radiation']),
                    pressure=float(row['pressure']),
                    signal_strength=float(row['signal_strength']),
                    velocity=float(row['velocity']),
                    power_consumption=float(row['power_consumption']),
                ))
            Telemetry.objects.bulk_create(bulk)
            records_created = len(bulk)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {records_created} telemetry records for mission "{mission.name}".'
        ))
        self.stdout.write('Run the analysis pipeline: POST /api/missions/1/analyze/')
