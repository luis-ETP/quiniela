# ISO 3166-1 alpha-2 codes for flagcdn.com
FLAG_CODES = {
    "Spain": "es", "France": "fr", "England": "gb-eng",
    "Argentina": "ar", "Portugal": "pt", "Brazil": "br",
    "Netherlands": "nl", "Germany": "de", "Belgium": "be",
    "Morocco": "ma", "Colombia": "co", "Uruguay": "uy",
    "Croatia": "hr", "Japan": "jp", "United States": "us",
    "Norway": "no", "Switzerland": "ch", "Mexico": "mx",
    "Senegal": "sn", "Ecuador": "ec", "Türkiye": "tr",
    "Austria": "at", "Canada": "ca", "Egypt": "eg",
    "Sweden": "se", "South Korea": "kr", "Paraguay": "py",
    "Iran": "ir", "Côte d'Ivoire": "ci", "Czechia": "cz",
    "Scotland": "gb-sct", "Australia": "au", "Algeria": "dz",
    "Bosnia and Herzegovina": "ba", "Tunisia": "tn", "Panama": "pa",
    "Ghana": "gh", "South Africa": "za", "DR Congo": "cd",
    "Iraq": "iq", "Uzbekistan": "uz", "Qatar": "qa",
    "Saudi Arabia": "sa", "Jordan": "jo", "New Zealand": "nz",
    "Cape Verde": "cv", "Haiti": "ht", "Curaçao": "cw",
}

API_NAME_MAP = {
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "Czech Republic": "Czechia",
    "Ivory Coast": "Côte d'Ivoire",
    "Turkey": "Türkiye",
    "IR Iran": "Iran",
    "USA": "United States",
    "Curacao": "Curaçao",
    "Congo DR": "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Cabo Verde": "Cape Verde",
}

def normalize(name):
    if not name:
        return name
    return API_NAME_MAP.get(name, name)

def flag_url(name):
    code = FLAG_CODES.get(name, "")
    if not code:
        return ""
    return f"https://flagcdn.com/24x18/{code}.png"

def flag_img(name):
    url = flag_url(name)
    if not url:
        return ""
    return f'<img src="{url}" width="24" height="18" style="vertical-align:middle;margin-right:4px" alt="{name}">'
