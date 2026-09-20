# SmartCivic AI

SmartCivic AI is a Python and Gradio civic complaint system. Citizens can describe a municipal issue, receive automatic category and urgency routing, submit a ticket, track its lifecycle, and co-sign active reports. Department staff get searchable queue analytics, status updates, and CSV export.

## Run locally

```powershell
cd "C:\Users\parth\.gemini\antigravity-ide\scratch\intelligent-complaint-system"
python -m pip install -r requirements.txt
python app.py
```

Open the local Gradio URL printed in the terminal, normally `http://127.0.0.1:7860`.

## Included workflows

- Report intake with common-issue examples and live AI routing preview.
- Category, priority, department, officer, landmark, urgency, and duplicate detection.
- SQLite-backed complaint records that persist between launches.
- Four-stage tracking: Registered, Assigned, In Progress, and Resolved.
- Department queue filters, searchable registry, status updates, workload counts, and CSV export.

## Project files

- `app.py`: Gradio interface, classifier, persistence, tracking, analytics, and export.
- `requirements.txt`: Python dependency list.
- `complaints.db`: Created automatically on first launch with realistic demonstration tickets.

The project no longer uses the previous Node server or browser JavaScript implementation.
