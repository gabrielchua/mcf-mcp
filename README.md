# MyCareersFuture MCP Server Demo

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

This repository hosts a proof-of-concept Model Context Protocol (MCP) server that wraps the public [MyCareersFuture (MCF)](https://www.mycareersfuture.gov.sg/) job search API. It illustrates how to expose live job listings to ChatGPT through MCP, and how to optionally pair those responses with an Apps SDK widget for richer rendering in the ChatGPT client.

## MCP + MyCareersFuture overview

The MCP server accepts structured tool requests, forwards them to the MCF API, and returns:

1. Structured JSON describing the queried job listings (titles, companies, salary hints, metadata).
2. An `_meta.openai/outputTemplate` pointer to a static widget bundle so compatible clients (such as ChatGPT with the Apps SDK) can render an interactive carousel.

Each call is validated with Pydantic models, logged for observability, and kept intentionally simple to serve as an approachable starting point for your own integrations. For a deeper breakdown of the server implementation, see [`MCP_SERVER.md`](./MCP_SERVER.md).

## Repository structure

- `mycareersfuture_server_python/` – FastAPI/uvicorn MCP server sourcing jobs from the MCF API.
- `src/` – Widget source code (MyCareersFuture carousel and Todo example) used when building UI assets.
- `assets/` – Generated HTML/JS/CSS bundles created during the build step.
- `build-all.mts` – Vite build orchestration script that packages per-widget assets.

## Prerequisites

- Node.js 18+
- pnpm (recommended) or npm/yarn
- Python 3.10+

## Install dependencies

Clone the repository and install JavaScript dependencies for the widget build:

```bash
pnpm install
```

If you prefer npm or yarn, install the root dependencies with your client of choice and adjust the commands below accordingly.

## Build widget assets

The MCP server serves static bundles that power the MyCareersFuture widget. Build them before running the server:

```bash
pnpm run build
```

This executes `build-all.mts`, producing versioned `.html`, `.js`, and `.css` files in `assets/`. Each widget includes its required CSS so you can host or distribute the bundles independently.

To iterate locally, use the Vite dev server:

```bash
pnpm run dev
```

If you want to preview the generated bundles without the MCP server, run the static file server after building:

```bash
pnpm run serve
```

This exposes the compiled assets at [`http://localhost:4444`](http://localhost:4444) with CORS enabled for local tooling.

## Run the MCP server

Create a virtual environment, install the Python dependencies, and start the FastAPI server:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r mycareersfuture_server_python/requirements.txt
uvicorn mycareersfuture_server_python.main:app --port 8000
```

The server listens for standard MCP requests over HTTP/SSE and exposes a single tool, `mycf-job-list`, which queries live jobs and returns structured results with widget metadata.

## Apps SDK integration (optional)

This project also demonstrates how the MyCareersFuture MCP responses can light up a front-end experience in ChatGPT. When the `_meta.openai/outputTemplate` field references the bundled widget, the Apps SDK renders:

- A horizontal carousel of job cards with titles, employers, salary hints, and metadata.
- Inline navigation controls for exploring multiple roles.

Using the Apps SDK is optional; MCP-compatible clients can consume the structured JSON without rendering the widget.

## Test in ChatGPT

Enable [developer mode](https://platform.openai.com/docs/guides/developer-mode) in ChatGPT, add the MCP server as a connector, and (if necessary) expose the local instance using a tunneling tool such as [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Add the connector URL (for example, `https://<custom_endpoint>.ngrok-free.app/mcp`), enable the connector in a conversation, and ask questions like “Find software engineering openings in Singapore.” ChatGPT will call `mycf-job-list`, receive structured job data, and—when using the Apps SDK—render the bundled widget.

## Next steps

- Customize the MCP handler in `mycareersfuture_server_python/main.py` to call additional APIs or enforce business rules.
- Add new widgets under `src/` and extend the build script to package them.
- Harden the server for production (authentication, caching, rate limiting) before deploying to user-facing environments.

## Contributing

Contributions are welcome, but please note that we may not be able to review every suggestion.

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
