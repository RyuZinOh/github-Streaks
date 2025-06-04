class Theme:
    def __init__(self, name, background_color, text_color, progress_bar_color, circle_fill_color, circle_text_color, crown_theme_color):
        self.name = name
        self.background_color = background_color
        self.text_color = text_color
        self.progress_bar_color = progress_bar_color
        self.circle_fill_color = circle_fill_color
        self.circle_text_color = circle_text_color
        self.crown_theme_color = crown_theme_color 

# Define some themes
themes = {
    "midnight": Theme(
        name="midnight",
        background_color="#1e1e1e",
        text_color="#ffffff",
        progress_bar_color="#5e17eb",
        circle_fill_color="#5e17eb",
        circle_text_color="#000000",
        crown_theme_color="#5e17eb" 
    ),
    "goldenshade": Theme(
        name="goldenshade",
        background_color="#FFF5CC",
        text_color="#1F1A17",
        progress_bar_color="#FFD700",
        circle_fill_color="#FFC107",
        circle_text_color="#1F1A17",
        crown_theme_color="#000000" 
    ),
    "ocean_breeze": Theme(
    name="ocean_breeze",
    background_color="#0a192f",
    text_color="#e6f1ff",
    progress_bar_color="#00b4d8",
    circle_fill_color="#48cae4",
    circle_text_color="#0a192f",
    crown_theme_color="#90e0ef"
),
"forest_canopy": Theme(
    name="forest_canopy",
    background_color="#1a2e1f",
    text_color="#e8f4ea",
    progress_bar_color="#4c956c",
    circle_fill_color="#7bb662",
    circle_text_color="#1a2e1f",
    crown_theme_color="#d8f3dc"
),"sunset_glow": Theme(
    name="sunset_glow",
    background_color="#2b2d42",
    text_color="#f8f7f9",
    progress_bar_color="#ef233c",
    circle_fill_color="#ff7b00",
    circle_text_color="#2b2d42",
    crown_theme_color="#ff9e00"
),"lavender_mist": Theme(
    name="lavender_mist",
    background_color="#3a3042",
    text_color="#f9f5ff",
    progress_bar_color="#9673b7",
    circle_fill_color="#d4b2d8",
    circle_text_color="#3a3042",
    crown_theme_color="#e9d4ff"
),"monochrome": Theme(
    name="monochrome",
    background_color="#121212",
    text_color="#ffffff",
    progress_bar_color="#555555",
    circle_fill_color="#dddddd",
    circle_text_color="#121212",
    crown_theme_color="#ffffff"
),
}

def get_theme(theme_name: str):
    return themes.get(theme_name, themes["midnight"])