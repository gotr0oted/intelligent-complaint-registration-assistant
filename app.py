from __future__ import annotations

import csv
import io
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import gradio as gr


ROOT = Path(__file__).parent
DATABASE = ROOT / "complaints.db"

CATEGORIES = {
    "Electricity & Streetlight": {
        "department": "Municipal Electrical & Energy Dept",
        "officer": "Engr. Rajesh Sharma (Power Grid Div)",
        "keywords": "electricity power blackout streetlight street light lamp wire sparking transformer pole current voltage dark meter hanging fuse grid".split(),
    },
    "Water Supply & Sewerage": {
        "department": "Water Supply & Sewerage Board",
        "officer": "Engr. Priya Nair (Hydraulics & Drainage)",
        "keywords": "water pipe leakage burst drain drainage sewage gutter contamination dirty overflow manhole tap pressure pipeline smell sewer flooding".split(),
    },
    "Roads & Infrastructure": {
        "department": "Public Works Department (PWD)",
        "officer": "Chief Insp. Amit Patel (PWD Infrastructure)",
        "keywords": "road pothole crack asphalt divider sidewalk pavement bridge speed breaker cave accident debris traffic junction tar damaged crater construction".split(),
    },
    "Waste & Sanitation": {
        "department": "City Sanitation & Solid Waste Dept",
        "officer": "Officer Sunita Rao (Sanitation Ops)",
        "keywords": "garbage trash waste dump dustbin bin litter filth uncollected animal rotting cleanliness sweeper stagnant mosquitoes compost".split(),
    },
    "Public Safety & Hazards": {
        "department": "Municipal Disaster & Public Safety Wing",
        "officer": "Capt. Vikram Verma (Emergency Response)",
        "keywords": "danger hazard fire smoke fall tree collapse building emergency shock stray dogs bitten open pit unsafe gas spark life threatening".split(),
    },
    "Telecom & Connectivity": {
        "department": "Urban Digital & Telecom Infrastructure",
        "officer": "Tech Lead Ananya Roy (Civic Telecom)",
        "keywords": "fiber cable internet broadband telecom tower network signal digging".split(),
    },
}

PRIORITY_RULES = {
    "Critical": "emergency danger life sparking electric shock fire collapsed burst accident deadly hospital gas leak child injury urgent",
    "High": "flooding blackout blocked stagnant open manhole 3 days 4 days 5 days week severe deep pothole overflowing unsafe",
    "Medium": "flickering smell delay broken damaged pothole street light off dustbin full leaking tap",
}

SEEDS = [
    ("Broken streetlight with exposed wire sparking in rain", "The streetlight outside house #42 on 5th Cross Road has been broken for three days and sparking dangerously in the rain. Children play nearby.", "Electricity & Streetlight", "Critical", "Municipal Electrical & Energy Dept", "Engr. Rajesh Sharma (Power Grid Div)", "5th Cross Rd, Indiranagar, Ward 12", "In Progress", 7, 36),
    ("Major water pipeline burst flooding roadway", "Heavy water pressure caused underground pipe burst opposite City General Hospital. Clean drinking water wasting into open storm drain for 6 hours.", "Water Supply & Sewerage", "High", "Water Supply & Sewerage Board", "Engr. Priya Nair (Hydraulics & Drainage)", "Hospital Road, Sector 3, Ward 08", "Assigned", 14, 14),
    ("Deep crater pothole near Metro Pillar 142", "Large crater pothole after monsoon showers. Two two-wheelers skidded today morning. Needs quick cold-mix asphalt patch.", "Roads & Infrastructure", "High", "Public Works Department (PWD)", "Chief Insp. Amit Patel (PWD Infrastructure)", "Metro Pillar 142, Ring Road, Ward 15", "In Progress", 19, 48),
    ("Overflowing commercial waste bin near vegetable market", "Community dustbin has not been cleared for 4 days. Foul odor spreading to residential apartments.", "Waste & Sanitation", "Medium", "City Sanitation & Solid Waste Dept", "Officer Sunita Rao (Sanitation Ops)", "Market Cross, Ward 04", "Resolved", 5, 72),
    ("Fallen tree branches blocking broadband cable", "Storm caused a large branch to snap onto overhead telecom wires opposite St. Mary High School.", "Telecom & Connectivity", "Low", "Urban Digital & Telecom Infrastructure", "Tech Lead Ananya Roy (Civic Telecom)", "Opposite St. Mary School, Ward 02", "Resolved", 3, 96),
]


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS complaints (
            id TEXT PRIMARY KEY, title TEXT, description TEXT, category TEXT,
            priority TEXT, department TEXT, officer TEXT, location TEXT,
            status TEXT, upvotes INTEGER, citizen_name TEXT, phone TEXT,
            created_at TEXT, updated_at TEXT, logs TEXT
        )""")
        if connection.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] == 0:
            for index, seed in enumerate(SEEDS):
                title, description, category, priority, department, officer, location, status, upvotes, age = seed
                created = (datetime.now() - timedelta(hours=age)).isoformat(timespec="seconds")
                connection.execute(
                    "INSERT INTO complaints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"CMP-2026-{1042 - index * 3}", title, description, category, priority, department, officer, location, status, upvotes, "Anonymous Citizen", "Not Provided", created, now(), f"Registered|{created}|Complaint registered and routed to {department}.")
                )


def rows() -> list[dict[str, Any]]:
    with connect() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM complaints ORDER BY created_at DESC")]


def analyze(description: str, location: str = "") -> dict[str, Any]:
    text = description.strip().lower()
    if not text:
        return {"category": "Unclassified", "priority": "Low", "department": "General Public Grievance Cell", "officer": "Awaiting description", "confidence": 0, "landmark": location or "Not detected", "urgency": "Add a complaint description", "missing": "Describe the issue and how long it has existed."}
    scores = {category: sum(3 if len(keyword.split()) > 1 else 1.5 for keyword in data["keywords"] if keyword in text) for category, data in CATEGORIES.items()}
    category = max(scores, key=scores.get)
    if scores[category] == 0:
        category = "Roads & Infrastructure"
    priority = "Low"
    for level in ("Critical", "High", "Medium"):
        if any(rule in text for rule in PRIORITY_RULES[level].split()):
            priority = level
            break
    words = re.findall(r"\b\w+\b", text)
    confidence = min(98, max(68, round((scores[category] or 1) / (4 if len(words) > 5 else 2) * 100)))
    landmark_match = re.search(r"\b(?:near|opposite|behind|beside|next to|at)\s+([^.,\n]{3,40})", description, re.I)
    landmark = location.strip() or (landmark_match.group(0).strip() if landmark_match else "Zone 4, Central District")
    elapsed = re.search(r"(?:\d+|two|three|four|five|several)\s+(?:days|hours|weeks|months|nights)", text)
    missing = []
    if not location.strip() and not landmark_match:
        missing.append("a street number or nearby landmark")
    if len(words) < 6:
        missing.append("how long the problem has existed")
    return {"category": category, "priority": priority, "department": CATEGORIES[category]["department"], "officer": CATEGORIES[category]["officer"], "confidence": confidence, "landmark": landmark, "urgency": f"Ongoing: {elapsed.group(0)}" if elapsed else "Standard SLA dispatch", "missing": " and ".join(missing)}


def duplicate(description: str, category: str) -> str:
    new_words = set(re.findall(r"\b\w{3,}\b", description.lower()))
    best = None
    for item in rows():
        if item["status"] in ("Resolved", "Closed"):
            continue
        item_words = set(re.findall(r"\b\w{3,}\b", item["description"].lower()))
        union = new_words | item_words
        score = len(new_words & item_words) / len(union) if union else 0
        score += 0.25 if item["category"] == category else 0
        if score > 0.45 and (best is None or score > best[0]):
            best = (score, item)
    if not best:
        return ""
    return f"Similar active report: {best[1]['id']} | {best[1]['title']} | {round(best[0] * 100)}% match | {best[1]['status']} | {best[1]['upvotes']} citizens affected"


def preview(description: str, location: str) -> tuple[str, str, str, str, str, str, str]:
    result = analyze(description, location)
    warning = duplicate(description, result["category"]) if description.strip() else ""
    follow_up = f"AI follow-up: add {result['missing']}." if result["missing"] else "AI follow-up: all key dispatch details detected."
    return (result["category"], result["priority"], result["department"], result["officer"], f"{result['confidence']}% match", f"{result['landmark']} | {result['urgency']}", f"{warning}\n{follow_up}")


def create_complaint(location: str, description: str, name: str, phone: str) -> str:
    if not location.strip() or not description.strip():
        return "**Please provide both a location and a complaint description.**"
    result = analyze(description, location)
    with connect() as connection:
        number = connection.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] + 1050
        ticket_id = f"CMP-2026-{number}"
        timestamp = now()
        connection.execute("INSERT INTO complaints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (ticket_id, description[:57] + ("..." if len(description) > 57 else ""), description, result["category"], result["priority"], result["department"], result["officer"], location, "Registered", 1, name or "Anonymous Citizen", phone or "Not Provided", timestamp, timestamp, f"Registered|{timestamp}|Report received and routed to {result['department']} with {result['priority']} priority."))
    return f"### Complaint registered\nYour reference ID is **{ticket_id}**. Keep this ID to track the complaint."


def track(ticket_id: str) -> str:
    item = next((row for row in rows() if row["id"].lower() == ticket_id.strip().lower()), None)
    if not item:
        return "### Complaint not found\nCheck the reference ID and try again."
    steps = ["Registered", "Assigned", "In Progress", "Resolved"]
    current = steps.index(item["status"]) if item["status"] in steps else 0
    timeline = "\n".join(f"{'DONE' if index < current else 'CURRENT' if index == current else 'PENDING'}  **{step}**" for index, step in enumerate(steps))
    return f"## {item['id']}  ·  {item['status']}\n\n**{item['title']}**\n\n{item['description']}\n\n**Category:** {item['category']}  |  **Priority:** {item['priority']}\n\n**Location:** {item['location']}\n\n**Department:** {item['department']}\n\n**Officer:** {item['officer']}\n\n**Supporters:** {item['upvotes']} citizens\n\n### Service timeline\n{timeline}"


def upvote(ticket_id: str) -> str:
    with connect() as connection:
        connection.execute("UPDATE complaints SET upvotes = upvotes + 1 WHERE lower(id) = lower(?)", (ticket_id.strip(),))
    return track(ticket_id)


def dashboard(search: str, category: str, priority: str, status: str) -> tuple[str, str, str]:
    data = rows()
    filtered = [item for item in data if (not search or search.lower() in " ".join(str(item[field]) for field in ("id", "title", "description", "location", "department")).lower()) and (category == "All" or item["category"] == category) and (priority == "All" or item["priority"] == priority) and (status == "All" or item["status"] == status)]
    resolved = sum(item["status"] in ("Resolved", "Closed") for item in data)
    summary = f"## Department command center\n\n**{len(data)}** total reports &nbsp; **{len(data) - resolved}** active &nbsp; **{sum(item['priority'] == 'Critical' and item['status'] != 'Resolved' for item in data)}** critical &nbsp; **{round(resolved / len(data) * 100) if data else 0}%** resolution rate"
    categories = "\n".join(f"- **{name}:** {sum(item['category'] == name for item in data)}" for name in CATEGORIES)
    table = "| ID | Category | Priority | Status | Location | Supporters |\n|---|---|---|---|---|---|\n" + "\n".join(f"| {item['id']} | {item['category']} | {item['priority']} | {item['status']} | {item['location']} | {item['upvotes']} |" for item in filtered)
    return summary + "\n\n### Workload by category\n" + categories, f"Showing {len(filtered)} report(s)", table


def update_status(ticket_id: str, new_status: str, note: str) -> str:
    with connect() as connection:
        item = connection.execute("SELECT logs FROM complaints WHERE id = ?", (ticket_id.strip(),)).fetchone()
        if not item:
            return "Ticket ID not found."
        timestamp = now()
        log = item[0] + f"\n{new_status}|{timestamp}|{note or 'Status updated by municipal officer.'}"
        connection.execute("UPDATE complaints SET status = ?, updated_at = ?, logs = ? WHERE id = ?", (new_status, timestamp, log, ticket_id.strip()))
    return f"{ticket_id.strip()} updated to {new_status}."


def export_csv() -> str:
    output = io.StringIO()
    fields = ["id", "title", "description", "category", "priority", "department", "officer", "location", "status", "upvotes", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: item[field] for field in fields} for item in rows())
    path = ROOT / "complaints_export.csv"
    path.write_text(output.getvalue(), encoding="utf-8")
    return str(path)


initialize_database()

CSS = """body { background: #f7f7f6; color: #252525; } .gradio-container { width: calc(100% - 40px) !important; max-width: 1180px !important; margin: 0 auto !important; padding-top: 1.25rem !important; } .site-heading { border-bottom: 1px solid #d6d6d2; padding: 0 0 1rem; margin-bottom: 1rem; } .site-heading h1 { color: #253746; font-size: 1.7rem; font-weight: 600; margin: 0 0 .25rem; } .site-heading p { color: #656565; font-size: .92rem; margin: 0; } .section-box { border: 1px solid #d9d9d5; border-radius: 5px; padding: 1rem; background: #ffffff; } .muted { color: #666666; font-size: .88rem; } footer { display: none !important; }"""

with gr.Blocks(title="City Complaint Service", css=CSS, theme=gr.themes.Default()) as app:
    gr.HTML("<div class='site-heading'><h1>City Complaint Service</h1><p>Submit and track public service complaints.</p></div>")
    with gr.Tabs():
        with gr.Tab("Submit complaint"):
            gr.Markdown("### New complaint\nProvide the location and a short description of the issue.", elem_classes="muted")
            with gr.Row():
                with gr.Column(scale=2):
                    quick = gr.Radio(["Streetlight", "Water leak", "Pothole", "Garbage", "Safety hazard"], label="Use an example (optional)")
                    location = gr.Textbox(label="Street address or landmark", placeholder="5th Cross Road, Ward 12")
                    description = gr.Textbox(label="Complaint details", lines=5, placeholder="What happened? Include how long the issue has existed.")
                    with gr.Row():
                        name = gr.Textbox(label="Your name (optional)")
                        phone = gr.Textbox(label="Contact phone (optional)")
                    submit = gr.Button("Submit complaint", variant="primary")
                    receipt = gr.Markdown()
                with gr.Column(elem_classes="section-box"):
                    gr.Markdown("### Service routing")
                    category = gr.Textbox(label="Category", interactive=False)
                    priority = gr.Textbox(label="Priority", interactive=False)
                    department = gr.Textbox(label="Department", interactive=False)
                    officer = gr.Textbox(label="Contact officer", interactive=False)
                    confidence = gr.Textbox(label="Match confidence", interactive=False)
                    extracted = gr.Textbox(label="Location and response time", interactive=False)
                    ai_note = gr.Markdown()
            quick_examples = {"Streetlight": ("5th Cross Road, Ward 12", "Streetlight broken and sparking dangerously near school gate for three days"), "Water leak": ("Hospital Road, Sector 3, Ward 08", "Major drinking water pipeline burst opposite City Hospital flooding the road"), "Pothole": ("Metro Pillar 142, Ring Road, Ward 15", "Large crater pothole caused two bike accidents today"), "Garbage": ("Market Cross, Ward 04", "Community waste bin overflowing for 4 days, foul smell spreading to homes"), "Safety hazard": ("Opposite St. Mary School, Ward 02", "Storm snapped a large tree branch onto overhead cables blocking the lane")}
            quick.change(lambda choice: quick_examples.get(choice, ("", "")), quick, [location, description])
            location.input(preview, [description, location], [category, priority, department, officer, confidence, extracted, ai_note])
            description.input(preview, [description, location], [category, priority, department, officer, confidence, extracted, ai_note])
            submit.click(create_complaint, [location, description, name, phone], receipt)
        with gr.Tab("Track complaint"):
            ticket = gr.Textbox(label="Complaint reference ID", placeholder="CMP-2026-1042")
            with gr.Row():
                find = gr.Button("Search", variant="primary")
                support = gr.Button("Add my support")
            tracking = gr.Markdown("Enter a reference ID to see its service timeline.")
            find.click(track, ticket, tracking)
            support.click(upvote, ticket, tracking)
        with gr.Tab("Staff queue"):
            with gr.Row():
                search = gr.Textbox(label="Search")
                filter_category = gr.Dropdown(["All"] + list(CATEGORIES), value="All", label="Category")
                filter_priority = gr.Dropdown(["All", "Critical", "High", "Medium", "Low"], value="All", label="Priority")
                filter_status = gr.Dropdown(["All", "Registered", "Assigned", "In Progress", "Resolved"], value="All", label="Status")
            summary = gr.Markdown()
            result_count = gr.Markdown()
            registry = gr.Markdown()
            refresh = gr.Button("Refresh queue", variant="primary")
            with gr.Row():
                edit_id = gr.Textbox(label="Ticket ID")
                edit_status = gr.Dropdown(["Registered", "Assigned", "In Progress", "Resolved"], value="In Progress", label="New status")
                edit_note = gr.Textbox(label="Official note")
            update = gr.Button("Update status")
            update_result = gr.Markdown()
            export = gr.DownloadButton("Export CSV")
            inputs = [search, filter_category, filter_priority, filter_status]
            refresh.click(dashboard, inputs, [summary, result_count, registry])
            for control in [search, filter_category, filter_priority, filter_status]:
                control.change(dashboard, inputs, [summary, result_count, registry])
            update.click(update_status, [edit_id, edit_status, edit_note], update_result).then(dashboard, inputs, [summary, result_count, registry])
            export.click(export_csv, outputs=export)
            app.load(dashboard, inputs, [summary, result_count, registry])


if __name__ == "__main__":
    app.launch()