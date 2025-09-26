from fastapi import APIRouter, Depends, HTTPException, status, Request
router = APIRouter(prefix="/api/auth", tags=["auth"])
@router.get("/me")
def me():
    return {"message": f"Hello"}