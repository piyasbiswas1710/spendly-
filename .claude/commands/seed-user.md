---
description: Create a single dummy user in the database
allowed-tools: Read, Bash(python3:*)
---

# Create a Dummy User

**Important:** If running on Windows, use the project's virtual environment interpreter (`venv\Scripts\python.exe`) or `python` instead of `python3` for all Python commands. 
## Objective

Create a single realistic dummy Indian user in the `users` table of the SQLite database.

## Instructions

1. Read `database/db.py` to understand:
   - The `users` table schema.
   - The `get_db()` helper function.

2. Reuse the existing `get_db()` helper for the database connection.

3. Generate a realistic random Indian user using common Indian names from any region.

### Name

Generate a realistic Indian first and last name.

Examples:

- Rahul Sharma
- Priya Iyer
- Arjun Nair
- Sneha Banerjee

### Email

Generate an email using the format:

```text
firstname.lastnameNN@gmail.com
```

where `NN` is a random 2–3 digit number.

Before inserting:

- Check whether the email already exists in the `users` table.
- If it exists, generate another suffix until a unique email is found.

### Password

Use:

```text
password123
```

Hash it using:

```python
from werkzeug.security import generate_password_hash
```

### Created At

Use the current datetime.

## Database Rules

- Use the existing `get_db()` helper.
- Use parameterized SQL queries only.
- Do not use f-strings or string formatting in SQL.
- Commit the transaction after insertion.

## Output

After successfully inserting the user, print:

```text
User created successfully

ID: <id>
Name: <name>
Email: <email>
```