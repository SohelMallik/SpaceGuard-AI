# SpaceGuard AI
### AI-Powered Spacecraft Health Monitoring & Mission Decision-Support System

> **IBM AI Builders Challenge Submission**
> Built with **IBM Bob** | Powered by **IBM Granite via watsonx.ai**

---

## Project Overview

SpaceGuard AI transforms raw spacecraft telemetry into actionable mission insights. The system continuously monitors spacecraft sensor readings, detects multi-parameter anomalies using machine learning, scores overall spacecraft health, predicts dangerous trends before they reach critical thresholds, and generates clear natural-language explanations powered by IBM Granite — all within a polished mission-control dashboard.

---

## Problem Statement

Spacecraft generate large volumes of telemetry (temperature, battery voltage, fuel level, radiation, pressure, signal strength, velocity, power consumption). Mission operators must analyze this information quickly to identify abnormal behavior. Traditional dashboards display raw data and graphs but offer no intelligence layer.

**SpaceGuard AI transforms:**

```
Raw Telemetry → AI Analysis → Anomaly Detection → Risk Assessment → Explanation → Recommended Action
```

---

## Proposed Solution

A full-stack AI-powered web application that:

1. Ingests real-time or CSV-uploaded spacecraft telemetry
2. Runs Isolation Forest multi-parameter anomaly detection on every record
3. Computes a transparent health score (0–100) with risk levels
4. Predicts future parameter values using linear regression trend analysis
5. Calls IBM Granite via watsonx.ai to generate structured natural-language explanations
6. Automatically creates prioritized alerts for operator attention
7. Provides a conversational AI mission assistant backed by IBM Granite

---

## Selected Challenge Theme

**AI for Mission-Critical Systems** — Applying AI to spacecraft health monitoring, a domain where reliable anomaly detection and clear AI explanations directly support mission safety.

---

## Key Features

| Feature | Description |
|---|---|
| Mission Control Dashboard | Dark-themed, real-time mission-control UI with Bootstrap 5 |
| Telemetry Ingestion | Single-record API + bulk CSV upload with validation |
| AI Anomaly Detection | Isolation Forest multi-parameter ML model |
| Health Score Engine | 0–100 score with transparent score_breakdown |
| Predictive Monitoring | Linear regression time-to-threshold warnings |
| IBM Granite Explanation | Structured AI explanation with evidence and recommended action |
| AI Mission Assistant | Conversational assistant powered by IBM Granite |
| Alert System | Automatic alerts with duplicate suppression and lifecycle management |
| Historical Analytics | Charts for all parameters over time + alert log |

---

## AI Approach

### Anomaly Detection — Isolation Forest
- Trained on spacecraft telemetry data
- Detects multi-parameter anomalies that single-threshold checks would miss
- Returns anomaly score, severity, suspicious parameters, and affected subsystem
- Supplemented by safety-threshold rule-based layer

### Health Scoring — Rule-Based + ML
- Deducts points for anomaly severity, threshold violations, and worsening trends
- Returns explainable `score_breakdown` dict showing each component's contribution

### Predictive Monitoring — Linear Regression
- Fits linear regression over last 20 telemetry records
- Computes slope to estimate time-to-threshold for key parameters
- Generates plain-English warning messages

### Generative AI — IBM Granite
- Receives structured JSON context built entirely from database-sourced values
- Explicitly instructed not to invent sensor readings
- Generates structured analysis: problem, subsystem, severity, evidence, cause, recommended action
- Rule-based fallback when watsonx API is unavailable, clearly labeled

---

## AI Architecture

```
Spacecraft Telemetry Record
          ↓
    Validation (Django Serializer)
          ↓
    Data Preprocessing
          ↓
  ┌───────────────────────────────┐
  │  Isolation Forest             │
  │  anomaly_detector.py          │→ anomaly_score, severity, subsystem
  └───────────────────────────────┘
          ↓
  ┌───────────────────────────────┐
  │  Linear Regression            │
  │  predictor.py                 │→ trend, predicted_value, time_to_threshold
  └───────────────────────────────┘
          ↓
  ┌───────────────────────────────┐
  │  Risk Engine                  │
  │  risk_engine.py               │→ health_score (0-100), risk_level
  └───────────────────────────────┘
          ↓
  ┌───────────────────────────────┐
  │  IBM Granite via watsonx.ai   │
  │  granite_service.py           │→ detected_problem, evidence, recommended_action
  └───────────────────────────────┘
          ↓
  Alert Service + Dashboard + API Response
```

---

## System Architecture

```
SpaceGuard-AI/
├── backend/
│   ├── manage.py
│   ├── spaceguard/          # Django project settings, URLs, exception handler
│   ├── missions/            # Mission model, ViewSet, dashboard views
│   ├── telemetry/           # Telemetry model, ingestion API, CSV upload, seed command
│   ├── anomaly/             # AIAnalysis model
│   ├── alerts/              # Alert model, AlertService, AlertViewSet
│   ├── assistant/           # Assistant app (endpoint in missions/views.py)
│   └── ai/
│       ├── anomaly_detector.py   # Isolation Forest service
│       ├── risk_engine.py        # Health score computation
│       ├── predictor.py          # Trend prediction
│       ├── granite_service.py    # IBM Granite / watsonx integration
│       └── pipeline.py           # Pipeline orchestrator
├── data/
│   ├── generate_sample.py        # Demo data generator
│   └── sample_telemetry.csv      # 200-record demo dataset
├── models/                       # Cached ML model artifacts
├── templates/
│   ├── base.html
│   ├── dashboard/
│   └── analytics/
├── static/css/ js/
└── docs/
```

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.13, Django 6.0, Django REST Framework 3.17 |
| AI/ML | scikit-learn (Isolation Forest, Linear Regression), NumPy, Pandas |
| Generative AI | IBM Granite (ibm/granite-13b-instruct-v2) via IBM watsonx.ai |
| Database | SQLite (prototype) — PostgreSQL-ready |
| Frontend | Django Templates, Bootstrap 5, Chart.js 4, Vanilla JS |
| Primary Dev Tool | IBM Bob |
| Version Control | Git / GitHub |

---

## How IBM Bob Was Used

IBM Bob was the **primary development tool** used throughout the entire software development lifecycle of SpaceGuard AI:

- **Requirements Analysis** — Bob analyzed the full product specification and identified core components, dependencies, and MVP scope.
- **Architecture Planning** — Bob designed the 13-phase implementation plan, database schema, AI pipeline, and REST API structure, saved to `spaceguard-ai-plan.md`.
- **Django Project Scaffolding** — Bob created the complete project directory, initialized the Django project, and scaffolded all five Django apps.
- **Database Model Development** — Bob wrote all four Django ORM models (Mission, Telemetry, Alert, AIAnalysis) with proper relationships, indexes, choices, and validation.
- **REST API Implementation** — Bob implemented all DRF serializers, ViewSets, custom actions, and URL routers across all apps.
- **ML Integration** — Bob implemented the Isolation Forest anomaly detector, Risk Engine health scorer, and Linear Regression trend predictor as clean, testable service classes.
- **IBM Granite Integration** — Bob implemented the full watsonx.ai REST API integration including IAM token exchange, prompt construction with structured context injection, response parsing, and rule-based fallback.
- **Frontend Development** — Bob created all Django templates with Bootstrap 5, Chart.js interactive charts, dark mission-control theme CSS, and JavaScript for the chat interface and analysis trigger.
- **Telemetry Simulation** — Bob wrote the 200-record sample dataset generator with realistic anomaly scenarios.
- **Testing** — Bob wrote 19 unit and integration tests covering models, APIs, anomaly detection, health scoring, alert service, and pipeline validation.
- **Documentation** — Bob generated this README and the architecture plan documentation.

---

## IBM Granite / watsonx Integration

The integration is implemented in [`backend/ai/granite_service.py`](backend/ai/granite_service.py).

### How it works:
1. After anomaly detection and health scoring, a structured JSON context is assembled containing **only database-sourced telemetry values** — the model is never given latitude to invent readings.
2. The prompt explicitly instructs Granite: *"Use ONLY the telemetry values provided below. Do NOT invent or estimate any sensor readings."*
3. The watsonx.ai REST API is called with IBM IAM bearer token authentication.
4. The response is parsed into structured fields: detected_problem, affected_subsystem, severity, evidence, possible_cause, recommended_action.
5. If the API call fails, a rule-based fallback explanation is returned, clearly labeled as "Rule-Based Fallback".

### Mission Assistant:
The conversational assistant builds a context object from the database (latest telemetry, health score, active alerts, latest analysis) and sends it to Granite with the operator's question.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/spaceguard-ai.git
cd spaceguard-ai

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

WATSONX_API_KEY=your-ibm-api-key-here
WATSONX_PROJECT_ID=your-project-id-here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-instruct-v2
```

> **Never commit `.env` to version control.**

---

## Running the Application

```bash
# 1. Run database migrations
python SpaceGuard-AI/backend/manage.py migrate

# 2. Generate sample telemetry data
python SpaceGuard-AI/data/generate_sample.py

# 3. Seed the database with the demo mission
python SpaceGuard-AI/backend/manage.py seed_telemetry

# 4. Create admin user (optional)
python SpaceGuard-AI/backend/manage.py createsuperuser

# 5. Run the development server
python SpaceGuard-AI/backend/manage.py runserver

# Visit: http://localhost:8000
```

---

## API Documentation

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/missions/` | List all missions |
| POST | `/api/missions/` | Create a mission |
| GET | `/api/missions/{id}/` | Mission detail |
| GET | `/api/missions/{id}/health/` | Current health score |
| GET | `/api/missions/{id}/anomalies/` | Anomalous telemetry records |
| GET | `/api/missions/{id}/alerts/` | Mission alerts |
| POST | `/api/missions/{id}/analyze/` | Run full AI pipeline |
| POST | `/api/missions/{id}/assistant/` | AI mission assistant chat |
| POST | `/api/missions/{id}/telemetry/` | Ingest single telemetry record |
| POST | `/api/missions/{id}/telemetry/upload/` | Bulk CSV upload |
| GET | `/api/alerts/` | All alerts (filterable by status, mission) |
| PATCH | `/api/alerts/{id}/` | Update alert status |

Browse the full API at `/api/` (DRF browsable interface).

---

## Demo Scenario

The `data/sample_telemetry.csv` file contains a built-in anomaly scenario:

**Records 1–140:** Normal spacecraft operations
- Temperature: ~25°C, Battery: ~28V, Signal: ~-70 dBm

**Records 141–200:** Progressive degradation
- Temperature rises +0.45°C per record (reaching ~52°C)
- Battery voltage falls -0.08V per record
- Signal strength weakens -0.25 dBm per record

### Running the demo:
```bash
# 1. Seed the data
python SpaceGuard-AI/backend/manage.py seed_telemetry --reset

# 2. Start the server
python SpaceGuard-AI/backend/manage.py runserver

# 3. Open http://localhost:8000

# 4. Click "Run Analysis" on the dashboard
#    → AI detects the thermal/electrical/communication anomaly
#    → IBM Granite generates explanation and recommended action

# 5. Ask the mission assistant:
#    "Why did spacecraft health decrease?"
#    "Which subsystem has the highest risk?"
#    "What should mission operators investigate first?"
```

---

## Future Improvements

- **WebSocket real-time updates** — Replace polling with Django Channels for live dashboard
- **PostgreSQL migration** — Switch from SQLite for production scale
- **Advanced ML models** — LSTM autoencoder for temporal anomaly detection
- **Multi-mission comparison** — Side-by-side health scoring across missions
- **User authentication** — Role-based access: operator vs read-only viewer
- **Alert notifications** — Email/Slack webhook integration
- **Grafana export** — Time-series data export for external dashboards
- **Confidence scores** — Uncertainty quantification on Granite explanations

---

## Team Information

- **Developer:** Sohel Mallik
- **Organization:** [Your Organization]
- **Challenge:** IBM AI Builders Challenge
- **Primary Tool:** IBM Bob

---

## License

MIT License — see LICENSE file for details.
