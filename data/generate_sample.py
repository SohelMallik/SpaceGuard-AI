"""
SpaceGuard AI — Sample Telemetry Generator
Generates 200 realistic telemetry records for the demo scenario.

Normal operations: records 1-140
Anomaly onset:     records 141-200 (rising temp, falling battery voltage, weakening signal)

Run: python data/generate_sample.py
"""
import csv
import os
import numpy as np
from datetime import datetime, timezone, timedelta

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'sample_telemetry.csv')
SPACECRAFT_ID = 'ISS-Alpha'
START_TIME = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
INTERVAL_MINUTES = 5
N_RECORDS = 200

rng = np.random.default_rng(42)


def generate_normal(n: int, start_idx: int = 0):
    """Generate n records with normal operating parameters."""
    records = []
    for i in range(n):
        ts = START_TIME + timedelta(minutes=(start_idx + i) * INTERVAL_MINUTES)
        records.append({
            'timestamp': ts.isoformat(),
            'spacecraft_id': SPACECRAFT_ID,
            'temperature': round(rng.normal(25, 2.5), 2),
            'battery_voltage': round(rng.normal(28.0, 0.5), 2),
            'battery_current': round(rng.normal(8.0, 0.8), 2),
            'fuel_level': round(max(0, 75.0 - i * 0.05 + rng.normal(0, 0.3)), 2),
            'radiation': round(rng.normal(12.0, 2.0), 2),
            'pressure': round(rng.normal(101.3, 1.0), 2),
            'signal_strength': round(rng.normal(-70.0, 3.0), 2),
            'velocity': round(rng.normal(7.66, 0.05), 4),
            'power_consumption': round(rng.normal(250.0, 15.0), 2),
        })
    return records


def generate_anomalous(n: int, start_idx: int = 140):
    """Generate n records with progressive thermal + electrical + comm degradation."""
    records = []
    for i in range(n):
        ts = START_TIME + timedelta(minutes=(start_idx + i) * INTERVAL_MINUTES)
        # Progressive degradation
        temp = 25 + (i * 0.45) + rng.normal(0, 1.5)          # rising temperature
        voltage = 28.0 - (i * 0.08) + rng.normal(0, 0.3)     # falling voltage
        current = 8.0 + (i * 0.05) + rng.normal(0, 0.5)      # increasing current draw
        signal = -70.0 - (i * 0.25) + rng.normal(0, 2.0)     # weakening signal
        fuel = max(0, 68.0 - i * 0.05 + rng.normal(0, 0.3))  # normal fuel consumption
        radiation = 12.0 + (i * 0.15) + rng.normal(0, 1.5)   # slight radiation increase
        records.append({
            'timestamp': ts.isoformat(),
            'spacecraft_id': SPACECRAFT_ID,
            'temperature': round(float(temp), 2),
            'battery_voltage': round(float(max(5.0, voltage)), 2),
            'battery_current': round(float(current), 2),
            'fuel_level': round(float(fuel), 2),
            'radiation': round(float(radiation), 2),
            'pressure': round(rng.normal(101.3, 1.0), 2),
            'signal_strength': round(float(max(-150.0, signal)), 2),
            'velocity': round(rng.normal(7.66, 0.05), 4),
            'power_consumption': round(rng.normal(250.0 + i * 1.5, 15.0), 2),
        })
    return records


def main():
    normal_records = generate_normal(140, start_idx=0)
    anomaly_records = generate_anomalous(60, start_idx=140)
    all_records = normal_records + anomaly_records

    fieldnames = [
        'timestamp', 'spacecraft_id', 'temperature', 'battery_voltage', 'battery_current',
        'fuel_level', 'radiation', 'pressure', 'signal_strength', 'velocity', 'power_consumption',
    ]

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f'Generated {len(all_records)} telemetry records -> {OUTPUT_PATH}')
    print('Records 1-140: normal operations')
    print('Records 141-200: progressive thermal/electrical/comm degradation')


if __name__ == '__main__':
    main()
