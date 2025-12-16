## Project Description

**Problem statement**  
I’m building a simple HR leave-management system for small teams who need to track employees, their leave balances (annual, sick, family, unpaid), and public holidays, while giving admins clear control and an audit trail, and giving employees an easy way to request time off and see their calendars.

**Solution**  
I implemented a web app where:

- **Admins can:**
  - Add and manage employees (with roles, departments, job titles, profile pictures).
  - Approve/reject leave requests, which automatically adjusts leave balances.
  - Configure public holidays (including recurring ones and Sunday-observed-on-Monday rules).
  - View audit logs of key administrative actions.

- **Employees can:**
  - Log in, update their profile, and change their password.
  - Apply for leave (including partial-day leave using hours) and upload supporting documents.
  - See their current leave balances, full leave history, and a calendar view of their leave and holidays.

There’s also a public marketing/landing page with a newsletter-style subscription and a “book a demo” form that stores leads in the database.

## Tech Stack

**Backend & language**
- Python with Flask as the web framework.
- Session-based auth with password hashing using Werkzeug.

**Database & data layer**
- PostgreSQL as the database.
- Direct SQL queries using psycopg2 and DictCursor (no ORM).
- Schema managed partly in code (`CREATE TABLE IF NOT EXISTS` in `app.py`) and partly via `.sql` migration files.

**Configuration & environment**
- python-dotenv to load environment variables from a `.env` file (DB credentials, `FLASK_SECRET_KEY`, etc.).

**File uploads & storage**
- Profile pictures and leave documents uploaded through forms and stored in `static/uploads`, using Werkzeug’s `secure_filename` to sanitize filenames.

**Frontend**
- Jinja2 templates via Flask for views like dashboards, calendars, admin screens, and the landing page.
- Static assets:
  - CSS (`style.css`, `landing.css`, `get.css`, `toast.css`) for layout and styling.
  - JavaScript (`confirmations.js`, `toast.js`) for confirmations and toast notifications.
  - Images for the landing page and dashboards.

## How I run it

I set `FLASK_APP=app.py` and run the app with:

```bash
flask run --debug
```