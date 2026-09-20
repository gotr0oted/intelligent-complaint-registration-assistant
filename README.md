# SmartCivic AI

An intelligent civic complaint registration and management system built with **Python, Gradio, and SQLite**.

## Features

- Register civic complaints in natural language
- Automatic category and priority detection
- Department & officer routing
- Duplicate complaint detection
- Complaint tracking with reference ID
- Staff queue with search, filters & status updates
- CSV export and persistent SQLite storage

## Tech Stack

- Python
- Gradio
- SQLite

## Project Structure

```text
SmartCivic-AI/
├── app.py
├── complaints.db
├── requirements.txt
└── README.md
```

## Run Locally

1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

2. Run the application

```bash
python app.py
```

3. Open the Gradio URL shown in the terminal (normally `http://127.0.0.1:7860`).

## Complaint Workflow

```text
Citizen
   │
   ▼
Enter Complaint
   │
   ▼
AI Analysis
(Category • Priority • Routing)
   │
   ▼
SQLite Database
   │
   ▼
Track Complaint / Staff Queue
```

## Author

**Parth Pusadkar**

B.Tech Computer Science & Engineering  
Symbiosis Institute of Technology, Nagpur
