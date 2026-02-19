import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, date, time
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
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    day_of_week = now.strftime("%A")
    current_hour = now.hour

    prompt = f"""
    Today is {day_of_week}, {today_date}. 
    The current time is {current_hour}:00.

    Extract the event(s) from the User Text into a JSON object.

    ### RULES:
    Provide a 'calendar_name' (a creative, short name for this specific group of events, e.g., "Spring Semester 2026", "Study Grind", or "Gym Routine").
    1. **Relative Dates**: 
    - If user says "tomorrow" and it's currently before 4 AM, "tomorrow" means today ({today_date}). 
    - Otherwise, "tomorrow" is the calendar day after {today_date}.
    2. **Date Inference**: Use {today_date} as the base. If no year is given, use {now.year}.
    3. **Time Formatting**: Convert all times to 24-hour HH:MM format (e.g., "4-6" becomes 16:00 and 18:00).
    4. **Recurrence**: 
    - If it's a one-time event (like "study tomorrow"), set 'days' to the 2-letter code for that specific day and 'end_date' to the same as 'start_date'.
    - If it's a list/schedule, use the 'classes' array.
    5. **Output**: Return ONLY JSON.
    6. **Missing End Dates**: 
   - If the user provides a single one-time event (e.g., "Study tomorrow"), set 'end_date' equal to 'start_date'.
   - If the user provides a recurring event (e.g., "Gym every Monday") but NO end date, set 'end_date' to 3 months from {today_date}.

    ### EXAMPLES:
    - Text: "Study tomorrow from 4-6"
    Result: {{"title": "Study", "days": ["TU"], "start_time": "16:00", "end_time": "18:00", "start_date": "2026-02-17", "end_date": "2026-02-17"}}

    - Text: "Gym MWF 8am"
    Result: {{"title": "Gym", "days": ["MO", "WE", "FR"], "start_time": "08:00", "end_time": "09:00", "start_date": "{today_date}", "end_date": "2026-05-01"}}

    User Text: "{text}"

    Return ONLY a JSON object with exactly this structure:
    {{
        "calendar_name": "Creative Name",
        "classes": [
            {{
            "title": "Event Name",
            "days": ["MO", "TU"],
            "start_time": "HH:MM",
            "end_time": "HH:MM",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD"
            }}
        ]
    }}
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

    #get calendar name
    calendar_name = parsed_response.get("calendar_name", "My AI Schedule")

    if not access_token or not parsed_response:
        return {"error": "Authentication failed or data lost."}

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # --- STEP A: CREATE THE NEW CALENDAR ---
    calendar_body = {
        "summary": calendar_name,  # This is the name of the new calendar
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
            # 1. Basic event structure
            event = {
                "summary": item.get("title", "New Event"),
                "start": {
                    "dateTime": f"{item['start_date']}T{item['start_time']}:00", 
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": f"{item['start_date']}T{item['end_time']}:00", 
                    "timeZone": "America/New_York"
                }
            }

            # 2. Only add recurrence if it's meant to repeat
            # Check if the end_date is different from the start_date OR if there are multiple days
            if item['start_date'] != item['end_date'] or len(item['days']) > 1:
                # Format the UNTIL date for Google (YYYYMMDDTHHMMSSZ)
                until_date = item['end_date'].replace('-', '')
                event["recurrence"] = [
                    f"RRULE:FREQ=WEEKLY;BYDAY={','.join(item['days'])};UNTIL={until_date}T235959Z"
                ]

            # 3. Post to Google
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
        "calendar_name": calendar_name
    })