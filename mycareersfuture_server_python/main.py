"""MyCareersFuture job search MCP server implemented with the Python FastMCP helper.

This server exposes widget-backed tools that query the public MyCareersFuture
search API and render interactive HTML dashboards summarising the returned job
postings. Every tool request fetches fresh data, produces structured content
for downstream automation, and embeds a job-focused UI so clients can browse
open roles without leaving the conversation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import logging
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Final, List, Optional

import requests

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError


logger = logging.getLogger("mycareersfuture.mcp")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


@dataclass(frozen=True)
class JobPosting:
    """Thin representation of a MyCareersFuture job posting."""

    id: str
    title: str
    company: Optional[str]
    url: Optional[str]
    salary: Optional[str]
    location: Optional[str]
    region: Optional[str]
    categories: List[str]
    employment_types: List[str]
    skills: List[str]
    updated_at: Optional[str]
    posted_at: Optional[str]
    score: Optional[float]
    lat: Optional[float]
    lng: Optional[float]

    def to_structured(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "jobUrl": self.url,
            "salary": self.salary,
            "location": self.location,
            "region": self.region,
            "categories": self.categories,
            "employmentTypes": self.employment_types,
            "skills": self.skills,
            "updatedAt": self.updated_at,
            "postedAt": self.posted_at,
            "score": self.score,
            "lat": self.lat,
            "lng": self.lng,
        }


@dataclass(frozen=True)
class JobSearchResult:
    search_term: str
    total: int
    jobs: List[JobPosting]


def _format_salary(raw: Optional[Dict[str, Any]]) -> Optional[str]:
    if not raw:
        return None
    minimum = raw.get("minimum")
    maximum = raw.get("maximum")
    salary_type = raw.get("type", {}).get("salaryType", "")
    if minimum is None and maximum is None:
        return None
    if minimum and maximum and minimum != maximum:
        salary_range = f"${minimum:,.0f} – ${maximum:,.0f}"
    else:
        value = minimum if minimum is not None else maximum
        salary_range = f"${value:,.0f}" if value is not None else None
    if not salary_range:
        return None
    suffix = f" {salary_type.title()}" if salary_type else ""
    return f"{salary_range}{suffix}"


API_URL: Final[str] = "https://api.mycareersfuture.gov.sg/v2/search"
DEFAULT_LIMIT: Final[int] = 20
DEFAULT_PAGE: Final[int] = 0
REQUEST_TIMEOUT: Final[int] = 12


class JobSearchInput(BaseModel):
    """Schema for job tools.

    Note: `searchTerm` is optional so the widget can render without user input.
    A sensible default is used when omitted.
    """

    search_term: Optional[str] = Field(
        "software engineer",
        alias="searchTerm",
        description=(
            "Phrase to search for on MyCareersFuture "
            "(default: 'software engineer')."
        ),
    )
    limit: int = Field(
        DEFAULT_LIMIT,
        alias="limit",
        description="Maximum number of results to return (1-50).",
        ge=1,
        le=50,
    )
    page: int = Field(
        DEFAULT_PAGE,
        alias="page",
        description="Zero-based page index on MyCareersFuture.",
        ge=0,
        le=50,
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


def _request_jobs(payload: JobSearchInput) -> JobSearchResult:
    params = {"limit": payload.limit, "page": payload.page}
    term = (
        (payload.search_term or "software engineer").strip()
        or "software engineer"
    )
    logger.info(
        "Requesting MyCareersFuture search (term=%r, limit=%d, page=%d)",
        term,
        payload.limit,
        payload.page,
    )
    start = perf_counter()
    try:
        response = requests.post(
            API_URL,
            params=params,
            json={"search": term},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "openai-apps-sdk-examples/1.0",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        elapsed = perf_counter() - start
        logger.exception(
            "MyCareersFuture request failed "
            "(term=%r, limit=%d, page=%d, elapsed=%.2fs)",
            term,
            payload.limit,
            payload.page,
            elapsed,
        )
        raise

    data = response.json()

    raw_results = data.get("results", []) or []
    postings: List[JobPosting] = []
    for item in raw_results:
        metadata = item.get("metadata", {}) or {}
        posted_company = item.get("postedCompany") or {}
        address = item.get("address") or {}
        categories = [
            str(cat.get("category"))
            for cat in item.get("categories", [])
            if cat and cat.get("category")
        ]
        employment_types = [
            str(emp.get("employmentType"))
            for emp in item.get("employmentTypes", [])
            if emp and emp.get("employmentType")
        ]
        skills = [
            str(skill.get("skill"))
            for skill in item.get("skills", [])
            if skill and skill.get("skill")
        ]
        districts = address.get("districts") or []
        primary_district = districts[0] if districts else {}
        location = (
            address.get("street")
            or primary_district.get("location")
            or address.get("district")
        )
        salary = _format_salary(item.get("salary"))
        postings.append(
            JobPosting(
                id=str(
                    metadata.get("jobPostId")
                    or item.get("uuid")
                    or len(postings)
                ),
                title=str(item.get("title") or "Untitled role"),
                company=posted_company.get("name"),
                url=metadata.get("jobDetailsUrl"),
                salary=salary,
                location=location,
                region=primary_district.get("region"),
                categories=categories,
                employment_types=employment_types,
                skills=skills,
                updated_at=metadata.get("updatedAt"),
                posted_at=metadata.get("newPostingDate"),
                score=item.get("score"),
                lat=address.get("lat"),
                lng=address.get("lng"),
            )
        )

    total_results = int(data.get("total") or len(postings))
    elapsed = perf_counter() - start
    logger.info(
        "MyCareersFuture search succeeded "
        "(term=%r, status=%s, total=%d, returned=%d, elapsed=%.2fs)",
        term,
        response.status_code,
        total_results,
        len(postings),
        elapsed,
    )

    return JobSearchResult(
        search_term=term,
        total=total_results,
        jobs=postings,
    )


MIME_TYPE: Final[str] = "text/html+skybridge"
COMPONENT_URI: Final[str] = "ui://widget/mycf-job-list.html"
TOOL_NAME: Final[str] = "mycf-job-list"
WIDGET_NAME: Final[str] = "mycf-job-list"
WIDGET_TITLE: Final[str] = "MyCareersFuture job list"
WIDGET_DESCRIPTION: Final[
    str
] = (
    "Displays a horizontal carousel of job listings from MyCareersFuture with "
    "details like salary, location, and company."
)


def _load_component_html() -> str:
    """Return the built widget bundle, falling back to a placeholder message."""
    assets_dir = Path(__file__).parent.parent / "assets"
    logger.info("Looking for component HTML in %s", assets_dir)

    if assets_dir.exists():
        html_files = sorted(assets_dir.glob("mycareersfuture-*.html"))
        logger.info("Found %d component files: %s", len(html_files), html_files)
        if html_files:
            html_path = html_files[0]
            html_content = html_path.read_text(encoding="utf-8")
            logger.info(
                "Loaded component from %s (%d bytes)", html_path, len(html_content)
            )
            return html_content

    logger.warning(
        "Built component not found. Run 'pnpm install' and 'pnpm run build' first."
    )
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MyCareersFuture Jobs</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 2rem;
      text-align: center;
    }
    .error {
      background: #fee;
      border: 1px solid #fcc;
      padding: 1rem;
      border-radius: 8px;
      color: #c00;
    }
  </style>
</head>
<body>
  <div class="error">
    <h2>Component Not Built</h2>
    <p>
      Please run <code>pnpm install && pnpm run build</code>
      to build the component.
    </p>
  </div>
  <div id="mycareersfuture-root"></div>
</body>
</html>"""


mcp = FastMCP(
    name="mycareersfuture-python",
    stateless_http=True,
)


TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "searchTerm": {
            "type": "string",
            "description": (
                "Phrase to search for on MyCareersFuture "
                "(default: 'software engineer')."
            ),
            "default": "software engineer",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results to fetch (1-50).",
            "minimum": 1,
            "maximum": 50,
            "default": DEFAULT_LIMIT,
        },
        "page": {
            "type": "integer",
            "description": "Zero-based page of results to request.",
            "minimum": 0,
            "maximum": 50,
            "default": DEFAULT_PAGE,
        },
    },
    "additionalProperties": False,
}


def _tool_meta() -> Dict[str, Any]:
    return {
        "openai/outputTemplate": COMPONENT_URI,
        "openai/toolInvocation/invoking": "Gathering job listings…",
        "openai/toolInvocation/invoked": "Job listings ready.",
        "openai/widgetAccessible": True,
        "openai/resultCanProduceWidget": True,
        "annotations": {
            "destructiveHint": False,
            "openWorldHint": False,
            "readOnlyHint": True,
        },
    }


# Register the static component resource
@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    logger.info("Registering widget resource %s", COMPONENT_URI)
    return [
        types.Resource(
            name=WIDGET_NAME,
            title=WIDGET_TITLE,
            uri=COMPONENT_URI,
            description="MyCareersFuture job list widget markup",
            mimeType=MIME_TYPE,
            _meta={
                **_tool_meta(),
                "openai/widgetDescription": WIDGET_DESCRIPTION,
            },
        )
    ]


@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> List[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(
            name=WIDGET_NAME,
            title=WIDGET_TITLE,
            uriTemplate=COMPONENT_URI,
            description="MyCareersFuture job list widget markup",
            mimeType=MIME_TYPE,
            _meta={
                **_tool_meta(),
                "openai/widgetDescription": WIDGET_DESCRIPTION,
            },
        )
    ]


async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    logger.info("read_resource() called for URI %s", req.params.uri)

    if str(req.params.uri) != COMPONENT_URI:
        logger.warning("Unknown resource requested: %s", req.params.uri)
        return types.ServerResult(
            types.ReadResourceResult(
                contents=[],
                _meta={"error": f"Unknown resource: {req.params.uri}"},
            )
        )

    logger.info("Returning component HTML for %s", COMPONENT_URI)

    component_html = _load_component_html()

    logger.info("Component HTML length: %d bytes", len(component_html))
    logger.info("MIME type: %s", MIME_TYPE)

    contents: List[types.TextResourceContents] = [
        types.TextResourceContents(
            uri=COMPONENT_URI,
            mimeType=MIME_TYPE,
            text=component_html,
            _meta={
                **_tool_meta(),
                "openai/widgetDescription": WIDGET_DESCRIPTION,
            },
        )
    ]

    logger.info("Resource read complete for %s", COMPONENT_URI)
    return types.ServerResult(types.ReadResourceResult(contents=contents))


# Register the tool
@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name=TOOL_NAME,
            title=WIDGET_TITLE,
            description=(
                "Search for jobs on MyCareersFuture and return an interactive "
                "carousel of results."
            ),
            inputSchema=deepcopy(TOOL_INPUT_SCHEMA),
            _meta=_tool_meta(),
        )
    ]


# Handle tool calls - return ONLY structured data, no HTML
async def _call_tool_request(req: types.CallToolRequest) -> types.ServerResult:
    if req.params.name != TOOL_NAME:
        logger.warning("Unknown tool requested: %s", req.params.name)
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Unknown tool: {req.params.name}",
                    )
                ],
                isError=True,
            )
        )

    arguments = req.params.arguments or {}
    try:
        payload = JobSearchInput.model_validate(arguments)
    except ValidationError as exc:
        logger.warning(
            "Validation error for tool %s: %s", req.params.name, exc.errors()
        )
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Input validation error: {exc.errors()}",
                    )
                ],
                isError=True,
            )
        )

    logger.info(
        "Tool %s invoked with searchTerm=%r, limit=%d, page=%d",
        TOOL_NAME,
        payload.search_term,
        payload.limit,
        payload.page,
    )

    try:
        result = _request_jobs(payload)
    except requests.RequestException as exc:
        logger.error(
            "Tool %s failed to fetch jobs (term=%r): %s",
            TOOL_NAME,
            payload.search_term,
            exc,
        )
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Unable to fetch jobs from MyCareersFuture: {exc}",
                    )
                ],
                isError=True,
            )
        )

    logger.info(
        "Tool %s returning %d jobs (total_available=%d)",
        TOOL_NAME,
        len(result.jobs),
        result.total,
    )

    structured_content = {
        "searchTerm": result.search_term,
        "total": result.total,
        "jobs": [job.to_structured() for job in result.jobs],
    }

    logger.debug("Structured content keys: %s", list(structured_content.keys()))
    if result.jobs:
        logger.debug("First job title: %s", result.jobs[0].title)

    if result.jobs:
        text_summary = (
            f"Found {result.total:,} jobs for '{result.search_term}'. "
            f"Showing top {len(result.jobs)} results in the carousel."
        )
    else:
        text_summary = (
            f"No jobs found for '{result.search_term}'. Try a broader search."
        )

    component_html = _load_component_html()
    logger.debug(
        "Embedding component HTML in response (%d bytes)", len(component_html)
    )

    embedded_resource = types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=COMPONENT_URI,
            mimeType=MIME_TYPE,
            text=component_html,
            title=WIDGET_TITLE,
        ),
    )

    return types.ServerResult(
        types.CallToolResult(
            content=[
                embedded_resource,  # <-- Embed the widget HTML
                types.TextContent(
                    type="text",
                    text=text_summary,
                )
            ],
            structuredContent=structured_content,
            _meta=_tool_meta(),
        )
    )


mcp._mcp_server.request_handlers[types.CallToolRequest] = _call_tool_request
mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource


app = mcp.streamable_http_app()

try:
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
