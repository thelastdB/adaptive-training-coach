import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import jwt

from server.deps import ALGORITHM, JWT_SECRET, get_current_user
from server.models.auth import TokenResponse, UserProfile

router = APIRouter()

STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
# The backend's own public URL — Strava redirects here after consent
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

STRAVA_SCOPE = "activity:read_all"
JWT_TTL_DAYS = 30


def _issue_jwt(user_id: str) -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(days=JWT_TTL_DAYS)
    return jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=ALGORITHM)


@router.get("/strava")
def strava_login():
    """Redirect the user to Strava's OAuth consent screen."""
    redirect_uri = f"{BACKEND_URL}/api/v1/auth/strava/callback"
    params = {
        "client_id":      STRAVA_CLIENT_ID,
        "redirect_uri":   redirect_uri,
        "response_type":  "code",
        "scope":          STRAVA_SCOPE,
        "approval_prompt": "force",
    }
    url = "https://www.strava.com/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/strava/callback")
def strava_callback(code: str | None = None, error: str | None = None):
    """
    Strava redirects here after OAuth consent.
    Exchanges the code for tokens, upserts the user in Supabase, issues a JWT,
    then redirects the frontend to /auth/callback?token=<jwt>.
    """
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=access_denied")

    # Exchange code for Strava tokens
    try:
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id":     STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "code":          code,
                "grant_type":    "authorization_code",
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Strava token exchange failed: {exc}")

    athlete = token_data.get("athlete", {})
    athlete_id = athlete.get("id")
    if not athlete_id:
        raise HTTPException(status_code=502, detail="Strava response missing athlete id")

    athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    athlete_pic = athlete.get("profile") or athlete.get("profile_medium")

    # Upsert user record in Supabase
    from db_supabase import upsert_user
    user_id = upsert_user(
        strava_athlete_id=int(athlete_id),
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_expires_at=int(token_data["expires_at"]),
        athlete_name=athlete_name,
        athlete_profile_pic=athlete_pic or "",
    )

    token = _issue_jwt(user_id)
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={token}")


@router.get("/me", response_model=UserProfile)
def get_me(user_id: str = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    from db_supabase import get_user_by_strava_id
    user = get_user_by_strava_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(
        user_id=user_id,
        athlete_name=user.get("athlete_name") or "",
        athlete_profile_pic=user.get("athlete_profile_pic"),
    )


@router.post("/logout")
def logout():
    """JWT is stateless — client should discard the token."""
    return {"status": "ok"}
