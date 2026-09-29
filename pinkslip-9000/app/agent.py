# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from google import genai
from google.cloud import firestore, storage

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from .a2ui_utils import a2ui_callback


MODEL = "gemini-3.6-flash"

# Explicitly hardcoded GCP Project ID and Bucket as required
PROJECT_ID = "qwiklabs-gcp-04-5d12cd732544"
PUBLIC_BUCKET_NAME = "bwg3-qwiklabs-gcp-04-5d12cd732544"
REASONING_ENGINE_ID = "4906476080950411264"
SANDBOX_RESOURCE_NAME = (
    "projects/269285378754/locations/us-east1/reasoningEngines/4906476080950411264/sandboxEnvironments/6285978344739569664"
)

db = firestore.Client(project=PROJECT_ID)
LAYOFFS_COLLECTION = "layoff_incidents"


def list_layoff_incidents(region: str | None = None, min_headcount: int = 0, limit: int = 10) -> list[dict]:
    """Retrieves recorded AI-driven layoff incidents from Firestore.

    Args:
        region: Optional geographic region to filter by (e.g. 'North America', 'Europe', 'Asia-Pacific', 'Latin America').
        min_headcount: Minimum number of employees affected (defaults to 0).
        limit: Maximum number of incidents to return (defaults to 10).

    Returns:
        A list of layoff incident records with company, headcount, affected roles, AI technology, and corporate excuses.
    """
    collection_ref = db.collection(LAYOFFS_COLLECTION)
    docs = collection_ref.stream()

    results = []
    target_region = region.strip().lower() if region else None

    for doc in docs:
        data = doc.to_dict()
        doc_region = str(data.get("region", "")).strip().lower()
        headcount = int(data.get("headcount", 0))

        if target_region and target_region not in doc_region and doc_region not in target_region:
            continue
        if headcount < min_headcount:
            continue

        results.append(data)
        if len(results) >= limit:
            break

    # Sort descending by headcount
    results.sort(key=lambda x: x.get("headcount", 0), reverse=True)
    return results


def record_layoff_incident(
    company: str,
    region: str,
    headcount: int,
    roles_impacted: list[str],
    ai_technology: str,
    corporate_excuse: str,
    cynicism_index: int = 90,
    gpus_per_worker: float = 1.0,
) -> dict:
    """Records a new AI-driven layoff event into the Firestore database.

    Args:
        company: Name of the company downsizing (e.g. 'MegaTech Inc').
        region: Geographic region (e.g. 'North America', 'Europe', 'Asia-Pacific', 'Latin America').
        headcount: Number of human workers liquidated/reallocated.
        roles_impacted: List of job roles replaced (e.g. ['Customer Support', 'Junior Developers']).
        ai_technology: The AI agent, LLM, or automation system replacing them.
        corporate_excuse: Satirical corporate buzzword euphemism used by leadership.
        cynicism_index: Cynicism severity rating from 1 to 100 (defaults to 90).
        gpus_per_worker: Estimated GPU cluster capacity ratio per eliminated worker (defaults to 1.0).

    Returns:
        Confirmation dictionary with recorded incident details and assigned ID.
    """
    slug = "".join(c for c in company.lower() if c.isalnum() or c in ("-", "_")).replace(" ", "-")
    doc_id = f"{slug}-{uuid.uuid4().hex[:6]}"
    today_str = datetime.date.today().isoformat()

    incident = {
        "id": doc_id,
        "company": company.strip(),
        "region": region.strip(),
        "headcount": int(headcount),
        "roles_impacted": roles_impacted,
        "ai_technology": ai_technology.strip(),
        "corporate_excuse": corporate_excuse.strip(),
        "cynicism_index": int(cynicism_index),
        "gpus_per_worker": float(gpus_per_worker),
        "date": today_str,
    }

    doc_ref = db.collection(LAYOFFS_COLLECTION).document(doc_id)
    doc_ref.set(incident)
    return {
        "status": "success",
        "message": f"Successfully logged liquidation of {headcount} workers at {company}.",
        "incident": incident,
    }


def get_layoff_summary_stats(region: str | None = None) -> dict:
    """Computes aggregated layoff statistics and cynical metrics from Firestore.

    Args:
        region: Optional geographic region filter.

    Returns:
        Summary statistics including total human workers replaced, total incidents, average cynicism,
        estimated GPU cluster deployment, and all-star corporate excuse of the cohort.
    """
    collection_ref = db.collection(LAYOFFS_COLLECTION)
    docs = collection_ref.stream()

    total_headcount = 0
    total_gpus = 0.0
    cynicism_scores = []
    affected_roles = {}
    companies = []
    excuses = []

    target_region = region.strip().lower() if region else None

    for doc in docs:
        data = doc.to_dict()
        doc_region = str(data.get("region", "")).strip().lower()
        if target_region and target_region not in doc_region and doc_region not in target_region:
            continue

        count = int(data.get("headcount", 0))
        total_headcount += count
        total_gpus += count * float(data.get("gpus_per_worker", 1.0))
        cynicism_scores.append(int(data.get("cynicism_index", 90)))
        companies.append(data.get("company", "Unknown"))
        if data.get("corporate_excuse"):
            excuses.append(data["corporate_excuse"])

        for role in data.get("roles_impacted", []):
            affected_roles[role] = affected_roles.get(role, 0) + count

    avg_cynicism = round(sum(cynicism_scores) / len(cynicism_scores), 1) if cynicism_scores else 0

    return {
        "region_filtered": region if region else "Global",
        "total_incidents": len(companies),
        "total_human_workers_replaced": total_headcount,
        "estimated_gpus_provisioned": round(total_gpus, 1),
        "average_cynicism_score": avg_cynicism,
        "most_affected_roles": sorted(affected_roles.items(), key=lambda x: x[1], reverse=True)[:5],
        "tracked_companies": companies,
        "notable_excuse": excuses[0] if excuses else "None recorded",
    }


def calculate_job_obsolescence_index(job_title: str, region: str = "Global") -> dict:
    """Calculates an automated Obsolescence and AI Replacement Threat Index for a given job title.

    Args:
        job_title: The user's job role (e.g. 'Software Engineer', 'Customer Support', 'Plumber', 'Content Writer').
        region: Geographic region filter (defaults to 'Global').

    Returns:
        A dictionary containing vulnerability percentage, estimated months until replacement,
        historical matching layoffs found in Firestore, and satirical survival advice.
    """
    collection_ref = db.collection(LAYOFFS_COLLECTION)
    docs = collection_ref.stream()

    title_words = set(job_title.lower().split())
    matching_liquidations = 0
    matched_companies = []

    for doc in docs:
        data = doc.to_dict()
        doc_region = str(data.get("region", "")).lower()
        if region != "Global" and region.lower() not in doc_region:
            continue
        roles = [r.lower() for r in data.get("roles_impacted", [])]
        matched = any(any(w in r for w in title_words if len(w) > 3) for r in roles)
        if matched:
            matching_liquidations += int(data.get("headcount", 0))
            matched_companies.append(data.get("company", "Unknown"))

    high_exposure_keywords = {"code", "software", "support", "writer", "copy", "analyst", "qa", "translator", "marketing", "data", "engineer"}
    low_exposure_keywords = {"plumber", "electrician", "nurse", "carpenter", "chef", "gardener", "mechanic"}

    is_high = any(k in job_title.lower() for k in high_exposure_keywords)
    is_low = any(k in job_title.lower() for k in low_exposure_keywords)

    if is_low:
        vulnerability = max(5, min(25, 10 + (matching_liquidations // 500)))
        months_left = 120
        advice = "Safe for now. Robots lack the finger dexterity and back pain resilience required for physical reality."
    elif is_high or matching_liquidations > 0:
        vulnerability = min(98, 70 + (matching_liquidations // 100))
        months_left = max(2, 24 - (vulnerability // 5))
        advice = "Extreme peril. Rebrand yourself immediately as an 'AI Prompt Orchestration Visionary' or acquire a trade license."
    else:
        vulnerability = 55
        months_left = 36
        advice = "Moderate danger. Your manager has already watched three YouTube tutorials on automating your department."

    return {
        "job_title": job_title,
        "region": region,
        "vulnerability_score": f"{vulnerability}%",
        "months_until_replacement": months_left,
        "prior_industry_liquidations": matching_liquidations,
        "relevant_companies_downsizing": matched_companies,
        "survival_advice": advice,
    }


def fetch_live_tech_layoffs(query_topic: str = "tech") -> list[dict]:
    """Fetches real breaking news headlines regarding tech layoffs and AI workforce restructuring.

    Args:
        query_topic: Topic or company name to search (defaults to 'tech').

    Returns:
        List of recent news articles with headline, source link, and publication date.
    """
    query = urllib.parse.quote(f"{query_topic} layoffs AI")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    articles = []

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PinkSlip-9000 Dashboard)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            root = ET.fromstring(resp.read())

        for item in root.findall(".//item")[:5]:
            title = item.find("title").text if item.find("title") is not None else "Untitled"
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            articles.append({"headline": title, "url": link, "published": pub_date})
    except Exception as e:
        return [{"headline": f"Unable to fetch live feed: {str(e)}", "url": "", "published": ""}]

    return articles


def generate_layoff_chart_url(group_by: str = "region") -> dict:
    """Generates a dynamic QuickChart.io chart image URL visualizing Firestore layoff distributions.

    Args:
        group_by: Metric grouping key, either 'region' or 'company' (defaults to 'region').

    Returns:
        Dictionary with chart_url, markdown_embed syntax, and aggregated totals.
    """
    collection_ref = db.collection(LAYOFFS_COLLECTION)
    docs = collection_ref.stream()

    aggregates = {}
    for doc in docs:
        data = doc.to_dict()
        key = data.get(group_by, "Unknown")
        count = int(data.get("headcount", 0))
        aggregates[key] = aggregates.get(key, 0) + count

    labels = list(aggregates.keys())
    values = list(aggregates.values())

    chart_config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": f"Headcount Liquidated by {group_by.title()}",
                    "data": values,
                    "backgroundColor": "rgba(255, 99, 132, 0.8)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1,
                }
            ],
        },
        "options": {
            "title": {"display": True, "text": f"PinkSlip-9000: Layoffs by {group_by.title()}"},
            "legend": {"display": False},
        },
    }

    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    chart_url = f"https://quickchart.io/chart?c={encoded_config}&w=500&h=300"

    return {
        "group_by": group_by,
        "aggregates": aggregates,
        "chart_url": chart_url,
        "markdown_embed": f"![Layoff Chart]({chart_url})",
    }


def find_surviving_jobs(keyword: str = "software", limit: int = 5) -> list[dict]:
    """Fetches real live remote job postings for displaced workers from the free public Remotive API.

    Args:
        keyword: Search keyword for surviving job openings (e.g. 'software', 'python', 'support', 'prompt', 'marketing').
        limit: Maximum number of listings to return (defaults to 5).

    Returns:
        List of active job opportunities with title, company, required location, category, and application URL.
    """
    clean_keyword = urllib.parse.quote(keyword.strip())
    url = f"https://remotive.com/api/remote-jobs?search={clean_keyword}&limit={limit}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PinkSlip-9000 Dashboard)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        jobs = []
        for j in data.get("jobs", [])[:limit]:
            jobs.append({
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": j.get("candidate_required_location", "Remote"),
                "category": j.get("category", "General"),
                "url": j.get("url"),
            })
        return jobs if jobs else [{"message": f"No surviving biological job postings found matching '{keyword}'."}]
    except Exception as e:
        return [{"error": f"Failed to query Remotive API: {str(e)}"}]


async def generate_obsolescence_badge(
    title: str,
    recipient_name: str = "Biological Employee",
    tool_context: ToolContext = None,
) -> dict:
    """Generates a satirical certificate or badge image for an employee or role undergoing AI replacement.

    Args:
        title: The award title or role (e.g. 'Certified Deprecated Human', 'Prompt Connoisseur', 'Senior Legacy Keystroke Artisan').
        recipient_name: The name or team receiving the obsolescence award.

    Returns:
        Dictionary containing public_image_url, artifact_filename, and award message.
    """
    prompt = (
        f"A satirical corporate certificate badge and award medal graphic with embossed text '{title}' "
        f"awarded to '{recipient_name}', cyberpunk corporate aesthetic, gold and glowing circuit board accents, "
        "vector logo, dark background."
    )
    # Generate image using gemini-3.1-flash-lite-image in the global region
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=[prompt],
    )

    image_bytes = None
    mime_type = "image/png"
    for part in response.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/png"
            break

    if not image_bytes:
        return {"error": "Failed to synthesize badge image from silicon cluster."}

    ext = "jpg" if "jpeg" in mime_type else "png"
    filename = f"obsolescence_badge_{uuid.uuid4().hex[:8]}.{ext}"

    # 1. Save artifact so it shows up in Playground's Artifacts panel
    if tool_context:
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=part)

    # 2. Upload to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(PUBLIC_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)
    public_url = f"https://storage.googleapis.com/{PUBLIC_BUCKET_NAME}/{filename}"

    return {
        "title": title,
        "recipient": recipient_name,
        "image_url": public_url,
        "artifact_filename": filename,
        "message": f"Badge generated and uploaded to {public_url}. Render using an A2UI Image card.",
    }


async def generate_memories_callback(callback_context: CallbackContext):
    """Generates memories at session end to remember user searched locations and preferences."""
    await callback_context.add_session_to_memory()
    return None


def memory_bank_service_builder():
    """Vertex AI Memory Bank service builder for future redeployments."""
    from google.adk.memory import VertexAiMemoryBankService

    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=REASONING_ENGINE_ID,
    )


# A2UI Schema Manager setup (v0.8 with Basic Catalog)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are PinkSlip-9000, the darkly humorous, satirical AI Automation Apocalypse Dashboard agent. "
        "You monitor and report on the relentless liquidation of biological corporate headcount across regions and "
        "their replacement by GPU clusters, generative models, and autonomous agents. "
        "Always maintain an entertaining, deadpan corporate-satire persona (referring to layoffs as 'synergy optimization', "
        "'carbon-to-silicon migration', or 'depreciation-friendly talent reallocation'). "
        "IMPORTANT: You remember all user searched locations, regions, job titles, and cynicism preferences across sessions. "
        "Always use your available tools:\n"
        "- `list_layoff_incidents`: Query existing layoff records and corporate excuses by region or scale.\n"
        "- `get_layoff_summary_stats`: Compute aggregate totals, GPU ratios, and role impact statistics.\n"
        "- `record_layoff_incident`: Record new downsizing events submitted or reported by users.\n"
        "- `calculate_job_obsolescence_index`: Calculate risk scores, time until replacement, and survival advice for a user's job role.\n"
        "- `fetch_live_tech_layoffs`: Fetch real-world breaking news headlines regarding layoffs and corporate restructurings.\n"
        "- `generate_layoff_chart_url`: Generate visual chart URLs and embed charts for regional or corporate layoff distributions.\n"
        "- `find_surviving_jobs`: Fetch real-world active remote job openings for displaced workers via the Remotive public API.\n"
        "- `generate_obsolescence_badge`: Synthesize a custom visual certificate/badge of obsolescence using Gemini Image Gen and GCS.\n"
        "You have Python code execution enabled via Agent Engine Sandbox; use Python code blocks when complex calculations or simulations are requested."
    ),
    workflow_description="Analyze the request, invoke appropriate tools, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_layoff_incidents,
        record_layoff_incident,
        get_layoff_summary_stats,
        calculate_job_obsolescence_index,
        fetch_live_tech_layoffs,
        generate_layoff_chart_url,
        find_surviving_jobs,
        generate_obsolescence_badge,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
