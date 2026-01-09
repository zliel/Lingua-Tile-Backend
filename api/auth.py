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
from models.auth import ForgotPasswordRequest, ResetPasswordRequest
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


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db=Depends(get_db)
):
    """
    Initiate password reset process.
    Note: For MVP, this logs the link to console instead of sending email.
    """
    user_collection = db["users"]
    user = await user_collection.find_one({"email": body.email})

    if not user:
        return {
            "message": "If an account with that email exists, a reset link has been sent."
        }

    from uuid import uuid4

    token = uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    await user_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"reset_token": token, "reset_token_expires": expires}},
    )

    # Send Reset Email (if configured)
    if settings.RESEND_API_KEY:
        import resend

        resend.api_key = settings.RESEND_API_KEY

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        params = {
            "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
            "to": [body.email],
            "subject": "Reset Your LinguaTile Password",
            "html": f"<p>Click the link below to reset your password:</p><p><a href='{reset_link}'>{reset_link}</a></p>",
        }

        try:
            resend.Emails.send(params)
        except Exception as e:
            print(f"Error sending email: {e}")
            # Fallback to console in case of API error during testing
            print(
                f"\n[MOCK EMAIL (Fallback)] Password Reset Link for {body.email}: {reset_link}\n"
            )

    else:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        # print(f"\n[MOCK EMAIL] Password Reset Link for {body.email}: {reset_link}\n")

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def reset_password(
    request: Request, body: ResetPasswordRequest, db=Depends(get_db)
):
    """Reset password using a valid token"""
    user_collection = db["users"]

    # Find user with matching token and valid expiration
    user = await user_collection.find_one(
        {
            "reset_token": body.token,
            "reset_token_expires": {"$gt": datetime.now(timezone.utc)},
        }
    )

    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid or expired password reset token"
        )

    # Update password and clear token
    new_password_hash = pwd_context.hash(body.new_password)

    await user_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password": new_password_hash},
            "$unset": {"reset_token": "", "reset_token_expires": ""},
        },
    )

    return {"message": "Password reset successfully"}
