import streamlit as st
import re
import json
import random
import threading
import time
import urllib.parse
import urllib.request
import smtplib
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Supabase (via REST API) ───────────────────────────────────────────────────
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]

def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def sb_get(table, match_col, match_val):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{urllib.parse.quote(str(match_val))}"
    req = urllib.request.Request(url, headers=_sb_headers())
    try:
        with urllib.request.urlopen(req) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except Exception:
        return None

def sb_upsert(table, data: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(data).encode()
    headers = {**_sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"Supabase upsert error: {e}")
        return None

# ── Account & Schedule helpers ────────────────────────────────────────────────
def load_account(email: str):
    return sb_get("accounts", "email", email)

def save_account(user: dict):
    sb_upsert("accounts", {
        "email":    user["email"],
        "name":     user.get("name", ""),
        "password": user.get("password", ""),
        "picture":  user.get("picture", ""),
        "google":   user.get("google", False),
    })

def load_schedules(email: str):
    row = sb_get("schedules", "email", email)
    if row and "data" in row:
        return row["data"] if isinstance(row["data"], list) else json.loads(row["data"])
    return []

def save_schedules():
    if st.session_state.user:
        sb_upsert("schedules", {
            "email": st.session_state.user["email"],
            "data":  st.session_state.schedules,
        })

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Study Planner", page_icon="📚",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
    --green:#1B5E40; --green2:#2E7D56; --green3:#4CAF82;
    --cream:#F8F6F1; --white:#FFFFFF; --ink:#0D1F16;
    --muted:#6B8F77; --border:#C8DDD3;
    --shadow:0 4px 24px rgba(27,94,64,.10); --radius:14px;
}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:var(--cream);color:var(--ink);}
.stApp{background:var(--cream);}
#MainMenu,footer,header{visibility:hidden;}
.topbar{background:var(--green);color:var(--white);padding:14px 32px;
    border-radius:0 0 var(--radius) var(--radius);display:flex;align-items:center;
    gap:12px;margin-bottom:28px;box-shadow:var(--shadow);}
.topbar-title{font-family:'DM Serif Display';font-size:1.5rem;letter-spacing:.5px;}
.topbar-sub{font-size:.85rem;opacity:.75;margin-top:2px;}
div[data-testid="stHorizontalBlock"] button{border-radius:50px!important;
    border:2px solid var(--border)!important;background:var(--white)!important;
    color:var(--green)!important;font-weight:500!important;transition:all .2s;}
div[data-testid="stHorizontalBlock"] button:hover{background:var(--green)!important;
    color:var(--white)!important;border-color:var(--green)!important;}
.card{background:var(--white);border-radius:var(--radius);padding:24px 28px;
    box-shadow:var(--shadow);border:1px solid var(--border);margin-bottom:20px;}
.card-title{font-family:'DM Serif Display';font-size:1.25rem;color:var(--green);
    margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--border);}
.greeting-card{background:linear-gradient(135deg,var(--green) 0%,var(--green2) 100%);
    color:var(--white);border-radius:var(--radius);padding:32px;margin-bottom:24px;box-shadow:var(--shadow);}
.greeting-card h2{font-family:'DM Serif Display';font-size:2rem;margin:0 0 6px;}
.greeting-card p{opacity:.8;margin:0;}
.stat-box{background:var(--cream);border:1px solid var(--border);border-radius:10px;
    padding:16px 24px;text-align:center;min-width:110px;}
.stat-num{font-size:2rem;font-weight:700;color:var(--green);line-height:1;}
.stat-lbl{font-size:.78rem;color:var(--muted);margin-top:4px;}
.stTextInput input,.stSelectbox div[data-baseweb="select"],.stNumberInput input{
    border:2px solid var(--border)!important;border-radius:10px!important;
    background:var(--cream)!important;font-family:'DM Sans'!important;color:var(--ink)!important;}
.stTextInput input:focus{border-color:var(--green)!important;}
.stButton>button[kind="primary"],.stFormSubmitButton>button{
    background:var(--green)!important;color:var(--white)!important;border:none!important;
    border-radius:50px!important;padding:10px 32px!important;font-weight:600!important;
    font-size:.95rem!important;transition:all .2s!important;
    box-shadow:0 4px 12px rgba(27,94,64,.25)!important;}
.stButton>button[kind="primary"]:hover{background:var(--green2)!important;
    transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(27,94,64,.35)!important;}
.stButton>button{border:2px solid var(--green)!important;color:var(--green)!important;
    border-radius:50px!important;background:transparent!important;font-weight:500!important;transition:all .2s!important;}
.stButton>button:hover{background:var(--green)!important;color:var(--white)!important;}
.alert-success{background:#E8F5EE;border-left:4px solid var(--green3);border-radius:8px;
    padding:12px 16px;color:var(--green);font-size:.9rem;margin:8px 0;}
.alert-error{background:#FFF0F0;border-left:4px solid #E53935;border-radius:8px;
    padding:12px 16px;color:#B71C1C;font-size:.9rem;margin:8px 0;}
.task-pill{display:inline-block;border-radius:50px;padding:3px 12px;font-size:.78rem;font-weight:600;margin-left:8px;}
.pill-pending{background:#FFF8E1;color:#F57F17;}
.pill-completed{background:#E8F5EE;color:var(--green);}
.pill-missed{background:#FFF0F0;color:#C62828;}
hr{border-color:var(--border);margin:20px 0;}
.reminder-toast{background:var(--green);color:white;padding:14px 20px;border-radius:var(--radius);
    margin-bottom:12px;font-size:.9rem;display:flex;align-items:center;gap:10px;animation:slideIn .4s ease;}
@keyframes slideIn{from{transform:translateY(-10px);opacity:0;}to{transform:translateY(0);opacity:1;}}
</style>
""", unsafe_allow_html=True)

# ── Session defaults ──────────────────────────────────────────────────────────
def init_state():
    for k, v in {
        "logged_in": False, "user": None, "page": "login",
        "active_tab": "Dashboard", "schedules": [],
        "reminders_sent": set(), "in_app_reminders": [],
        "google_access_token": "",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Validators ────────────────────────────────────────────────────────────────
PW_RE = re.compile(r'^(?=.*[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]).{8,}$')

def valid_gmail(email: str) -> bool:
    if not email: return False
    email = email.strip().lower()
    if not email.endswith("@gmail.com"): return False
    local = email[:-10]
    if not (6 <= len(local) <= 30): return False
    if not re.match(r'^[a-z0-9.]+$', local): return False
    if local.startswith('.') or local.endswith('.') or '..' in local: return False
    return True

def valid_password(pw): return bool(PW_RE.match(pw))

def greeting():
    h = datetime.now().hour
    return "Good Morning" if h < 12 else "Good Afternoon" if h < 17 else "Good Evening"

def difficulty_color(d):
    return {"Easy":"#4CAF82","Medium":"#FB8C00","Hard":"#E53935"}.get(d,"#888")

# ── Email reminder ────────────────────────────────────────────────────────────
def send_email_reminder(to_email, task_name, start_time, access_token="", sender_email=""):
    if not access_token or not sender_email: return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Study Reminder: {task_name} starts in 15 min!"
        msg["From"] = sender_email
        msg["To"]   = to_email
        msg.attach(MIMEText(f"""
        <div style="font-family:sans-serif;max-width:500px;margin:auto;background:#f8f6f1;
                    border-radius:12px;padding:28px;border:1px solid #c8ddd3;">
          <h2 style="color:#1B5E40;margin:0 0 8px;">AI Study Planner</h2>
          <div style="background:#fff;border-radius:10px;padding:20px;border:1px solid #c8ddd3;">
            <p style="margin:0 0 8px;font-size:1.1rem;font-weight:600;">{task_name}</p>
            <p style="margin:0;color:#6B8F77;">Starts at <b>{start_time}</b> - 15 minutes away!</p>
          </div>
        </div>""", "html"))
        auth_str   = f"user={sender_email}\x01auth=Bearer {access_token}\x01\x01"
        auth_bytes = base64.b64encode(auth_str.encode()).decode()
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo(); smtp.starttls(); smtp.ehlo()
            smtp.docmd("AUTH", "XOAUTH2 " + auth_bytes)
            smtp.sendmail(sender_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def check_reminders():
    now = datetime.now()
    for sched in st.session_state.schedules:
        for day in sched.get("days", []):
            for task in day.get("tasks", []):
                tid = task.get("id", "")
                if tid in st.session_state.reminders_sent: continue
                try:
                    dt   = datetime.strptime(f"{day['date']} {task['start']}", "%Y-%m-%d %H:%M")
                    diff = (dt - now).total_seconds() / 60
                    if 0 < diff <= 15:
                        st.session_state.in_app_reminders.append(
                            {"msg": f"'{task['name']}' starts at {task['start']} today!", "task_id": tid})
                        st.session_state.reminders_sent.add(tid)
                        token  = st.session_state.get("google_access_token", "")
                        sender = st.session_state.user["email"]
                        threading.Thread(target=send_email_reminder,
                            args=(sender, task["name"], task["start"], token, sender), daemon=True).start()
                except: pass

# ── Schedule generator ────────────────────────────────────────────────────────
def generate_schedule(plan_days, available, committed, tasks):
    days = []
    today = datetime.today()
    diff_order = {"Hard":1,"Medium":2,"Easy":3}
    sorted_tasks = sorted(tasks, key=lambda t: diff_order.get(t.get("difficulty","Medium"),2))
    total = len(sorted_tasks)
    if total < plan_days:
        extras = []
        for j in range(plan_days - total):
            base = sorted_tasks[j % total].copy()
            base["name"] = f"Revisit: {base['name']}"
            base["duration"] = max(20, int(base.get("duration",60))//2)
            base["difficulty"] = "Easy"
            extras.append(base)
        sorted_tasks += extras
        total = len(sorted_tasks)
    day_task_map = {i:[] for i in range(plan_days)}
    for idx, task in enumerate(sorted_tasks):
        day_task_map[idx % plan_days].append(task)

    for i in range(plan_days):
        date_str   = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        label      = (today + timedelta(days=i)).strftime("%A, %d %b")
        av         = available.get(i, available.get(0, {"start":"09:00","end":"17:00"}))
        slot_start = datetime.strptime(f"{date_str} {av['start']}", "%Y-%m-%d %H:%M")
        slot_end   = datetime.strptime(f"{date_str} {av['end']}",   "%Y-%m-%d %H:%M")
        committed_today = [c for c in committed if c.get("day",0) == i]
        scheduled_tasks = []
        current = slot_start

        def skip_committed(cur, dur_min, _c=committed_today, _d=date_str):
            end = cur + timedelta(minutes=dur_min)
            for c in _c:
                try:
                    cs = datetime.strptime(f"{_d} {c['start']}", "%Y-%m-%d %H:%M")
                    ce = datetime.strptime(f"{_d} {c['end']}",   "%Y-%m-%d %H:%M")
                    if cur < ce and end > cs: cur = ce; end = cur + timedelta(minutes=dur_min)
                except: pass
            return cur, end

        def add_slot(cur, name, dur_min, difficulty="", deadline="", is_auto=False,
                     _s=scheduled_tasks, _e=slot_end, _d=date_str):
            cur, end = skip_committed(cur, dur_min)
            if end > _e: return cur, False
            _s.append({"id": f"{_d}_{name[:20]}_{random.randint(1000,9999)}",
                        "name":name,"start":cur.strftime("%H:%M"),"end":end.strftime("%H:%M"),
                        "duration":dur_min,"deadline":deadline,"difficulty":difficulty,
                        "status":"Pending","auto":is_auto})
            return end, True

        current, ok = add_slot(current, "🧘 Morning Meditation", 20, difficulty="Easy", is_auto=True)
        if ok: current += timedelta(minutes=5)

        todays = sorted(day_task_map.get(i,[]), key=lambda t: diff_order.get(t.get("difficulty","Medium"),2))
        done_today = []
        for idx2, task in enumerate(todays):
            current, ok = add_slot(current, task["name"], int(task.get("duration",60)),
                                   difficulty=task.get("difficulty","Medium"), deadline=task.get("deadline",""))
            if ok:
                done_today.append(task["name"])
                current += timedelta(minutes=20 if (idx2+1)%2==0 else 10)

        if done_today:
            rev_min = max(20, min(45, sum(int(t.get("duration",60)) for t in todays)//4))
            current, _ = add_slot(current, f"📝 Revision: {' + '.join(done_today[:3])}", rev_min,
                                  difficulty="Easy", is_auto=True)
            current += timedelta(minutes=5)

        if i == plan_days - 1:
            all_names = [t["name"] for t in sorted_tasks if not t["name"].startswith("Revisit")]
            add_slot(current, "🔁 Final Recap: All Topics",
                     max(30, min(60, len(all_names)*10)), difficulty="Easy", is_auto=True)

        days.append({"date":date_str,"label":label,"tasks":scheduled_tasks})
    return days

# ── Topbar ────────────────────────────────────────────────────────────────────
def topbar(subtitle=""):
    sub_html = f'<div class="topbar-sub">{subtitle}</div>' if subtitle else ''
    st.markdown(
        '<div class="topbar"><span style="font-size:1.8rem;">&#128218;</span>'
        '<div><div class="topbar-title">AI Study Planner</div>' + sub_html + '</div></div>',
        unsafe_allow_html=True)

# ── Google OAuth ──────────────────────────────────────────────────────────────
def get_google_auth_url():
    params = {
        "client_id":     st.secrets["google"]["client_id"],
        "redirect_uri":  st.secrets["google"]["redirect_uri"],
        "response_type": "code",
        "scope":         "openid email profile https://mail.google.com/",
        "access_type":   "offline",
        "prompt":        "consent select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

def exchange_code_for_tokens(code):
    data = urllib.parse.urlencode({
        "code": code,
        "client_id":     st.secrets["google"]["client_id"],
        "client_secret": st.secrets["google"]["client_secret"],
        "redirect_uri":  st.secrets["google"]["redirect_uri"],
        "grant_type":    "authorization_code",
    }).encode()
    try:
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
        with urllib.request.urlopen(req) as r: return json.loads(r.read())
    except Exception as e: return {"error": str(e)}

def get_google_userinfo(access_token):
    try:
        req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo",
                                     headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req) as r: return json.loads(r.read())
    except Exception as e: return {"error": str(e)}

def handle_google_callback():
    code = st.query_params.get("code", "")
    if not code: return False
    st.query_params.clear()
    with st.spinner("Signing you in with Google..."):
        tokens = exchange_code_for_tokens(code)
        if "error" in tokens: st.error(f"Google sign-in failed: {tokens['error']}"); return False
        access_token = tokens.get("access_token", "")
        userinfo = get_google_userinfo(access_token)
        if "error" in userinfo: st.error("Could not fetch Google profile."); return False
        email = userinfo.get("email", "")
        if not valid_gmail(email): st.error("Only @gmail.com accounts are supported."); return False
        user = {"name": userinfo.get("name", email.split("@")[0]),
                "email": email, "password": "", "picture": userinfo.get("picture",""), "google": True}
        save_account(user)
        st.session_state.logged_in           = True
        st.session_state.user                = user
        st.session_state.google_access_token = access_token
        st.session_state.schedules           = load_schedules(email)
        st.session_state.page                = "dashboard"
        return True

# ── Login page ────────────────────────────────────────────────────────────────
def login_page():
    if handle_google_callback(): st.rerun(); return
    topbar()
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            st.markdown('<div class="card-title">🔐 Login</div>', unsafe_allow_html=True)
            auth_url = get_google_auth_url()
            st.markdown(f"""
            <a href="{auth_url}" target="_self" style="text-decoration:none;">
              <div style="display:flex;align-items:center;justify-content:center;gap:12px;
                background:#fff;border:2px solid #c8ddd3;border-radius:50px;padding:11px 24px;
                cursor:pointer;font-family:'DM Sans',sans-serif;font-weight:600;color:#1B5E40;
                box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:8px;">
                <svg width="20" height="20" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.7 2.5 30.2 0 24 0 14.8 0 6.9 5.4 3 13.3l7.8 6C12.6 13.1 17.9 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17z"/>
                  <path fill="#FBBC05" d="M10.8 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7L2.5 13.3A23.9 23.9 0 0 0 0 24c0 3.8.9 7.4 2.5 10.6l8.3-5.9z"/>
                  <path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.5-5.8c-2.1 1.4-4.7 2.3-7.7 2.3-6.1 0-11.3-3.6-13.2-8.8l-7.8 6C6.9 42.6 14.8 48 24 48z"/>
                </svg>
                Continue with Google
              </div>
            </a>""", unsafe_allow_html=True)

            st.markdown("<div style='text-align:center;color:var(--muted);margin:12px 0;font-size:.85rem;'>── or use email & password ──</div>", unsafe_allow_html=True)
            email    = st.text_input("Gmail Address", placeholder="yourname@gmail.com", key="li_email")
            password = st.text_input("Password", type="password", key="li_pw")

            if st.button("Login", use_container_width=True, type="primary"):
                if not valid_gmail(email):
                    st.markdown('<div class="alert-error">❌ Invalid Gmail address.</div>', unsafe_allow_html=True)
                else:
                    acct = load_account(email)
                    if not acct:
                        st.markdown('<div class="alert-error">❌ No account found. Please create one.</div>', unsafe_allow_html=True)
                    elif acct.get("google") and not acct.get("password"):
                        st.markdown('<div class="alert-error">❌ This account uses Google Sign-In.</div>', unsafe_allow_html=True)
                    elif acct["password"] != password:
                        st.markdown('<div class="alert-error">❌ Incorrect password.</div>', unsafe_allow_html=True)
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user      = acct
                        st.session_state.schedules = load_schedules(email)
                        st.session_state.page      = "dashboard"
                        st.rerun()

            st.markdown("---")
            st.markdown("<p style='text-align:center;color:var(--muted);font-size:.9rem;'>New user?</p>", unsafe_allow_html=True)
            if st.button("Create Account", use_container_width=True):
                st.session_state.page = "register"; st.rerun()

# ── Register page ─────────────────────────────────────────────────────────────
def register_page():
    topbar()
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            st.markdown('<div class="card-title">✨ Create Account</div>', unsafe_allow_html=True)
            name    = st.text_input("Full Name", placeholder="Your Name", key="reg_name")
            email   = st.text_input("Gmail Address", placeholder="yourname@gmail.com", key="reg_email")
            pw      = st.text_input("Set Password", type="password", key="reg_pw",
                                     help="Min 8 chars with at least 1 special character")
            pw_conf = st.text_input("Confirm Password", type="password", key="reg_pw2")

            if st.button("Create Account", use_container_width=True, type="primary"):
                errors = []
                if not name.strip():       errors.append("Name is required.")
                if not valid_gmail(email): errors.append("Invalid Gmail address.")
                if not valid_password(pw): errors.append("Password must be 8+ chars with 1 special character.")
                if pw != pw_conf:          errors.append("Passwords do not match.")
                if load_account(email):    errors.append("An account with this Gmail already exists.")
                if errors:
                    for e in errors: st.markdown(f'<div class="alert-error">❌ {e}</div>', unsafe_allow_html=True)
                else:
                    save_account({"name":name.strip(),"email":email,"password":pw,"picture":"","google":False})
                    st.markdown('<div class="alert-success">✅ Account created! You can now log in.</div>', unsafe_allow_html=True)
                    time.sleep(1); st.session_state.page = "login"; st.rerun()

            st.markdown("---")
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = "login"; st.rerun()

# ── Dashboard ─────────────────────────────────────────────────────────────────
def dashboard_page():
    check_reminders()
    st.markdown('<script>setTimeout(function(){window.location.reload();},60000);</script>',
                unsafe_allow_html=True)

    for r in st.session_state.in_app_reminders:
        st.markdown(f'<div class="reminder-toast">🔔 {r["msg"]}</div>', unsafe_allow_html=True)
    if st.session_state.in_app_reminders:
        if st.button("Dismiss Reminders"):
            st.session_state.in_app_reminders = []; st.rerun()

    user = st.session_state.user
    topbar(subtitle=f"{greeting()}, {user['name']} 👋")

    tabs = ["Dashboard","New Plans","Progress","Update Schedules","Profile"]
    cols = st.columns(len(tabs))
    for col, tab in zip(cols, tabs):
        with col:
            if st.button(tab, use_container_width=True,
                         type="primary" if st.session_state.active_tab == tab else "secondary"):
                st.session_state.active_tab = tab; st.rerun()

    st.markdown("---")
    t = st.session_state.active_tab
    if   t == "Dashboard":        tab_home()
    elif t == "New Plans":        tab_new_plans()
    elif t == "Progress":         tab_progress()
    elif t == "Update Schedules": tab_update()
    elif t == "Profile":          tab_profile()

# ── Tab: Home ─────────────────────────────────────────────────────────────────
def tab_home():
    user = st.session_state.user
    st.markdown(f'<div class="greeting-card"><h2>Hi! {greeting()}, {user["name"]} 🌿</h2>'
                f'<p>{datetime.now().strftime("%A, %d %B %Y")}</p></div>', unsafe_allow_html=True)

    if not st.session_state.schedules:
        st.markdown('<div class="card"><div class="card-title">📅 No Schedules Yet</div>'
                    '<p style="color:var(--muted);">Go to <b>New Plans</b> to generate your first study schedule!</p></div>',
                    unsafe_allow_html=True)
        return

    total = completed = missed = 0
    for sched in st.session_state.schedules:
        for day in sched.get("days",[]):
            for task in day.get("tasks",[]):
                total += 1
                if task["status"] == "Completed": completed += 1
                elif task["status"] == "Missed":  missed += 1
    pending = total - completed - missed

    st.markdown('<div class="card"><div class="card-title">📊 Overview</div>', unsafe_allow_html=True)
    for col, num, lbl, clr in zip(st.columns(4),
        [total, pending, completed, missed],
        ["Total Tasks","Pending","Completed","Missed"],
        ["#1B5E40","#F57F17","#2E7D32","#C62828"]):
        with col:
            st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:{clr};">{num}</div>'
                        f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    today_str = datetime.today().strftime("%Y-%m-%d")
    st.markdown('<div class="card"><div class="card-title">📅 Today\'s Tasks</div>', unsafe_allow_html=True)
    found = False
    pill_map = {"Pending": "pill-pending", "Completed": "pill-completed", "Missed": "pill-missed"}
    for sched in st.session_state.schedules:
        for day in sched.get("days",[]):
            if day["date"] == today_str:
                for task in day["tasks"]:
                    found = True
                    task_status = task["status"]
                    pill_cls = pill_map.get(task_status, "")
                    c1, c2, c3 = st.columns([0.1, 3, 1])
                    with c1:
                        checked = st.checkbox("", key=f"chk_{task['id']}", value=(task_status == "Completed"))
                    if checked and task_status != "Completed":
                        task["status"] = "Completed"; save_schedules(); st.rerun()
                    with c2:
                        st.markdown(
                            f'<div style="display:flex;align-items:center;">'
                            f'<span style="width:90px;color:var(--muted);font-size:.85rem;">{task["start"]}–{task["end"]}</span>'
                            f'<span style="flex:1;font-weight:500;">{task["name"]}</span></div>',
                            unsafe_allow_html=True)
                    with c3:
                        st.markdown(
                            f"<span class='task-pill {pill_cls}'>{task_status}</span>",
                            unsafe_allow_html=True)
    if not found:
        st.markdown("<p style='color:var(--muted);'>No tasks scheduled for today.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab: New Plans ────────────────────────────────────────────────────────────
def tab_new_plans():
    st.markdown('<div class="card"><div class="card-title">📅 Create New Study Plan</div>', unsafe_allow_html=True)
    st.markdown("**Plan for how many days?**")
    plan_days = st.select_slider("", options=[1,2,3,4,5,6,7], value=3, key="plan_days")

    st.markdown("---\n**⏰ Daily Available Time**")
    available = {}
    for i in range(plan_days):
        with st.expander(f"Day {i+1} — {(datetime.today()+timedelta(days=i)).strftime('%A, %d %b')}"):
            c1, c2 = st.columns(2)
            with c1: s = st.time_input("Start", value=datetime.strptime("09:00","%H:%M").time(), key=f"avail_s_{i}")
            with c2: e = st.time_input("End",   value=datetime.strptime("17:00","%H:%M").time(), key=f"avail_e_{i}")
            available[i] = {"start":s.strftime("%H:%M"),"end":e.strftime("%H:%M")}

    st.markdown("---\n**🔒 Committed Time**")
    if "committed" not in st.session_state: st.session_state.committed = []
    for idx, c in enumerate(st.session_state.committed):
        c1,c2,c3,c4,c5 = st.columns([2,1,1,1,1])
        with c1: c["event"] = st.text_input("Event", value=c["event"], key=f"ce_{idx}")
        with c2: c["day"]   = st.number_input("Day#", min_value=1, max_value=plan_days, value=max(1,c["day"]+1), key=f"cd_{idx}") - 1
        with c3: cs = st.time_input("Start", value=datetime.strptime(c["start"],"%H:%M").time(), key=f"cs_{idx}"); c["start"] = cs.strftime("%H:%M")
        with c4: ce = st.time_input("End",   value=datetime.strptime(c["end"],"%H:%M").time(),   key=f"cee_{idx}"); c["end"]   = ce.strftime("%H:%M")
        with c5:
            st.write("")
            if st.button("✕", key=f"del_c_{idx}"): st.session_state.committed.pop(idx); st.rerun()
    if st.button("＋ Add Committed Time Block"):
        st.session_state.committed.append({"event":"","day":0,"start":"12:00","end":"13:00"}); st.rerun()

    st.markdown("---\n**📚 Add Tasks**")
    if "tasks_input" not in st.session_state:
        st.session_state.tasks_input = [{"name":"","duration":60,"deadline":"","difficulty":"Medium"}]
    for idx, task in enumerate(st.session_state.tasks_input):
        c1,c2,c3,c4,c5 = st.columns([2,1,1.2,1.2,0.5])
        with c1: task["name"]       = st.text_input("Task Name",      value=task["name"],      key=f"tn_{idx}", placeholder="e.g. Maths Chapter 3")
        with c2: task["duration"]   = st.number_input("Duration (min)",value=task["duration"],  min_value=10, step=10, key=f"td_{idx}")
        with c3: task["deadline"]   = st.text_input("Deadline",        value=task["deadline"],  key=f"tdd_{idx}", placeholder="DD-MM-YYYY")
        with c4: task["difficulty"] = st.selectbox("Difficulty", ["Easy","Medium","Hard"],
                                        index=["Easy","Medium","Hard"].index(task["difficulty"]), key=f"tdf_{idx}")
        with c5:
            st.write("")
            if st.button("✕", key=f"del_t_{idx}") and len(st.session_state.tasks_input) > 1:
                st.session_state.tasks_input.pop(idx); st.rerun()
    if st.button("＋ Add Task"):
        st.session_state.tasks_input.append({"name":"","duration":60,"deadline":"","difficulty":"Medium"}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Generate Schedule", type="primary"):
        valid_tasks = [t for t in st.session_state.tasks_input if t["name"].strip()]
        if not valid_tasks: st.error("Please add at least one task.")
        else:
            with st.spinner("🧠 Building your personalized schedule..."):
                time.sleep(1)
                days = generate_schedule(plan_days, available, st.session_state.committed, valid_tasks)
            sched = {"created": datetime.now().strftime("%Y-%m-%d %H:%M"), "days": days}
            st.session_state.schedules.append(sched)
            save_schedules()
            st.success("✅ Schedule generated! Check your Dashboard.")
            st.session_state.active_tab = "Dashboard"; st.rerun()

# ── Tab: Progress ─────────────────────────────────────────────────────────────
def tab_progress():
    st.markdown('<div class="card"><div class="card-title">📈 Progress Overview</div>', unsafe_allow_html=True)
    if not st.session_state.schedules:
        st.markdown("<p style='color:var(--muted);'>No schedules yet.</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True); return

    total = completed = missed = 0
    by_day = {}; by_hour = {}
    for sched in st.session_state.schedules:
        for day in sched.get("days",[]):
            by_day[day["label"]] = {"completed":0,"total":0}
            for task in day["tasks"]:
                total += 1; by_day[day["label"]]["total"] += 1
                if task["status"] == "Completed":
                    completed += 1; by_day[day["label"]]["completed"] += 1
                    try: h=int(task["start"].split(":")[0]); by_hour[h]=by_hour.get(h,0)+1
                    except: pass
                elif task["status"] == "Missed": missed += 1

    rate = round(completed/total*100,1) if total else 0
    for col, val, lbl, clr in zip(st.columns(3),
        [f"{rate}%", completed, missed],
        ["Completion Rate","Completed","Missed"],
        ["var(--green)","#2E7D32","#C62828"]):
        with col:
            st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:{clr};">{val}</div>'
                        f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if by_day:
        st.markdown('<div class="card"><div class="card-title">📊 Completion Rate by Day</div>', unsafe_allow_html=True)
        st.bar_chart({"Completion %":[round(v["completed"]/v["total"]*100,1) if v["total"] else 0 for v in by_day.values()]},
                     use_container_width=True, color="#1B5E40")
        st.markdown('</div>', unsafe_allow_html=True)

    if by_hour:
        st.markdown('<div class="card"><div class="card-title">⏰ Most Productive Hours</div>', unsafe_allow_html=True)
        st.bar_chart({"Completions":[c for _,c in sorted(by_hour.items())]}, use_container_width=True, color="#4CAF82")
        st.markdown('</div>', unsafe_allow_html=True)

    pill_map = {"Pending": "pill-pending", "Completed": "pill-completed", "Missed": "pill-missed"}
    st.markdown('<div class="card"><div class="card-title">📋 All Tasks</div>', unsafe_allow_html=True)
    for sched in st.session_state.schedules:
        for day in sched.get("days",[]):
            st.markdown(f"**{day['label']}**")
            for task in day["tasks"]:
                task_status = task["status"]
                pill_cls = pill_map.get(task_status, "")
                c1, c2, c3 = st.columns([3,1,1])
                with c1:
                    st.markdown(
                        f"{task['start']} \u2013 {task['end']}  **{task['name']}** "
                        f"<span class='task-pill {pill_cls}'>{task_status}</span>",
                        unsafe_allow_html=True)
                with c2:
                    if task_status != "Completed":
                        if st.button("✅ Done", key=f"done_{task['id']}"):
                            task["status"]="Completed"; save_schedules(); st.rerun()
                with c3:
                    if task_status == "Pending":
                        if st.button("❌ Missed", key=f"miss_{task['id']}"):
                            task["status"]="Missed"; save_schedules(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab: Update ───────────────────────────────────────────────────────────────
def tab_update():
    st.markdown('<div class="card"><div class="card-title">✏️ Update Schedules</div>', unsafe_allow_html=True)
    if not st.session_state.schedules:
        st.markdown("<p style='color:var(--muted);'>No schedules to update yet.</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True); return
    for si, sched in enumerate(st.session_state.schedules):
        st.markdown(f"**Schedule created:** {sched['created']}")
        for di, day in enumerate(sched.get("days",[])):
            with st.expander(f"📅 {day['label']}"):
                for ti, task in enumerate(day["tasks"]):
                    c1,c2,c3,c4,c5 = st.columns([2,1,1,1,1])
                    with c1: task["name"]       = st.text_input("Name",  value=task["name"],  key=f"u_n_{si}{di}{ti}")
                    with c2: task["start"]      = st.text_input("Start", value=task["start"], key=f"u_s_{si}{di}{ti}")
                    with c3: task["end"]        = st.text_input("End",   value=task["end"],   key=f"u_e_{si}{di}{ti}")
                    with c4: task["difficulty"] = st.selectbox("Diff",["Easy","Medium","Hard"],
                                                    index=["Easy","Medium","Hard"].index(task.get("difficulty","Medium")),
                                                    key=f"u_d_{si}{di}{ti}")
                    with c5:
                        st.write("")
                        if st.button("🗑️", key=f"del_t_{si}{di}{ti}"):
                            day["tasks"].pop(ti); save_schedules(); st.rerun()
        if st.button(f"🗑️ Delete This Schedule", key=f"del_sched_{si}"):
            st.session_state.schedules.pop(si); save_schedules(); st.rerun()
        st.markdown("---")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tab: Profile ──────────────────────────────────────────────────────────────
def tab_profile():
    user = st.session_state.user
    if user.get("picture"):
        st.markdown(f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">'
                    f'<img src="{user["picture"]}" style="width:72px;height:72px;border-radius:50%;border:3px solid var(--green);"/>'
                    f'<div><div style="font-family:DM Serif Display;font-size:1.3rem;color:var(--green);">{user["name"]}</div>'
                    f'<div style="color:var(--muted);font-size:.9rem;">{user["email"]}</div></div></div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">👤 Edit Profile</div>', unsafe_allow_html=True)
    new_name = st.text_input("Name", value=user["name"], key="prof_name")
    if user.get("google"):
        st.markdown(f'<p style="color:var(--muted);font-size:.9rem;">📧 Signed in with Google: <b>{user["email"]}</b></p>',
                    unsafe_allow_html=True)
        new_email = user["email"]
    else:
        new_email = st.text_input("Edit Gmail", value=user["email"], key="prof_email")

    st.markdown("---")
    if st.session_state.get("google_access_token"):
        st.markdown('<div class="alert-success">🔔 Email reminders are <b>active</b>.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-error" style="background:#FFF8E1;border-left-color:#F9A825;color:#5D4037;">'
                    '⚠️ Email reminders inactive. Sign in with Google to enable.</div>', unsafe_allow_html=True)

    if st.button("💾 Save Changes", type="primary"):
        errs = []
        if not new_name.strip(): errs.append("Name cannot be empty.")
        if not user.get("google") and not valid_gmail(new_email): errs.append("Invalid Gmail.")
        if errs:
            for e in errs: st.markdown(f'<div class="alert-error">❌ {e}</div>', unsafe_allow_html=True)
        else:
            user["name"] = new_name.strip(); user["email"] = new_email
            save_account(user); save_schedules()
            st.markdown('<div class="alert-success">✅ Profile saved!</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🚪 Logout"):
        for k in ["logged_in","user","google_access_token","schedules","page"]:
            st.session_state[k] = False if k=="logged_in" else None if k in ["user"] else "" if k in ["google_access_token","page"] else []
        st.session_state.page = "login"; st.rerun()

# ── Router ────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.page == "register": register_page()
    else: login_page()
else:
    dashboard_page()
