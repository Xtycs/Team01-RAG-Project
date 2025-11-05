# Testing Guide

This guide lists the recommended steps for exercising the Local Privacy-First RAG Assistant inside a fresh GitHub Codespace. The commands assume you are working from the repository root (`/workspaces/Team01-RAG-Project`).

## 1. Create and Activate a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 2. Install Test Dependencies
Install the minimal tooling needed to run the automated checks.
```bash
pip install -r requirements-dev.txt
```

## 3. Run the Python Test Suite
Execute the unit and integration tests that cover ingestion, retrieval, and generation modules.
```bash
pytest backend
```

To view verbose output, append `-vv` to the command.

## 4. Optional: Launch the API Gateway for Manual Verification
If you want to perform manual end-to-end checks from the frontend, start the local API server in a separate terminal.
```bash
python -m backend.api.gateway
```

With the server running, open another terminal and serve the frontend assets (for example with Python's built-in HTTP server) to complete the "Upload → Ask → Cited Result" flow.
```bash
python -m http.server --directory frontend 9000
```

## 5. Deactivate the Virtual Environment (when finished)
```bash
deactivate
```

Following this sequence ensures your Codespace has the required tooling and that the project passes the automated regression tests before any manual QA.
