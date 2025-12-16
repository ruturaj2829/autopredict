# Railway 502 Bad Gateway - Troubleshooting Guide

## Problem
Backend returns `502 Bad Gateway` - "Application failed to respond"

This means the Railway backend application is **not running** or **crashed on startup**.

## Immediate Actions

### 1. Check Railway Deployment Status
1. Go to Railway dashboard
2. Select your backend service
3. Go to **Deployments** tab
4. Check the **latest deployment**:
   - ✅ **Success** = Deployment completed but app might have crashed
   - ❌ **Failed** = Build/deployment failed
   - ⏳ **Building** = Still deploying

### 2. Check Railway Logs (CRITICAL)
1. Railway dashboard → Your service → **Logs** tab
2. Look for:
   - **Startup errors** (Python import errors, syntax errors)
   - **"Application failed to respond"** messages
   - **Port binding errors**
   - **Missing dependencies**

### 3. Common Issues & Fixes

#### Issue: App Crashes on Startup
**Symptoms**: Logs show Python errors, import errors, or tracebacks

**Fix**: Check logs for specific error and fix the code

#### Issue: Port Not Binding
**Symptoms**: App starts but Railway can't connect

**Fix**: Ensure `PORT` environment variable is used correctly:
```python
# In start.sh or main.py
PORT = os.getenv("PORT", "8000")
uvicorn.run(app, host="0.0.0.0", port=int(PORT))
```

#### Issue: Health Check Failing
**Symptoms**: Railway health check times out

**Fix**: Ensure `/` endpoint works and responds quickly

#### Issue: Import Errors
**Symptoms**: `ModuleNotFoundError` in logs

**Fix**: Check `requirements.txt` includes all dependencies

### 4. Quick Test Commands

#### Test if backend is accessible:
```bash
curl https://autopredict-production.up.railway.app/
```

#### Test OPTIONS (preflight):
```bash
curl -X OPTIONS https://autopredict-production.up.railway.app/api/v1/telemetry/risk -v
```

#### Test POST:
```bash
curl -X POST https://autopredict-production.up.railway.app/api/v1/telemetry/risk \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TEST","rf_features":{},"lstm_sequence":[]}'
```

## What to Check in Railway Logs

Look for these patterns:

### ✅ Good Signs:
- "FastAPI application startup complete"
- "App is ready to accept requests"
- "CORS enabled for all origins"
- "Uvicorn running on 0.0.0.0:PORT"

### ❌ Bad Signs:
- "ModuleNotFoundError"
- "SyntaxError"
- "ImportError"
- "Address already in use"
- "Application failed to respond"
- No startup messages at all

## Next Steps

1. **Check Railway logs** and share the error message
2. **Verify deployment completed** successfully
3. **Check if service is running** (not paused/stopped)
4. **Try manual redeploy** if needed

## If Logs Show Nothing

1. Railway dashboard → Service → **Settings**
2. Check **Service Status** (should be "Active")
3. Check **Resource Limits** (might be out of memory)
4. Try **Restart Service** button

---

**Share the Railway logs output** and I can help fix the specific issue!

