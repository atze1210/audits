"""
Generate audit registry from README.md.

Parses the README.md to extract audit report metadata and saves the results to:
  - data/audits/audit_registry.json
  - data/audits/Main_Database.db
"""

import json
import os
import re
import sqlite3
import urllib.parse
from pathlib import Path

README_PATH = "README.md"
DATA_FOLDER = "data/audits"
JSON_OUTPUT = os.path.join(DATA_FOLDER, "audit_registry.json")
DB_OUTPUT = os.path.join(DATA_FOLDER, "Main_Database.db")

os.makedirs(DATA_FOLDER, exist_ok=True)


def parse_readme(readme_path: str) -> list[dict]:
    """Parse the README.md and extract audit report entries."""
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    audits = []
    current_section = ""
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Top-level section (## ...)
        if line.startswith("## ") and not line.startswith("### "):
            current_section = line[3:].strip()
            i += 1
            continue

        # Audit entry (### MM-YYYY ...)
        if line.startswith("### "):
            title = line[4:].strip()

            # Parse date from title (format: MM-YYYY or YYYY-MM)
            date_match = re.match(r"^(\d{2})-(\d{4})\s+", title)
            if date_match:
                month = date_match.group(1)
                year = date_match.group(2)
                date = f"{year}-{month}"
                audit_name = title[date_match.end():].strip()
            else:
                date = ""
                audit_name = title

            # Collect the body lines until next ### or ##
            body_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("### ") and not lines[i].startswith("## "):
                body_lines.append(lines[i])
                i += 1

            body = "\n".join(body_lines)

            # Extract report PDF link
            report_link_match = re.search(r"See\s+(?:the\s+)?(?:\[.*?\]\(.*?\)\s+and\s+)?\[(?:full\s+)?report\]\(([^)]+)\)", body)
            if not report_link_match:
                # Try alternative pattern for multiple reports
                report_link_match = re.search(r"\[(?:full\s+)?(?:initial|report)\]\(([^)]+)\)", body)

            report_link = ""
            if report_link_match:
                report_link = urllib.parse.unquote(report_link_match.group(1))

            # Determine auditor from title
            auditor = extract_auditor(audit_name)

            # Extract issue counts
            total_issues = extract_issue_count(body, r"Total Issues?:\s*(\d+)")
            critical_issues = extract_issue_count(body, r"Critical Issues?:\s*(\d+)")
            high_issues = extract_issue_count(body, r"High(?:\s+Risk)?\s+Issues?:\s*(\d+)")
            medium_issues = extract_issue_count(body, r"Medium(?:\s+Risk)?\s+Issues?:\s*(\d+)")
            low_issues = extract_issue_count(body, r"Low(?:\s+Risk)?\s+Issues?:\s*(\d+)")

            audit_entry = {
                "Date": date,
                "Section": current_section,
                "Title": audit_name,
                "Auditor": auditor,
                "ReportLink": report_link,
                "TotalIssues": total_issues,
                "CriticalIssues": critical_issues,
                "HighIssues": high_issues,
                "MediumIssues": medium_issues,
                "LowIssues": low_issues,
            }
            audits.append(audit_entry)
            continue

        i += 1

    return audits


def extract_auditor(title: str) -> str:
    """Extract auditor name from audit title."""
    known_auditors = [
        "MixBytes",
        "Sigma Prime",
        "Quantstamp",
        "Statemind",
        "ChainSecurity",
        "Oxorio",
        "Ackee Blockchain",
        "Hexens",
        "Certora",
        "OpenZeppelin",
        "Pessimistic",
        "Code4rena",
        "Diligence",
        "Consensys Diligence",
        "Consensys",
        "Verilog",
        "Cantina",
        "Zellic",
        "Nethermind",
        "Runtime Verification",
        "Composable Security",
        "QSP",
    ]
    for auditor in known_auditors:
        if auditor.lower() in title.lower():
            return auditor
    return ""


def extract_issue_count(text: str, pattern: str) -> int | None:
    """Extract a numeric issue count from text using a regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            pass
    return None


def save_json(audits: list[dict], output_path: str) -> None:
    """Save audit registry to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"fields": list(audits[0].keys()) if audits else [], "data": audits}, f, indent=4)
    print(f"Audit registry saved to {output_path}")


def save_db(audits: list[dict], db_path: str) -> None:
    """Save audit registry to SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Main_Database (
            Date TEXT,
            Section TEXT,
            Title TEXT,
            Auditor TEXT,
            ReportLink TEXT,
            TotalIssues INTEGER,
            CriticalIssues INTEGER,
            HighIssues INTEGER,
            MediumIssues INTEGER,
            LowIssues INTEGER,
            PRIMARY KEY (Date, Title)
        )
    """)

    for audit in audits:
        cursor.execute("""
            INSERT OR REPLACE INTO Main_Database
                (Date, Section, Title, Auditor, ReportLink, TotalIssues, CriticalIssues, HighIssues, MediumIssues, LowIssues)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit["Date"],
            audit["Section"],
            audit["Title"],
            audit["Auditor"],
            audit["ReportLink"],
            audit["TotalIssues"],
            audit["CriticalIssues"],
            audit["HighIssues"],
            audit["MediumIssues"],
            audit["LowIssues"],
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Database updated at {db_path}")


if __name__ == "__main__":
    audits = parse_readme(README_PATH)
    print(f"Parsed {len(audits)} audit entries from {README_PATH}")
    save_json(audits, JSON_OUTPUT)
    save_db(audits, DB_OUTPUT)
    print("Done.")
