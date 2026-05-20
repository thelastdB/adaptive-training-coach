# Session 5: Integration + Deployment

## Tasks (do in order)
1. End-to-end auth flow: Strava OAuth → JWT → protected routes
2. Error states: API down, Strava disconnected, no plan generated yet
3. Loading states: skeleton cards in WeekGrid during fetch
4. railway.toml + Procfile for FastAPI deployment
5. vercel.json with /app/* rewrite to index.html
6. Environment variable documentation in README

## Environment variables needed
Backend: SUPABASE_URL, SUPABASE_KEY, STRAVA_CLIENT_ID,
         STRAVA_CLIENT_SECRET, JWT_SECRET, CORS_ORIGINS
Frontend: VITE_API_URL