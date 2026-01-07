from datetime import datetime, timedelta, timezone

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from api.dependencies import (
    ALGORITHM,
    SECRET_KEY,
    get_current_user,
    get_db,
    pwd_context,
)
from api.users import is_admin
from app.config import get_settings
from app.limiter import limiter
from models.login import LoginModel
from models.users import User

settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["Auth"])
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def login_user(request: Request, user: LoginModel, db=Depends(get_db)):
    """Login a user"""
    user_collection = db["users"]
    found_user = await user_collection.find_one({"username": user.username})

    if found_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    elif not pwd_context.verify(
        user.password if user.password else "", found_user["password"]
    ):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Convert found_user to User model and remove its password from the response
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "token": access_token,
        "token_type": "bearer",
        "isAdmin": "admin" in found_user.get("roles", []),
        "username": found_user.get("username", ""),
    }


@router.get("/check-admin", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def check_admin(request: Request, current_user: User = Depends(get_current_user)):
    """Check if the current user is an admin"""
    if is_admin(current_user):
        return {"isAdmin": True}
    else:
        return {"isAdmin": False}


@router.get("/login/google")
async def login_google(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    redirect_uri = request.url_for("auth_google")

    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google")
async def auth_google(request: Request, db=Depends(get_db)):
    try:
        if "error" in request.query_params:
            raise HTTPException(
                status_code=400, detail=request.query_params.get("error")
            )
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"OAuth failure: {str(e)}"
        ) from None

    user_info = token.get("userinfo")
    if not user_info:
        user_info = await oauth.google.userinfo(token=token)

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    user_collection = db["users"]
    user = await user_collection.find_one({"email": email})

    if not user:
        from uuid import uuid4

        base_username = email.split("@")[0]
        new_username = base_username
        while await user_collection.find_one({"username": new_username}):
            new_username = f"{base_username}_{uuid4().hex[:4]}"

        new_user = User(
            username=new_username,
            email=email,
            auth_provider="google",
            roles=["user"],
        )
        await user_collection.insert_one(
            new_user.model_dump(by_alias=True, exclude={"id"})
        )
        user = await user_collection.find_one({"email": email})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    is_admin = "admin" in user.get("roles", [])
    target_url = f"http://localhost:5173/sso-callback?token={access_token}&username={user['username']}&isAdmin={is_admin}"
    return RedirectResponse(target_url)
