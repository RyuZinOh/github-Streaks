from datetime import datetime
from io import BytesIO
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
import svgwrite
from fastapi.responses import StreamingResponse
from base64 import b64encode
import json
from theme import get_theme
from typing import List, Dict, Optional

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
CROWN_SVG_PATH = "assets/crown.svg"

# Load allowed usernames
with open("allowed.json", "r") as file:
    allowed_usernames = [username.lower() for username in json.load(file)]

class StreakCalculator:
    @staticmethod
    def calculate_streaks(contributions: List[Dict]) -> Dict:
        if not contributions:
            return {
                "max_streak": 0,
                "ongoing_streak": 0,
                "total_contributions": 0,
                "last_contribution_date": None
            }

        contributions.sort(key=lambda x: x["date"])
        
        max_streak = 0
        current_streak = 0
        previous_day = None
        total_contributions = 0
        last_contribution_date = None
        
        now = datetime.now()
        today = now.date()
        
        for day in contributions:
            date = day["date"].date()
            count = day["contributions_count"]
            total_contributions += count
            
            if count > 0:
                last_contribution_date = date
            
            if previous_day is not None:
                day_diff = (date - previous_day).days
                
                if day_diff == 1 and count > 0:
                    current_streak += 1
                elif count > 0:
                    current_streak = 1
                elif date != today:
                    current_streak = 0
            elif count > 0:
                current_streak = 1
            
            if current_streak > max_streak:
                max_streak = current_streak
            
            previous_day = date
        
        ongoing_streak = current_streak
        if last_contribution_date != today:
            ongoing_streak = 0
        
        return {
            "max_streak": max_streak,
            "ongoing_streak": ongoing_streak,
            "total_contributions": total_contributions,
            "last_contribution_date": last_contribution_date
        }

def fetch_github_data(username: str) -> Dict:
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="GitHub Token is missing!")
    
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
    
    variables = {"username": username}
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(
        GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Error fetching data from GitHub"
        )
    
    return response.json()

@app.get("/")
def home():
    return {"message": "GitHub Streak API is running!"}

@app.get("/streak/{username}")
def get_github_streak(username: str):
    try:
        data = fetch_github_data(username)
        
        if "errors" in data:
            raise HTTPException(status_code=404, detail="GitHub user not found")
        
        weeks_data = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        contributions = []
        
        for week in weeks_data:
            for day in week["contributionDays"]:
                day_date = datetime.strptime(day["date"], "%Y-%m-%d")
                contributions.append({
                    "date": day_date,
                    "contributions_count": day["contributionCount"]
                })
        
        streak_data = StreakCalculator.calculate_streaks(contributions)
        
        return {
            "username": username,
            "max_streak": streak_data["max_streak"],
            "ongoing_streak": streak_data["ongoing_streak"],
            "total_contributions": streak_data["total_contributions"],
            "last_contribution_date": streak_data["last_contribution_date"].isoformat() if streak_data["last_contribution_date"] else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/streak/{username}/image")
def get_streak_image(
    username: str, 
    theme: str = "goldenshade"
):
    selected_theme = get_theme(theme.lower())

    # Check if user is allowed
    if username.lower() not in allowed_usernames:
        return generate_access_denied_svg(selected_theme)
    
    try:
        streak_data = get_github_streak(username)
        return generate_streak_svg(username, streak_data, selected_theme)
    except HTTPException as e:
        if e.status_code == 404:
            return generate_user_not_found_svg(username, selected_theme)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating streak image: {str(e)}")

def generate_access_denied_svg(theme) -> StreamingResponse:
    dwg = svgwrite.Drawing(size=("550px", "300px"), viewBox="0 0 550 300")
    dwg.add(dwg.rect(insert=(0, 0), size=(550, 300), fill="#1e1e1e", rx=30, ry=30))
    
    
    
    access_denied_message = [
        "Access Denied", 
        "You are not authorized!",
    ]
    
    text = dwg.text(
        "",
        insert=(30, 120),
        font_size="22px",
        fill="white",
        font_weight="bold",
        style="font-family: 'Poppins', sans-serif;"
    )
    
    line_height = 30
    for i, line in enumerate(access_denied_message):
        text.add(dwg.tspan(line, x=[30], dy=[line_height if i > 0 else 0]))
    
    dwg.add(text)
    dwg.add(dwg.rect(
        insert=(0, 0), 
        size=(550, 300), 
        fill="none", 
        stroke="#FF5555", 
        stroke_width=5, 
        rx=30, 
        ry=30
    ))
    
    svg_output = BytesIO(dwg.tostring().encode('utf-8'))
    return StreamingResponse(svg_output, media_type="image/svg+xml")

def generate_user_not_found_svg(username: str, theme) -> StreamingResponse:
    dwg = svgwrite.Drawing(size=("550px", "300px"), viewBox="0 0 550 300")
    dwg.add(dwg.rect(insert=(0, 0), size=(550, 300), fill=theme.background_color, rx=30, ry=30))
    
    message = [
        f"User @{username} not found",
        "Please check the username and try again"
    ]
    
    text = dwg.text(
        "",
        insert=(30, 120),
        font_size="22px",
        fill=theme.text_color,
        font_weight="bold",
        style="font-family: 'Poppins', sans-serif;"
    )
    
    line_height = 30
    for i, line in enumerate(message):
        text.add(dwg.tspan(line, x=[30], dy=[line_height if i > 0 else 0]))
    
    dwg.add(text)
    
    svg_output = BytesIO(dwg.tostring().encode('utf-8'))
    return StreamingResponse(svg_output, media_type="image/svg+xml")

def generate_streak_svg(
    username: str,
    streak_data: Dict,
    theme
) -> StreamingResponse:
    max_streak = streak_data["max_streak"]
    ongoing_streak = streak_data["ongoing_streak"]
    total_contributions = streak_data["total_contributions"]
    
    dwg = svgwrite.Drawing(size=("550px", "300px"), viewBox="0 0 550 300")
    dwg.add(dwg.rect(insert=(0, 0), size=(550, 300), fill=theme.background_color, rx=30, ry=30))
    
    try:
        avatar_url = f"https://github.com/{username}.png"
        response = requests.get(avatar_url, timeout=5)
        if response.status_code == 200:
            avatar_data_url = f"data:image/png;base64,{b64encode(response.content).decode('utf-8')}"
            clip_path = dwg.defs.add(dwg.clipPath(id="avatarClip"))
            clip_path.add(dwg.circle(center=(45, 40), r=30))
            dwg.add(dwg.image(
                avatar_data_url, 
                insert=(15, 10), 
                size=(60, 60), 
                clip_path="url(#avatarClip)"
            ))
    except Exception:
        pass
    
    dwg.add(dwg.text(
        f"@{username}", 
        insert=(90, 55), 
        font_size="24px", 
        font_weight="bold", 
        fill=theme.text_color, 
        style="font-family: 'Poppins', sans-serif;"
    ))
    
    today = datetime.now()
    month_name = today.strftime("%B")
    localized_date = f"{month_name} {today.day}, {today.year}"
    dwg.add(dwg.text(
        localized_date, 
        insert=(30, 125), 
        font_size="40px", 
        font_weight="bold", 
        fill=theme.text_color, 
        style="font-family: 'Poppins', sans-serif;"
    ))
    
    dwg.add(dwg.text(
        f"Total Contributions: {total_contributions}", 
        insert=(30, 195), 
        font_size="20px", 
        fill=theme.text_color, 
        style="font-family: 'Poppins', sans-serif;"
    ))
    
    dwg.add(dwg.text(
        f"Ongoing Streak: {ongoing_streak} days", 
        insert=(30, 225), 
        font_size="20px", 
        fill=theme.text_color, 
        style="font-family: 'Poppins', sans-serif;"
    ))
    
    circle_center = (480, 125)
    circle_radius = 60
    dwg.add(dwg.circle(
        center=circle_center, 
        r=circle_radius, 
        fill=theme.circle_fill_color
    ))
    
    dwg.add(dwg.text(
        str(max_streak), 
        insert=(circle_center[0] - 25, circle_center[1] + 5), 
        font_size="45px", 
        font_weight="bold", 
        fill=theme.circle_text_color, 
        style="font-family: 'Poppins', sans-serif;"
    ))
    
    dwg.add(dwg.text(
        "DAYS", 
        insert=(circle_center[0] - 23, circle_center[1] + 25), 
        font_size="18px", 
        font_weight="bold", 
        fill=theme.circle_text_color, 
        style="font-family: 'Poppins', sans-serif;"
    ))
    
    if os.path.exists(CROWN_SVG_PATH):
        try:
            with open(CROWN_SVG_PATH, "r", encoding='utf-8') as crown_file:
                crown_svg = crown_file.read()
                crown_svg = crown_svg.replace(
                    'fill="currentColor"', 
                    f'fill="{theme.crown_theme_color}"'
                )
                dwg.add(dwg.image(
                    href=f"data:image/svg+xml;base64,{b64encode(crown_svg.encode('utf-8')).decode('utf-8')}", 
                    insert=(circle_center[0] - 33, circle_center[1] - 122), 
                    size=(69, 69)
                ))
        except Exception:
            pass
    
    svg_output = BytesIO(dwg.tostring().encode('utf-8'))
    return StreamingResponse(svg_output, media_type="image/svg+xml")