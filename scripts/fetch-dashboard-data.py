#!/usr/bin/env python3
"""Fetch productive hours from GitHub Projects V2 and build website/dashboard/data.json."""

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
OUTPUT_PATH = ROOT / "website" / "dashboard" / "data.json"
GRAPHQL_URL = "https://api.github.com/graphql"

SPRINT_RE = re.compile(r"^sprint-(\d+)$", re.IGNORECASE)
WEEK_RE = re.compile(r"(\d+)")
DRAFT_VERIFICATION_RE = re.compile(r"\bverifica\b.*\bpr\b", re.IGNORECASE)

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
    skipped_no_role = 0

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
            week_label = None
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

            # Esclude voci senza ore o precedenti alla Settimana 1
            if hours <= 0 or week_number is None or week_number < 1:
                continue

            is_draft = content.get("__typename") == "DraftIssue"
            if not is_draft and status != fields_cfg["done_value"] and content.get("state") != "CLOSED":
                continue

            labels = [lbl["name"] for lbl in (content.get("labels") or {}).get("nodes", [])]
            sprint = None
            role = None
            for lbl in labels:
                low = lbl.lower()
                sprint_match = SPRINT_RE.match(low)
                if sprint_match:
                    sprint = f"Sprint {sprint_match.group(1)}"
                elif low in known_roles:
                    role = low

            if is_draft and role is None:
                if DRAFT_VERIFICATION_RE.search(content.get("title", "")):
                    role = "verification"
                    
            # Ignora voci prive di una label di ruolo valida
            if role is None:
                skipped_no_role += 1
                continue

            assignees = [a["login"] for a in (content.get("assignees") or {}).get("nodes", [])]
            if not assignees:
                continue

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

    if skipped_no_role:
        print(
            f"Avviso: ignorate {skipped_no_role} voci con ore ma senza label di ruolo.",
            file=sys.stderr,
        )

    return project_title, entries


def mock_entries(config: dict) -> list[dict]:
    """Dati di esempio su 3 settimane (2 sprint) con rotazione ruoli per test locale."""
    return [
        # Settimana 1 - Sprint 1
        {"title": "Stesura bozza Analisi dei Requisiti", "url": None, "issue_number": 62, "member_login": "simonegiuliano", "member_name": "Simone Giuliano", "role": "analysis", "sprint": "Sprint 1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 4.0},
        {"title": "Casi d'uso autenticazione", "url": None, "issue_number": 97, "member_login": "username-sara", "member_name": "Sara Ballardin", "role": "analysis", "sprint": "Sprint 1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 5.0},
        {"title": "Setup CI/CD e repository", "url": None, "issue_number": 40, "member_login": "username-alvise", "member_name": "Alvise Greggio", "role": "administration", "sprint": "Sprint 1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 4.5},
        {"title": "Coordinamento sprint 1", "url": None, "issue_number": 51, "member_login": "username-tommaso", "member_name": "Tommaso Zorzetto", "role": "representative", "sprint": "Sprint 1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 5.0},
        {"title": "Verifica struttura documenti", "url": None, "issue_number": 70, "member_login": "username-daniele", "member_name": "Daniele Nuzzaci", "role": "verification", "sprint": "Sprint 1", "week": "Settimana 1", "week_number": 1, "week_start": "2026-11-09", "hours": 4.0},
        # Settimana 2 - Sprint 1
        {"title": "Stesura introduzione ai casi d'uso", "url": None, "issue_number": 113, "member_login": "simonegiuliano", "member_name": "Simone Giuliano", "role": "analysis", "sprint": "Sprint 1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 3.5},
        {"title": "Casi d'uso struttura impianto", "url": None, "issue_number": 105, "member_login": "username-shuhui", "member_name": "Shuhui Chen", "role": "analysis", "sprint": "Sprint 1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 5.5},
        {"title": "Verifica casi d'uso autenticazione", "url": None, "issue_number": 99, "member_login": "username-federico", "member_name": "Federico Temporin", "role": "verification", "sprint": "Sprint 1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 4.5},
        {"title": "Prototipo iniziale server MCP", "url": None, "issue_number": 118, "member_login": "username-alvise", "member_name": "Alvise Greggio", "role": "development", "sprint": "Sprint 1", "week": "Settimana 2", "week_number": 2, "week_start": "2026-11-16", "hours": 3.0},
        # Settimana 3 - Sprint 2 (cambio ruoli!)
        {"title": "Implementazione cruscotto ore", "url": None, "issue_number": 135, "member_login": "simonegiuliano", "member_name": "Simone Giuliano", "role": "administration", "sprint": "Sprint 2", "week": "Settimana 3", "week_number": 3, "week_start": "2026-11-23", "hours": 5.0},
        {"title": "Architettura connettore KNX", "url": None, "issue_number": 136, "member_login": "username-sara", "member_name": "Sara Ballardin", "role": "design", "sprint": "Sprint 2", "week": "Settimana 3", "week_number": 3, "week_start": "2026-11-23", "hours": 4.0},
        {"title": "Sviluppo client MCP base", "url": None, "issue_number": 137, "member_login": "username-tommaso", "member_name": "Tommaso Zorzetto", "role": "development", "sprint": "Sprint 2", "week": "Settimana 3", "week_number": 3, "week_start": "2026-11-23", "hours": 4.5},
        {"title": "Coordinamento sprint 2", "url": None, "issue_number": 138, "member_login": "username-daniele", "member_name": "Daniele Nuzzaci", "role": "representative", "sprint": "Sprint 2", "week": "Settimana 3", "week_number": 3, "week_start": "2026-11-23", "hours": 4.0},
        {"title": "Verifica Analisi dei Requisiti", "url": None, "issue_number": 139, "member_login": "username-shuhui", "member_name": "Shuhui Chen", "role": "verification", "sprint": "Sprint 2", "week": "Settimana 3", "week_number": 3, "week_start": "2026-11-23", "hours": 5.0},
        {"title": "Test integrazione OAuth2", "url": None, "issue_number": 140, "member_login": "username-federico", "member_name": "Federico Temporin", "role": "development", "sprint": "Sprint 2", "week": "Settimana 3", "week_number": 3, "week_start": "2026-11-23", "hours": 4.0},
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
            "max_hours_per_member": config.get("max_hours_per_member", 95),
            "total_budget_eur": config["total_budget_eur"],
            "roles": config["roles"],
        },
        "members": config["members"],
        "entries": entries,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Salvato {OUTPUT_PATH} ({len(entries)} voci).")

def _gauge_color(pct: float) -> str:
    if pct > 100:
        return "#dc2626"
    if pct >= 85:
        return "#d97706"
    return "#5d3a9b"


def _render_gauge_card(
    x: int,
    title: str,
    pct: float,
    subtitle: str,
) -> str:
    import math

    cx = x + 180
    cy = 142
    r = 72
    circ = math.pi * r
    clamped = max(0.0, min(100.0, pct))
    color = _gauge_color(pct)

    # Arco di progresso (semicerchio superiore da sinistra a destra)
    arc_path = f"M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}"
    progress_svg = ""
    if clamped > 0:
        filled = (clamped / 100.0) * circ
        progress_svg = (
            f'<path d="{arc_path}" fill="none" stroke="{color}" '
            f'stroke-width="18" stroke-linecap="butt" '
            f'stroke-dasharray="{filled:.2f} {circ:.2f}" />'
        )

    # Lancetta tachimetro (0% a sinistra, 50% in alto, 100% a destra)
    angle = math.pi + (clamped / 100.0) * math.pi
    dx, dy = math.cos(angle), math.sin(angle)
    needle_len = 76
    bw = 4.5
    tip_x, tip_y = cx + dx * needle_len, cy + dy * needle_len
    b1_x, b1_y = cx - dy * bw, cy + dx * bw
    b2_x, b2_y = cx + dy * bw, cy - dx * bw

    return f"""
  <g>
    <rect x="{x}" y="10" width="360" height="215" rx="14" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" />
    <text x="{cx}" y="38" text-anchor="middle" font-size="12" font-weight="700" fill="#64748b" letter-spacing="0.8">{title}</text>
    <path d="{arc_path}" fill="none" stroke="#e2e8f0" stroke-width="18" stroke-linecap="butt" />
    {progress_svg}
    <polygon points="{b1_x:.1f},{b1_y:.1f} {tip_x:.1f},{tip_y:.1f} {b2_x:.1f},{b2_y:.1f}" fill="#1e293b" />
    <circle cx="{cx}" cy="{cy}" r="6.5" fill="#1e293b" />
    <circle cx="{cx}" cy="{cy}" r="2.8" fill="#ffffff" />
    <text x="{cx - r}" y="{cy + 16}" text-anchor="middle" font-size="10" font-weight="600" fill="#64748b">0%</text>
    <text x="{cx + r}" y="{cy + 16}" text-anchor="middle" font-size="10" font-weight="600" fill="#64748b">100%</text>
    <text x="{cx}" y="{cy + 44}" text-anchor="middle" font-size="26" font-weight="700" fill="{color}">{pct:.1f}%</text>
    <text x="{cx}" y="{cy + 66}" text-anchor="middle" font-size="12" fill="#475569">{subtitle}</text>
  </g>"""


def generate_readme_gauges() -> None:
    import json
    import re
    from datetime import datetime
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    data_path = root / "website" / "dashboard" / "data.json"
    svg_path = root / "assets" / "dashboard-kpi.svg"
    readme_path = root / "README.md"

    raw = json.loads(data_path.read_text(encoding="utf-8"))
    budget = raw["budget"]
    roles = budget["roles"]
    valid_entries = [
        e for e in raw.get("entries", [])
        if e.get("role") in roles and (e.get("week_number") or 0) >= 1
    ]

    total_planned_hours = sum(r["total_hours"] for r in roles.values())
    total_actual_hours = sum(e["hours"] for e in valid_entries)
    total_actual_cost = sum(
        e["hours"] * roles[e["role"]]["hourly_rate"] for e in valid_entries
    )
    total_budget_eur = budget["total_budget_eur"]

    hours_pct = (total_actual_hours / total_planned_hours * 100.0) if total_planned_hours > 0 else 0.0
    cost_pct = (total_actual_cost / total_budget_eur * 100.0) if total_budget_eur > 0 else 0.0

    hours_card = _render_gauge_card(
        x=10,
        title="AVANZAMENTO ORE",
        pct=hours_pct,
        subtitle=f"{total_actual_hours:.1f} h fatte su {total_planned_hours:.0f} h preventivate",
    )
    cost_card = _render_gauge_card(
        x=390,
        title="CONSUMO BUDGET",
        pct=cost_pct,
        subtitle=f"€ {total_actual_cost:.0f} spesi su € {total_budget_eur:.0f} preventivati",
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 235" width="760" height="235" role="img" aria-label="Avanzamento ore e consumo budget del progetto">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  </style>
  {hours_card}
  {cost_card}
</svg>
"""
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")

    start_tag = "<!-- DASHBOARD-SUMMARY:START -->"
    end_tag = "<!-- DASHBOARD-SUMMARY:END -->"
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        if start_tag in content and end_tag in content:
            gen_raw = raw.get("generated_at", "")
            try:
                dt = datetime.fromisoformat(gen_raw.replace("Z", "+00:00"))
                updated_str = dt.strftime("%d/%m/%Y %H:%M UTC")
            except ValueError:
                updated_str = gen_raw

            block = (
                f"{start_tag}\n"
                f'<p align="center">\n'
                f'  <img src="assets/dashboard-kpi.svg" alt="Avanzamento ore e consumo budget" width="760">\n'
                f"</p>\n"
                f'<p align="center"><sub>Dati complessivi di progetto · Aggiornato il {updated_str}</sub></p>\n'
                f"{end_tag}"
            )
            pattern = re.compile(rf"{re.escape(start_tag)}.*?{re.escape(end_tag)}", re.DOTALL)
            readme_path.write_text(pattern.sub(lambda _: block, content, count=1), encoding="utf-8")

            
if __name__ == "__main__":
    main()
    generate_readme_gauges()