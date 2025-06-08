from fastapi import FastAPI, Request, Form, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
SITE_URL = os.getenv("SITE_URL")  # e.g., "https://yourdomain.com"

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login", response_class=HTMLResponse)
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if result.user:
            token = result.session.access_token
            response.set_cookie(key="access_token", value=token, httponly=True, samesite="Lax")
            return HTMLResponse(
                "<p>Login successful! <a href='/dashboard'>Go to Dashboard</a></p>"
            )
        else:
            return HTMLResponse("<p>Login failed. Please check your credentials.</p>", status_code=401)
    except Exception as e:
        return HTMLResponse(f"<p>Error: {str(e)}</p>", status_code=500)

@app.get("/magic", response_class=HTMLResponse)
def magic_login_page(request: Request):
    return templates.TemplateResponse("magic_login.html", {"request": request})

@app.post("/api/magic-login", response_class=HTMLResponse)
def send_magic_link(email: str = Form(...)):
    try:
        result = supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "email_redirect_to": f"{SITE_URL}/token-handler"  # トークン受け取り用URL
            }
        })
        return HTMLResponse(f"<p>Magic link sent to {email}. Please check your inbox.</p>")
    except Exception as e:
        return HTMLResponse(f"<p>Failed to send magic link: {str(e)}</p>", status_code=500)
    
@app.get("/token-handler", response_class=HTMLResponse)
def token_handler(request: Request):
    html = """
    <script>
      const fragment = window.location.hash.substring(1);
      const params = new URLSearchParams(fragment);
      const accessToken = params.get("access_token");

      if (accessToken) {
        document.cookie = `access_token=${accessToken}; path=/`;
        window.location.href = "/dashboard";  // or Streamlit endpoint
      } else {
        document.body.innerHTML = "<p>Token missing. Please try again.</p>";
      }
    </script>
    """
    return HTMLResponse(content=html)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return HTMLResponse("<h2>✅ You are logged in! Welcome to Dashboard.</h2>")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    html = """
    <h2>🎉 Welcome to your Dashboard</h2>
    <p>You are logged in!</p>
    <p><a href='/logout'>Logout</a></p>
    """
    return HTMLResponse(content=html)

@app.get("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return RedirectResponse(url="/login", status_code=302)
