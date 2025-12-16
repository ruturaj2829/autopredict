# Railway Backend Setup - Step by Step

## Finding Service Settings (Not Project Settings)

### Step 1: Navigate to Your Service
1. In Railway dashboard, click on your **project name** (e.g., "prolific-gratitude")
2. You should see a list of **services** (e.g., "backend", "api", etc.)
3. **Click on your backend service** (the one running FastAPI)

### Step 2: Add Environment Variable
Once you're in the **Service** view (not Project view):

1. Look for tabs at the top: **"Deployments"**, **"Metrics"**, **"Variables"**, **"Settings"**, etc.
2. Click on **"Variables"** tab
3. Click **"+ New Variable"** or **"Add Variable"**
4. Add:
   - **Name**: `FRONTEND_URL`
   - **Value**: Your Vercel URL (e.g., `https://autopredict.vercel.app`)
5. Click **Save**

### Step 3: Redeploy (if needed)
- Railway will auto-redeploy when you add variables
- Or go to **Deployments** → Click **"Redeploy"**

---

## Alternative: If You Don't See Variables Tab

### Option A: Use Service Settings
1. In your **Service** view (not Project)
2. Click **"Settings"** tab
3. Scroll down to **"Environment Variables"** section
4. Add `FRONTEND_URL` there

### Option B: Use Railway CLI
```bash
railway variables set FRONTEND_URL=https://autopredict.vercel.app
```

### Option C: Update Code Directly
If you can't find the Variables section, we can hardcode it temporarily:

1. Edit `backend/app.py`
2. Find the CORS section (around line 33)
3. Replace with:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://autopredict.vercel.app",  # Add your Vercel URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then commit and push:
```bash
git add backend/app.py
git commit -m "Add Vercel URL to CORS"
git push origin main
```

---

## Quick Visual Guide

**Railway Dashboard Structure:**
```
Railway Dashboard
├── Projects (what you're seeing now)
│   └── prolific-gratitude (Project Settings)
│       └── Services
│           └── [Your Backend Service] ← GO HERE
│               ├── Deployments
│               ├── Variables ← ADD VARIABLE HERE
│               ├── Settings
│               └── Logs
```

**You need to:**
1. Click on your **Service** (not Project)
2. Then go to **Variables** tab

