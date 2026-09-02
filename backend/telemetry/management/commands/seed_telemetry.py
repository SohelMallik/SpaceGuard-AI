"""
Django management command: seed_telemetry
Seeds the database with two demo missions and 200 sample telemetry records each.
"""
import os
import csv
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Resolve CSV path robustly from the monorepo root
_HERE = Path(__file__).resolve()
# commands/ -> management/ -> telemetry/ -> backend/ -> (SpaceGuard-AI or repo root)
# Try both one and two levels above backend/
_CANDIDATES = [
    _HERE.parents[4] / 'data' / 'sample_telemetry.csv',   # monorepo root
    _HERE.parents[3] / 'data' / 'sample_telemetry.csv',   # inside SpaceGuard-AI/
]


def _find_csv():
    for p in _CANDIDATES:
        if p.exists():
            return str(p)
    return None


class Command(BaseCommand):
    help = 'Seeds the database with two SpaceGuard AI demo missions and sample telemetry data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo missions before seeding.',
        )

    def handle(self, *args, **options):
        from missions.models import Mission
        from telemetry.models import Telemetry

        if options['reset']:
            Mission.objects.filter(spacecraft_name__in=['ISS-Alpha', 'Deep-Probe-1']).delete()
            self.stdout.write('Deleted existing demo missions.')

        # ── Mission 1: ISS-Alpha (reads from CSV) ───────────────────────
        mission1, created = Mission.objects.get_or_create(
            spacecraft_name='ISS-Alpha',
            defaults={
                'name': 'Demo Mission Alpha',
                'description': 'Low-Earth orbit monitoring mission. Demonstrates thermal and electrical anomaly detection.',
                'launch_date': '2024-01-15',
                'status': 'ACTIVE',
            }
        )
        verb = 'Created' if created else 'Using existing'
        self.stdout.write(self.style.SUCCESS(f'{verb} mission: {mission1}'))

        csv_path = _find_csv()
        if not csv_path:
            self.stderr.write(
                f'CSV not found. Searched: {[str(p) for p in _CANDIDATES]}. '
                'Run data/generate_sample.py first.'
            )
            return

        if not mission1.telemetry_records.exists():
            records_created = self._seed_from_csv(mission1, csv_path)
            self.stdout.write(self.style.SUCCESS(
                f'Seeded {records_created} telemetry records for "{mission1.name}".'
            ))
        else:
            self.stdout.write(f'Skipping CSV seed — {mission1.name} already has telemetry.')

        # ── Mission 2: Deep-Probe-1 (synthetic deep-space scenario) ────
        mission2, created2 = Mission.objects.get_or_create(
            spacecraft_name='Deep-Probe-1',
            defaults={
                'name': 'Deep Space Probe Mission',
                'description': 'Deep-space probe with elevated radiation exposure and communication challenges.',
                'launch_date': '2024-06-01',
                'status': 'ACTIVE',
            }
        )
        verb2 = 'Created' if created2 else 'Using existing'
        self.stdout.write(self.style.SUCCESS(f'{verb2} mission: {mission2}'))

        if not mission2.telemetry_records.exists():
            records2 = self._generate_deep_space(mission2)
            Telemetry.objects.bulk_create(records2)
            self.stdout.write(self.style.SUCCESS(
                f'Seeded {len(records2)} deep-space telemetry records for "{mission2.name}".'
            ))
        else:
            self.stdout.write(f'Skipping synthetic seed — {mission2.name} already has telemetry.')

        self.stdout.write(self.style.SUCCESS('\nSetup complete! Next steps:'))
        self.stdout.write(f'  POST /api/missions/{mission1.pk}/analyze/  ← run AI pipeline for ISS-Alpha')
        self.stdout.write(f'  POST /api/missions/{mission2.pk}/analyze/  ← run AI pipeline for Deep-Probe-1')
        self.stdout.write('  Visit: http://localhost:8000')

    # ------------------------------------------------------------------
    @staticmethod
    def _seed_from_csv(mission, csv_path) -> int:
        from telemetry.models import Telemetry
        bulk = []
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
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
        return len(bulk)

    @staticmethod
    def _generate_deep_space(mission) -> list:
        """Generate 150 synthetic deep-space telemetry records with radiation spike scenario."""
        from telemetry.models import Telemetry
        rng = np.random.default_rng(99)
        START = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        records = []
        for i in range(150):
            ts = START + timedelta(minutes=i * 10)
            # Deep space: colder, higher radiation, weaker signal, slower velocity
            anomalous = i >= 100  # last 50 records: radiation spike + signal degradation
            temp        = rng.normal(10, 3) + (i - 100) * 0.3 if anomalous else rng.normal(10, 3)
            battery     = max(16.0, rng.normal(26, 0.4) - (i - 100) * 0.06) if anomalous else rng.normal(26, 0.4)
            radiation   = rng.normal(30, 3) + (i - 100) * 0.8 if anomalous else rng.normal(30, 3)
            signal      = max(-145.0, rng.normal(-95, 4) - (i - 100) * 0.3) if anomalous else rng.normal(-95, 4)
            records.append(Telemetry(
                mission=mission,
                timestamp=ts,
                temperature=round(float(temp), 2),
                battery_voltage=round(float(battery), 2),
                battery_current=round(float(rng.normal(6, 0.5)), 2),
                fuel_level=round(float(max(0, 60 - i * 0.08 + rng.normal(0, 0.3))), 2),
                radiation=round(float(max(0, radiation)), 2),
                pressure=round(float(rng.normal(100, 0.8)), 2),
                signal_strength=round(float(signal), 2),
                velocity=round(float(rng.normal(15.2, 0.1)), 4),
                power_consumption=round(float(rng.normal(210, 12)), 2),
            ))
        return records
