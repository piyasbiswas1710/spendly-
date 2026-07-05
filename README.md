# Spendly

A personal expense tracking web application built with Flask and SQLite.

**Live demo:** https://expense-tracker-production-1d62.up.railway.app

## Features

- User registration and login
- Profile dashboard with spending stats, category breakdown, and recent transactions
- Add, edit, and delete expenses
- Date-range filtering (this month, last month, custom range, etc.)

## Tech Stack

- **Backend:** Flask 3.1.3 (Python 3.10+)
- **Database:** SQLite
- **Frontend:** Server-rendered Jinja2 templates, HTML5, CSS3, Vanilla JavaScript
- **Testing:** pytest, pytest-flask
- **Deployment:** Railway (Gunicorn)

## Running Locally

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

The app runs at `http://localhost:5001`.

## Running Tests

```bash
pytest
```

## Development Notes

This project was built using **agentic coding** — [Claude Code](https://claude.com/claude-code) was used throughout to implement features, write tests, and deploy the application.
