# MCP Server Overview

This project includes a single Model Context Protocol (MCP) server that powers the MyCareersFuture job dashboard widget bundled with the Apps SDK examples.

## MyCareersFuture MCP server

- **Location**: `mycareersfuture_server_python/main.py`
- **Purpose**: Queries the public [MyCareersFuture](https://www.mycareersfuture.gov.sg/) API to surface live job postings. Responses include structured data and a widget reference so ChatGPT can render an interactive carousel through the Apps SDK.
- **Entrypoint**: `uvicorn mycareersfuture_server_python.main:app --port 8000`
- **Tool**:
  - `mycf-job-list` – Returns job listings together with `_meta.openai/outputTemplate` metadata pointing to `ui://widget/mycf-job-list.html`.
- **Resource**:
  - `ui://widget/mycf-job-list.html` (MIME type: `text/html+skybridge`) – Bundled HTML/CSS/JS served from `assets/mycareersfuture-*.html`.

### Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r mycareersfuture_server_python/requirements.txt
uvicorn mycareersfuture_server_python.main:app --port 8000
```

Add the server as a connector in ChatGPT (developer mode) and invoke `mycf-job-list`. The widget renders automatically when the response metadata references the bundled asset.
