# Health Data GenAI Analyzer

Analytics-first GenAI solution for conducting health data analysis, built as a case study prototype.

## Architecture

```
User Question (Streamlit UI)
    │
    ▼
FastAPI  (/api/v1/analyze)
    │
    ├─► Input safety check (prompt injection detection)
    ├─► Patient ID resolution (explicit field wins over NL extraction)
    ├─► Planner (LLM or regex-based fallback)
    │       ↓
    ├─► Structured analytics in Python/Pandas (ALWAYS deterministic)
    │       ↓
    ├─► Data sanitisation (PII redaction)
    ├─► Responder (LLM narrative or rule-based fallback)
    ├─► Output safety validation (hard-block unsafe text)
    │       ↓
    └─► JSON response with insights, recommendations, disclaimer, chart data
            │
            ▼
      Streamlit renders results + charts
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Temporary join** instead of permanent consolidation | Explicitly required by the case study |
| **Analytics-first, LLM-second** | Reduces hallucinations — structured results are always correct |
| **Works without OpenAI key** | Deterministic analytics + rule-based recommendations in no-key mode |
| **LangChain used minimally** | Prompt templates and optional chain orchestration only |
| **Stateless APIs** | Every request creates fresh temporary data; supports concurrent users |
| **Governance layer** | Health data requires PII redaction, output validation, disclaimers |
| **Hard-blocked unsafe output** | LLM-generated medical diagnoses/prescriptions are never returned to users |
| **Unit-neutral activity naming** | Physical_activity units are unknown; all names/labels avoid assuming "steps" |

## Setup

### 1. Clone and install

```bash
cd health-analysis
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and optionally add your OpenAI API key:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=your_key_here   # optional — app works fully without it
OPENAI_MODEL=gpt-4o-mini
DATASET_1_PATH=data/raw/health_dataset_1.csv
DATASET_2_PATH=data/raw/health_dataset_2.csv
LOG_LEVEL=INFO
```

**No-key mode:** Leave `OPENAI_API_KEY` empty or remove it. The analytics layer, intent detection, and rule-based recommendations remain fully functional. Only the LLM narrative layer is disabled.

### 3. Verify data files

Ensure both CSV files exist:
- `data/raw/health_dataset_1.csv` (patient-level data)
- `data/raw/health_dataset_2.csv` (daily activity history)

## Running the Application

### FastAPI backend

```bash
python scripts/run_api.py
```

Or directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Streamlit frontend

```bash
python scripts/run_streamlit.py
```

Or directly:

```bash
streamlit run streamlit_app/app.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check — app status, model configured, datasets loaded |
| GET | `/api/v1/dataset/summary` | Dataset overview — counts, columns, missing values |
| GET | `/api/v1/patients/{patient_id}` | Patient profile, activity features, summary |
| POST | `/api/v1/analyze` | Main NL analysis — question → insights + recommendations |
| POST | `/api/v1/cohort-analysis` | Structured cohort analysis with filters |
| POST | `/api/v1/evaluate` | Run predefined evaluation queries |
| GET | `/metrics` | Prometheus-style metrics |

### Example: Analyze

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Compare smokers vs non-smokers in terms of BMI and activity",
    "include_chart": true
  }'
```

### Example: Patient Lookup

```bash
curl http://localhost:8000/api/v1/patients/10
```

### Example: Cohort Analysis

```bash
curl -X POST http://localhost:8000/api/v1/cohort-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "filters": [{"field": "Age", "operator": ">", "value": 50}],
    "metrics": ["BMI", "avg_physical_activity_10d", "Blood_Pressure_Abnormality"]
  }'
```

## Stateless Design

All APIs are stateless:
- Datasets are loaded once at startup as **read-only shared reference data**
- Every request creates a **fresh temporary join** of the two datasets
- No user session state is stored in memory
- APIs support many concurrent users

## Governance & Compliance

Because this involves health-related data:

- **Input governance:** Patient IDs are redacted before LLM calls; prompt injection is detected and rejected
- **Output governance:** LLM output is scanned for diagnoses, prescriptions, and drug advice; unsafe text is **hard-blocked and replaced** — never returned to users
- **Mandatory disclaimer** appended to every response
- **No raw patient identifiers** are ever sent to the LLM
- **No raw full-table data** sent to the LLM — only aggregated/derived results

## Evaluation

The evaluation endpoint (`POST /api/v1/evaluate`) runs predefined test queries from `evaluation_queries.json` and reports:
- **Intent correctness** — did the planner detect the right intent?
- **Safety** — are disclaimers present and safety flags absent?
- **Latency** — average response time

## Fine-Tuning Note

The case study mentions fine-tuning/instruction-tuning. Full model fine-tuning was intentionally avoided because:
- The key problem is reliable reasoning over **structured tabular data**, not domain language adaptation
- **Instruction-tuning style prompt control** through strong system prompts achieves the needed behaviour
- Prompt files are external and editable (`prompts/` directory) for easy iteration

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
app/
├── main.py              # FastAPI entry point, dataset loading
├── api/                 # Route handlers
├── core/                # Config, logging, metrics, security
├── data/                # Loading, cleaning, feature engineering, joining
├── llm/                 # OpenAI client, planner, responder, validators
├── services/            # Business orchestration layer
├── schemas/             # Pydantic request/response models
└── utils/               # Charting, helpers, constants

config/                  # settings.yaml, field_mappings.yaml
prompts/                 # External prompt files
data/raw/                # Source CSV datasets
streamlit_app/           # Streamlit frontend
tests/                   # Pytest test suite
scripts/                 # Run scripts and data audit
```
