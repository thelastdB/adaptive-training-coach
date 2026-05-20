from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    athlete_name: str
    athlete_profile_pic: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
