# VendorClear AI — Vendor Intelligence Platform

> AI-powered vendor compliance and vendor intelligence platform for enterprise utility companies.  
> Built with React + Vite (frontend) and Node.js + Express + Gemini AI (backend).

---

## Project Overview

VendorClear AI automates the analysis of Certificates of Insurance (COI) and Vendor Diversity Certificates using Google Gemini AI. It extracts structured data from documents, applies rule-based compliance validation, calculates risk scores, and provides real-time dashboards and alerts for procurement and compliance teams.

**Core capabilities:**
- AI document analysis (COI, diversity certificates, general compliance docs)
- Insurance verification against configurable coverage thresholds
- Vendor diversity certification tracking (MBE, WBE, DBE, SBE, VOSB, HUBZone)
- Risk scoring engine (0–100, tiered Low / Medium / High)
- Proactive expiry alerts with configurable lead times
- Compliance trend analytics and board-ready reports
- Natural-language AI assistant for vendor queries

---

## Architecture

```
Browser (React SPA)
       │  HTTP/JSON
       ▼
Express API  (Node.js)
  ├─ Multer        → secure file upload
  ├─ Gemini AI     → document extraction
  ├─ Compliance Engine → rule-based validation
  └─ In-memory store  → (swap for PostgreSQL/MongoDB in prod)
```

---

## Folder Structure

```
vendorclear-ai/
├── client/                         # React + Vite frontend
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Sidebar.jsx
│       │   │   ├── Navbar.jsx
│       │   │   └── AppLayout.jsx
│       │   ├── ui/
│       │   │   ├── Button.jsx
│       │   │   ├── Badge.jsx
│       │   │   ├── Card.jsx
│       │   │   ├── Toast.jsx
│       │   │   └── Modal.jsx
│       │   └── dashboard/
│       │       ├── StatCard.jsx
│       │       ├── RiskMeter.jsx
│       │       └── Charts.jsx
│       ├── pages/
│       │   ├── Landing.jsx
│       │   ├── Dashboard.jsx
│       │   ├── Vendors.jsx
│       │   ├── Upload.jsx
│       │   ├── Analysis.jsx
│       │   ├── Reports.jsx
│       │   ├── Alerts.jsx
│       │   ├── Analytics.jsx
│       │   └── Settings.jsx
│       ├── hooks/
│       │   ├── useTheme.js
│       │   ├── useToast.js
│       │   └── useAnalysis.js
│       ├── services/
│       │   └── api.js               # Axios wrapper for all API calls
│       └── utils/
│           └── helpers.js
│
├── server/                          # Node.js + Express backend
│   ├── index.js                     # ← server_index.js
│   ├── package.json                 # ← server_package.json
│   ├── .env                         # ← copy from server_env_example.txt
│   ├── config/
│   │   └── index.js                 # ← server_config.js
│   ├── middleware/
│   │   ├── logger.js                # ← server_logger.js
│   │   ├── errorHandler.js          # ← server_errorHandler.js
│   │   ├── rateLimit.js             # ← server_rateLimit.js
│   │   └── uploadMiddleware.js      # ← server_uploadMiddleware.js
│   ├── services/
│   │   ├── geminiService.js         # ← server_geminiService.js
│   │   └── complianceEngine.js      # ← server_complianceEngine.js
│   ├── controllers/
│   │   └── index.js                 # ← server_controllers.js
│   ├── routes/
│   │   └── index.js                 # ← server_routes.js
│   ├── uploads/                     # auto-created at runtime
│   └── logs/                        # auto-created at runtime
│
└── README.md
```

> **Note:** The delivered backend files are prefixed `server_` (e.g. `server_index.js`).  
> Rename and place them in the folder structure above before running.

---

## Installation

### Prerequisites
- Node.js ≥ 18.0.0
- npm ≥ 9.0.0
- Google Gemini API key ([get one free](https://aistudio.google.com/app/apikey))

### 1 · Clone / set up folders

```bash
mkdir vendorclear-ai && cd vendorclear-ai
mkdir -p server/config server/middleware server/services server/controllers server/routes server/uploads server/logs
```

### 2 · Place backend files

Rename the delivered `server_*.js` files and move them into the structure above:

| Delivered file             | → Place at                            |
|----------------------------|---------------------------------------|
| `server_index.js`          | `server/index.js`                     |
| `server_package.json`      | `server/package.json`                 |
| `server_config.js`         | `server/config/index.js`              |
| `server_logger.js`         | `server/middleware/logger.js`         |
| `server_errorHandler.js`   | `server/middleware/errorHandler.js`   |
| `server_rateLimit.js`      | `server/middleware/rateLimit.js`      |
| `server_uploadMiddleware.js` | `server/middleware/uploadMiddleware.js` |
| `server_geminiService.js`  | `server/services/geminiService.js`    |
| `server_complianceEngine.js` | `server/services/complianceEngine.js` |
| `server_controllers.js`    | `server/controllers/index.js`         |
| `server_routes.js`         | `server/routes/index.js`              |

### 3 · Install dependencies

```bash
cd server
npm install
```

---

## Environment Variables

Copy `server_env_example.txt` → `server/.env` and fill in your values:

```env
PORT=5000
NODE_ENV=development
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
CLIENT_ORIGIN=http://localhost:5173
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=20
RATE_LIMIT_WINDOW_MIN=15
RATE_LIMIT_MAX_REQUESTS=100
ANALYZE_RATE_LIMIT_MAX=10
LOG_LEVEL=info
```

---

## Gemini API Setup

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key into your `.env` as `GEMINI_API_KEY`
4. The default model is `gemini-1.5-flash` (fast, free tier available)
5. For higher accuracy, change to `gemini-1.5-pro` in `.env`

> **Without an API key**, the server runs in **mock mode** — it returns realistic sample COI and diversity cert extractions so you can develop the frontend without a Gemini account.

---

## Run Backend

```bash
# Development (auto-restart on file changes)
cd server
npm run dev

# Production
npm start
```

Server starts on `http://localhost:5000` by default.

---

## Run Frontend

```bash
cd client
npm install
npm run dev
```

Frontend starts on `http://localhost:5173`.

---

## Build for Production

```bash
# Frontend
cd client && npm run build        # outputs to client/dist/

# Backend — set NODE_ENV=production in .env, then:
cd server && npm start
```

For production deployment, serve the `client/dist/` folder via Nginx or a CDN, and run the Express server behind a reverse proxy.

---

## API Reference

| Method | Endpoint              | Description                              |
|--------|-----------------------|------------------------------------------|
| GET    | `/api/health`         | Health check                             |
| POST   | `/api/upload`         | Upload document (multipart/form-data, field: `document`) |
| POST   | `/api/analyze`        | Analyze document with Gemini AI          |
| GET    | `/api/analysis/:id`   | Retrieve analysis result by ID           |
| POST   | `/api/evaluate`       | Run compliance rules on extracted JSON   |
| GET    | `/api/dashboard`      | Dashboard stats, trends, risk breakdown  |
| GET    | `/api/vendors`       | Vendor list (filterable, paginated)   |
| GET    | `/api/alerts`         | Active compliance alerts                 |
| GET    | `/api/reports`        | Compliance report summary                |

### Example: Upload + Analyze

```bash
# Step 1: Upload file
curl -X POST http://localhost:5000/api/upload \
  -F "document=@/path/to/acme-coi.pdf"
# → { "data": { "id": "uuid-here", ... } }

# Step 2: Analyze with Gemini
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{ "uploadId": "uuid-here", "documentTypeHint": "COI" }'
# → { "data": { "status": "COMPLIANT", "riskScore": 88, ... } }
```

### Example: Paste raw text

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "rawText": "CERTIFICATE OF INSURANCE ... [full document text]",
    "documentTypeHint": "COI"
  }'
```

---

## Compliance Rules

The compliance engine applies these rules automatically:

| Rule                  | Severity | Trigger                                      | Score Impact |
|-----------------------|----------|----------------------------------------------|-------------|
| GL_MISSING            | CRITICAL | No General Liability policy found            | −40         |
| GL_EXPIRED            | CRITICAL | GL policy expiry date is in the past         | −40         |
| GL_EXPIRING_SOON      | WARNING  | GL expires within 30 days                   | −15         |
| GL_BELOW_THRESHOLD    | HIGH     | GL aggregate < $2,000,000                   | −25         |
| WC_MISSING            | HIGH     | No Workers Comp policy found                 | −20         |
| WC_EXPIRED            | CRITICAL | WC policy expired                            | −30         |
| AUTO_BELOW_THRESHOLD  | MEDIUM   | Auto CSL < $500,000                         | −10         |
| NO_ADDITIONAL_INSURED | MEDIUM   | Company not listed as Additional Insured     | −8          |
| CERT_EXPIRED          | CRITICAL | Diversity cert expiry date is in the past    | −50         |
| LOW_OWNERSHIP         | HIGH     | Ownership < 51%                             | −25         |

**Status mapping:**
- Any CRITICAL finding → `NON_COMPLIANT`
- Any HIGH finding or score < 70 → `NEEDS_REVIEW`
- No HIGH/CRITICAL findings → `COMPLIANT`

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React 18, Vite, TailwindCSS, Framer Motion, Chart.js |
| Backend    | Node.js 18+, Express 4, Multer          |
| AI         | Google Gemini 1.5 Flash / Pro           |
| Security   | Helmet, CORS, express-rate-limit        |
| Logging    | Winston                                 |
| Validation | express-validator                       |

---

*© 2026 VendorClear AI, Inc. — Vendor Intelligence, Clarity Assured.*
