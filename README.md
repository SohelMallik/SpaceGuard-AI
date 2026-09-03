<div align="center">

# 🛰️ SpaceGuard AI

### AI-Powered Spacecraft Health Monitoring & Mission Decision-Support System

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![IBM watsonx](https://img.shields.io/badge/IBM%20watsonx-Granite-0F62FE?style=flat-square&logo=ibm&logoColor=white)](https://www.ibm.com/watsonx)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

> **IBM AI Builders Challenge Submission**
> Built with **IBM Bob** · Powered by **IBM Granite via watsonx.ai**

[Overview](#-overview) · [Features](#-features) · [Screenshots](#-screenshots) · [Architecture](#-architecture) · [Installation](#-installation) · [API Reference](#-api-reference) · [Testing](#-testing)

</div>

---

## 📖 Overview

SpaceGuard AI transforms raw spacecraft telemetry into actionable mission insights. The system continuously monitors sensor readings across 9 parameters, detects multi-parameter anomalies using an Isolation Forest ML model, computes a transparent health score (0–100), predicts dangerous trends before they cross critical thresholds, and generates structured natural-language explanations powered by **IBM Granite** — all within a polished, dark-themed mission-control dashboard.

```
Raw Telemetry → AI Analysis → Anomaly Detection → Risk Assessment → Explanation → Recommended Action
```

### Problem Statement

Spacecraft generate large volumes of telemetry (temperature, battery voltage, fuel level, radiation, pressure, signal strength, velocity, and power consumption). Mission operators must analyze this stream quickly to identify abnormal behavior. Traditional dashboards display raw graphs but provide **no intelligence layer** — SpaceGuard AI closes that gap.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Mission Control Dashboard** | Dark-themed real-time UI built with Bootstrap 5 and Chart.js 4 |
| **Telemetry Ingestion** | Single-record REST API + bulk CSV upload with full validation |
| **AI Anomaly Detection** | Isolation Forest multi-parameter ML model with rule-based safety layer |
| **Health Score Engine** | Transparent 0–100 score with `score_breakdown` per contributing factor |
| **Predictive Monitoring** | Linear regression trend analysis with time-to-threshold warnings |
| **IBM Granite Explanation** | Structured AI output: problem · subsystem · severity · evidence · action |
| **AI Mission Assistant** | Conversational assistant powered by IBM Granite, grounded in live DB context |
| **Alert System** | Auto-generated, deduplicated, lifecycle-managed prioritized alerts |
| **Historical Analytics** | Parameter charts over time, alert logs, anomaly history |

---

## 📸 Screenshots

### 🛰️ Spacecraft Monitor · ☀️ Space Weather · 🌍 Mission Overview

| Spacecraft Monitor | Space Weather | Mission Overview |
|--------------------|---------------|------------------|
| ![Spacecraft Monitor](https://github.com/SohelMallik/SpaceGuard-AI/blob/1c6d756426e99c181a60acd8045cd179c585d303/Screenshots/Spacecraft%20Monitor.png) | ![Space Weather](https://github.com/SohelMallik/SpaceGuard-AI/blob/53e1924bba10471902f67bc150e8f29e13d5b947/Screenshots/Space%20Weather.png) | ![Mission Overview](https://github.com/SohelMallik/SpaceGuard-AI/blob/53e1924bba10471902f67bc150e8f29e13d5b947/Screenshots/Mission%20Overview.png) |

### 🚀 Launch Analyzer · 🤖 AI Insight · 📊 Risk History

| Launch Analyzer | AI Insight | Risk History |
|-----------------|-----------|--------------|
| ![Launch Analyzer](https://github.com/SohelMallik/SpaceGuard-AI/blob/78d0ce75af27a8281293c2dae7584a264a8f1de5/Screenshots/Launch%20Analyzer.png) | ![AI Insight](https://github.com/SohelMallik/SpaceGuard-AI/blob/78d0ce75af27a8281293c2dae7584a264a8f1de5/Screenshots/AI%20Insight.png) | ![Risk History](https://github.com/SohelMallik/SpaceGuard-AI/blob/78d0ce75af27a8281293c2dae7584a264a8f1de5/Screenshots/Risk%20History.png) |

### 🧠 Model Performance

| Model Performance |
|---|
| ![Model Performance](https://github.com/SohelMallik/SpaceGuard-AI/blob/a4221940a38f0943270b3f26f7d2cfb898b8c3e0/Screenshots/Model%20Performance.png) |

---

## 🧠 AI Architecture

### Pipeline Overview

```
Spacecraft Telemetry Record
          ↓
    Validation (Django REST Framework Serializer)
          ↓
    Data Preprocessing
          ↓
  ┌────────────────────────────────┐
  │  Isolation Forest              │
  │  ai/anomaly_detector.py        │ → anomaly_score · severity · affected_subsystem
  └────────────────────────────────┘
          ↓
  ┌────────────────────────────────┐
  │  Linear Regression             │
  │  ai/predictor.py               │ → trend · predicted_value · time_to_threshold
  └────────────────────────────────┘
          ↓
  ┌────────────────────────────────┐
  │  Risk Engine                   │
  │  ai/risk_engine.py             │ → health_score (0–100) · risk_level
  └────────────────────────────────┘
          ↓
  ┌────────────────────────────────┐
  │  IBM Granite via watsonx.ai    │
  │  ai/granite_service.py         │ → detected_problem · evidence · recommended_action
  └────────────────────────────────┘
          ↓
  Alert Service + Dashboard + REST API Response
```

### Anomaly Detection — Isolation Forest
- Trained on historical spacecraft telemetry records stored in the database
- Detects multi-parameter anomalies that single-threshold rules would miss
- Outputs: `anomaly_score`, `severity` (NORMAL/LOW/MODERATE/HIGH/CRITICAL), `suspicious_parameters`, `affected_subsystem`
- Supplemented by a safety-threshold rule-based layer for hard limit violations

### Health Scoring — Explainable Rule-Based + ML

Each record receives a health score starting at **100** with transparent deductions:

| Component | Deduction |
|---|---|
| Anomaly severity | 0 – 50 pts (NORMAL → CRITICAL) |
| Threshold violations | 2 pts per warning, 10 pts per critical breach |
| Trend penalty | Up to 10 pts for worsening critical parameters |

The `score_breakdown` dictionary is returned in every analysis response, showing each component's exact contribution.

| Score Range | Risk Level | Category |
|---|---|---|
| 90 – 100 | NORMAL | Excellent |
| 75 – 89 | LOW | Good |
| 60 – 74 | MODERATE | Moderate Risk |
| 40 – 59 | HIGH | High Risk |
| 0 – 39 | CRITICAL | Critical |

### Predictive Monitoring — Linear Regression
- Fits a linear model over the **last 20 telemetry records** per mission
- Computes slope to estimate time-to-threshold for `temperature`, `battery_voltage`, and `signal_strength`
- Generates plain-English warning messages surfaced on the dashboard

### Generative AI — IBM Granite (ibm/granite-13b-instruct-v2)
- Receives a structured JSON context assembled **entirely from database values** — the model is never given latitude to invent sensor readings
- Prompt explicitly instructs: *"Use ONLY the telemetry values provided below. Do NOT invent or estimate any sensor readings."*
- Parses the response into 6 structured fields: `detected_problem`, `affected_subsystem`, `severity`, `evidence`, `possible_cause`, `recommended_action`
- Rule-based fallback is returned when the watsonx API is unreachable, clearly labeled `"Rule-Based Fallback"`

---

## 🏗️ System Architecture

```
SpaceGuard-AI/
├── backend/
│   ├── manage.py
│   ├── spaceguard/              # Django project: settings, root URLs, exception handler
│   ├── missions/                # Mission model, MissionViewSet, dashboard views
│   ├── telemetry/               # Telemetry model, ingestion API, CSV upload, seed command
│   ├── anomaly/                 # AIAnalysis model (stores pipeline results)
│   ├── alerts/                  # Alert model, AlertService (deduplication), AlertViewSet
│   ├── assistant/               # AI Mission Assistant app
│   └── ai/
│       ├── anomaly_detector.py  # Isolation Forest service + subsystem classifier
│       ├── risk_engine.py       # Health score computation with score_breakdown
│       ├── predictor.py         # Linear regression trend predictor
│       ├── granite_service.py   # IBM Granite / watsonx.ai REST integration
│       └── pipeline.py          # Orchestrates the full analysis pipeline
├── data/
│   ├── generate_sample.py       # Synthetic demo dataset generator
│   └── sample_telemetry.csv     # 200-record demo dataset with built-in anomaly scenario
├── models/                      # Cached ML model artifacts (joblib)
├── templates/
│   ├── base.html                # Base template with dark mission-control theme
│   ├── dashboard/               # Home, mission overview, launch analyzer pages
│   └── analytics/               # Risk history, anomaly explorer
├── static/
│   ├── css/                     # Mission-control dark theme stylesheet
│   └── js/                      # Chart.js wrappers, AI assistant chat interface
└── docs/                        # Architecture plan and API documentation
```

---

## 🛠️ Technology Stack

| Layer | Technology | Version |
|---|---|---|
| **Backend** | Python | 3.13 |
| **Web Framework** | Django | 6.0.7 |
| **REST API** | Django REST Framework | 3.17.1 |
| **ML — Anomaly Detection** | scikit-learn (Isolation Forest) | 1.9.0 |
| **ML — Trend Prediction** | scikit-learn (Linear Regression) | 1.9.0 |
| **Data Processing** | NumPy, Pandas | 2.5.1 / 3.0.5 |
| **Generative AI** | IBM Granite (ibm/granite-13b-instruct-v2) | — |
| **AI Platform** | IBM watsonx.ai | REST API v1 |
| **Database** | SQLite (dev) — PostgreSQL-ready | — |
| **Frontend** | Bootstrap 5 + Chart.js 4 + Vanilla JS | — |
| **Model Serialization** | joblib | 1.5.3 |
| **Primary Dev Tool** | IBM Bob | — |

---

## 🤖 How IBM Bob Was Used

IBM Bob was the **primary development tool** across the entire software development lifecycle:

- **Requirements Analysis** — Analyzed the product spec, identified core components, dependencies, and MVP scope
- **Architecture Planning** — Designed the 13-phase implementation plan, DB schema, AI pipeline, and REST API structure
- **Django Scaffolding** — Created the full project directory, initialized Django, and scaffolded all five apps
- **Model Development** — Wrote all four Django ORM models (Mission, Telemetry, Alert, AIAnalysis) with indexes, choices, and relationships
- **REST API** — Implemented all DRF serializers, ViewSets, custom actions, and URL routers
- **ML Integration** — Implemented Isolation Forest, Risk Engine, and Linear Regression as clean, testable service classes
- **IBM Granite Integration** — Full watsonx.ai REST API integration: IAM token exchange, prompt construction, response parsing, rule-based fallback
- **Frontend Development** — All Django templates with Bootstrap 5, Chart.js charts, dark theme CSS, and chat-interface JavaScript
- **Telemetry Simulation** — 200-record dataset generator with realistic progressive anomaly scenario
- **Testing** — 19 unit and integration tests covering models, APIs, anomaly detection, health scoring, alert service, and pipeline
- **Documentation** — This README and architecture plan documentation

---

## ⚙️ IBM Granite / watsonx.ai Integration

Implemented in [`backend/ai/granite_service.py`](backend/ai/granite_service.py).

### How it works

1. After anomaly detection and health scoring, a structured JSON context is assembled containing **only database-sourced telemetry values**
2. The prompt instructs Granite: *"Use ONLY the telemetry values provided below. Do NOT invent or estimate any sensor readings."*
3. IBM IAM bearer token is obtained via API key exchange (`POST https://iam.cloud.ibm.com/identity/token`)
4. The watsonx.ai text generation endpoint is called (`POST /ml/v1/text/generation`)
5. The response is parsed into structured fields: `detected_problem`, `affected_subsystem`, `severity`, `evidence`, `possible_cause`, `recommended_action`
6. On any API failure, a rule-based fallback is returned, clearly labeled `"Rule-Based Fallback"`

### Mission Assistant

The conversational assistant builds a context object from the live database (latest telemetry, health score, active alerts, latest AI analysis) and forwards it to Granite with the operator's natural-language question.

---

## 🚀 Installation

### Prerequisites

- Python 3.13+
- pip
- IBM watsonx.ai account with API key and Project ID ([sign up free](https://www.ibm.com/watsonx))

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/spaceguard-ai.git
cd spaceguard-ai

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🔧 Environment Configuration

Copy `.env.example` to `.env` inside the `SpaceGuard-AI/` directory and fill in your credentials:

```bash
cp SpaceGuard-AI/.env.example SpaceGuard-AI/.env
```

```env
# Django
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# IBM watsonx / Granite
WATSONX_API_KEY=your-ibm-api-key-here
WATSONX_PROJECT_ID=your-watsonx-project-id-here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-instruct-v2
```


---

## ▶️ Running the Application

```bash
# 1. Apply database migrations
python SpaceGuard-AI/backend/manage.py migrate

# 2. Generate the sample telemetry dataset
python SpaceGuard-AI/data/generate_sample.py

# 3. Seed the database with the demo mission and telemetry
python SpaceGuard-AI/backend/manage.py seed_telemetry

# 4. (Optional) Create a Django admin superuser
python SpaceGuard-AI/backend/manage.py createsuperuser

# 5. Start the development server
python SpaceGuard-AI/backend/manage.py runserver
```

Open **http://localhost:8000** in your browser.
Django admin panel: **http://localhost:8000/admin/**
DRF browsable API: **http://localhost:8000/api/**

---

## 🗂️ API Reference

### Missions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/missions/` | List all missions |
| `POST` | `/api/missions/` | Create a mission |
| `GET` | `/api/missions/{id}/` | Mission detail |
| `GET` | `/api/missions/{id}/health/` | Current health score + breakdown |
| `GET` | `/api/missions/{id}/anomalies/` | All anomalous telemetry records |
| `GET` | `/api/missions/{id}/alerts/` | Active alerts for this mission |
| `POST` | `/api/missions/{id}/analyze/` | **Run the full AI pipeline** on latest record |
| `POST` | `/api/missions/{id}/assistant/` | Send a question to the AI Mission Assistant |

### Telemetry

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/missions/{id}/telemetry/` | Ingest a single telemetry record |
| `POST` | `/api/missions/{id}/telemetry/upload/` | Bulk upload via CSV file |

### Alerts

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/alerts/` | All alerts (filterable by `status`, `mission`) |
| `PATCH` | `/api/alerts/{id}/` | Update alert status (NEW → INVESTIGATING → RESOLVED) |

Full interactive documentation is available at `/api/` via the DRF browsable interface.

### Example — Ingest Telemetry

```bash
curl -X POST http://localhost:8000/api/missions/1/telemetry/ \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2025-01-15T12:00:00Z",
    "temperature": 28.5,
    "battery_voltage": 27.8,
    "battery_current": 8.2,
    "fuel_level": 72.0,
    "radiation": 13.5,
    "pressure": 101.1,
    "signal_strength": -72.0,
    "velocity": 7.65,
    "power_consumption": 255.0
  }'
```

### Example — Run AI Analysis

```bash
curl -X POST http://localhost:8000/api/missions/1/analyze/
```

---

## 🧪 Testing

The test suite covers models, REST API, anomaly detection, health scoring, alert service, and pipeline integration — **19 tests total**.

```bash
cd SpaceGuard-AI/backend
python manage.py test tests --verbosity=2
```

### Test Coverage

| Suite | Tests | What is tested |
|---|---|---|
| `MissionModelTests` | 2 | `__str__`, default status |
| `TelemetryModelTests` | 2 | `__str__`, anomaly field defaults |
| `AlertModelTests` | 1 | Alert creation, default status |
| `AnomalyDetectorTests` | 3 | Normal result structure, threshold breach detection, subsystem classification |
| `RiskEngineTests` | 3 | Nominal score, critical severity deduction, `score_breakdown` presence |
| `MissionAPITests` | 4 | List, create, health endpoint, analyze with no data |
| `AlertAPITests` | 2 | List alerts, status lifecycle update |
| `AlertServiceTests` | 2 | Alert creation, duplicate suppression |

---

## 🎮 Demo Scenario

The bundled `data/sample_telemetry.csv` contains a built-in progressive degradation scenario:

| Records | State | Details |
|---|---|---|
| 1 – 140 | ✅ Normal operations | Temperature ~25°C · Battery ~28V · Signal ~-70 dBm |
| 141 – 200 | ⚠️ Progressive degradation | Temperature +0.45°C/record · Battery -0.08V/record · Signal -0.25 dBm/record |

### Running the demo

```bash
# Reset and seed the database
python SpaceGuard-AI/backend/manage.py seed_telemetry --reset

# Start the server
python SpaceGuard-AI/backend/manage.py runserver
```

1. Open **http://localhost:8000**
2. Click **"Run Analysis"** on the dashboard
   - AI detects the thermal/electrical/communication compound anomaly
   - IBM Granite generates a structured explanation and recommended action
3. Try the Mission Assistant with these questions:
   - *"Why did spacecraft health decrease?"*
   - *"Which subsystem has the highest risk?"*
   - *"What should mission operators investigate first?"*

---

## 🗄️ Data Model

```
Mission ──< Telemetry ──< AIAnalysis
   └──< Alert
```

| Model | Key Fields |
|---|---|
| `Mission` | `name`, `spacecraft_name`, `launch_date`, `status` |
| `Telemetry` | `timestamp`, `temperature`, `battery_voltage`, `fuel_level`, `radiation`, `pressure`, `signal_strength`, `velocity`, `power_consumption`, `is_anomaly`, `anomaly_score` |
| `AIAnalysis` | `telemetry` (FK), `health_score`, `risk_level`, `anomaly_result`, `explanation`, `predictions` |
| `Alert` | `mission` (FK), `telemetry` (FK), `subsystem`, `severity`, `status`, `description` |

---

## 🔮 Challenge Theme

**AI for Mission-Critical Systems** — Applying AI to spacecraft health monitoring, a domain where reliable anomaly detection and clear AI explanations directly support mission safety decisions.

---

## 👤 Team Information

| Field | Detail |
|---|---|
| **Developer** | Sohel Mallik |
| **Challenge** | IBM AI Builders Challenge |
| **Organization** | IBM BOB HACKATHON |
| **Primary Dev Tool** | IBM Bob |
| **AI Model** | IBM Granite (ibm/granite-13b-instruct-v2) via watsonx.ai |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ using **IBM Bob** · Powered by **IBM Granite** via **IBM watsonx.ai**

</div>
