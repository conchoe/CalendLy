import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import OpenAI
from datetime import date
from fastapi.templating import Jinja2Templates

load_dotenv()
app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory store (Note: This clears if the server restarts)
TOKEN_STORE = {}

# --- AI PARSING LOGIC ---
def ai_extract_schedule(text: str):
    today = date.today() 
    
    prompt = f"""
    Today's date is {today}. 
    
    Extract the following schedule or list of recurring events into a JSON object.
    Text: "{text}"
    
    INSTRUCTIONS:
    1. If a year is not mentioned, use {today.year}.
    2. If a specific start date is not mentioned, assume the events start as soon as possible after {today} or starting on {today}.
       only start on a day in the week that is specified in the Text.
    3. If user provides only one event, then have the end date be 7 days after {today}.
    4. If the user provides a list of events, return them in a list called "classes". 
    (Note: keep the key name "classes" for code compatibility, but treat them as generic events).
    
    Return ONLY JSON with these keys:
    title, days (list of 2-letter codes: MO, TU, WE, TH, FR, SA, SU), 
    start_time (HH:MM), end_time (HH:MM), 
    start_date (YYYY-MM-DD), end_date (YYYY-MM-DD).
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # This renders the file from the /templates folder
    return templates.TemplateResponse("index.html", {"request": request})
   
@app.post("/run")
async def run_process(payload: dict):
    # 1. Parse text with AI
    parsed_data = ai_extract_schedule(payload["text"])
    
    # 2. Store data temporarily to use after OAuth
    TOKEN_STORE["pending_event"] = parsed_data
    
    # 3. Trigger OAuth
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={os.getenv('GOOGLE_CLIENT_ID')}"
        f"&redirect_uri={os.getenv('GOOGLE_REDIRECT_URI')}"
        "&scope=https://www.googleapis.com/auth/calendar"
        "&access_type=offline&prompt=consent"
    )
    return {"auth_url": auth_url}

@app.get("/oauth/callback")
def oauth_callback(request: Request, code: str):
    # 1. Exchange Code for Token
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }).json()

    access_token = token_resp.get("access_token")
    parsed_response = TOKEN_STORE.get("pending_event")

    if not access_token or not parsed_response:
        return {"error": "Authentication failed or data lost."}

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # --- STEP A: CREATE THE NEW CALENDAR ---
    calendar_body = {
        "summary": "My AI Schedule",  # This is the name of the new calendar
        "timeZone": "America/New_York"
    }
    
    create_cal_res = requests.post(
        "https://www.googleapis.com/calendar/v3/calendars",
        headers=headers,
        json=calendar_body
    ).json()

    new_calendar_id = create_cal_res.get("id")
    
    if not new_calendar_id:
        return {"error": "Failed to create new calendar", "details": create_cal_res}

    # --- STEP B: ADD EVENTS TO THAT NEW CALENDAR ---
    classes_to_add = parsed_response.get("classes", [parsed_response])
    results = []
    
    for item in classes_to_add:
        try:
            event = {
                "summary": item.get("title", "New Class"),
                "start": {"dateTime": f"{item['start_date']}T{item['start_time']}:00", "timeZone": "America/New_York"},
                "end": {"dateTime": f"{item['start_date']}T{item['end_time']}:00", "timeZone": "America/New_York"},
                "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={','.join(item['days'])};UNTIL={item['end_date'].replace('-', '')}T235959Z"]
            }

            # We use {new_calendar_id} instead of 'primary' here
            requests.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{new_calendar_id}/events",
                headers=headers,
                json=event
            )
            results.append(f"Added: {item.get('title')}")
        except Exception as e:
            results.append(f"Failed to add {item.get('title')}: {str(e)}")

    return templates.TemplateResponse("success.html", {
        "request": request,
        "results": results,
        "calendar_name": "My AI Schedule"
    })