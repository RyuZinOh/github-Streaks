from datetime import datetime
from io import BytesIO
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import requests
import os
import json
import svgwrite
from base64 import b64encode
from typing import List, Dict
from dotenv import load_dotenv
from theme import get_theme

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GitHub Token missing in environment variables!")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
CROWN_SVG_PATH = "assets/crown.svg"
CROWN_AVAILABLE = os.path.exists(CROWN_SVG_PATH)

with open("allowed.json", "r") as file:
    allowed_usernames = [username.lower() for username in json.load(file)]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_github_data(username: str) -> List[Dict]:
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(
        GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": {"username": username}},
        headers=headers,
        timeout=10
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="GitHub fetch failed")
    json_data = response.json()
    if "errors" in json_data:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    days = []
    for week in json_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": datetime.strptime(day["date"], "%Y-%m-%d"),
                "contributions_count": day["contributionCount"]
            })
    return days



##git streak calculation logic
class StreakCalculator:
    @staticmethod
    def calculate_streaks(contributions: List[Dict]) -> Dict:
        if not contributions:
            return {"max_streak": 0, "ongoing_streak": 0, "total_contributions": 0, "last_contribution_date": None}
        contributions.sort(key=lambda x: x["date"])
        max_streak = current_streak = total = 0
        last_date = None
        previous_day = None
        today = datetime.now().date()
        for day in contributions:
            date = day["date"].date()
            count = day["contributions_count"]
            total += count
            if count > 0:
                last_date = date
            if previous_day is not None:
                diff = (date - previous_day).days
                if diff == 1 and count > 0:
                    current_streak += 1
                elif count > 0:
                    current_streak = 1
                elif date != today:
                    current_streak = 0
            elif count > 0:
                current_streak = 1
            max_streak = max(max_streak, current_streak)
            previous_day = date
        ongoing_streak = 0
        if last_date and (today - last_date).days <= 1:
            ongoing_streak = current_streak
        return {
            "max_streak": max_streak,
            "ongoing_streak": ongoing_streak,
            "total_contributions": total,
            "last_contribution_date": last_date
        }


## trying to reducing caching for updated result
def svg_response(dwg: svgwrite.Drawing) -> StreamingResponse:
    svg_output = BytesIO(dwg.tostring().encode("utf-8"))
    response = StreamingResponse(svg_output, media_type="image/svg+xml")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/")
def home():
    return {"message": "GitHub Streak API is running!"}

@app.get("/streak/{username}")
def get_github_streak(username: str):
    contributions = fetch_github_data(username)
    streak = StreakCalculator.calculate_streaks(contributions)
    return {
        "username": username,
        "max_streak": streak["max_streak"],
        "ongoing_streak": streak["ongoing_streak"],
        "total_contributions": streak["total_contributions"],
        "last_contribution_date": streak["last_contribution_date"].isoformat() if streak["last_contribution_date"] else None
    }

@app.get("/streak/{username}/image")
def get_streak_image(username: str, theme: str = "goldenshade"):
    selected_theme = get_theme(theme.lower())
    if username.lower() not in allowed_usernames:
        return generate_access_denied_svg(selected_theme)
    try:
        contributions = fetch_github_data(username)
        streak_data = StreakCalculator.calculate_streaks(contributions)
        return generate_streak_svg(username, streak_data, selected_theme)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_streak_svg(username: str, streak: Dict, theme) -> StreamingResponse:
    dwg = svgwrite.Drawing(size=("550px", "300px"), viewBox="0 0 550 300")
    dwg.add(dwg.rect((0, 0), (550, 300), fill=theme.background_color, rx=30, ry=30))
    try:
        avatar_url = f"https://github.com/{username}.png"
        avatar_res = requests.get(avatar_url, timeout=5)
        if avatar_res.status_code == 200:
            data_url = f"data:image/png;base64,{b64encode(avatar_res.content).decode()}"
            clip_path = dwg.defs.add(dwg.clipPath(id="avatarClip"))
            clip_path.add(dwg.circle(center=(45, 40), r=30))
            dwg.add(dwg.image(data_url, insert=(15, 10), size=(60, 60), clip_path="url(#avatarClip)"))
    except:
        pass
    dwg.add(dwg.text(f"@{username}", insert=(90, 55), font_size="24px", font_weight="bold", fill=theme.text_color, style="font-family: 'Poppins', sans-serif;"))
    dwg.add(dwg.text(datetime.now().strftime("%B %d, %Y"), insert=(30, 125), font_size="40px", font_weight="bold", fill=theme.text_color, style="font-family: 'Poppins', sans-serif;"))
    dwg.add(dwg.text(f"Total Contributions: {streak['total_contributions']}", insert=(30, 195), font_size="20px", fill=theme.text_color, style="font-family: 'Poppins', sans-serif;"))
    dwg.add(dwg.text(f"Ongoing Streak: {streak['ongoing_streak']} days", insert=(30, 225), font_size="20px", fill=theme.text_color, style="font-family: 'Poppins', sans-serif;"))
    center = (480, 125)
    dwg.add(dwg.circle(center=center, r=60, fill=theme.circle_fill_color))
    dwg.add(dwg.text(str(streak["max_streak"]), insert=(center[0] - 25, center[1] + 5), font_size="45px", font_weight="bold", fill=theme.circle_text_color, style="font-family: 'Poppins', sans-serif;"))
    dwg.add(dwg.text("DAYS", insert=(center[0] - 23, center[1] + 25), font_size="18px", font_weight="bold", fill=theme.circle_text_color, style="font-family: 'Poppins', sans-serif;"))
    if CROWN_AVAILABLE:
        try:
            with open(CROWN_SVG_PATH, "r", encoding="utf-8") as f:
                crown_svg = f.read().replace('fill="currentColor"', f'fill="{theme.crown_theme_color}"')
                encoded = b64encode(crown_svg.encode()).decode()
                dwg.add(dwg.image(href=f"data:image/svg+xml;base64,{encoded}", insert=(center[0] - 33, center[1] - 122), size=(69, 69)))
        except:
            pass
    return svg_response(dwg)

def generate_access_denied_svg(theme) -> StreamingResponse:
    dwg = svgwrite.Drawing(size=("550px", "300px"), viewBox="0 0 550 300")
    dwg.add(dwg.rect((0, 0), (550, 300), fill="#1e1e1e", rx=30, ry=30))
    text = dwg.text("", insert=(30, 120), font_size="22px", fill="white", font_weight="bold", style="font-family: 'Poppins', sans-serif;")
    text.add(dwg.tspan("Access Denied", x=[30], dy=[30]))
    text.add(dwg.tspan("You are not authorized!", x=[30], dy=[30]))
    dwg.add(text)
    dwg.add(dwg.rect((0, 0), (550, 300), fill="none", stroke="#FF5555", stroke_width=5, rx=30, ry=30))
    return svg_response(dwg)
