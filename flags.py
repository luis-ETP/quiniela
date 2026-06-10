# Emoji flags por equipo
FLAGS = {
    "Spain": "🇪🇸", "France": "🇫🇷", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Argentina": "🇦🇷", "Portugal": "🇵🇹", "Brazil": "🇧🇷",
    "Netherlands": "🇳🇱", "Germany": "🇩🇪", "Belgium": "🇧🇪",
    "Morocco": "🇲🇦", "Colombia": "🇨🇴", "Uruguay": "🇺🇾",
    "Croatia": "🇭🇷", "Japan": "🇯🇵", "United States": "🇺🇸",
    "Norway": "🇳🇴", "Switzerland": "🇨🇭", "Mexico": "🇲🇽",
    "Senegal": "🇸🇳", "Ecuador": "🇪🇨", "Türkiye": "🇹🇷",
    "Austria": "🇦🇹", "Canada": "🇨🇦", "Egypt": "🇪🇬",
    "Sweden": "🇸🇪", "South Korea": "🇰🇷", "Paraguay": "🇵🇾",
    "Iran": "🇮🇷", "Côte d'Ivoire": "🇨🇮", "Czechia": "🇨🇿",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Australia": "🇦🇺", "Algeria": "🇩🇿",
    "Bosnia and Herzegovina": "🇧🇦", "Tunisia": "🇹🇳", "Panama": "🇵🇦",
    "Ghana": "🇬🇭", "South Africa": "🇿🇦", "DR Congo": "🇨🇩",
    "Iraq": "🇮🇶", "Uzbekistan": "🇺🇿", "Qatar": "🇶🇦",
    "Saudi Arabia": "🇸🇦", "Jordan": "🇯🇴", "New Zealand": "🇳🇿",
    "Cape Verde": "🇨🇻", "Haiti": "🇭🇹", "Curaçao": "🇨🇼",
}

# football-data.org team name → our name
API_NAME_MAP = {
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "Czechia": "Czechia",
    "Czech Republic": "Czechia",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "Ivory Coast": "Côte d'Ivoire",
    "Côte d'Ivoire": "Côte d'Ivoire",
    "Turkey": "Türkiye",
    "Türkiye": "Türkiye",
    "Iran": "Iran",
    "IR Iran": "Iran",
    "USA": "United States",
    "United States": "United States",
    "Curaçao": "Curaçao",
    "Curacao": "Curaçao",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Scotland": "Scotland",
    "England": "England",
    "Cape Verde": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Saudi Arabia": "Saudi Arabia",
    "New Zealand": "New Zealand",
}

def normalize(name):
    """Convert API team name to our internal name."""
    if not name:
        return name
    return API_NAME_MAP.get(name, name)

def flag(name):
    return FLAGS.get(name, "🏳️")
