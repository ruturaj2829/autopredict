# Vercel Frontend Setup - Fix Connection Error

## Problem
Frontend is trying to connect to `localhost:8080` instead of your Railway backend.

## Solution: Set Environment Variable in Vercel

### Step-by-Step:

1. **Go to Vercel Dashboard**
   - Open https://vercel.com
   - Sign in and select your project

2. **Navigate to Environment Variables**
   - Click on your project
   - Go to **Settings** (top navigation)
   - Click **Environment Variables** (left sidebar)

3. **Add the Variable**
   - Click **"Add New"** or **"+ Add"** button
   - **Key**: `NEXT_PUBLIC_BACKEND_URL`
   - **Value**: Your Railway backend URL
     - Example: `https://autopredict-backend.up.railway.app`
     - Get this from Railway → Service → Settings → Networking → Public Domain
   - **Environment**: Select ALL (Production, Preview, Development)
   - Click **Save**

4. **Redeploy Frontend** (CRITICAL!)
   - Go to **Deployments** tab
   - Find your latest deployment
   - Click the **⋯** (three dots) menu
   - Select **"Redeploy"**
   - Wait for deployment to complete

5. **Test**
   - Open your Vercel frontend URL
   - Open browser console (F12)
   - Click "Run live call"
   - Should now connect to Railway backend instead of localhost

---

## Quick Check: Verify Variable is Set

After redeploying, you can verify:
1. Open your Vercel site
2. Open browser console (F12)
3. Type: `console.log(process.env.NEXT_PUBLIC_BACKEND_URL)`
4. Should show your Railway URL (not undefined)

---

## If Still Not Working

### Option 1: Check Railway Backend URL
Make sure your Railway backend is accessible:
```bash
curl https://your-backend.up.railway.app/
```
Should return: `{"status": "ok", ...}`

### Option 2: Hardcode Temporarily (for testing)
If environment variables aren't working, we can hardcode it in the frontend code temporarily.

### Option 3: Check CORS
Make sure Railway backend has CORS configured for your Vercel domain.

