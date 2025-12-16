# CORS Testing Guide

## Current Status
- Backend URL: `https://autopredict-production.up.railway.app`
- Frontend URL: `https://autopredict.vercel.app`
- CORS: Configured with middleware override

## Test Backend CORS Manually

### Test 1: Check if backend responds to OPTIONS
```bash
curl -X OPTIONS https://autopredict-production.up.railway.app/api/v1/telemetry/risk \
  -H "Origin: https://autopredict.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

**Expected Response:**
- Status: 200 OK
- Headers should include:
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Methods: ...`
  - `Access-Control-Allow-Headers: ...`

### Test 2: Check if backend responds to POST
```bash
curl -X POST https://autopredict-production.up.railway.app/api/v1/telemetry/risk \
  -H "Origin: https://autopredict.vercel.app" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TEST","rf_features":{},"lstm_sequence":[]}' \
  -v
```

**Expected Response:**
- Status: 200 or 422 (depending on payload)
- Headers should include `Access-Control-Allow-Origin: *`

## If CORS Still Fails

### Check Railway Deployment
1. Go to Railway dashboard
2. Check if latest deployment completed successfully
3. Check deployment logs for any errors
4. Verify the deployment includes the latest CORS fixes

### Check Railway Logs
Look for:
- "CORS enabled for all origins"
- "CORS allowed origins: ..."
- Any CORS-related errors

### Manual Fix (If Needed)
If Railway hasn't redeployed, you can manually trigger:
1. Railway dashboard → Service → Deployments
2. Click "Redeploy" on latest deployment
3. Or make a small code change to trigger auto-deploy

## Debugging Steps

1. **Check if backend is running:**
   ```bash
   curl https://autopredict-production.up.railway.app/
   ```
   Should return: `{"status": "ok", ...}`

2. **Check CORS headers in browser:**
   - Open browser DevTools (F12)
   - Go to Network tab
   - Try the API call
   - Check the OPTIONS request (preflight)
   - Look at Response Headers
   - Should see `Access-Control-Allow-Origin: *`

3. **Check Railway logs:**
   - Railway dashboard → Service → Logs
   - Look for startup messages
   - Check for CORS configuration logs

## Expected Behavior After Fix

✅ OPTIONS request returns 200 with CORS headers
✅ POST request returns data with CORS headers
✅ Browser console shows no CORS errors
✅ Frontend can successfully call backend APIs

