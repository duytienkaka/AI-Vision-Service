from typing import Annotated

from fastapi import Header, HTTPException, status


def require_bearer_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is missing",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is invalid",
        )

    return token
