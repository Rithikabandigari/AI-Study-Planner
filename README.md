# 📚 AI Study Planner — Setup Guide

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔐 Google Sign-In Setup (One-time, ~5 minutes)

### Step 1 — Create a Google Cloud Project
1. Go to → https://console.cloud.google.com/
2. Click **New Project** → name it `AI Study Planner` → **Create**

### Step 2 — Enable Gmail API
1. Go to **APIs & Services → Library**
2. Search **Gmail API** → click → **Enable**

### Step 3 — OAuth Consent Screen
1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → **Create**
3. App name: `AI Study Planner`, fill in your email
4. On the **Scopes** step add: `openid`, `email`, `profile`, `https://mail.google.com/`
5. On **Test users** step → add your Gmail

### Step 4 — Create OAuth Credentials
1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. Type: **Web application**
4. Authorized redirect URIs → add: `http://localhost:8501`
5. Click **Create** → copy **Client ID** and **Client Secret**

### Step 5 — Add to app
Open `data/oauth_config.json` and fill in:
```json
{
  "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
  "client_secret": "YOUR_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8501"
}
```

### Step 6 — Run!
```bash
streamlit run app.py
```
Click **Continue with Google** → sign in → done! ✅

---

## 🔔 Email Reminders
- Sign in with Google = reminders work automatically
- App sends email from YOUR Gmail to YOUR Gmail, 15 min before each task
- Also shows in-app toast notifications
- Zero app passwords needed!
