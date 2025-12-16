# Deployment URLs Reference

## Production URLs

### Backend (Railway)
- **URL**: `https://autopredict-production.up.railway.app`
- **Health Check**: `https://autopredict-production.up.railway.app/`
- **API Docs**: `https://autopredict-production.up.railway.app/docs`
- **Health Endpoint**: `https://autopredict-production.up.railway.app/health`

### Frontend (Vercel)
- **URL**: `https://autopredict.vercel.app`
- **Production**: `https://autopredict.vercel.app`

---

## Environment Variables

### Vercel Frontend
- `NEXT_PUBLIC_BACKEND_URL` = `https://autopredict-production.up.railway.app`

### Railway Backend
- `FRONTEND_URL` = `https://autopredict.vercel.app` (optional, for CORS)

---

## Quick Test Commands

### Test Backend Health
```bash
curl https://autopredict-production.up.railway.app/
```

### Test Backend API
```bash
curl -X POST https://autopredict-production.up.railway.app/api/v1/telemetry/risk \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TEST","rf_features":{},"lstm_sequence":[]}'
```

### Test Frontend → Backend
1. Open: `https://autopredict.vercel.app`
2. Open browser console (F12)
3. Click "Run live call" on any feature
4. Should connect to: `https://autopredict-production.up.railway.app`

---

## Status Check

✅ Backend deployed: `https://autopredict-production.up.railway.app`
✅ Frontend deployed: `https://autopredict.vercel.app`
✅ CORS configured: Backend allows all origins
✅ Environment variables: Should be set in Vercel

---

## Troubleshooting

If frontend still shows `localhost:8080`:
1. Check Vercel → Settings → Environment Variables
2. Verify `NEXT_PUBLIC_BACKEND_URL` = `https://autopredict-production.up.railway.app`
3. Redeploy frontend (Deployments → Redeploy)

If CORS errors persist:
1. Check Railway deployment logs
2. Verify backend is running: `curl https://autopredict-production.up.railway.app/`
3. Check browser console for exact error

