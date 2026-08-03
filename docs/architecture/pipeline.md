# SpaceGuard AI — Architecture Documentation

## AI Pipeline Flow

```
Spacecraft Telemetry Record Received (POST /api/missions/{id}/telemetry/)
    |
    v
[1] Input Validation
    Django REST Framework TelemetrySerializer validates all 9 sensor fields.
    Physical range checks: temperature (-100 to 300°C), battery_voltage (0-100V), etc.
    |
    v
[2] Telemetry Record Saved to SQLite
    Telemetry.objects.create(...)
    |
    v
[3] AI Pipeline Triggered (auto on ingestion)
    ai/pipeline.py :: run_analysis_pipeline(telemetry_record)
    |
    v
[4] Isolation Forest Anomaly Detection
    ai/anomaly_detector.py :: AnomalyDetector.analyze(record)
    - Load or train IsolationForest on mission telemetry
    - Score sample: predict() + score_samples()
    - Normalize score to [0, 1]
    - Check each parameter against THRESHOLDS dict
    - Classify severity: NORMAL / LOW / MODERATE / HIGH / CRITICAL
    - Map suspicious parameters to subsystem via SUBSYSTEM_MAP
    Output: { is_anomaly, anomaly_score, severity, suspicious_parameters, affected_subsystem }
    |
    v
[5] Trend Prediction
    ai/predictor.py :: TrendPredictor.predict_all(mission)
    - Fetch last 20 telemetry records per monitored parameter
    - Fit linear regression (numpy polyfit)
    - Compute predicted value at horizon_minutes=15
    - Estimate time-to-threshold crossing if slope trends toward limit
    Output: list of { parameter, current_value, predicted_value, trend_direction,
                       time_to_threshold_minutes, warning_message }
    |
    v
[6] Health Score Computation
    ai/risk_engine.py :: RiskEngine.compute_health(record, anomaly_result, recent_records)
    - Start from 100 points
    - Deduct: anomaly severity (0/5/15/30/50 pts)
    - Deduct: each out-of-threshold parameter (2-10 pts)
    - Deduct: worsening trend across recent records (0-10 pts)
    - Clamp to [0, 100]
    - Map to risk_level: NORMAL / LOW / MODERATE / HIGH / CRITICAL
    Output: { health_score, risk_level, health_category, score_breakdown }
    |
    v
[7] IBM Granite Explanation (only for non-NORMAL severity)
    ai/granite_service.py :: GraniteService.explain_anomaly(...)
    - Build structured JSON prompt with ONLY database-sourced values
    - Exchange IBM API key for IAM bearer token
    - POST to watsonx.ai /ml/v1/text/generation
    - Parse response for labeled sections
    - Fallback: rule-based explanation if API unavailable
    Output: { detected_problem, affected_subsystem, severity, evidence,
               possible_cause, recommended_action, generated_by }
    |
    v
[8] Alert Creation (if severity >= MODERATE)
    alerts/services.py :: AlertService.create_if_needed(...)
    - Check for existing unresolved alert on same subsystem (duplicate suppression)
    - Create Alert with description and recommended_action from Granite output
    |
    v
[9] AIAnalysis Record Saved
    anomaly/models.py :: AIAnalysis.objects.create(...)
    Stores: input_context (JSON), result (JSON), raw_response (str)
    |
    v
[10] API Response returned / Dashboard rendered
```

## Database ERD (Simplified)

```
Mission
  id | name | spacecraft_name | status | launch_date | created_at
    |
    +--< Telemetry
    |      id | mission_id | timestamp | temperature | battery_voltage |
    |         battery_current | fuel_level | radiation | pressure |
    |         signal_strength | velocity | power_consumption |
    |         anomaly_score | is_anomaly
    |
    +--< Alert
    |      id | mission_id | telemetry_id | subsystem | severity |
    |         description | recommended_action | status | created_at
    |
    +--< AIAnalysis
           id | mission_id | telemetry_id | analysis_type |
              input_context | result | raw_response | created_at
```

## Safety Thresholds Configuration

Defined in `backend/ai/anomaly_detector.py :: THRESHOLDS`:

| Parameter | Min | Max | Critical Limit |
|---|---|---|---|
| temperature | -50°C | 85°C | >100°C |
| battery_voltage | 22V | 32V | <18V |
| battery_current | -5A | 20A | >25A |
| fuel_level | 5% | 100% | <5% |
| radiation | 0 mSv | 50 mSv | >100 mSv |
| pressure | 95 kPa | 110 kPa | >120 kPa |
| signal_strength | -120 dBm | -40 dBm | <-130 dBm |
| velocity | 0 km/s | 30 km/s | >35 km/s |
| power_consumption | 0W | 500W | >600W |

## Subsystem Mapping

| Parameter | Subsystem |
|---|---|
| temperature | THERMAL |
| radiation | RADIATION |
| pressure | ENVIRONMENTAL |
| battery_voltage, battery_current, power_consumption | ELECTRICAL |
| signal_strength | COMMUNICATION |
| fuel_level | PROPULSION |
| velocity | NAVIGATION |
