# Railway Port Configuration Fix

## Issue
App starts on port 8080 but Railway might be checking a different port, causing 502 errors.

## Solution

### Step 1: Verify Railway HTTP Proxy Port
1. Go to Railway dashboard → Your backend service
2. Go to **Settings** → **Networking** (or **HTTP Proxy**)
3. Check **Application Port** setting:
   - Should be: **8080** (matches what your app is using)
   - If it's set to 8000 or something else, change it to **8080**

### Step 2: Verify PORT Environment Variable
1. Railway dashboard → Service → **Variables**
2. Check if `PORT` is set:
   - If set, it should be **8080**
   - If not set, Railway will use the HTTP Proxy port setting

### Step 3: Ensure App Uses PORT Correctly
The `start.sh` script already uses `$PORT` correctly:
```bash
PORT=${PORT:-8000}  # Defaults to 8000 if PORT not set
uvicorn --port "$PORT"
```

But Railway is setting PORT=8080, so the app runs on 8080, which is correct.

## Current Status
- ✅ App starts successfully on port 8080
- ✅ App responds to GET / (200 OK)
- ❌ App shuts down after one request (likely Railway health check issue)

## Next Steps

1. **Check Railway HTTP Proxy Port**:
   - Settings → Networking → Application Port
   - Should be **8080**

2. **Check Railway Health Check**:
   - Settings → Health Check
   - Path: `/`
   - Should succeed (we saw 200 OK in logs)

3. **Check if Service is Paused**:
   - Railway might be pausing the service if health checks fail
   - Check service status in Railway dashboard

4. **Check Railway Logs for Errors**:
   - Look for any errors after the "200 OK" response
   - Check if Railway is killing the container

## Quick Fix
If Railway HTTP Proxy is set to 8000 but app runs on 8080:
1. Change Railway HTTP Proxy Application Port to **8080**
2. Or set `PORT=8080` in Railway environment variables
3. Redeploy

