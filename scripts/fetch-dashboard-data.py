#!/usr/bin/env python3
"""Fetch productive hours from GitHub Projects V2 and build website/cruscotto/data.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "scripts" / "budget-config.json"
OUTPUT_PATH = ROOT / "website" / "cruscotto" / "data.json"
GRAPHQL_URL = "https://api.github.com/graphql"

SPRINT_RE = re.compile(r"^sprint-(\d+)$", re.IGNORECASE)
WEEK_RE = re.compile(r"(\d+)")

QUERY = """
query($org: String!, $number: Int!, $cursor: String) {
  organization(login: $org) {
    projectV2(number: $number) {
      title
      items(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldIterationValue {
                title
                startDate
                duration
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
          content {
            __typename
            ... on Issue {
              number
              title
              state
              url
              assignees(first: 10) { nodes { login } }
              labels(first: 20) { nodes { name } }
            }
            ... on PullRequest {
              number
              title
              state
              url
              assignees(first: 10) { nodes { login } }
              labels(first: 20) { nodes { name } }
            }
            ... on DraftIssue {
              title
              assignees(first: 10) { nodes { login } }
            }
          }
        }
      }
    }
  }
}
"""


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def graphql_request(token: str, variables: dict) -> dict:
    payload = json.dumps({"query": QUERY, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "On-By-One-Dashboard",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Errore HTTP {exc.code} da GitHub GraphQL: {body}") from exc

    if data.get("errors"):
        raise RuntimeError(f"Errore GraphQL: {json.dumps(data['errors'], indent=2)}")
    return data["data"]


def extract_items(config: dict, token: str) -> tuple[str, list[dict]]:
    org = config["org"]
    number = config["project_number"]
    fields_cfg = config["fields"]
    known_roles = set(config["roles"].keys())
    members_map = config["members"]

    cursor = None
    project_title = "Rendicontazione ore"
    entries: list[dict] = []

    while True:
        data = graphql_request(token, {"org": org, "number": number, "cursor": cursor})
        project = data["organization"]["projectV2"]
        if not project:
            raise RuntimeError(f"Project #{number} non trovato nell'organizzazione {org}.")
        project_title = project["title"]

        items = project["items"]
        for node in items["nodes"]:
            content = node.get("content")
            if not content:
                continue

            status = None
            week_label = "No Settimana"
            week_number = None
            week_start = None
            hours = 0.0

            for fv in node.get("fieldValues", {}).get("nodes", []):
                field_name = (fv.get("field") or {}).get("name")
                if not field_name:
                    continue
                if field_name == fields_cfg["status"] and "name" in fv:
                    status = fv["name"]
                elif field_name == fields_cfg["hours"] and fv.get("number") is not None:
                    hours = float(fv["number"])
                elif field_name == fields_cfg["week"]:
                    raw_week = fv.get("title") or fv.get("name")
                    if raw_week:
                        week_label = raw_week
                        match = WEEK_RE.search(raw_week)
                        week_number = int(match.group(1)) if match else None
                    if fv.get("startDate"):
                        week_start = fv["startDate"]

            # Considera solo voci completate (o draft) con ore > 0
            if hours <= 0:
                continue
            if week_number is None or week_number < 1:
                continue
            is_draft = content.get("__typename") == "DraftIssue"
            if not is_draft and status != fields_cfg["done_value"] and content.get("state") != "CLOSED":
                continue

            labels = [lbl["name"] for lbl in (content.get("labels") or {}).get("nodes", [])]
            sprint = "Nessuno sprint"
            role = "unassigned"
            for lbl in labels:
                low = lbl.lower()
                if SPRINT_RE.match(low):
                    sprint = low
                elif low in known_roles:
                    role = low

            assignees = [a["login"] for a in (content.get("assignees") or {}).get("nodes", [])]
            if not assignees:
                assignees = ["unassigned"]

            # Se più persone sono assegnate alla stessa issue, suddivide equamente le ore
            split_hours = round(hours / len(assignees), 2)
            for login in assignees:
                entries.append(
                    {
                        "title": content.get("title", "Senza titolo"),
                        "url": content.get("url"),
                        "issue_number": content.get("number"),
                        "member_login": login,
                        "member_name": members_map.get(login, login),
                        "role": role,
                        "sprint": sprint,
                        "week": week_label,
                        "week_number": week_number,
                        "week_start": week_start,
                        "hours": split_hours,
                    }
                )

        if not items["pageInfo"]["hasNextPage"]:
            break
        cursor = items["pageInfo"]["endCursor"]

    return project_title, entries


def mock_entries(config: dict) -> list[dict]:
    """Dati fittizi per testare grafici e filtri in locale prima di collegare il token."""
    return [
        {"title": "Stesura bozza Analisi dei Requisiti", "url": None, "issue_number": 62, "member_login": "simonegiuliano", "member_name": "Simone Giuliano", "role": "analysis", "sprint": "sprint-1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 3.0},
        {"title": "Stesura introduzione ai casi d'uso", "url": None, "issue_number": 113, "member_login": "simonegiuliano", "member_name": "Simone Giuliano", "role": "analysis", "sprint": "sprint-1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 1.5},
        {"title": "Casi d'uso autenticazione", "url": None, "issue_number": 97, "member_login": "username-sara", "member_name": "Sara Ballardin", "role": "analysis", "sprint": "sprint-1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 5.0},
        {"title": "Casi d'uso struttura impianto", "url": None, "issue_number": 105, "member_login": "username-shuhui", "member_name": "Shuhui Chen", "role": "analysis", "sprint": "sprint-1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 4.5},
        {"title": "Setup CI/CD e repository", "url": None, "issue_number": 40, "member_login": "username-alvise", "member_name": "Alvise Greggio", "role": "administration", "sprint": "sprint-1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 4.0},
        {"title": "Coordinamento sprint 1 e verbale", "url": None, "issue_number": 51, "member_login": "username-tommaso", "member_name": "Tommaso Zorzetto", "role": "representative", "sprint": "sprint-1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 5.0},
        {"title": "Verifica documenti candidatura e AdR", "url": None, "issue_number": 88, "member_login": "username-daniele", "member_name": "Daniele Nuzzaci", "role": "verification", "sprint": "sprint-1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 4.0},
        {"title": "Verifica casi d'uso autenticazione", "url": None, "issue_number": 99, "member_login": "username-federico", "member_name": "Federico Temporin", "role": "verification", "sprint": "sprint-1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 3.5},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera i dati JSON per il cruscotto.")
    parser.add_argument("--mock", action="store_true", help="Genera dati di esempio senza chiamare GitHub API.")
    args = parser.parse_args()

    config = load_config()
    if args.mock:
        project_title = "Rendicontazione ore (Dati di esempio)"
        entries = mock_entries(config)
    else:
        token = os.environ.get("GH_PROJECT_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Errore: imposta la variabile d'ambiente GH_PROJECT_TOKEN (con permesso read:project).")
        project_title, entries = extract_items(config, token)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_mock": args.mock,
        "project_title": project_title,
        "budget": {
            "project_weeks": config["project_weeks"],
            "target_hours_per_member": config["target_hours_per_member"],
            "total_budget_eur": config["total_budget_eur"],
            "roles": config["roles"],
        },
        "members": config["members"],
        "entries": entries,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Salvato {OUTPUT_PATH} ({len(entries)} voci).")


if __name__ == "__main__":
    main()
