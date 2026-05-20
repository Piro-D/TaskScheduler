"""
ADHD Task Scheduler - Flask Application
Main entry point for the web application.
"""

import os
import json
import uuid
from flask import Flask, redirect, request, session, url_for, render_template
from werkzeug.utils import secure_filename

# Import service modules
from TaskEstimator import estimate_project_tasks
from LLM_Decomposition import process_document
from DurationEstimator import predict_duration_adhd
from oauth_service import get_authorization_url, handle_oauth_callback
from calendar_service import push_to_calendar
import config

# ==========================================
# APP INITIALIZATION
# ==========================================
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ACTIVE_SCHEDULE_FILE = 'active_schedule.json'

# ==========================================
# FILE-BASED STATE MANAGEMENT (Bypasses 4KB Cookie Limit)
# ==========================================
def load_state():
    """Load the task backlog and calendar events from a local file safely."""
    default_state = {"tasks": [], "events": []}
    
    if not os.path.exists(ACTIVE_SCHEDULE_FILE):
        return default_state
        
    try:
        with open(ACTIVE_SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
            # Ensure the keys exist, if not, return default
            if 'tasks' in data and 'events' in data:
                return data
            else:
                return default_state
    except (json.JSONDecodeError, KeyError):
        # If the file is corrupted JSON, return default and potentially back up the bad file
        print("⚠️ Warning: active_schedule.json was corrupted. Resetting to empty state.")
        return default_state

def save_state(tasks, events):
    """Save the task backlog and calendar events to a local file."""
    with open(ACTIVE_SCHEDULE_FILE, 'w') as f:
        json.dump({"tasks": tasks, "events": events}, f, indent=4)

def sync_calendar(tasks):
    """
    Centralized function to delete old events, schedule new ones, 
    and save the new state to the JSON file.
    """
    state = load_state()
    
    # We combine the session settings with the file-based event IDs for the calendar service
    sync_data = dict(session)
    sync_data['active_event_ids'] = state.get('events', [])
    
    # Push to Google Calendar
    new_event_ids = push_to_calendar(tasks, sync_data)
    
    # Save the updated task list and new calendar IDs to our file
    save_state(tasks, new_event_ids)

# ==========================================
# ML PIPELINE INTEGRATION
# ==========================================
def run_ml_decomposition(filepath):
    print(f"\n🚀 Bridging to TaskEstimator.py...")
    try:
        pipeline_result = estimate_project_tasks(filepath, buffer=config.BUFFER_MULTIPLIER)
        if pipeline_result.get("status") != "success":
            print(f"❌ Pipeline Error: {pipeline_result.get('message')}")
            return None
        
        formatted_tasks = []
        for task in pipeline_result.get("tasks", []):
            try:
                duration = int(task.get("estimated_duration_minutes", 60))
                formatted_tasks.append({
                    "name": task.get("task_name", "Unnamed Task"),
                    "duration_minutes": duration
                })
            except Exception as e:
                print(f"⚠️ Warning: Could not parse task data: {task} | Error: {e}")
        
        print(f"✅ Bridge successful. Passed {len(formatted_tasks)} formatted tasks.")
        return formatted_tasks
    except Exception as e:
        print(f"❌ ML Pipeline Error: {e}")
        return None

# ==========================================
# WEB ROUTES - DASHBOARD
# ==========================================
@app.route('/')
def index():
    logged_in = 'credentials' in session
    current_span = session.get('attention_span', config.DEFAULT_ATTENTION_SPAN)
    break_duration = session.get('break_duration', config.DEFAULT_BREAK_DURATION)
    
    message = request.args.get('message')
    active_tab = request.args.get('tab', 'pipeline')
    
    decompose_result = session.pop('decompose_result', None)
    estimate_result = session.pop('estimate_result', None)
    
    default_config = {day: [{"start": "08:00", "end": "20:00"}] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
    working_hours_config = session.get('working_hours_config', default_config)
    
    # Fetch the accumulative task backlog from the FILE, not the session!
    state = load_state()
    saved_tasks = state['tasks']
    has_saved_tasks = len(saved_tasks) > 0
    
    return render_template(
        'index.html',
        logged_in=logged_in,
        current_span=current_span,
        working_hours_config=working_hours_config,
        break_duration=break_duration,
        message=message,
        active_tab=active_tab,
        decompose_result=decompose_result,
        estimate_result=estimate_result,
        saved_tasks=saved_tasks,
        has_saved_tasks=has_saved_tasks
    )

# ==========================================
# WEB ROUTES - AUTHENTICATION
# ==========================================
@app.route('/authorize')
def authorize():
    try:
        authorization_url, state, code_verifier = get_authorization_url()
        session['state'] = state
        session['code_verifier'] = code_verifier
        return redirect(authorization_url)
    except Exception as e:
        return redirect(url_for('index', message=f"❌ Google OAuth Error: {str(e)}"))

@app.route('/oauth2callback')
def oauth2callback():
    try:
        credentials = handle_oauth_callback(request.url, session.get('state'), session.get('code_verifier'))
        session['credentials'] = credentials
        session.pop('state', None)
        session.pop('code_verifier', None)
        return redirect(url_for('index'))
    except Exception as e:
        return redirect(url_for('index', message=f"❌ OAuth Callback Error: {str(e)}"))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==========================================
# WEB ROUTES - ACTIONS & TOOLS
# ==========================================
@app.route('/update_settings', methods=['POST'])
def update_settings():
    session['attention_span'] = int(request.form.get('span', config.DEFAULT_ATTENTION_SPAN))
    session['break_duration'] = int(request.form.get('break_duration', config.DEFAULT_BREAK_DURATION))
    
    selected_days = request.form.getlist('working_days')
    new_config = {}
    for day in selected_days:
        new_config[day] = [{"start": request.form.get(f"{day}_start", "08:00"), "end": request.form.get(f"{day}_end", "20:00")}]
    session['working_hours_config'] = new_config
    session.modified = True 
    
    # Resync the calendar using the tasks from the file
    state = load_state()
    if state['tasks'] and 'credentials' in session:
        try:
            sync_calendar(state['tasks'])
            return redirect(url_for('index', message="✅ Settings saved & Calendar dynamically updated!", tab='pipeline'))
        except Exception as e:
            return redirect(url_for('index', message=f"⚠️ Settings saved, but Calendar update failed: {e}", tab='pipeline'))
            
    return redirect(url_for('index', message="✅ Schedule configuration saved!", tab='pipeline'))

@app.route('/schedule_tasks', methods=['POST'])
def schedule_tasks():
    """Upload Document and APPEND to Task Backlog"""
    if 'credentials' not in session: return redirect(url_for('index', message="❌ Log in first.", tab='pipeline'))
    if 'task_file' not in request.files or request.files['task_file'].filename == '':
        return redirect(url_for('index', message="❌ No file selected.", tab='pipeline'))

    file = request.files['task_file']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)

    new_ml_tasks = run_ml_decomposition(filepath)
    try: os.remove(filepath)
    except Exception: pass

    if not new_ml_tasks: return redirect(url_for('index', message="❌ AI processing failed.", tab='pipeline'))

    # Load file state, append new tasks, and resync!
    state = load_state()
    existing_tasks = state['tasks']
    
    for t in new_ml_tasks:
        t['id'] = str(uuid.uuid4())
        existing_tasks.append(t)

    try:
        sync_calendar(existing_tasks)
        return redirect(url_for('index', message="✅ Document parsed! Tasks appended to backlog and scheduled.", tab='pipeline'))
    except Exception as e:
        return redirect(url_for('index', message=f"⚠️ Scheduled failed: {str(e)}", tab='pipeline'))

# ==========================================
# BACKLOG MANAGEMENT ROUTES
# ==========================================
@app.route('/update_backlog', methods=['POST'])
def update_backlog():
    """Update durations, mark tasks as complete, and resync calendar."""
    if 'credentials' not in session: return redirect(url_for('index', message="❌ Log in first."))
    
    state = load_state()
    task_ids = request.form.getlist('task_ids')
    updated_tasks = []
    
    for t_id in task_ids:
        # If checked "Done", it is skipped and naturally deleted from the new list
        if request.form.get(f'complete_{t_id}'):
            continue
        
        new_duration = int(request.form.get(f'duration_{t_id}', 0))
        new_name = request.form.get(f'name_{t_id}', "Task")
        
        if new_duration > 0:
            # Preserve old attributes if it exists, otherwise create new
            original = next((t for t in state['tasks'] if t.get('id') == t_id), None)
            if original:
                original['name'] = new_name
                original['duration_minutes'] = new_duration
                updated_tasks.append(original)
            else:
                updated_tasks.append({"id": t_id, "name": new_name, "duration_minutes": new_duration})
    
    try:
        sync_calendar(updated_tasks)
        return redirect(url_for('index', message="✅ Backlog updated & Calendar synced!", tab='pipeline'))
    except Exception as e:
        return redirect(url_for('index', message=f"⚠️ Update saved, but Calendar sync failed: {e}", tab='pipeline'))

@app.route('/clear_backlog', methods=['POST'])
def clear_backlog():
    """Wipes out all tasks and clears upcoming calendar blocks."""
    if 'credentials' in session:
        try:
            sync_calendar([]) # Pushing an empty list deletes all events and clears the file
        except: pass
    return redirect(url_for('index', message="🧹 All tasks cleared!", tab='pipeline'))

# ==========================================
# INDIVIDUAL TOOL ROUTES
# ==========================================
@app.route('/tool_decompose', methods=['POST'])
def tool_decompose():
    if 'doc_file' not in request.files or request.files['doc_file'].filename == '':
        return redirect(url_for('index', message="❌ No file selected.", tab='decompose'))
        
    file = request.files['doc_file']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)
    
    result = process_document(filepath)
    try: os.remove(filepath)
    except: pass
    
    if result.get('status') == 'success':
        session['decompose_result'] = result.get('tasks')
        return redirect(url_for('index', message="✅ Decomposition complete!", tab='decompose'))
    return redirect(url_for('index', message=f"❌ Error: {result.get('message')}", tab='decompose'))

@app.route('/tool_estimate', methods=['POST'])
def tool_estimate():
    try:
        expert_hours = float(request.form.get('hours', 1))
        complexity = int(request.form.get('complexity', 3))
        task_type = request.form.get('task_type', 'general')
        
        minutes = predict_duration_adhd(expert_hours * 3600, complexity, task_type, buffer=config.BUFFER_MULTIPLIER)
        
        session['estimate_result'] = {
            "hours": expert_hours, "complexity": complexity, "type": task_type, "adhd_minutes": minutes
        }
        return redirect(url_for('index', message="✅ Prediction generated!", tab='estimate'))
    except Exception as e:
        return redirect(url_for('index', message=f"❌ Estimation Error: {str(e)}", tab='estimate'))

@app.route('/tool_schedule', methods=['POST'])
def tool_schedule():
    """APPEND Manual Tasks to Backlog"""
    if 'credentials' not in session: return redirect(url_for('index', message="❌ Log in first.", tab='schedule'))
    try:
        raw_json = request.form.get('json_tasks', '[]')
        tasks = json.loads(raw_json)
        
        state = load_state()
        existing_tasks = state['tasks']
        
        for t in tasks:
            clean_task = {
                "id": str(uuid.uuid4()), 
                "name": t.get("name", "Manual Task"), 
                "duration_minutes": int(t.get("duration_minutes", 30))
            }
            existing_tasks.append(clean_task)
            
        sync_calendar(existing_tasks)
        return redirect(url_for('index', message="✅ Custom tasks appended to backlog and scheduled!", tab='schedule'))
    except json.JSONDecodeError:
        return redirect(url_for('index', message="❌ Invalid JSON format.", tab='schedule'))
    except Exception as e:
        return redirect(url_for('index', message=f"❌ Scheduling Error: {str(e)}", tab='schedule'))

if __name__ == '__main__':
    app.run(port=8080, debug=True)
