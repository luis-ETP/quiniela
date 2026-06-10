"""
Run once to seed teams and matches into Supabase.
Usage:
  SUPABASE_URL=... SUPABASE_SECRET_KEY=... python seed.py
"""
import os
from database import get_admin_client

sb = get_admin_client()

# ── Teams ─────────────────────────────────────────────────────────────────────
TEAMS = [
    (1,"Spain","H",2,"+420",1),
    (2,"France","I",3,"+460",2),
    (3,"England","L",4,"+650",3),
    (4,"Argentina","J",1,"+1000",4),
    (5,"Portugal","K",5,"+1000",5),
    (6,"Brazil","C",6,"+850",6),
    (7,"Netherlands","F",8,"+1600",8),
    (8,"Germany","E",10,"+1300",7),
    (9,"Belgium","G",9,"+2200",10),
    (10,"Morocco","C",7,"+6000",12),
    (11,"Colombia","K",13,"+4000",11),
    (12,"Uruguay","H",17,"+6000",13),
    (13,"Croatia","L",11,"+7000",15),
    (14,"Japan","F",18,"+4500",17),
    (15,"United States","D",16,"+6000",18),
    (16,"Norway","I",31,"+3500",9),
    (17,"Switzerland","B",19,"+6500",14),
    (18,"Mexico","A",14,"+6500",20),
    (19,"Senegal","I",15,"+12500",19),
    (20,"Ecuador","E",24,"+10000",16),
    (21,"Türkiye","D",22,"+8000",21),
    (22,"Austria","J",23,"+12500",23),
    (23,"Canada","B",30,"+17500",24),
    (24,"Egypt","G",29,"+25000",27),
    (25,"Sweden","F",38,"+17500",25),
    (26,"South Korea","A",25,"+70000",26),
    (27,"Paraguay","D",40,"+20000",22),
    (28,"Iran","G",20,"+100000",32),
    (29,"Côte d'Ivoire","E",33,"+17500",35),
    (30,"Czechia","A",39,"+60000",28),
    (31,"Scotland","C",43,"+30000",33),
    (32,"Australia","D",27,"+250000",29),
    (33,"Algeria","J",28,"+250000",31),
    (34,"Bosnia and Herzegovina","B",64,"+40000",30),
    (35,"Tunisia","F",46,"+200000",36),
    (36,"Panama","L",34,"+250000",38),
    (37,"Ghana","L",73,"+60000",34),
    (38,"South Africa","A",60,"+250000",37),
    (39,"DR Congo","K",45,"+250000",44),
    (40,"Iraq","I",56,"+250000",40),
    (41,"Uzbekistan","K",50,"+250000",43),
    (42,"Qatar","B",55,"+250000",45),
    (43,"Saudi Arabia","H",61,"+250000",42),
    (44,"Jordan","J",63,"+250000",41),
    (45,"New Zealand","G",85,"+250000",39),
    (46,"Cape Verde","H",68,"+250000",46),
    (47,"Haiti","C",81,"+250000",47),
    (48,"Curaçao","E",83,"+250000",48),
]

def get_bombo(r):
    if r <= 12: return "A"
    if r <= 24: return "B"
    if r <= 36: return "C"
    return "D"

PTS = {"A":(1.0,0.5),"B":(1.5,0.75),"C":(2.0,1.0),"D":(3.0,1.5)}

print("Seeding teams...")
sb.table("teams").delete().neq("id","00000000-0000-0000-0000-000000000000").execute()

team_rows = []
for ranking, nombre, grupo, fifa_rank, odds, opta_rank in TEAMS:
    bombo = get_bombo(ranking)
    pv, pe = PTS[bombo]
    team_rows.append({
        "ranking_compuesto": ranking,
        "nombre": nombre,
        "grupo_oficial": grupo,
        "bombo": bombo,
        "pts_victoria": pv,
        "pts_empate": pe,
        "ranking_fifa": fifa_rank,
        "odds_las_vegas": odds,
        "ranking_modelo": opta_rank,
    })

sb.table("teams").insert(team_rows).execute()
print(f"  {len(team_rows)} teams inserted")

# Build team name→id map
teams_data = sb.table("teams").select("id,nombre").execute().data
team_id = {t["nombre"]: t["id"] for t in teams_data}

# ── Matches ───────────────────────────────────────────────────────────────────
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
    (73,"2026-06-28","Ronda de 32","","",""),
    (74,"2026-06-29","Ronda de 32","","",""),
    (75,"2026-06-30","Ronda de 32","","",""),
    (76,"2026-06-29","Ronda de 32","","",""),
    (77,"2026-06-30","Ronda de 32","","",""),
    (78,"2026-06-30","Ronda de 32","","",""),
    (79,"2026-07-01","Ronda de 32","","",""),
    (80,"2026-07-01","Ronda de 32","","",""),
    (81,"2026-07-02","Ronda de 32","","",""),
    (82,"2026-07-01","Ronda de 32","","",""),
    (83,"2026-07-03","Ronda de 32","","",""),
    (84,"2026-07-02","Ronda de 32","","",""),
    (85,"2026-07-03","Ronda de 32","","",""),
    (86,"2026-07-04","Ronda de 32","","",""),
    (87,"2026-07-04","Ronda de 32","","",""),
    (88,"2026-07-03","Ronda de 32","","",""),
    (89,"2026-07-04","Octavos","","",""),
    (90,"2026-07-04","Octavos","","",""),
    (91,"2026-07-05","Octavos","","",""),
    (92,"2026-07-06","Octavos","","",""),
    (93,"2026-07-06","Octavos","","",""),
    (94,"2026-07-07","Octavos","","",""),
    (95,"2026-07-07","Octavos","","",""),
    (96,"2026-07-07","Octavos","","",""),
    (97,"2026-07-09","Cuartos","","",""),
    (98,"2026-07-10","Cuartos","","",""),
    (99,"2026-07-11","Cuartos","","",""),
    (100,"2026-07-12","Cuartos","","",""),
    (101,"2026-07-14","Semifinal","","",""),
    (102,"2026-07-15","Semifinal","","",""),
    (103,"2026-07-18","Tercer lugar","","",""),
    (104,"2026-07-19","Final","","",""),
]

print("Seeding matches...")
sb.table("matches").delete().neq("id","00000000-0000-0000-0000-000000000000").execute()

match_rows = []
for numero, fecha, fase, grupo, local, visitante in MATCHES:
    row = {
        "numero": numero,
        "fecha": fecha,
        "fase": fase,
        "grupo": grupo,
        "estado": "Programado",
        "local_nombre": local or None,
        "visitante_nombre": visitante or None,
        "local_id": team_id.get(local) if local else None,
        "visitante_id": team_id.get(visitante) if visitante else None,
    }
    match_rows.append(row)

sb.table("matches").insert(match_rows).execute()
print(f"  {len(match_rows)} matches inserted")
print("Done ✓")
