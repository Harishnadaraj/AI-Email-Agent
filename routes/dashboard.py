from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("app/templates/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()