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

Prompt Logs:

1. I am building an app that takes a block of text and uses an AI api call to parse this into a dataset that can be used to create a google calendar here is my instructions Perfect — this is exactly the right instinct. Below is a very concrete, no-fluff, step-by-step plan optimized for:



⏱ ~3 hours

🧠 Backend-first

🧱 Minimal frontend (HTML + JS)

🐍 FastAPI + requests

🎯 One recurring event → Google Calendar

If you follow this in order, you will end with a working system, not half-built pieces.

🧭 PHASE 0 — Lock the MVP (5 minutes)

MVP definition (do NOT expand this):



User pastes schedule text

AI extracts one recurring class

Adds it to primary Google Calendar

No preview

No DB

No user accounts

🔧 PHASE 1 — Google Cloud Setup (25–30 min)

1️⃣ Create Google Cloud Project

https://console.cloud.google.com

New Project → name it anything

2️⃣ Enable Calendar API

APIs & Services → Library

Enable Google Calendar API

3️⃣ Configure OAuth Consent Screen

User Type: External

App name: anything

Scopes:

https://www.googleapis.com/auth/calendar.events

Add your email as test user

⚠️ Skip branding, privacy policy, etc.

4️⃣ Create OAuth Credentials

APIs & Services → Credentials

Create → OAuth Client ID

Application type: Web application

Authorized redirect URI:



http://localhost:8000/oauth/callback

Save:



Client ID

Client Secret

🐍 PHASE 2 — FastAPI Backend Skeleton (30 min)

5️⃣ Create project



mkdir calendar-aicd calendar-ai

python -m venv venvsource venv/bin/activate

pip install fastapi uvicorn requests python-dotenv

6️⃣ Basic FastAPI app



# main.pyfrom fastapi import FastAPIfrom fastapi.responses import RedirectResponse



app = FastAPI()@app.get("/")def root():

return {"status": "ok"}

Run:





uvicorn main:app --reload

🔐 PHASE 3 — Google OAuth Flow (45 min)

7️⃣ Environment variables

Create .env:





GOOGLE_CLIENT_ID=xxx

GOOGLE_CLIENT_SECRET=yyy

GOOGLE_REDIRECT_URI=http://localhost:8000/oauth/callback

Load them:





import osfrom dotenv import load_dotenv

load_dotenv()

8️⃣ Start OAuth endpoint



@app.get("/auth/google")def auth_google():

url = (

"https://accounts.google.com/o/oauth2/v2/auth"

"?response_type=code"

f"&client_id={os.getenv('GOOGLE_CLIENT_ID')}"

f"&redirect_uri={os.getenv('GOOGLE_REDIRECT_URI')}"

"&scope=https://www.googleapis.com/auth/calendar.events"

"&access_type=offline"

"&prompt=consent"

)

return RedirectResponse(url)

9️⃣ OAuth callback



import requests



TOKEN_STORE = {}@app.get("/oauth/callback")def oauth_callback(code: str):

token_resp = requests.post(

"https://oauth2.googleapis.com/token",

data={

"code": code,

"client_id": os.getenv("GOOGLE_CLIENT_ID"),

"client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),

"redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),

"grant_type": "authorization_code",

},

).json()



TOKEN_STORE["access_token"] = token_resp["access_token"]

return {"status": "authenticated"}

✅ Test this now — if this fails, fix it before moving on.

🧠 PHASE 4 — AI Parsing Endpoint (30 min)

🔑 You want text → JSON, nothing else.

10️⃣ /parse



@app.post("/parse")def parse_schedule(payload: dict):

text = payload["text"]



# TODO: Replace with OpenAI call

return {

"title": "CS 112",

"days": ["MO", "WE", "FR"],

"start_time": "10:10",

"end_time": "11:00",

"start_date": "2026-01-15",

"end_date": "2026-05-02"

}

🚨 Hardcode first. Replace later.

📅 PHASE 5 — Create Calendar Event (30 min)

11️⃣ Event builder



def build_event(data):

return {

"summary": data["title"],

"start": {

"dateTime": f"{data['start_date']}T{data['start_time']}:00",

"timeZone": "America/New_York"

},

"end": {

"dateTime": f"{data['start_date']}T{data['end_time']}:00",

"timeZone": "America/New_York"

},

"recurrence": [

f"RRULE:FREQ=WEEKLY;BYDAY={','.join(data['days'])}"

]

}

12️⃣ Insert event



@app.post("/create-event")def create_event(data: dict):

headers = {

"Authorization": f"Bearer {TOKEN_STORE['access_token']}",

"Content-Type": "application/json"

}



event = build_event(data)



resp = requests.post(

"https://www.googleapis.com/calendar/v3/calendars/primary/events",

headers=headers,

json=event

)



return resp.json()

🎉 If this works, you’re basically done.

🌐 PHASE 6 — Minimal Frontend (20 min)

13️⃣ index.html



<textarea id="text"></textarea><button onclick="go()">Add to Calendar</button><script>async function go() {

const text = document.getElementById("text").value;



const parsed = await fetch("/parse", {

method: "POST",

headers: {"Content-Type": "application/json"},

body: JSON.stringify({text})

}).then(r => r.json());



await fetch("/auth/google");

}</script>

(This just triggers OAuth for MVP.)

🚀 PHASE 7 — Deploy to Render (Optional)

Add uvicorn main:app --host 0.0.0.0 --port 10000

Update OAuth redirect URI to Render URL

Set env vars in Render dashboard

🏁 FINAL CHECKLIST

✅ OAuth works

✅ Event appears in Google Calendar

✅ No secrets in frontend

✅ Backend does all the work

🧠 After You’re Done (Optional Polish)

Replace hardcoded parser with AI

2. OKay can you give me a step by step process to implement this with a minimalist frontend, focusing mostly on having a working backend.

3.  what is google_client_secret supposed to be

4. why do i need the /oauth/callback

5. it says calendly is restricted to users within its organization. this is the error i got Error 403: org_internal
Request details: access_type=offline scope=https://www.googleapis.com/auth/calendar.events response_type=code redirect_uri=http://127.0.0.1:8000/oath/callback prompt=consent flowName=GeneralOAuthFlow client_id=715585543513-q8v4jv4urslmiihg8g1v8firavlqv2rd.apps.googleusercontent.com

how do i fix this

6. Now I want to make it so that it does not automatically add the events to my calendar can I make it so that it produces a new calendar that the user can choose to add to their?
