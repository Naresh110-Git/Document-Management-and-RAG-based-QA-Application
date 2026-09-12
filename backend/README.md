# Document Management and RAG-based Q&A Application

This repository contains a FastAPI backend for document ingestion, semantic search, and RAG-powered Q&A with provider abstraction.

Run tests
----

Prefer running tests with `pytest` so test discovery and `conftest.py` hooks are applied. From the `backend` directory run:

PowerShell (Windows):

```powershell
./run_tests.ps1
```

Unix/macOS:

```bash
./run_tests.sh
```

If you prefer running `pytest` directly, ensure you run it from the `backend` folder so the `app` package can be imported:

```powershell
Set-Location 'c:\path\to\repo\backend'
python -m pytest -vv
```

If you need to execute a file directly, use the helper script instead of `python file.py`:

```powershell
python run_file.py tests\test_auth_api.py
```

This launcher ensures the `backend` package root is on `sys.path` before the target script executes, which avoids `ModuleNotFoundError: No module named 'app'` when running individual files.

For normal execution and development, install the backend in editable mode once:

```powershell
python -m pip install -e .
```

Then you can run modules directly from the backend folder, for example:

```powershell
python -m app.main
```

If you want a cleaner pytest output, use the project’s configured runner from the backend folder:

```powershell
python -m pytest -q
```

The project is already configured to ignore known deprecation warnings from SWIG-based native dependencies that do not affect your application logic.

## Continuous Integration

A GitHub Actions workflow is configured at `.github/workflows/backend-tests.yml` to run the backend test suite on push and pull requests. It includes both an in-process backend job and a Postgres-backed integration job using the `pgvector/pgvector:pg16` service.
