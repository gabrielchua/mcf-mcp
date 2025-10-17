# MyCareersFuture MCP server (Python)

This directory contains a Python implementation of a MyCareersFuture-focused Model Context Protocol server built with the official `FastMCP` helper. The server turns live job search results from [MyCareersFuture](https://www.mycareersfuture.gov.sg/) into interactive dashboards so clients can browse openings without leaving the conversation.

## Prerequisites

- Python 3.10+
- A virtual environment (recommended)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Heads up:** There is a similarly named package called `modelcontextprotocol`
> on PyPI that is unrelated to the official MCP SDK. The requirements file
> already pulls in the official `mcp` distribution with its FastAPI extra. If
> you previously installed the other project, run `pip uninstall
> modelcontextprotocol` before installing these requirements.

## Run the server

```bash
python main.py
```

This starts a FastAPI app with uvicorn on `http://127.0.0.1:8000` (equivalently
`uvicorn mycareersfuture_server_python.main:app --port 8000`). The HTTP and SSE
endpoints follow the standard FastMCP layout:

- `GET /mcp` exposes the SSE stream.
- `POST /mcp/messages?sessionId=...` accepts follow-up messages for an active session.

Each tool queries MyCareersFuture in real time, returns structured job data, and
embeds an HTML widget (jobs list, spotlight roles, or hiring insights) so the
ChatGPT client can render an interactive view immediately.

## Next steps

Use these handlers as a starting point when adding authentication, additional
filters (e.g. salary bands or regions), custom analytics, or integrations with
internal systems.
