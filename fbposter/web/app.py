"""
FastAPI Web Dashboard for Facebook Auto-Poster
"""
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ..utils.config import get_config, set_profile, get_current_profile, list_profiles, get_profile_dir, get_profiles_dir
from ..utils.telegram import get_notifier
from ..data.storage import DataStore, LogStore
from ..data.models import Group, Text, Job
import shutil
import json
import subprocess
import threading

# Create FastAPI app
app = FastAPI(
    title="Facebook Auto-Poster Dashboard",
    description="Web interface for managing Facebook auto-posting",
    version="1.0.0"
)

# Add session middleware for authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("DASHBOARD_SECRET_KEY", "change-this-secret-key-in-production")
)

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Authentication
def get_dashboard_password() -> str:
    """Get dashboard password from environment"""
    return os.getenv("DASHBOARD_PASSWORD", "admin")


def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated"""
    return request.session.get("authenticated", False)


def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    return True


# Helper to get stores
def get_stores(profile: Optional[str] = None):
    """Get data and log stores for current/specified profile"""
    if profile:
        set_profile(profile)
    return DataStore(), LogStore()


def has_chrome_session(profile: Optional[str] = None) -> bool:
    """Check if profile has a Chrome session (logged into Facebook)"""
    if profile:
        chrome_dir = get_profile_dir(profile) / "chrome-profile"
    else:
        # Default profile uses root chrome-profile
        from pathlib import Path
        package_dir = Path(__file__).parent.parent.parent
        chrome_dir = package_dir / "chrome-profile"

    # Check if chrome profile exists and has data
    if not chrome_dir.exists():
        return False

    # Check for Default directory with actual login data
    default_dir = chrome_dir / "Default"
    if not default_dir.exists():
        return False

    # Check for Cookies file - indicates browser was actually used
    cookies_file = default_dir / "Cookies"
    if not cookies_file.exists():
        return False

    # Check cookies file has reasonable size (>10KB suggests actual login)
    try:
        if cookies_file.stat().st_size < 10000:
            return False
    except:
        return False

    return True


def get_session_profile(request: Request) -> Optional[str]:
    """Get the current profile from session"""
    return request.session.get("current_profile")


def set_session_profile(request: Request, profile: Optional[str]):
    """Set the current profile in session"""
    if profile:
        request.session["current_profile"] = profile
    elif "current_profile" in request.session:
        del request.session["current_profile"]


# ============== Auth Routes ==============

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """Login page"""
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Handle login"""
    if password == get_dashboard_password():
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=302)
    return RedirectResponse(url="/login?error=Invalid+password", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    """Handle logout"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# ============== Dashboard Routes ==============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, profile: Optional[str] = None):
    """Main dashboard"""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    # Handle profile switching - store in session
    if profile is not None:  # Explicitly passed (even empty string means "default")
        if profile == "":
            set_session_profile(request, None)
            set_profile(None)
        else:
            set_session_profile(request, profile)
            set_profile(profile)
    else:
        # Use profile from session
        session_profile = get_session_profile(request)
        if session_profile:
            set_profile(session_profile)

    current_profile = get_session_profile(request)
    data_store, log_store = get_stores()

    groups = data_store.load_groups()
    texts = data_store.load_texts()
    jobs = data_store.load_jobs()
    stats = log_store.get_success_rate(days=7)

    # Group cities
    cities = {}
    for g in groups:
        if g.city not in cities:
            cities[g.city] = {"total": 0, "active": 0}
        cities[g.city]["total"] += 1
        if g.active:
            cities[g.city]["active"] += 1

    return templates.TemplateResponse("index.html", {
        "request": request,
        "profile": current_profile,
        "profiles": list_profiles(),
        "has_session": has_chrome_session(current_profile),
        "stats": {
            "total_groups": len(groups),
            "active_groups": len([g for g in groups if g.active]),
            "texts": len(texts),
            "jobs": len(jobs),
            "enabled_jobs": len([j for j in jobs if j.enabled]),
            "posts_7d": stats["total"],
            "success_rate": stats["success_rate"]
        },
        "cities": cities,
        "recent_jobs": jobs[:5]
    })


# ============== Groups Routes ==============

@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, city: Optional[str] = None, _=Depends(require_auth)):
    """Groups management page"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()
    groups = data_store.load_groups()

    if city:
        groups = [g for g in groups if g.city == city]

    # Get all cities for filter
    all_groups = data_store.load_groups()
    cities = sorted(set(g.city for g in all_groups))

    return templates.TemplateResponse("groups.html", {
        "request": request,
        "profile": session_profile,
        "profiles": list_profiles(),
        "groups": groups,
        "cities": cities,
        "selected_city": city
    })


@app.post("/groups/add")
async def add_group(
    request: Request,
    city: str = Form(...),
    url: str = Form(...),
    name: str = Form(""),
    _=Depends(require_auth)
):
    """Add a new group"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()

    group = Group(city=city, url=url, name=name)
    data_store.add_group(group)

    return RedirectResponse(url="/groups", status_code=302)


@app.post("/groups/{group_id}/toggle")
async def toggle_group(request: Request, group_id: str, _=Depends(require_auth)):
    """Toggle group active status"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()

    groups = data_store.load_groups()
    for g in groups:
        if g.id == group_id or g.id.startswith(group_id):
            g.active = not g.active
            break

    data_store.save_groups(groups)
    return RedirectResponse(url="/groups", status_code=302)


@app.post("/groups/{group_id}/delete")
async def delete_group(request: Request, group_id: str, _=Depends(require_auth)):
    """Delete a group"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()
    data_store.remove_group(group_id)
    return RedirectResponse(url="/groups", status_code=302)


# ============== Texts Routes ==============

@app.get("/texts", response_class=HTMLResponse)
async def texts_page(request: Request, _=Depends(require_auth)):
    """Text templates management page"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()
    texts = data_store.load_texts()

    return templates.TemplateResponse("texts.html", {
        "request": request,
        "profile": session_profile,
        "profiles": list_profiles(),
        "texts": texts
    })


@app.post("/texts/add")
async def add_text(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
    image_url: str = Form(""),
    _=Depends(require_auth)
):
    """Add a new text template"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()

    text = Text(name=name, content=content, image_url=image_url)
    data_store.add_text(text)

    return RedirectResponse(url="/texts", status_code=302)


@app.post("/texts/{text_id}/delete")
async def delete_text(request: Request, text_id: str, _=Depends(require_auth)):
    """Delete a text template"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()
    data_store.remove_text(text_id)
    return RedirectResponse(url="/texts", status_code=302)


# ============== Jobs Routes ==============

@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, _=Depends(require_auth)):
    """Jobs management page"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()
    jobs = data_store.load_jobs()
    texts = data_store.load_texts()
    groups = data_store.load_groups()

    # Get cities
    cities = sorted(set(g.city for g in groups))

    # Enrich jobs with text names and cities list
    text_map = {t.id: t.name for t in texts}
    for job in jobs:
        job.text_name = text_map.get(job.text_id, "Unknown")
        job.cities = job.group_filters.get("cities", []) if job.group_filters else []

    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "profile": session_profile,
        "profiles": list_profiles(),
        "has_session": has_chrome_session(session_profile),
        "jobs": jobs,
        "texts": texts,
        "cities": cities
    })


@app.post("/jobs/add")
async def add_job(
    request: Request,
    name: str = Form(...),
    text_id: str = Form(...),
    cities: str = Form(""),
    _=Depends(require_auth)
):
    """Add a new job"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()

    # Parse cities (comma-separated or empty for all)
    city_list = [c.strip() for c in cities.split(",") if c.strip()] if cities else []

    # Build group_filters dict
    group_filters = {"cities": city_list} if city_list else {}

    job = Job(name=name, text_id=text_id, group_filters=group_filters, schedule="manual")
    data_store.add_job(job)

    return RedirectResponse(url="/jobs", status_code=302)


@app.post("/jobs/{job_id}/toggle")
async def toggle_job(request: Request, job_id: str, _=Depends(require_auth)):
    """Toggle job enabled status"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()

    job = data_store.get_job(job_id)
    if job:
        job.enabled = not job.enabled
        data_store.update_job(job)

    return RedirectResponse(url="/jobs", status_code=302)


@app.post("/jobs/{job_id}/delete")
async def delete_job(request: Request, job_id: str, _=Depends(require_auth)):
    """Delete a job"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, _ = get_stores()
    data_store.remove_job(job_id)
    return RedirectResponse(url="/jobs", status_code=302)


@app.post("/jobs/{job_id}/run")
async def run_job(request: Request, job_id: str, _=Depends(require_auth)):
    """Run a job in background"""
    # Get profile from session
    current_profile = get_session_profile(request)
    has_session = has_chrome_session(current_profile)

    # Build the command
    cmd = ["fbposter"]
    if current_profile:
        cmd.extend(["--profile", current_profile])
    cmd.extend(["run", job_id])

    # If no Chrome session, run with visible browser for login
    if not has_session:
        cmd.append("--no-headless")

    try:
        # Run the job in background (non-blocking)
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent process
        )

        if has_session:
            return RedirectResponse(url="/jobs?success=Job+started+in+background.+Check+Logs+for+progress.", status_code=302)
        else:
            return RedirectResponse(url="/jobs?success=Job+started.+Browser+opened+for+login.+Complete+login+to+continue.", status_code=302)

    except Exception as e:
        return RedirectResponse(url=f"/jobs?error=Failed+to+start+job:+{str(e)[:50]}", status_code=302)


# ============== Logs Routes ==============

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, limit: int = 50, _=Depends(require_auth)):
    """Logs viewing page"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    _, log_store = get_stores()
    logs = log_store.get_recent_logs(limit=limit)

    return templates.TemplateResponse("logs.html", {
        "request": request,
        "profile": session_profile,
        "profiles": list_profiles(),
        "logs": logs,
        "limit": limit
    })


# ============== API Routes ==============

@app.get("/api/status")
async def api_status(request: Request, _=Depends(require_auth)):
    """API endpoint for status"""
    # Apply session profile
    session_profile = get_session_profile(request)
    if session_profile:
        set_profile(session_profile)
    else:
        set_profile(None)

    data_store, log_store = get_stores()

    groups = data_store.load_groups()
    texts = data_store.load_texts()
    jobs = data_store.load_jobs()
    stats = log_store.get_success_rate(days=7)

    return {
        "profile": session_profile,
        "groups": {
            "total": len(groups),
            "active": len([g for g in groups if g.active])
        },
        "texts": len(texts),
        "jobs": {
            "total": len(jobs),
            "enabled": len([j for j in jobs if j.enabled])
        },
        "stats_7d": stats
    }


# ============== Profiles Routes ==============

@app.get("/profiles", response_class=HTMLResponse)
async def profiles_page(request: Request, _=Depends(require_auth)):
    """Profiles management page"""
    session_profile = get_session_profile(request)
    profile_names = list_profiles()
    profiles_data = []

    for name in profile_names:
        profile_dir = get_profile_dir(name)
        groups_file = profile_dir / "groups.json"
        texts_file = profile_dir / "texts.json"
        jobs_file = profile_dir / "jobs.json"

        profiles_data.append({
            "name": name,
            "groups": _count_json_items(groups_file),
            "texts": _count_json_items(texts_file),
            "jobs": _count_json_items(jobs_file),
            "has_chrome": has_chrome_session(name)
        })

    return templates.TemplateResponse("profiles.html", {
        "request": request,
        "profile": session_profile,
        "profiles": list_profiles(),
        "profiles_data": profiles_data
    })


@app.post("/profiles/create")
async def create_profile(
    request: Request,
    name: str = Form(...),
    _=Depends(require_auth)
):
    """Create a new profile"""
    # Sanitize name
    name = name.strip().lower().replace(" ", "-")

    profile_dir = get_profile_dir(name)

    if profile_dir.exists():
        return RedirectResponse(url="/profiles?error=Profile+already+exists", status_code=302)

    # Create profile directory structure
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "logs").mkdir(exist_ok=True)

    # Create empty data files
    for filename in ["groups.json", "texts.json", "jobs.json"]:
        with open(profile_dir / filename, 'w') as f:
            json.dump([], f)

    return RedirectResponse(url="/profiles?success=Profile+created", status_code=302)


@app.post("/profiles/{profile_name}/delete")
async def delete_profile(request: Request, profile_name: str, _=Depends(require_auth)):
    """Delete a profile"""
    profile_dir = get_profile_dir(profile_name)

    if not profile_dir.exists():
        return RedirectResponse(url="/profiles?error=Profile+not+found", status_code=302)

    shutil.rmtree(profile_dir)
    return RedirectResponse(url="/profiles?success=Profile+deleted", status_code=302)


def _count_json_items(file_path) -> int:
    """Count items in a JSON array file"""
    if not file_path.exists():
        return 0
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except:
        return 0


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
