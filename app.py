import os
import datetime
from flask import Flask, redirect, request, session, url_for, render_template_string
from werkzeug.utils import secure_filename
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# ==========================================
# APP CONFIGURATION
# ==========================================
app = Flask(__name__)
app.secret_key = "super_secret_adhd_scheduler_key" 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = ['https://www.googleapis.com/auth/calendar.events', 'https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRETS_FILE = "credentials.json"

# Set up a temporary folder to store uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# 1. THE FRONTEND UI (HTML)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ADHD Task Scheduler</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .btn { display: inline-block; padding: 10px 20px; color: white; background: #4285F4; text-decoration: none; border-radius: 5px; font-weight: bold; border: none; cursor: pointer; width: 100%; text-align: center; box-sizing: border-box;}
        .btn-danger { background: #EA4335; margin-top: 10px;}
        .settings-box, .task-box { background: #f9f9f9; padding: 15px; margin-top: 20px; border-radius: 5px; border: 1px solid #ddd;}
        .form-group { margin-bottom: 15px; }
        label { font-weight: bold; display: block; margin-bottom: 5px; color: #555;}
        input[type="number"], input[type="time"], input[type="file"] { padding: 8px; border-radius: 4px; border: 1px solid #ccc; width: 100%; box-sizing: border-box; background: white;}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 ADHD Task Scheduler</h1>
        
        {% if not logged_in %}
            <p>Welcome! Please connect your Google Calendar to generate your personalized focus schedule.</p>
            <br>
            <a href="/authorize" class="btn">Log in with Google</a>
        {% else %}
            <p>✅ Connected to Google Calendar!</p>
            
            <div class="settings-box">
                <h3>⚙️ Focus Settings</h3>
                <form action="/update_settings" method="POST">
                    <div class="form-group">
                        <label>Attention Span (minutes):</label>
                        <input type="number" name="span" value="{{ current_span }}" min="5" max="60" required>
                    </div>
                    <div class="form-group" style="display: flex; gap: 10px;">
                        <div style="flex: 1;">
                            <label>Work Start Time:</label>
                            <input type="time" name="work_start" value="{{ work_start }}" required>
                        </div>
                        <div style="flex: 1;">
                            <label>Work End Time:</label>
                            <input type="time" name="work_end" value="{{ work_end }}" required>
                        </div>
                    </div>
                    <button type="submit" class="btn" style="padding: 8px 15px; font-size: 14px;">Save Settings</button>
                </form>
            </div>

            <div class="task-box">
                <h3>🎯 Upload Assignment/Syllabus</h3>
                <p style="font-size: 14px; color: #666;">Upload your PDF or Word Document. Our ML will extract the requirements, break them down, and schedule them.</p>
                <form action="/schedule_tasks" method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <input type="file" name="task_file" accept=".pdf, .doc, .docx" required>
                    </div>
                    <button type="submit" class="btn">Analyze File & Push to Calendar</button>
                </form>
            </div>
            
            <a href="/logout" class="btn btn-danger">Log Out</a>
            
            {% if message %}
                <p style="color: green; font-weight: bold; margin-top: 20px; text-align: center;">{{ message }}</p>
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""

# ==========================================
# 2. THE MACHINE LEARNING BRIDGE
# ==========================================
def run_ml_decomposition(filepath):
    """
    Takes the path of the uploaded file, passes it to your ML model,
    and returns the structured list of micro-tasks.
    """
    print(f"🤖 Processing uploaded document at: {filepath}")
    
    # ---------------------------------------------------------
    # TODO: PLUG IN YOUR ML FILE PARSER HERE
    # 1. Read the text from the file (using PyPDF2, pdfplumber, or python-docx)
    # 2. Feed that text into your ML model
    # 3. Return the decomposed tasks
    # 
    # Example:
    # tasks = process_document_with_ml(filepath)
    # ---------------------------------------------------------
    
    # Simulating the ML output for now
    ml_output = [
        {"name": "Extract key concepts from uploaded syllabus", "duration_minutes": 15},
        {"name": "Draft outline for main project deliverable", "duration_minutes": 30},
        {"name": "Review mandatory reading sections", "duration_minutes": 25}
    ]
    
    return ml_output

# ==========================================
# 3. WEB ROUTES & OAUTH FLOW
# ==========================================
def credentials_to_dict(credentials):
    return {'token': credentials.token, 'refresh_token': credentials.refresh_token, 'token_uri': credentials.token_uri, 'client_id': credentials.client_id, 'client_secret': credentials.client_secret, 'scopes': credentials.scopes}

@app.route('/')
def index():
    logged_in = 'credentials' in session
    current_span = session.get('attention_span', 20)
    work_start = session.get('work_start', '08:00')
    work_end = session.get('work_end', '20:00')
    message = request.args.get('message')
    return render_template_string(HTML_TEMPLATE, logged_in=logged_in, current_span=current_span, work_start=work_start, work_end=work_end, message=message)

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    session['code_verifier'] = flow.code_verifier 
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=session.get('state'))
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    flow.code_verifier = session.get('code_verifier') 
    flow.fetch_token(authorization_response=request.url)
    session['credentials'] = credentials_to_dict(flow.credentials)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    session['attention_span'] = int(request.form.get('span', 20))
    session['work_start'] = request.form.get('work_start', '08:00')
    session['work_end'] = request.form.get('work_end', '20:00')
    return redirect(url_for('index', message="Settings saved!"))

# ==========================================
# 4. SMART SCHEDULING ALGORITHMS
# ==========================================
def get_busy_intervals(service, time_min, time_max):
    events_result = service.events().list(calendarId='primary', timeMin=time_min.isoformat(), timeMax=time_max.isoformat(), singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    busy_intervals = []
    for event in events:
        if 'dateTime' in event['start']:
            start = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end = datetime.datetime.fromisoformat(event['end']['dateTime'])
            busy_intervals.append((start, end))
    return busy_intervals

def is_within_working_hours(target_start, target_end, working_hours_config):
    day_name = target_start.strftime("%A")
    if day_name not in working_hours_config: return False
    for block in working_hours_config[day_name]:
        allowed_start_dt = datetime.datetime.combine(target_start.date(), datetime.datetime.strptime(block["start"], "%H:%M").time()).replace(tzinfo=target_start.tzinfo)
        allowed_end_dt = datetime.datetime.combine(target_start.date(), datetime.datetime.strptime(block["end"], "%H:%M").time()).replace(tzinfo=target_start.tzinfo)
        if target_start >= allowed_start_dt and target_end <= allowed_end_dt: return True
    return False

def find_next_free_slot(duration_mins, current_search_time, working_hours, busy_intervals):
    while True:
        proposed_end = current_search_time + datetime.timedelta(minutes=duration_mins)
        if is_within_working_hours(current_search_time, proposed_end, working_hours):
            conflict = False
            for busy_start, busy_end in busy_intervals:
                if current_search_time < busy_end and busy_start < proposed_end:
                    conflict = True
                    current_search_time = busy_end
                    break
            if not conflict: return current_search_time, proposed_end
        current_search_time += datetime.timedelta(minutes=5)

# ==========================================
# 5. MAIN ROUTE LOGIC (WITH FILE UPLOAD)
# ==========================================
@app.route('/schedule_tasks', methods=['POST'])
def schedule_tasks():
    if 'credentials' not in session: return redirect(url_for('index'))

    # 1. File Upload Handling
    if 'task_file' not in request.files:
        return redirect(url_for('index', message="Error: No file uploaded."))
    
    file = request.files['task_file']
    if file.filename == '':
        return redirect(url_for('index', message="Error: No file selected."))

    # Secure the filename and save it temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 2. Feed the saved file to your ML model
    ml_tasks = run_ml_decomposition(filepath)

    # 3. Clean up: Delete the file from the server now that ML is done with it
    try:
        os.remove(filepath)
    except Exception as e:
        print(f"Warning: Could not delete temp file {filepath}. Error: {e}")

    # Initialize Google Calendar connection
    creds = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=creds)

    # 4. Cleanup Old Schedule
    if 'active_event_ids' in session:
        for event_id in session['active_event_ids']:
            try: service.events().delete(calendarId='primary', eventId=event_id).execute()
            except Exception: pass
        session.pop('active_event_ids', None)

    # 5. Divide Sessions based on Attention Span
    attention_span = session.get('attention_span', 20)
    schedule = []
    current_session = []
    current_time = 0

    for task in ml_tasks:
        rem_time = task['duration_minutes']
        while rem_time > 0:
            avail = attention_span - current_time
            if rem_time <= avail:
                current_session.append({"name": task['name'], "duration": rem_time})
                current_time += rem_time
                rem_time = 0
            else:
                current_session.append({"name": task['name'], "duration": avail})
                schedule.append(current_session)
                current_session = []
                current_time = 0
                rem_time -= avail
            if current_time == attention_span:
                schedule.append(current_session)
                current_session = []
                current_time = 0
    if current_session: schedule.append(current_session)

    # 6. Smart Push to Google Calendar
    now = datetime.datetime.now().astimezone()
    search_horizon = now + datetime.timedelta(days=14) 
    busy_intervals = get_busy_intervals(service, now, search_horizon)
    current_search_time = now
    
    start_time = session.get('work_start', '08:00')
    end_time = session.get('work_end', '20:00')
    working_hours_config = {day: [{"start": start_time, "end": end_time}] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
    generated_ids = []

    for i, sess in enumerate(schedule, 1):
        duration = sum(t['duration'] for t in sess)
        slot_start, slot_end = find_next_free_slot(duration_mins=duration, current_search_time=current_search_time, working_hours=working_hours_config, busy_intervals=busy_intervals)
        
        desc = f"Focus Session {i}\n" + "\n".join([f"• {t['name']} ({t['duration']}m)" for t in sess])
        event = {
            'summary': f'Focus Session {i}',
            'description': desc,
            'colorId': '11',
            'start': {'dateTime': slot_start.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': slot_end.isoformat(), 'timeZone': 'UTC'},
        }
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        generated_ids.append(event_result.get('id'))
        current_search_time = slot_end + datetime.timedelta(minutes=5)

    session['active_event_ids'] = generated_ids
    return redirect(url_for('index', message=f"✅ Document analyzed and scheduled successfully!"))

if __name__ == '__main__':
    app.run(port=8080, debug=True)