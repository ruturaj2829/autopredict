# Frontend-Backend Connection Troubleshooting

## Problem: Still connecting to localhost:8080

### Step 1: Verify Environment Variable in Vercel

1. Go to Vercel Dashboard → Your Project → **Settings** → **Environment Variables**
2. Check that `NEXT_PUBLIC_BACKEND_URL` exists
3. Verify the value is your Railway URL (e.g., `https://your-backend.up.railway.app`)
4. Make sure it's set for **all environments** (Production, Preview, Development)

### Step 2: REDEPLOY Frontend (CRITICAL!)

**Important**: Next.js embeds `NEXT_PUBLIC_*` variables at **build time**, not runtime!

1. Go to **Deployments** tab in Vercel
2. Click the **⋯** (three dots) on your latest deployment
3. Click **"Redeploy"**
4. Wait for the build to complete (watch the build logs)
5. The new deployment will have the correct backend URL

### Step 3: Verify After Redeploy

1. Open your Vercel site
2. Open browser console (F12)
3. You should see:
   ```
   🔗 Backend URL: https://your-backend.up.railway.app
   🔍 Environment variable: https://your-backend.up.railway.app
   ```
4. If you still see `localhost:8080`, the variable wasn't set correctly

### Step 4: Check Railway Backend

Make sure your Railway backend is accessible:

```bash
curl https://your-backend.up.railway.app/
```

Should return: `{"status": "ok", ...}`

---

## Quick Test

After redeploying, open browser console and check:
- If you see `🔗 Backend URL: http://localhost:8080` → Variable not set or not redeployed
- If you see `🔗 Backend URL: https://your-backend.up.railway.app` → ✅ Working!

---

## Still Not Working?

### Option 1: Hardcode Temporarily (for demo)

Edit `frontend/app/page.tsx` and replace:
```typescript
const BACKEND_URL = "https://your-backend.up.railway.app";
```

Then commit and push:
```bash
git add frontend/app/page.tsx
git commit -m "Hardcode backend URL for demo"
git push origin main
```

Vercel will auto-deploy.

### Option 2: Check CORS

Make sure Railway backend has CORS configured:
- Railway → Service → Variables
- `FRONTEND_URL` should be your Vercel URL (e.g., `https://autopredict.vercel.app`)

