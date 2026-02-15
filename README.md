# CalendLy
*NOTE Google Oauth page requires me to verify my service, so in the meantime I have granted access to the whole 15-113 staff to use CalendLy

A web-based utility that converts text schedules—like syllabuses, shift rotations, or workout routines—into Google Calendar events.

What it does
CalendLy takes unstructured text and organizes it into a structured calendar format. Instead of manually creating dozens of individual entries, you paste the text once, and the app handles the rest.

Dedicated Calendars: To avoid cluttering your main schedule, the app creates a new, separate calendar in your Google account for every import.

Recurring Logic: It identifies weekly patterns (e.g., "Mondays and Wednesdays") and sets up recurring events automatically.

Context Awareness: The app uses the current date as a reference point to ensure events are placed in the correct month and year.

How to use it
Input: Paste your schedule text into the dashboard.

Authenticate: Sign in with Google to grant permission to create a new calendar.

Review: The app processes the data and creates a new calendar named "My AI Class Schedule" (or your custom name) with all events populated.

Tech Stack
Backend: FastAPI (Python)

Frontend: HTML5 / Tailwind CSS

APIs: Google Calendar API, OpenAI API

Deployment: Render