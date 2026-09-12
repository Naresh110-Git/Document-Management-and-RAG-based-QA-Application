# Document Management and RAG-based Q&A Application

Production-oriented FastAPI backend for authenticated document management, background PDF ingestion, embedding generation, vector search, and retrieval-augmented question answering (RAG).

## 1. Project Overview & Problem Statement

Modern enterprise applications require secure storage, indexing, and intelligent querying of domain documents. This application implements a complete, end-to-end RAG architecture:
- **Authentication & Security**: Multi-tenant user registration, JWT access/refresh token rotation, token version revocation (logout), and role-based access control (Admin vs. User).
- **Document Management**: Multi-format PDF upload, size and MIME type validation, file storage partitioned by user ID, and SHA256 checksum deduplication tracking.
- **Ingestion & Indexing**: PyMuPDF extraction with pdfplumber fallback, recursive character text chunking with offset tracking, local SentenceTransformer vector embeddings (`sentence-transformers/all-MiniLM-L6-v2`), and pgvector / vector persistence.
- **RAG Q&A Engine**: Query vector embedding, cosine similarity candidate retrieval, context-grounded prompt building with conversation history and strict citation requirements, and multi-provider LLM integration (Ollama, OpenAI, HuggingFace) with synchronous and Server-Sent Events (SSE) streaming output.
- **Operations & Observability**: Async background job queue for document processing, TTL document caching, request ID propagation, structured logging, sliding-window rate limiting (returning HTTP 429), and monitoring metrics endpoints.

---

## 2. Features

- **Auth & Accounts**:
  - `POST /api/v1/register` — Account registration with bcrypt hashing (work factor 12).
  - `POST /api/v1/login` — Authenticate and issue JWT access and refresh tokens.
  - `POST /api/v1/refresh` — Exchange refresh token for fresh token pair.
  - `POST /api/v1/logout` — Revoke active refresh tokens via user version increment.
  - `GET /api/v1/me` — Authenticated profile endpoint.
- **Document Ingestion & Management**:
  - `POST /api/v1/documents/upload` — Upload PDF files with validation and async background ingestion.
  - `GET /api/v1/documents/` — List owned documents with TTL caching.
  - `PUT /api/v1/documents/{id}` — Update title with ownership checks and cache invalidation.
  - `DELETE /api/v1/documents/{id}` — Delete file and database records with cache invalidation.
  - `POST /api/v1/documents/select` — Validate and select documents for targeted RAG retrieval.
  - `POST /api/v1/documents/reindex` — Recompute vector embeddings for user documents.
- **RAG & Chat**:
  - `POST /api/v1/chat/` — Submit question with optional document selection filter, retrieve grounded answer with citation metadata and latency tracking.
  - `POST /api/v1/chat/stream` — Stream response tokens over Server-Sent Events (`text/event-stream`).
  - `GET /api/v1/chat/history` — Fetch user conversation history.
  - `DELETE /api/v1/chat/history` — Clear conversation history.
- **Monitoring & Health**:
  - `GET /api/v1/health` — Service liveness and environment metadata.
  - `GET /api/v1/monitoring/metrics` — Live uptime, average request latency, and document count.
  - `GET /api/v1/monitoring/audit-log-count` — Count of security and audit events.
  - `GET /` — Root service discovery.

---

## 3. Architecture & Tech Stack

```mermaid
flowchart TD
  Client["Client Application / CLI"] --> API["FastAPI Application"]
  API --> MW["Middleware: Request Logging | Request ID | Rate Limiting | Metrics | CORS"]
  MW --> Router["API Router (/api/v1)"]
  Router --> AuthEndpoints["Auth APIs (/register, /login, /refresh, /me, /logout)"]
  Router --> DocEndpoints["Document APIs (/upload, /, /{id}, /select, /reindex)"]
  Router --> ChatEndpoints["Chat APIs (/, /stream, /history)"]
  Router --> MonitorEndpoints["Monitoring APIs (/health, /metrics, /audit-log-count)"]
  
  DocEndpoints --> DocSvc["DocumentService"]
  DocSvc --> BackgroundQueue["BackgroundTaskManager"]
  BackgroundQueue --> IngestSvc["IngestionService"]
  IngestSvc --> PyMuPDF["PyMuPDF / pdfplumber"]
  IngestSvc --> Chunker["RecursiveCharacterTextSplitter"]
  IngestSvc --> EmbSvc["EmbeddingService (SentenceTransformer)"]
  
  ChatEndpoints --> RAGSvc["RAGChatService"]
  RAGSvc --> EmbSvc
  RAGSvc --> VectorStore["pgvector / Cosine Similarity"]
  RAGSvc --> PromptEngine["Prompt Builder & Citations"]
  PromptEngine --> LLM["LLMService (Ollama | OpenAI | HuggingFace)"]
  
  AuthEndpoints --> AuthSvc["AuthService"]
  AuthSvc --> DB[(PostgreSQL + pgvector / SQLite)]
  DocSvc --> DB
  RAGSvc --> DB
```

### Technologies Used

| Layer | Component / Library |
|---|---|
| **Framework** | FastAPI, Starlette, Uvicorn |
| **Data Validation** | Pydantic v2, Pydantic-Settings |
| **Database & ORM** | PostgreSQL 16 with `pgvector`, SQLAlchemy 2.0 (Async), Alembic, SQLite (`aiosqlite` for tests) |
| **Security & Auth** | PyJWT (HS256), Bcrypt |
| **PDF Extraction** | PyMuPDF (fitz), pdfplumber |
| **Text Chunking** | LangChain Text Splitters (`RecursiveCharacterTextSplitter`) |
| **Vector Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`, 384 dimensions) |
| **LLM Inference** | Ollama REST API, OpenAI v1+ SDK, HuggingFace Inference API |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX |

---

## 4. Project Structure

```
.
├── docker-compose.yml              # PostgreSQL + pgvector and backend services
├── README.md                       # Comprehensive project documentation
└── backend/
    ├── Dockerfile                  # Container build definition
    ├── requirements.txt            # Python production and test dependencies
    ├── pyproject.toml              # Build system, package metadata, and pytest configuration
    ├── setup.py                    # Package installer script
    ├── alembic.ini                 # Database migrations configuration
    ├── .env.example                # Sample environment configuration template
    ├── app/
    │   ├── main.py                 # FastAPI application factory and lifespan manager
    │   ├── api/                    # API routes and dependency injection
    │   │   ├── router.py           # Master router
    │   │   ├── dependencies/       # Auth and service dependency providers
    │   │   └── v1/                 # Endpoints: auth, documents, chat, health, monitoring
    │   ├── core/                   # Config, security, exceptions, logging, request ID
    │   ├── database/               # Async engine, session maker, and Base model
    │   ├── middleware/             # Rate limit, metrics, request logging, request ID
    │   ├── models/                 # SQLAlchemy models: user, document, chunk, embedding, chat, audit
    │   ├── prompts/                # System prompts and grounded response templates
    │   ├── repositories/           # Data access layer for entities
    │   ├── schemas/                # Pydantic request and response models
    │   ├── services/               # Core business logic: auth, document, ingest, embeddings, rag, llm
    │   └── utils/                  # Request metadata extraction helpers
    ├── migrations/                 # Alembic migration scripts
    └── tests/                      # Unit, API, and End-to-End integration test suite
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.11+ (Python 3.12 or 3.13 recommended)
- Docker and Docker Compose (optional for local containerized deployment)
- PostgreSQL 16 with pgvector extension (or use Docker Compose)

### Local Environment Setup

1. **Clone the repository and enter the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows PowerShell**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   On Windows PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```

---

## 6. Environment Variables Configuration

Key configuration parameters in `.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://rag_user:rag_password@localhost:5432/rag_db` | Async SQLAlchemy database URL |
| `JWT_SECRET_KEY` | `change-me-in-production` | Secret key used to sign JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifespan in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifespan in days |
| `BCRYPT_ROUNDS` | `12` | Bcrypt hashing work factor (12-15) |
| `UPLOAD_DIR` | `uploads` | Directory for stored documents |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum upload size in Megabytes |
| `ALLOWED_UPLOAD_TYPES` | `application/pdf` | Allowed MIME types |
| `CHUNK_SIZE` | `1000` | Target chunk size in characters |
| `CHUNK_OVERLAP` | `200` | Character overlap between chunks |
| `RETRIEVAL_TOP_K` | `5` | Number of relevant chunks retrieved per query |
| `ACTIVE_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | SentenceTransformer model |
| `LLM_PROVIDER` | `ollama` | Active provider: `ollama`, `openai`, or `huggingface` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service base URL |
| `OLLAMA_MODEL` | `llama3.1` | Model name in Ollama |
| `OPENAI_API_KEY` | `""` | OpenAI API key (required if `LLM_PROVIDER=openai`) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `HUGGINGFACE_API_KEY` | `""` | Hugging Face user token |
| `HUGGINGFACE_MODEL` | `mistralai/Mistral-7B-Instruct-v0.3` | Hugging Face model repository |
| `RATE_LIMIT_REQUESTS` | `60` | Maximum requests permitted per client per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window duration in seconds |

---

## 7. Running the Application

### Option A: Using Docker Compose (Recommended for Full Stack)
Starts PostgreSQL with `pgvector` and the FastAPI backend service:
```bash
docker compose up --build
```
The API is accessible at `http://localhost:8000`.

### Option B: Running Locally with Uvicorn
Ensure database is available (or migrations executed):
```bash
# Run migrations
alembic upgrade head

# Start API service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verification & Documentation
- Health check:
  ```bash
  curl http://localhost:8000/api/v1/health
  ```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc UI: `http://localhost:8000/redoc`

---

## 8. Testing

The project includes an automated test suite with in-memory SQLite support for unit tests and integration tests.

Run all tests from the repository root:
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```
Or from the `backend/` directory:
```bash
pytest -v
```

### Test Suite Summary
- `test_auth_api.py`: Registration, login, refresh tokens, `/me`, and logout.
- `test_documents_api.py`: Upload, list, update, delete, document selection, and reindexing.
- `test_chat_history.py`: Q&A submission, SSE streaming, history query, and clearing.
- `test_chat_history_persistent.py`: Database persistence and session integration.
- `test_e2e_rag_workflow.py`: End-to-end user registration -> document upload -> ingestion -> vector embedding -> RAG answering -> streaming -> history.
- `test_middleware_monitoring.py`: Rate limiting 429 enforcement, live metrics, audit log count.
- `test_ingest.py`: PDF parsing and page text extraction.
- `test_llm_service.py`: Provider abstractions for Ollama, OpenAI, and HuggingFace.
- `test_rag_service.py`: Cosine similarity ranking, candidate retrieval, and prompt builder.
- `test_security.py`: Bcrypt password hashing and JWT encoding/decoding.
- `test_settings.py`: Pydantic settings parsing and validation rules.

---

## 9. Usage Examples

### 1. Register and Login
```bash
# Register
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "researcher@example.com", "password": "SecurePassword123!", "full_name": "Dr. Smith"}'

# Login
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email": "researcher@example.com", "password": "SecurePassword123!"}'
# Returns: {"access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 1800}
```

### 2. Upload Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@sample_paper.pdf"
```

### 3. Ask a Question (RAG)
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the primary methodology described in the document?"}'
```

### 4. Stream Answer via Server-Sent Events
```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize the key findings."}'
```

---

## 10. Troubleshooting

1. **`ModuleNotFoundError: No module named 'app'`**:
   Always run tests or modules either with `PYTHONPATH=backend` or by running `pytest` from the `backend/` directory.
2. **`Rate limit exceeded (HTTP 429)`**:
   The sliding-window middleware limits requests to 60 per minute per IP by default. Adjust `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` in `.env` if necessary.
3. **Database Connection Refused**:
   When running the complete stack, ensure PostgreSQL is started via `docker compose up postgres -d` or that your local PostgreSQL instance is running on port 5432.
4. **Ollama Offline**:
   When `LLM_PROVIDER=ollama` is set and Ollama is not running locally, the RAG service gracefully returns a fallback response or logs a clear error rather than crashing the API server.
