# ── Usuarios ──────────────────────────────────────────────────────────────────
USERS = {
    "messi10":      {"password": "Copa#737",    "nombre": "Messi10"},
    "ronaldo7":     {"password": "Gol#291",     "nombre": "Ronaldo7"},
    "mbappe9":      {"password": "Draft#445",   "nombre": "Mbappe9"},
    "neymar11":     {"password": "Bombo#183",   "nombre": "Neymar11"},
    "haaland9":     {"password": "Mundial#562", "nombre": "Haaland9"},
    "vinicius7":    {"password": "Crack#819",   "nombre": "Vinicius7"},
    "bellingham8":  {"password": "Copa#374",    "nombre": "Bellingham8"},
    "pedri6":       {"password": "Gol#156",     "nombre": "Pedri6"},
    "salah11":      {"password": "Draft#923",   "nombre": "Salah11"},
    "ochoa":        {"password": "Bombo#647",   "nombre": "Ochoa"},
    "modric10":     {"password": "Mundial#381", "nombre": "Modric10"},
    "debruyne17":   {"password": "Crack#294",   "nombre": "DeBruyne17"},
    "admin":        {"password": "Admin#2026!", "nombre": "Admin", "is_admin": True},
}

# ── Equipos ───────────────────────────────────────────────────────────────────
def get_bombo(r):
    if r <= 12: return "A"
    if r <= 24: return "B"
    if r <= 36: return "C"
    return "D"

PTS = {"A":(1.0,0.5),"B":(1.5,0.75),"C":(2.0,1.0),"D":(3.0,1.5)}

_teams_raw = [
    (1,"Spain","H",2),(2,"France","I",3),(3,"England","L",4),
    (4,"Argentina","J",1),(5,"Portugal","K",5),(6,"Brazil","C",6),
    (7,"Netherlands","F",8),(8,"Germany","E",10),(9,"Belgium","G",9),
    (10,"Morocco","C",7),(11,"Colombia","K",13),(12,"Uruguay","H",17),
    (13,"Croatia","L",11),(14,"Japan","F",18),(15,"United States","D",16),
    (16,"Norway","I",31),(17,"Switzerland","B",19),(18,"Mexico","A",14),
    (19,"Senegal","I",15),(20,"Ecuador","E",24),(21,"Türkiye","D",22),
    (22,"Austria","J",23),(23,"Canada","B",30),(24,"Egypt","G",29),
    (25,"Sweden","F",38),(26,"South Korea","A",25),(27,"Paraguay","D",40),
    (28,"Iran","G",20),(29,"Côte d'Ivoire","E",33),(30,"Czechia","A",39),
    (31,"Scotland","C",43),(32,"Australia","D",27),(33,"Algeria","J",28),
    (34,"Bosnia and Herzegovina","B",64),(35,"Tunisia","F",46),(36,"Panama","L",34),
    (37,"Ghana","L",73),(38,"South Africa","A",60),(39,"DR Congo","K",45),
    (40,"Iraq","I",56),(41,"Uzbekistan","K",50),(42,"Qatar","B",55),
    (43,"Saudi Arabia","H",61),(44,"Jordan","J",63),(45,"New Zealand","G",85),
    (46,"Cape Verde","H",68),(47,"Haiti","C",81),(48,"Curaçao","E",83),
]

TEAMS = {}
for ranking, nombre, grupo, fifa in _teams_raw:
    bombo = get_bombo(ranking)
    pv, pe = PTS[bombo]
    TEAMS[nombre] = {
        "nombre": nombre,
        "ranking": ranking,
        "grupo": grupo,
        "bombo": bombo,
        "pts_victoria": pv,
        "pts_empate": pe,
        "ranking_fifa": fifa,
    }

TEAMS_BY_RANKING = sorted(TEAMS.values(), key=lambda t: t["ranking"])

# ── Partidos de grupos (72) ───────────────────────────────────────────────────
MATCHES = [
    (1,"2026-06-11","Grupos","A","Mexico","South Africa"),
    (2,"2026-06-12","Grupos","A","South Korea","Czechia"),
    (3,"2026-06-12","Grupos","B","Canada","Bosnia and Herzegovina"),
    (4,"2026-06-13","Grupos","D","United States","Paraguay"),
    (5,"2026-06-14","Grupos","C","Haiti","Scotland"),
    (6,"2026-06-14","Grupos","D","Australia","Türkiye"),
    (7,"2026-06-14","Grupos","C","Brazil","Morocco"),
    (8,"2026-06-13","Grupos","B","Qatar","Switzerland"),
    (9,"2026-06-15","Grupos","E","Côte d'Ivoire","Ecuador"),
    (10,"2026-06-14","Grupos","E","Germany","Curaçao"),
    (11,"2026-06-14","Grupos","F","Netherlands","Japan"),
    (12,"2026-06-15","Grupos","F","Sweden","Tunisia"),
    (13,"2026-06-16","Grupos","H","Saudi Arabia","Uruguay"),
    (14,"2026-06-15","Grupos","H","Spain","Cape Verde"),
    (15,"2026-06-16","Grupos","G","Iran","New Zealand"),
    (16,"2026-06-15","Grupos","G","Belgium","Egypt"),
    (17,"2026-06-16","Grupos","I","France","Senegal"),
    (18,"2026-06-17","Grupos","I","Iraq","Norway"),
    (19,"2026-06-17","Grupos","J","Argentina","Algeria"),
    (20,"2026-06-17","Grupos","J","Austria","Jordan"),
    (21,"2026-06-18","Grupos","L","Ghana","Panama"),
    (22,"2026-06-17","Grupos","L","England","Croatia"),
    (23,"2026-06-17","Grupos","K","Portugal","DR Congo"),
    (24,"2026-06-18","Grupos","K","Uzbekistan","Colombia"),
    (25,"2026-06-18","Grupos","A","Czechia","South Africa"),
    (26,"2026-06-18","Grupos","B","Switzerland","Bosnia and Herzegovina"),
    (27,"2026-06-19","Grupos","B","Canada","Qatar"),
    (28,"2026-06-19","Grupos","A","Mexico","South Korea"),
    (29,"2026-06-20","Grupos","C","Brazil","Haiti"),
    (30,"2026-06-20","Grupos","C","Scotland","Morocco"),
    (31,"2026-06-20","Grupos","D","Türkiye","Paraguay"),
    (32,"2026-06-19","Grupos","D","United States","Australia"),
    (33,"2026-06-20","Grupos","E","Germany","Côte d'Ivoire"),
    (34,"2026-06-21","Grupos","E","Ecuador","Curaçao"),
    (35,"2026-06-20","Grupos","F","Netherlands","Sweden"),
    (36,"2026-06-21","Grupos","F","Tunisia","Japan"),
    (37,"2026-06-22","Grupos","H","Uruguay","Cape Verde"),
    (38,"2026-06-21","Grupos","H","Spain","Saudi Arabia"),
    (39,"2026-06-21","Grupos","G","Belgium","Iran"),
    (40,"2026-06-22","Grupos","G","New Zealand","Egypt"),
    (41,"2026-06-23","Grupos","I","Norway","Senegal"),
    (42,"2026-06-22","Grupos","I","France","Iraq"),
    (43,"2026-06-22","Grupos","J","Argentina","Austria"),
    (44,"2026-06-23","Grupos","J","Jordan","Algeria"),
    (45,"2026-06-23","Grupos","L","England","Ghana"),
    (46,"2026-06-24","Grupos","L","Panama","Croatia"),
    (47,"2026-06-23","Grupos","K","Portugal","Uzbekistan"),
    (48,"2026-06-24","Grupos","K","Colombia","DR Congo"),
    (49,"2026-06-25","Grupos","C","Scotland","Brazil"),
    (50,"2026-06-25","Grupos","C","Morocco","Haiti"),
    (51,"2026-06-24","Grupos","B","Switzerland","Canada"),
    (52,"2026-06-24","Grupos","B","Bosnia and Herzegovina","Qatar"),
    (53,"2026-06-25","Grupos","A","Czechia","Mexico"),
    (54,"2026-06-25","Grupos","A","South Africa","South Korea"),
    (55,"2026-06-25","Grupos","E","Curaçao","Côte d'Ivoire"),
    (56,"2026-06-25","Grupos","E","Ecuador","Germany"),
    (57,"2026-06-26","Grupos","F","Japan","Sweden"),
    (58,"2026-06-26","Grupos","F","Tunisia","Netherlands"),
    (59,"2026-06-26","Grupos","D","Türkiye","United States"),
    (60,"2026-06-26","Grupos","D","Paraguay","Australia"),
    (61,"2026-06-26","Grupos","I","Norway","France"),
    (62,"2026-06-26","Grupos","I","Senegal","Iraq"),
    (63,"2026-06-27","Grupos","G","Egypt","Iran"),
    (64,"2026-06-27","Grupos","G","New Zealand","Belgium"),
    (65,"2026-06-27","Grupos","H","Cape Verde","Saudi Arabia"),
    (66,"2026-06-27","Grupos","H","Uruguay","Spain"),
    (67,"2026-06-27","Grupos","L","Panama","England"),
    (68,"2026-06-27","Grupos","L","Croatia","Ghana"),
    (69,"2026-06-28","Grupos","J","Algeria","Austria"),
    (70,"2026-06-28","Grupos","J","Jordan","Argentina"),
    (71,"2026-06-28","Grupos","K","Colombia","Portugal"),
    (72,"2026-06-28","Grupos","K","DR Congo","Uzbekistan"),
]

MATCHES_BY_NUM = {m[0]: {"numero":m[0],"fecha":m[1],"fase":m[2],"grupo":m[3],"local":m[4],"visitante":m[5]} for m in MATCHES}
