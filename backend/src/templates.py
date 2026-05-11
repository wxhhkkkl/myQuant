from fastapi.templating import Jinja2Templates
from backend.src.config import BASE_DIR, ENV

templates_dir = BASE_DIR / "src" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["MYQUANT_ENV"] = ENV
