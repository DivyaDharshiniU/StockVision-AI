# Tech Stack & Build Commands

## Backend (Python)

- **Framework**: FastAPI 0.111 + Uvicorn
- **Data fetching**: yfinance 0.2.61 (async via ThreadPoolExecutor + asyncio.Semaphore)
- **Data processing**: pandas 2.2, NumPy 1.26
- **Config**: pydantic-settings 2.2 (loads from .env, project root)
- **Timezone**: pytz (IST / Asia/Kolkata)
- **Testing**: pytest 8.2 + Hypothesis 6.112 (property-based testing)
- **Python version**: 3.11+

## Frontend (TypeScript)

- **Framework**: React 18 + TypeScript 5.5
- **Build tool**: Vite 5
- **UI library**: AWS Cloudscape Design System 3.x
- **Charts**: Recharts 2.12
- **Testing**: Vitest 2
- **Node version**: 18+

## Common Commands

### Backend

```bash
# Create and activate virtualenv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend (from project root)
uvicorn backend.main:app --reload

# Run tests (from project root)
pytest tests/ -v
```

### Frontend

```bash
# Install dependencies (from frontend/)
cd frontend && npm install

# Run dev server (from frontend/)
npm run dev

# Build for production (from frontend/)
npm run build

# Run tests (from frontend/)
npm test
```

### Full Test Suite

```bash
pytest tests/ -v && cd frontend && npm test
```

## Environment Variables

Backend (project root `.env`):
- `CONCURRENCY_LIMIT` (default: 5) — max parallel yfinance downloads
- `REQUEST_TIMEOUT_S` (default: 10) — per-symbol HTTP timeout
- `CACHE_DIR` (default: .cache)

Frontend (`frontend/.env`):
- `VITE_API_BASE_URL` (default: http://localhost:8000)
