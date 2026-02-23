"""Fetch weekly tasks from Notion."""

import os
import time
import requests

DATABASE_ID = "2fa1a1849c7b809dba95f6fa1e4d8f9e"
NOTION_API = "https://api.notion.com/v1/databases"

_cache = {"tasks": None, "fetched_at": 0}
CACHE_TTL = 600  # 10 minutes


def _fetch_from_notion():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN environment variable not set")

    resp = requests.post(
        f"{NOTION_API}/{DATABASE_ID}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json={
            "filter": {
                "and": [
                    {"property": "Timing", "select": {"equals": "Must be done this week"}},
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Status", "status": {"does_not_equal": "Done last week or earlier"}},
                ]
            }
        },
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])

    tasks = []
    for page in results:
        props = page["properties"]
        title_arr = props.get("Task", {}).get("title", [])
        name = title_arr[0]["plain_text"] if title_arr else "Untitled"
        priority = (props.get("impact / priority", {}).get("select") or {}).get("name", "")
        tasks.append({"name": name, "priority": priority})

    return tasks


def get_weekly_tasks():
    """Return formatted task list string, cached for 10 minutes."""
    now = time.time()
    if _cache["tasks"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL:
        return _cache["tasks"]

    tasks = _fetch_from_notion()
    _cache["tasks"] = tasks
    _cache["fetched_at"] = now
    return tasks


def format_task_list(tasks):
    """Format tasks into a string for the prompt."""
    if not tasks:
        return "(No tasks found for this week)"
    lines = []
    for t in tasks:
        priority = f" [{t['priority']}]" if t["priority"] else ""
        lines.append(f"- {t['name']}{priority}")
    return "\n".join(lines)
