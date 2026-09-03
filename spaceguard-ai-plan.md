# SpaceGuard AI — Implementation Plan

## Confirmed Design Decisions

- **IBM Granite model:** `ibm/granite-13b-instruct-v2` (model ID in `.env` as `WATSONX_MODEL_ID` for easy override)
- **watsonx credentials:** Live integration from Phase 9 (real API key + project ID available)
- **Analysis trigger:** Auto-analyze on every telemetry record ingestion — full pipeline runs automatically

---

## Top-Level Overview

**Goal:** Build a complete AI-powered spacecraft health monitoring and mission decision-support web application called SpaceGuard AI for the IBM AI Builders Challenge hackathon.

**Scope:** A Django-based full-stack application featuring real-time telemetry analysis, ML anomaly detection (Isolation Forest), spacecraft health scoring, predictive trend monitoring, IBM Granite-powered natural-language explanations, a conversational mission assistant, an alert system, and a polished mission-control dashboard.

**Primary Tool:** IBM Bob throughout the entire SDLC.

**Approach:** Incremental phase-by-phase delivery. MVP first (dashboard + anomaly detection + health score + AI explanation), then progressively add advanced features. Each phase produces runnable, testable artifacts.

**MVP Definition:**
1. Telemetry dashboard displaying live/simulated data
2. AI anomaly detection (Isolation Forest)
3. Mission health score
4. IBM Granite AI explanation
5. Recommended action output

**Non-goals for MVP:**
- PostgreSQL migration (SQLite only for prototype)
- React/Next.js frontend
- Autonomous flight-control commands
- Production deployment configuration

---

## Architecture Overview

```
SpaceGuard-AI/
├── backend/
│   ├── manage.py
│   ├── spaceguard/          # Django project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── missions/            # Mission CRUD, status, health aggregation
│   ├── telemetry/           # Telemetry ingestion, storage, upload
│   ├── anomaly/             # Anomaly detection results, subsystem mapping
│   ├── alerts/              # Alert lifecycle management
│   ├── assistant/           # Conversational AI endpoint
│   └── ai/
│       ├── anomaly_detector.py   # Isolation Forest ML service
│       ├── risk_engine.py        # Health score + risk level computation
│       ├── predictor.py          # Linear regression trend prediction
│       └── granite_service.py    # IBM Granite / watsonx API integration
├── data/
│   └── sample_telemetry.csv
├── models/                  # Persisted ML model artifacts (.pkl)
├── templates/               # Django HTML templates
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── docs/
│   ├── screenshots/
│   └── architecture/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Database Schema

### Mission
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| name | CharField(200) | |
| description | TextField | blank=True |
| spacecraft_name | CharField(200) | |
| launch_date | DateField | null=True |
| status | CharField choices | ACTIVE / STANDBY / COMPLETED / LOST |
| created_at | DateTimeField auto_now_add | |

### Telemetry
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| mission | ForeignKey Mission | on_delete=CASCADE |
| timestamp | DateTimeField | db_index=True |
| temperature | FloatField | °C |
| battery_voltage | FloatField | V |
| battery_current | FloatField | A |
| fuel_level | FloatField | % |
| radiation | FloatField | mSv |
| pressure | FloatField | kPa |
| signal_strength | FloatField | dBm |
| velocity | FloatField | km/s |
| power_consumption | FloatField | W |
| anomaly_score | FloatField | null=True |
| is_anomaly | BooleanField | default=False |

### Alert
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| mission | ForeignKey Mission | on_delete=CASCADE |
| telemetry | ForeignKey Telemetry | null=True |
| subsystem | CharField choices | see subsystem list |
| severity | CharField choices | LOW / MODERATE / HIGH / CRITICAL |
| description | TextField | |
| recommended_action | TextField | |
| status | CharField choices | NEW / INVESTIGATING / RESOLVED |
| created_at | DateTimeField auto_now_add | |

### AIAnalysis
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| mission | ForeignKey Mission | on_delete=CASCADE |
| telemetry | ForeignKey Telemetry | null=True |
| analysis_type | CharField choices | ANOMALY / HEALTH / PREDICTION / EXPLANATION |
| input_context | JSONField | structured telemetry fed to LLM |
| result | JSONField | parsed AI output |
| raw_response | TextField | LLM raw text |
| created_at | DateTimeField auto_now_add | |

---

## AI/ML Pipeline

```
Raw Telemetry Record
      ↓
Input Validation (Django serializer)
      ↓
Data Preprocessing (Pandas normalization)
      ↓
Isolation Forest Anomaly Detection → anomaly_score, is_anomaly, severity, subsystem
      ↓
Linear Regression Trend Prediction → predicted values, time-to-threshold estimates
      ↓
Subsystem Classification (rule-assisted mapping of suspicious parameters)
      ↓
Risk Engine → health_score (0–100), risk_level (NORMAL/LOW/MODERATE/HIGH/CRITICAL)
      ↓
IBM Granite Prompt Construction (structured JSON context — NO invented values)
      ↓
Granite Response Parsing → problem, subsystem, severity, evidence, cause, recommendation
      ↓
Alert Creation (if severity >= MODERATE)
      ↓
Dashboard + API Response
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/missions/ | List all missions |
| POST | /api/missions/ | Create mission |
| GET | /api/missions/{id}/ | Mission detail |
| PATCH | /api/missions/{id}/ | Update mission |
| GET | /api/missions/{id}/telemetry/ | Paginated telemetry history |
| POST | /api/missions/{id}/telemetry/ | Ingest single record |
| POST | /api/missions/{id}/telemetry/upload/ | CSV bulk upload |
| GET | /api/missions/{id}/health/ | Current health score + risk |
| GET | /api/missions/{id}/anomalies/ | Anomaly records |
| GET | /api/missions/{id}/alerts/ | Alerts list |
| PATCH | /api/alerts/{id}/ | Update alert status |
| POST | /api/missions/{id}/analyze/ | Run full AI pipeline on latest data |
| POST | /api/missions/{id}/assistant/ | Conversational mission assistant |

---

## IBM Granite / watsonx Integration Points

1. **Anomaly Explanation** (`/api/missions/{id}/analyze/`) — After anomaly detection and health scoring, a structured JSON context is assembled and sent to Granite. The prompt explicitly instructs the model not to invent sensor values.
2. **Mission Assistant** (`/api/missions/{id}/assistant/`) — User questions are combined with the stored latest telemetry + analysis results as system context before calling Granite.
3. **Fallback** — If the watsonx API is unavailable or returns an error, the system returns a rule-based explanation constructed from the anomaly detection results, clearly labeled as "Rule-Based Explanation (AI unavailable)".

---

## Sub-Tasks

---

### Phase 1 — Project Scaffolding & Django Setup

**Intent:** Create the complete directory structure, Django project, five Django apps, and all configuration files. Establish a runnable baseline.

**Expected Outcomes:**
- `python manage.py runserver` starts successfully
- Django admin is accessible
- All five apps are registered in INSTALLED_APPS
- `.env.example`, `.gitignore`, and `requirements.txt` exist
- SQLite database initializes

**Todo List:**
1. Create the full directory tree as specified in the Architecture Overview
2. Initialize a Python virtual environment
3. Install Django, djangorestframework, python-dotenv, pandas, numpy, scikit-learn, requests
4. Run `django-admin startproject spaceguard backend/`
5. Run `python manage.py startapp` for: missions, telemetry, anomaly, alerts, assistant
6. Create `backend/ai/` as a Python package (not a Django app)
7. Configure `settings.py`: INSTALLED_APPS, DATABASES (SQLite), STATIC_ROOT, MEDIA_ROOT, REST_FRAMEWORK defaults, environment variable loading via python-dotenv
8. Create `spaceguard/urls.py` with api/ prefix routing
9. Create `.env.example` with WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, SECRET_KEY, DEBUG
10. Create `.gitignore` excluding .env, __pycache__, *.pyc, db.sqlite3, models/*.pkl, venv/
11. Create `requirements.txt`

**Relevant Context:** Greenfield project. No existing files.

**Status:** [ ] pending

---

### Phase 2 — Database Models & Migrations

**Intent:** Define all Django ORM models with proper field types, relationships, indexes, choices, and validation. Run initial migrations to create the schema.

**Expected Outcomes:**
- All four models (Mission, Telemetry, Alert, AIAnalysis) are created
- `python manage.py migrate` runs without errors
- Models are registered in their respective `admin.py` files
- Model `__str__` methods return meaningful values
- Django admin shows all models with useful list_display fields

**Todo List:**
1. Define `Mission` model in `missions/models.py`
2. Define `Telemetry` model in `telemetry/models.py` with db_index on timestamp and mission
3. Define `Alert` model in `alerts/models.py` with subsystem and severity choices
4. Define `AIAnalysis` model in `anomaly/models.py`
5. Register all models in their respective `admin.py`
6. Run `python manage.py makemigrations` for all apps
7. Run `python manage.py migrate`
8. Write model-level unit tests covering field validation and __str__ methods

**Relevant Context:** Schema defined in Database Schema section above.

**Status:** [ ] pending

---

### Phase 3 — Telemetry Simulator & Sample Dataset

**Intent:** Create realistic sample telemetry data covering normal operations and the demo anomaly scenario (rising temperature + falling battery voltage + weakening signal). Provide both a CSV file and a Django management command to seed the database.

**Expected Outcomes:**
- `data/sample_telemetry.csv` exists with ~200 records
- First ~140 records are normal operating range
- Records 141–200 introduce progressive thermal + electrical + communication degradation
- `python manage.py seed_telemetry` successfully loads the CSV into the database under a sample mission

**Todo List:**
1. Write `data/generate_sample.py` script using NumPy to produce realistic sensor readings with normal noise
2. Embed anomalous patterns from record 141 onward: temperature +0.4°C/record, battery_voltage -0.05V/record, signal_strength -0.3dBm/record
3. Output `data/sample_telemetry.csv`
4. Create Django management command `telemetry/management/commands/seed_telemetry.py`
5. Management command creates a sample Mission ("Demo Mission", "ISS-Alpha") and bulk-inserts Telemetry records
6. Test: run `python manage.py seed_telemetry` and verify record count via Django shell

**Relevant Context:** Telemetry model fields defined in Phase 2. Demo scenario described in Section 12 of requirements.

**Status:** [ ] pending

---

### Phase 4 — REST API Layer

**Intent:** Implement all REST API endpoints using DRF serializers, ViewSets, and routers. Endpoints must be fully functional for telemetry ingestion, retrieval, and CSV upload before AI features are attached.

**Expected Outcomes:**
- All endpoints listed in REST API Endpoints table return correct HTTP status codes
- MissionSerializer, TelemetrySerializer, AlertSerializer, AIAnalysisSerializer are complete with validation
- CSV upload endpoint parses and bulk-inserts valid records and returns errors for invalid rows
- Pagination is applied to telemetry list endpoint
- API browsable interface is accessible at /api/

**Todo List:**
1. Create serializers for all four models in each app's `serializers.py`
2. Create ViewSets: MissionViewSet, TelemetryViewSet, AlertViewSet
3. Add custom actions: `@action` for health, anomalies, analyze, upload, assistant
4. Register ViewSets with DRF DefaultRouter in `spaceguard/urls.py`
5. Implement CSV upload parsing: use Pandas to read uploaded file, validate columns, bulk create Telemetry records
6. Add DRF pagination class (PageNumberPagination, page_size=50)
7. Wire auto-analysis: after successful Telemetry record creation, call the full AI pipeline service directly within the same request cycle (synchronous MVP approach)
8. Write API tests using DRF APITestCase for each endpoint
9. Test manually using Django browsable API or curl

**Relevant Context:** API endpoint table defined above. Telemetry serializer must validate all nine sensor fields are present and within plausible physical ranges.

**Status:** [ ] pending

---

### Phase 5 — AI Anomaly Detection

**Intent:** Implement the Isolation Forest anomaly detection service that scores incoming telemetry records and classifies them by severity and affected subsystem.

**Expected Outcomes:**
- `backend/ai/anomaly_detector.py` contains a clean `AnomalyDetector` class
- Detector trains on the sample dataset on first use and caches the model to `models/isolation_forest.pkl`
- Given a telemetry record, it returns: `anomaly_score`, `is_anomaly`, `severity`, `suspicious_parameters`, `affected_subsystem`
- The analyze API endpoint (`POST /api/missions/{id}/analyze/`) calls the detector and saves results to Telemetry and AIAnalysis records
- Subsystem mapping: temperature/pressure/radiation → Thermal/Environmental, battery_voltage/battery_current/power_consumption → Electrical Power, signal_strength → Communication, fuel_level → Propulsion, velocity → Navigation

**Todo List:**
1. Create `backend/ai/__init__.py`
2. Implement `AnomalyDetector` class in `anomaly_detector.py`:
   - `train(telemetry_queryset)` — fits IsolationForest, saves to disk
   - `load_or_train(mission)` — loads pkl if exists, otherwise trains
   - `analyze(telemetry_record)` — returns structured result dict
3. Implement subsystem classifier as a separate function `classify_subsystem(suspicious_params)`
4. Wire `AnomalyDetector` into the `analyze` action on MissionViewSet
5. Persist anomaly_score and is_anomaly back to the Telemetry record
6. Create AIAnalysis record with input_context and result
7. Write unit tests for `AnomalyDetector.analyze()` using deterministic test vectors

**Relevant Context:** Isolation Forest from scikit-learn. Feature columns: temperature, battery_voltage, battery_current, fuel_level, radiation, pressure, signal_strength, velocity, power_consumption.

**Status:** [ ] pending

---

### Phase 6 — Health Score & Risk Engine

**Intent:** Implement a modular, explainable health scoring algorithm that produces a 0–100 score and a named risk level from anomaly results and raw telemetry values.

**Expected Outcomes:**
- `backend/ai/risk_engine.py` contains `RiskEngine` class
- `compute_health(telemetry_record, anomaly_result)` returns: `health_score` (int 0–100), `risk_level` (NORMAL/LOW/MODERATE/HIGH/CRITICAL), `health_category` (string label), `score_breakdown` (dict showing component contributions)
- GET `/api/missions/{id}/health/` returns the health result for the most recent telemetry record
- Health score accounts for: anomaly severity (major contributor), out-of-threshold individual parameters, trend direction from last 10 records

**Todo List:**
1. Implement `RiskEngine` class with `compute_health()` method
2. Define safety thresholds as a configuration dict (not hardcoded constants)
3. Scoring components: base score 100, deduct for anomaly severity (0/5/15/30/50), deduct for each out-of-range parameter (2–10 pts each), deduct for worsening trend (0–10 pts)
4. Map final score to risk level and category
5. Add `score_breakdown` dict to response for explainability
6. Wire into analyze endpoint result and `/health/` endpoint
7. Write unit tests with known telemetry inputs verifying expected score ranges

**Relevant Context:** Health categories defined in Feature 4 of requirements: 90–100 Excellent, 75–89 Good, 60–74 Moderate Risk, 40–59 High Risk, 0–39 Critical.

**Status:** [ ] pending

---

### Phase 7 — Predictive Monitoring

**Intent:** Implement a linear regression-based predictor that estimates future parameter values and computes time-to-threshold warnings.

**Expected Outcomes:**
- `backend/ai/predictor.py` contains `TrendPredictor` class
- `predict(mission, parameter, horizon_minutes=15)` returns: `current_value`, `predicted_value`, `trend_direction` (RISING/FALLING/STABLE), `time_to_threshold_minutes` (null if not approaching), `warning_message`
- Prediction is computed over the most recent 20 telemetry records
- Analyze endpoint includes prediction results for temperature, battery_voltage, and signal_strength

**Todo List:**
1. Implement `TrendPredictor` with `predict()` using sklearn `LinearRegression` over timestamps
2. Define threshold boundaries per parameter (same config dict as RiskEngine)
3. Compute slope and extrapolate to threshold crossing if slope is moving toward limit
4. Generate human-readable warning_message when threshold crossing is within 30 minutes
5. Wire into analyze endpoint result
6. Write unit tests with synthetic trending data verifying predicted values and warnings

**Relevant Context:** Requires at least 5 telemetry records for a meaningful prediction. Return `{"trend_direction": "INSUFFICIENT_DATA"}` if fewer records exist.

**Status:** [ ] pending

---

### Phase 8 — Mission Control Dashboard (Frontend)

**Intent:** Build the mission-control dashboard using Django templates, Bootstrap 5, and Chart.js. The dashboard must be visually polished and suitable for a hackathon demo.

**Expected Outcomes:**
- GET `/` renders the main dashboard
- Dashboard displays: mission header, health score widget, risk level badge, 8 telemetry cards, 4 Chart.js charts (temperature, battery voltage, fuel level, signal strength over time)
- AI Insights panel shows latest anomaly result, explanation, and recommendation
- Active Alerts panel lists NEW and INVESTIGATING alerts
- Chat interface for mission assistant is present (UI only at this stage, wired up in Phase 10)
- Dashboard is responsive (Bootstrap 5 grid)
- Dark space-themed color scheme

**Todo List:**
1. Create `templates/base.html` with Bootstrap 5 CDN, Chart.js CDN, and dark theme CSS
2. Create `templates/dashboard/index.html` extending base
3. Implement 8 telemetry cards with status color coding (green/yellow/orange/red based on thresholds)
4. Implement health score circular widget using CSS
5. Implement Chart.js line charts fed from a Django view that serializes recent telemetry to JSON
6. Create `missions/views.py` with `DashboardView` passing context: latest telemetry, health, recent alerts, chart data
7. Create `static/css/spaceguard.css` for dark theme, custom card styles, health score widget
8. Create `static/js/dashboard.js` for Chart.js initialization and auto-refresh (polling `/api/missions/{id}/health/` every 10 seconds)
9. Create `static/js/assistant.js` for chat interface interaction (stub that logs to console until Phase 10)
10. Add URL route `/` → DashboardView, `/missions/{id}/` → mission-specific dashboard

**Relevant Context:** Chart.js 4.x. Bootstrap 5. No React. Templates in `templates/` directory configured in settings.py.

**Status:** [ ] pending

---

### Phase 9 — IBM Granite / watsonx Integration

**Intent:** Implement `GraniteService` that takes structured telemetry + anomaly context and returns a structured AI explanation. Add fallback rule-based explanation for when the API is unavailable.

**Expected Outcomes:**
- `backend/ai/granite_service.py` contains `GraniteService` class
- `explain_anomaly(context_dict)` builds a strict prompt, calls watsonx API, parses response into structured fields
- Response contains: `detected_problem`, `affected_subsystem`, `severity`, `evidence`, `possible_cause`, `recommended_action`, `generated_by` ("IBM Granite" or "Rule-Based Fallback")
- Prompt explicitly instructs the model: "Use only the provided telemetry values. Do not invent sensor readings."
- Service reads credentials from environment variables only
- Fallback generates a rule-based explanation from anomaly result dict when API call fails
- AIAnalysis record is updated with the parsed response
- Analyze endpoint returns the full explanation in its response

**Todo List:**
1. Implement `GraniteService` with `explain_anomaly()` and `ask_assistant()` methods
2. Construct the Granite prompt template as a module-level constant — structured JSON input + strict instruction block
3. Call watsonx.ai REST API (POST to `/ml/v1/text/generation`) with IBM IAM authentication
4. Parse response text: extract structured fields using a simple parsing strategy (look for labeled sections)
5. Implement `_fallback_explanation(anomaly_result)` that builds a rule-based string
6. Handle API errors gracefully: log the error, return fallback, never raise 500 to the user
7. Write unit tests with a mocked watsonx response verifying parsing logic

**Relevant Context:** watsonx.ai REST API. IAM token exchange endpoint. Granite model ID from environment. Credentials: WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL.

**Status:** [ ] pending

---

### Phase 10 — AI Mission Assistant

**Intent:** Implement the conversational mission assistant endpoint and wire it to the dashboard chat interface.

**Expected Outcomes:**
- POST `/api/missions/{id}/assistant/` accepts `{"question": "..."}`, returns `{"answer": "...", "source": "IBM Granite"}`
- Assistant uses current mission health, latest 5 telemetry records, and recent alerts as context
- Assistant refuses to invent sensor values — context is injected from the database
- Chat interface in the dashboard sends POST requests and appends responses to the conversation thread
- If no telemetry data exists, assistant responds: "Insufficient telemetry data is available to determine this."

**Todo List:**
1. Create `assistant/views.py` with `AssistantView` (APIView)
2. Build context assembly function: queries latest telemetry, health score, recent alerts, latest AIAnalysis explanation
3. Construct assistant prompt: system role (mission assistant, factual only) + injected context JSON + user question
4. Call `GraniteService.ask_assistant(context, question)`
5. Wire URL `/api/missions/{id}/assistant/` → AssistantView
6. Update `static/js/assistant.js` to POST to endpoint and render response in chat UI
7. Add conversation turn display: user message (right-aligned), AI response (left-aligned, labeled "SpaceGuard AI")
8. Write tests covering: question with data available, question with no telemetry, API failure fallback

**Relevant Context:** GraniteService implemented in Phase 9. Context dict must contain only database-sourced values.

**Status:** [ ] pending

---

### Phase 11 — Alert System & Historical Analytics

**Intent:** Implement automatic alert creation when anomalies exceed severity thresholds, alert status management, and historical analytics views.

**Expected Outcomes:**
- Alerts are automatically created when `severity >= MODERATE` during the analyze pipeline
- Duplicate alert suppression: do not create a new alert for the same subsystem if an unresolved alert already exists
- PATCH `/api/alerts/{id}/` allows status update to INVESTIGATING or RESOLVED
- Historical analytics page `/missions/{id}/history/` shows Chart.js charts for all 9 parameters over time
- Historical page shows a filterable alert log table
- Alerts panel on dashboard refreshes with latest alert data

**Todo List:**
1. Implement `AlertService` in `alerts/services.py` with `create_if_needed(mission, anomaly_result, telemetry)` method
2. Add duplicate suppression: query for open alerts on the same subsystem before creating
3. Wire AlertService into the analyze pipeline (after Granite explanation is complete so recommendation can be stored)
4. Implement `AlertViewSet` with list, retrieve, and partial_update actions
5. Create `templates/analytics/history.html` with Chart.js charts (all parameters) and alert log table
6. Create `missions/views.py` `HistoryView` that serializes last 200 telemetry records to JSON for charts
7. Write tests for duplicate suppression, alert creation, and status transitions

**Relevant Context:** Alert model defined in Phase 2. Severity choices: LOW / MODERATE / HIGH / CRITICAL. Only MODERATE and above trigger alert creation.

**Status:** [ ] pending

---

### Phase 12 — Testing, Security & Error Handling

**Intent:** Harden the application with comprehensive tests, security configurations, input validation, and proper error handling.

**Expected Outcomes:**
- Test coverage for models, APIs, anomaly detection, health scoring, alert creation, AI context generation
- All API keys sourced from environment variables only — verified by test
- CSRF protection enabled
- File upload validation: only .csv files accepted, max size enforced
- No 500 errors exposed to client: all exceptions caught and returned as structured JSON error responses
- Security settings: DEBUG=False in production config, ALLOWED_HOSTS, SECURE_* headers in production settings block

**Todo List:**
1. Write model unit tests (Phase 2 tests completion if not done)
2. Write API integration tests for all endpoints using APITestCase
3. Write `ai/` unit tests for AnomalyDetector, RiskEngine, TrendPredictor, GraniteService (mocked)
4. Add DRF exception handler in `spaceguard/exceptions.py` returning consistent `{"error": ..., "detail": ...}` JSON
5. Add file upload validation middleware/serializer: check MIME type, extension, max 10MB
6. Add production-safe settings block in settings.py gated on ENV variable
7. Verify no hardcoded credentials exist anywhere in codebase (grep check)
8. Add `SECURITY.md` documenting credential handling

**Relevant Context:** All prior phases must be complete before this phase. Use Django's TestCase and DRF's APITestCase.

**Status:** [ ] pending

---

### Phase 13 — README, Docs & Final Demo Preparation

**Intent:** Produce professional project documentation, architecture diagrams, a demo walk-through script, and finalize the project for GitHub submission.

**Expected Outcomes:**
- `README.md` contains all 21 sections required by Section 13 of the specification
- `docs/architecture/` contains at least one architecture diagram
- `data/sample_telemetry.csv` produces the full demo scenario when seeded
- The demo scenario (normal → degrading → WARNING) is reproducible end-to-end
- Project passes all tests
- `.env.example` is present; `.env` is in `.gitignore`

**Todo List:**
1. Write `README.md` with all required sections including "How IBM Bob Was Used" section
2. Create `docs/architecture/pipeline.md` describing the AI pipeline with an ASCII diagram
3. Create `docs/architecture/db_schema.md` with ERD description
4. Take screenshots of working dashboard for README
5. Write `docs/DEMO_SCRIPT.md` walking through the demo scenario step-by-step
6. Final run of `python manage.py test` — all tests must pass
7. Final run of application end-to-end: seed data → analyze → view dashboard → ask assistant
8. Create git repository, add all files, verify .gitignore excludes .env and db.sqlite3

**Relevant Context:** README requirements specified in Section 13. "How IBM Bob Was Used" must be honest and accurate.

**Status:** [ ] pending

---

## MVP vs Advanced Feature Separation

### MVP (Phases 1–9 core path)
- Django project + apps running
- Telemetry models and API
- Sample data seeding
- Isolation Forest anomaly detection
- Health score + risk level
- IBM Granite explanation
- Basic dashboard

### Advanced Features (Phases 10–13 + future)
- Conversational mission assistant (Phase 10)
- Alert lifecycle management (Phase 11)
- Historical analytics charts (Phase 11)
- Comprehensive test suite (Phase 12)
- Production security hardening (Phase 12)
- Full documentation (Phase 13)
- Future: PostgreSQL migration, WebSocket real-time updates, more advanced ML models, user authentication, multi-mission comparison

---

## Implementation Roadmap

| Phase | Description | Depends On |
|---|---|---|
| 1 | Project scaffolding & Django setup | — |
| 2 | Database models & migrations | Phase 1 |
| 3 | Telemetry simulator & sample dataset | Phase 2 |
| 4 | REST API layer | Phase 2 |
| 5 | AI anomaly detection | Phase 3, 4 |
| 6 | Health score & risk engine | Phase 5 |
| 7 | Predictive monitoring | Phase 5, 6 |
| 8 | Mission control dashboard | Phase 4, 6 |
| 9 | IBM Granite / watsonx integration | Phase 5, 6, 7 |
| 10 | AI mission assistant | Phase 9 |
| 11 | Alert system & historical analytics | Phase 8, 9 |
| 12 | Testing, security & error handling | All prior |
| 13 | README, docs & demo preparation | All prior |
