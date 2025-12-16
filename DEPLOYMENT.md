# Deployment Guide - Railway (Backend) + Vercel (Frontend)

## ✅ Step 1: Get Your Deployment URLs

### Backend (Railway)
1. Go to your Railway dashboard
2. Select your backend service
3. Go to **Settings** → **Networking**
4. Copy your **Public Domain** (e.g., `https://autopredict-backend.up.railway.app`)

### Frontend (Vercel)
1. Go to your Vercel dashboard
2. Select your project
3. Copy your **Production URL** (e.g., `https://autopredict.vercel.app`)

---

## ✅ Step 2: Update Backend CORS (Railway)

Your backend needs to allow requests from your Vercel frontend.

### Option A: Update via Railway Environment Variables (Recommended)

1. In Railway dashboard → Your backend service → **Variables**
2. Add a new variable:
   - **Name**: `FRONTEND_URL`
   - **Value**: Your Vercel URL (e.g., `https://autopredict.vercel.app`)
3. Redeploy the backend

### Option B: Update Code Directly

Edit `backend/app.py` and update the CORS origins:

```python
# Get frontend URL from environment or use default
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://your-frontend.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        FRONTEND_URL,  # Add your Vercel URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then commit and push:
```bash
git add backend/app.py
git commit -m "Add Vercel frontend to CORS origins"
git push origin main
```

---

## ✅ Step 3: Configure Frontend Environment Variable (Vercel)

1. Go to Vercel dashboard → Your project → **Settings** → **Environment Variables**
2. Add a new variable:
   - **Name**: `NEXT_PUBLIC_BACKEND_URL`
   - **Value**: Your Railway backend URL (e.g., `https://autopredict-backend.up.railway.app`)
   - **Environment**: Production, Preview, Development (select all)
3. Click **Save**
4. **Redeploy** your frontend:
   - Go to **Deployments**
   - Click the **⋯** menu on the latest deployment
   - Select **Redeploy**

---

## ✅ Step 4: Test the Connection

### Test Backend Directly
```bash
curl https://your-backend.up.railway.app/
# Should return: {"status": "ok", "service": "AutoPredict Backend", ...}
```

### Test Frontend → Backend
1. Open your Vercel frontend URL
2. Click **"Run live call"** on any feature section
3. Check the browser console (F12) for any CORS errors
4. If you see errors, verify:
   - `NEXT_PUBLIC_BACKEND_URL` is set correctly in Vercel
   - Backend CORS includes your Vercel URL
   - Backend is running and healthy

---

## ✅ Step 5: Verify Everything Works

### Backend Health Check
- ✅ `GET https://your-backend.up.railway.app/` → Returns 200 OK
- ✅ `GET https://your-backend.up.railway.app/health` → Shows health status
- ✅ `GET https://your-backend.up.railway.app/docs` → FastAPI docs load

### Frontend → Backend Integration
- ✅ Frontend loads without errors
- ✅ "Run live call" buttons work
- ✅ API responses appear in the UI
- ✅ No CORS errors in browser console

---

## 🔧 Troubleshooting

### CORS Errors
**Error**: `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Fix**:
1. Verify `FRONTEND_URL` in Railway matches your Vercel URL exactly
2. Check backend logs in Railway to see if requests are arriving
3. Ensure backend CORS middleware includes your Vercel domain

### Backend Not Responding
**Error**: `Failed to fetch` or `Network error`

**Fix**:
1. Check Railway deployment logs for errors
2. Verify backend is healthy: `curl https://your-backend.up.railway.app/`
3. Check Railway service status (not paused/stopped)

### Environment Variable Not Working
**Error**: Frontend still uses `localhost:8080`

**Fix**:
1. In Vercel, verify `NEXT_PUBLIC_BACKEND_URL` is set
2. **Redeploy** the frontend (environment variables require redeploy)
3. Check browser console for the actual URL being used

### 503 Service Unavailable
**Error**: Backend returns 503 when calling inference endpoints

**Fix**:
- This is expected if model artifacts aren't deployed
- The app will start but inference endpoints will return 503
- For demo, you can skip inference endpoints or deploy artifacts

---

## 📝 Quick Reference

### Railway Backend
- **Dashboard**: https://railway.app
- **Service Settings**: Service → Settings
- **Environment Variables**: Settings → Variables
- **Logs**: Service → Deployments → Latest → Logs

### Vercel Frontend
- **Dashboard**: https://vercel.com
- **Environment Variables**: Project → Settings → Environment Variables
- **Deployments**: Project → Deployments
- **Redeploy**: Deployments → ⋯ → Redeploy

---

## 🎯 Next Steps

1. ✅ Backend deployed on Railway
2. ✅ Frontend deployed on Vercel
3. ✅ CORS configured
4. ✅ Environment variables set
5. ✅ Test the integration
6. 🎉 **You're ready to demo!**

For the hackathon demo, you can:
- Show the frontend UI
- Demonstrate live API calls
- Explain the architecture
- Highlight the innovations (Hybrid ML, LangGraph, UEBA, etc.)

