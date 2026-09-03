# SpaceGuard AI — Database Schema

## Entity Relationship Diagram

```
Mission
  id              BIGINT PK
  name            VARCHAR(200)
  description     TEXT (blank=True)
  spacecraft_name VARCHAR(200)
  launch_date     DATE (null=True)
  status          VARCHAR  ACTIVE | STANDBY | COMPLETED | LOST
  created_at      DATETIME (auto_now_add)

      |
      |  1 : many
      |
      +──< Telemetry
      |       id                BIGINT PK
      |       mission_id        FK → Mission
      |       timestamp         DATETIME  (db_index)
      |       temperature       FLOAT  °C
      |       battery_voltage   FLOAT  V
      |       battery_current   FLOAT  A
      |       fuel_level        FLOAT  %
      |       radiation         FLOAT  mSv
      |       pressure          FLOAT  kPa
      |       signal_strength   FLOAT  dBm
      |       velocity          FLOAT  km/s
      |       power_consumption FLOAT  W
      |       anomaly_score     FLOAT  (null=True)
      |       is_anomaly        BOOL   (default=False)
      |
      |       Composite index: (mission_id, timestamp)
      |
      +──< Alert
      |       id                 BIGINT PK
      |       mission_id         FK → Mission
      |       telemetry_id       FK → Telemetry (null=True)
      |       subsystem          VARCHAR  THERMAL | ELECTRICAL | COMMUNICATION |
      |                                   PROPULSION | NAVIGATION | RADIATION |
      |                                   ENVIRONMENTAL | UNKNOWN
      |       severity           VARCHAR  LOW | MODERATE | HIGH | CRITICAL
      |       description        TEXT
      |       recommended_action TEXT
      |       status             VARCHAR  NEW | INVESTIGATING | RESOLVED
      |       created_at         DATETIME (auto_now_add)
      |
      +──< AIAnalysis
              id             BIGINT PK
              mission_id     FK → Mission
              telemetry_id   FK → Telemetry (null=True)
              analysis_type  VARCHAR  ANOMALY | HEALTH | PREDICTION | EXPLANATION
              input_context  JSON   (structured telemetry context sent to LLM)
              result         JSON   (parsed AI output)
              raw_response   TEXT   (raw LLM response text)
              created_at     DATETIME (auto_now_add)
```

## Relationships

| Relationship | Cardinality | Cascade |
|---|---|---|
| Mission → Telemetry | 1 : many | DELETE CASCADE |
| Mission → Alert | 1 : many | DELETE CASCADE |
| Mission → AIAnalysis | 1 : many | DELETE CASCADE |
| Telemetry → Alert | 1 : many | SET NULL |
| Telemetry → AIAnalysis | 1 : many | SET NULL |

## Index Strategy

| Table | Index | Purpose |
|---|---|---|
| Telemetry | `(mission_id, timestamp)` | Fast time-series retrieval per mission |
| Telemetry | `timestamp` | Global chronological ordering |
| Alert | `(mission_id, status)` | Active alert lookups |

## Notes

- Database engine: **SQLite** (development). The schema is PostgreSQL-ready — swap `ENGINE` in `settings.py`.
- All models use `DEFAULT_AUTO_FIELD = BigAutoField` (64-bit integer PKs).
- `AIAnalysis.input_context` and `AIAnalysis.result` use Django's `JSONField` — stored as JSON text in SQLite, native JSONB in PostgreSQL.
