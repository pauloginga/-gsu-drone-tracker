# GSU/CIS Drone Tracker

A web app for the GSU drone unit to log and manage mission attendance.

- **Pilots/Operators** register, wait for admin approval, then log in and record
  each mission: date, take-off time, landing time (duration is calculated
  automatically), and flight remarks.
- **Admins (Supervisors)** approve/reject new pilot registrations, view all
  attendance records, export them as a PDF, and clear the sheet to start fresh.

---

## 1. Project structure

```
gsu_drone_tracker/
├── app.py                  <- all the backend logic (routes, database models)
├── requirements.txt        <- Python packages this app needs
├── Procfile                <- tells Render how to start the app
├── templates/               <- HTML pages
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── pilot_dashboard.html
│   └── admin_dashboard.html
└── static/
    ├── css/style.css        <- black/red theme
    └── img/background.jpeg  <- your GSU photo
```

## 2. Run it on your own laptop first

You'll need **Python 3.10+** installed. Then, in a terminal, inside the
`gsu_drone_tracker` folder:

```bash
# 1. Create a virtual environment (keeps this project's packages separate)
python -m venv venv

# 2. Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install the required packages
pip install -r requirements.txt

# 4. Start the app
python app.py
```

Open **http://127.0.0.1:5000** in your browser. The database file
(`drone_tracker.db`) is created automatically on first run.

### Create your first admin account

There are two ways to create an admin account:

**Option A — through the website (recommended if you'll have several supervisors)**

There's a "Supervisor/Admin registration" link on the login page. It asks for
an **Admin Setup Code** in addition to the usual details — this stops random
pilots from making themselves admins. By default the code is:

```
change-this-admin-code
```

**Change this before you go live.** Set your own code as an environment
variable called `ADMIN_SETUP_CODE`:

- Running locally: set it before starting the app, e.g. on Mac/Linux
  `export ADMIN_SETUP_CODE="your-secret-code"` (Windows: `set ADMIN_SETUP_CODE=your-secret-code`),
  then run `python app.py`.
- On Render: add it under **Environment Variables** (same place as `SECRET_KEY`).

Share this code only with the actual supervisors who should have admin access.

**Option B — from the terminal**

```bash
flask --app app create-admin
```

It will ask for your name, service number, email, and password, then create
an approved admin account you can log in with immediately.

---

Either way, once you have one admin account, that admin can also approve
every pilot who registers through the normal web registration page.

## 3. Put it online permanently (Render, free tier)

This keeps the app running even when your laptop is off.

1. **Create a GitHub account** (if you don't have one) and a new repository,
   e.g. `gsu-drone-tracker`.
2. Upload this whole folder to that repository (GitHub's website lets you
   drag-and-drop files if you're not comfortable with git commands yet).
3. Go to **[render.com](https://render.com)** and sign up (free).
4. Click **New +** → **Web Service**, and connect your GitHub repo.
5. Fill in:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
6. Under **Environment Variables**, add:
   - `SECRET_KEY` → any long random string (this secures login sessions)
7. Click **Create Web Service**. Render will build and deploy it — you'll get
   a public URL like `https://gsu-drone-tracker.onrender.com`.
8. Once it's live, open a terminal on Render (via the **Shell** tab in your
   Render dashboard) and run:
   ```bash
   flask --app app create-admin
   ```
   to create your first admin account on the live site.

**Note on the free tier:** if nobody visits the site for a while, Render
"sleeps" it, and the next visit takes ~30-60 seconds to wake up. Everything
still works — it's just a short delay after inactivity. If that becomes a
problem later, Render's paid tier ($7/month) removes it, or we can revisit
another host.

### About the database on Render's free tier

The free tier's disk is **not permanent** — if the service restarts, the
SQLite database file can reset. For a first version / pilot test this is
fine. Once you're happy with the app, tell me and I'll help you switch to
Render's free PostgreSQL database instead, which *does* persist properly —
it's a small change to the `DATABASE_URL` setting, nothing needs to be
rebuilt from scratch.

## 4. Using the app day-to-day

- **New pilot:** goes to the login page → clicks "Register here" → fills in
  their details → waits for admin approval.
- **Admin:** logs in → sees pending registrations at the top of the
  dashboard → clicks Approve or Reject.
- **Pilot (once approved):** logs in → fills in mission date, take-off time,
  landing time, and remarks → sees their own mission history below the form.
- **Admin:** sees everyone's attendance in one table → **Export as PDF** to
  download a report → **Clear Attendance Sheet** once you're done with a
  reporting period (this permanently deletes the current records after
  they've been exported, so export first).

## 6. Updating an existing install (new features added after you'd already been using the app)

If you already had the app running and pull in updated files (like the new
"delete user" or "admin remarks" features), your existing `drone_tracker.db`
file was created with the *old* table structure and won't have the new
columns yet. This will cause errors like `no such column`.

Since this is early testing, the simplest fix is to delete the old database
file and let the app recreate it fresh:

1. Stop the app (`Ctrl+C`)
2. Delete `drone_tracker.db` from the project folder
3. Restart the app (`python app.py` / `py app.py`) — a new, empty database
   is created automatically
4. Recreate your admin account (Option A or B from step 2 above) and have
   pilots re-register

**This deletes all existing data** (accounts and mission history), so only
do this while you're still testing. Once you're using this for real records,
tell me before updating the app further — we'll switch to a proper migration
approach that preserves your data instead of resetting it.

## 7. Things you may want to add later

Once this version is working well, natural next steps include:
- Editing/deleting a single mistaken entry (instead of clearing everything)
- Filtering the PDF export by date range or by pilot
- A password reset flow
- Drone/aircraft identifiers per mission, if you're tracking multiple drones

Happy to help you build any of these next — just ask.
