from flask import Flask, request, render_template_string
import requests
import os
import datetime
import random
import json
from collections import defaultdict

app = Flask(__name__)

@app.route('/')
def home():
    try:
        selected_sport = request.args.get("sport", "").strip()
        selected_league = request.args.get("league", "").strip()
        selected_status = request.args.get("status", "").strip()

        # URL de l'API 1xbet
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=100&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url)
        matches = response.json().get("Value", [])

        sports_detected = set()
        leagues_detected = set()
        data = []

        for match in matches:
            try:
                league = match.get("LE", "–")
                team1 = match.get("O1", "–")
                team2 = match.get("O2", "–")
                sport = detect_sport(league).strip()
                sports_detected.add(sport)
                leagues_detected.add(league)

                # --- Score --- (Structure corrigée selon l'API)
                sc = match.get("SC", {})
                fs = sc.get("FS", {})

                # Essayer différentes structures possibles pour les scores
                score1 = 0
                score2 = 0

                if isinstance(fs, dict):
                    score1 = fs.get("S1", 0) or fs.get("1", 0) or 0
                    score2 = fs.get("S2", 0) or fs.get("2", 0) or 0
                elif isinstance(fs, list) and len(fs) >= 2:
                    score1 = fs[0] if fs[0] is not None else 0
                    score2 = fs[1] if fs[1] is not None else 0

                # Conversion sécurisée en entier
                try:
                    score1 = int(score1) if score1 is not None else 0
                except (ValueError, TypeError):
                    score1 = 0
                try:
                    score2 = int(score2) if score2 is not None else 0
                except (ValueError, TypeError):
                    score2 = 0

                # --- Minute et Statut --- (Structure corrigée selon l'API)
                minute = None
                sc = match.get("SC", {})

                # Récupération du temps (TS = timestamp en secondes)
                if "TS" in sc and isinstance(sc["TS"], int):
                    minute = sc["TS"] // 60
                elif "T" in match and isinstance(match["T"], int):
                    minute = match["T"]

                # Récupération du statut du match
                hs = match.get("HS", 0)  # Statut principal
                tn = match.get("TN", "").lower()
                tns = match.get("TNS", "").lower()
                cps = sc.get("CPS", "")  # Statut du match dans SC

                # Détermination du statut
                statut = "À venir"
                is_live = False
                is_finished = False
                is_upcoming = False

                # Logique basée sur HS et autres indicateurs
                if hs == 1 or "live" in cps.lower() or (minute is not None and minute > 0):
                    statut = f"En cours ({minute}′)" if minute else "En cours"
                    is_live = True
                elif hs == 3 or "terminé" in tn or "finished" in tns.lower() or "final" in cps.lower():
                    statut = "Terminé"
                    is_finished = True
                elif hs == 0 or statut == "À venir":
                    is_upcoming = True

                if selected_sport and sport != selected_sport:
                    continue
                if selected_league and league != selected_league:
                    continue
                if selected_status == "live" and not is_live:
                    continue
                if selected_status == "finished" and not is_finished:
                    continue
                if selected_status == "upcoming" and not is_upcoming:
                    continue

                match_ts = match.get("S", 0)
                match_time = datetime.datetime.fromtimestamp(match_ts, datetime.timezone.utc).strftime('%d/%m/%Y %H:%M') if match_ts else "–"

                # --- Cotes ---
                odds_data = []
                # 1. Chercher dans E (G=1)
                for o in match.get("E", []):
                    if o.get("G") == 1 and o.get("T") in [1, 2, 3] and o.get("C") is not None:
                        odds_data.append({
                            "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                            "cote": o.get("C")
                        })
                # 2. Sinon, chercher dans AE
                if not odds_data:
                    for ae in match.get("AE", []):
                        if ae.get("G") == 1:
                            for o in ae.get("ME", []):
                                if o.get("T") in [1, 2, 3] and o.get("C") is not None:
                                    odds_data.append({
                                        "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                                        "cote": o.get("C")
                                    })
                if not odds_data:
                    formatted_odds = ["Pas de cotes disponibles"]
                else:
                    formatted_odds = [f"{od['type']}: {od['cote']}" for od in odds_data]

                # Nouvelle prédiction intelligente
                prediction = generer_prediction_intelligente(team1, team2, league, odds_data, sport)

                # --- Météo --- (Structure corrigée, souvent absente dans l'API)
                # La météo n'est pas toujours disponible dans cette API
                temp = "–"
                humid = "–"

                # Essayer de récupérer les données météo si disponibles
                meteo_data = match.get("MIS", [])
                if meteo_data and isinstance(meteo_data, list):
                    temp = next((item.get("V", "–") for item in meteo_data if item.get("K") == 9), "–")
                    humid = next((item.get("V", "–") for item in meteo_data if item.get("K") == 27), "–")

                data.append({
                    "team1": team1,
                    "team2": team2,
                    "score1": score1,
                    "score2": score2,
                    "league": league,
                    "sport": sport,
                    "status": statut,
                    "datetime": match_time,
                    "temp": temp,
                    "humid": humid,
                    "odds": formatted_odds,
                    "prediction": prediction,
                    "id": match.get("I", None)
                })
            except Exception as e:
                print(f"Erreur lors du traitement d'un match: {e}")
                continue

        # --- Pagination ---
        try:
            page = int(request.args.get('page', 1))
        except:
            page = 1
        per_page = 20
        total = len(data)
        total_pages = (total + per_page - 1) // per_page
        data_paginated = data[(page-1)*per_page:page*per_page]

        return render_template_string(TEMPLATE, data=data_paginated,
            sports=sorted(sports_detected),
            leagues=sorted(leagues_detected),
            selected_sport=selected_sport or "Tous",
            selected_league=selected_league or "Toutes",
            selected_status=selected_status or "Tous",
            page=page,
            total_pages=total_pages
        )

    except Exception as e:
        return f"Erreur : {e}"

def detect_sport(league_name):
    league = league_name.lower()
    if any(word in league for word in ["wta", "atp", "tennis"]):
        return "Tennis"
    elif any(word in league for word in ["basket", "nbl", "nba", "ipbl"]):
        return "Basketball"
    elif "hockey" in league:
        return "Hockey"
    elif any(word in league for word in ["tbl", "table"]):
        return "Table Basketball"
    elif "cricket" in league:
        return "Cricket"
    else:
        return "Football"

def traduire_pari(nom, valeur=None):
    """Traduit le nom d'un pari alternatif et sa valeur en français."""
    nom_str = str(nom).lower() if nom else ""
    valeur_str = str(valeur) if valeur is not None else ""
    valeur_str_lower = valeur_str.lower()
    # Cas Oui/Non
    if valeur_str_lower in ["yes", "oui"]:
        choix = "Oui"
    elif valeur_str_lower in ["no", "non"]:
        choix = "Non"
    else:
        choix = valeur_str
    if "total" in nom_str:
        if "over" in nom_str or "over" in valeur_str_lower or "+" in valeur_str:
            return ("Plus de buts", choix)
        elif "under" in nom_str or "under" in valeur_str_lower or "-" in valeur_str:
            return ("Moins de buts", choix)
        else:
            return ("Total buts", choix)
    elif "both teams to score" in nom_str:
        return ("Les deux équipes marquent", choix)
    elif "handicap" in nom_str:
        return ("Handicap", choix)
    elif "double chance" in nom_str:
        return ("Double chance", choix)
    elif "draw no bet" in nom_str:
        return ("Remboursé si match nul", choix)
    elif "odd/even" in nom_str or "odd" in nom_str or "even" in nom_str:
        return ("Nombre de buts pair/impair", choix)
    elif "clean sheet" in nom_str:
        return ("Clean sheet (équipe ne prend pas de but)", choix)
    elif "correct score" in nom_str:
        return ("Score exact", choix)
    elif "win to nil" in nom_str:
        return ("Gagne sans encaisser de but", choix)
    elif "first goal" in nom_str:
        return ("Première équipe à marquer", choix)
    elif "to win" in nom_str:
        return ("Pour gagner", choix)
    else:
        return (nom_str.capitalize(), choix)

def detecter_contexte_pari(match_data):
    """Détecte le contexte du pari (match complet, mi-temps, etc.) basé sur les données du match"""
    # Analyser les indicateurs de contexte dans les données
    tn = match_data.get("TN", "").lower()
    tns = match_data.get("TNS", "").lower()
    sc = match_data.get("SC", {})
    cps = sc.get("CPS", "").lower()

    # Détection du contexte
    if "1st half" in tns or "première" in tn or "1ère" in cps:
        return "première_mi_temps"
    elif "2nd half" in tns or "deuxième" in tn or "2ème" in cps:
        return "deuxième_mi_temps"
    elif "half" in tns or "mi-temps" in tn:
        return "mi_temps"
    else:
        return "match_complet"

def traduire_pari_type_groupe(type_pari, groupe, param, team1=None, team2=None, contexte="match_complet"):
    """
    Traduit le type de pari selon T, G et P (structure 1xbet) avec mapping canonique complet.

    STRUCTURE CANONIQUE 1XBET :
    ===========================
    Groupe 1 (1X2) : T=1→Victoire O1, T=2→Nul, T=3→Victoire O2
    Groupe 2 (Handicap asiatique) : T=7→O1, T=8→O2 (avec P=handicap)
    Groupe 8 (Handicap européen) : T=4→O1(-1), T=5→O1(+1), T=6→O2(0)
    Groupe 17 (Over/Under) : T=9→Over, T=10→Under (avec P=seuil)
    Groupe 19 (Pair/Impair) : T=180→Pair, T=181→Impair
    Groupe 62 (Corners) : T=14→Over corners, T=13→Under corners

    CHAMPS CONTEXTUELS :
    ===================
    - O1, O2 : Noms des équipes
    - TN/TNS : Période ("Mi-temps", "Match entier", etc.)
    - P : Paramètre (handicap, seuil, etc.)
    - G : Groupe du marché
    - T : Type de pari dans le groupe
    - C : Cote
    """

    # Suffixe de contexte
    contexte_suffix = {
        "première_mi_temps": " (1ère mi-temps)",
        "deuxième_mi_temps": " (2ème mi-temps)",
        "mi_temps": " (mi-temps)",
        "match_complet": ""
    }.get(contexte, "")

    # Groupe 1 - Résultat 1X2
    if groupe == 1:
        if type_pari == 1:
            return f"Victoire {team1} (O1){contexte_suffix}"
        elif type_pari == 2:
            return f"Match nul{contexte_suffix}"
        elif type_pari == 3:
            return f"Victoire {team2} (O2){contexte_suffix}"
        return f"1X2{contexte_suffix}"

    # Groupe 2 - Handicap asiatique (MAPPING OFFICIEL)
    if groupe == 2:
        if param is not None:
            if type_pari == 7:  # T=7 → Pari sur Équipe 1 (O1)
                return f"Handicap asiatique {team1} ({param:+g}) - Pari sur O1{contexte_suffix}"
            elif type_pari == 8:  # T=8 → Pari sur Équipe 2 (O2)
                return f"Handicap asiatique {team2} ({param:+g}) - Pari sur O2{contexte_suffix}"
            else:
                return f"Handicap asiatique ({param:+g}) - Type T{type_pari}{contexte_suffix}"
        return f"Handicap asiatique{contexte_suffix}"

    # Groupe 8 - Handicap européen (MAPPING CANONIQUE)
    if groupe == 8:
        if type_pari == 4:  # T=4 → Victoire Équipe 1 avec handicap -1
            return f"Handicap européen {team1} (-1) - {team1} doit gagner par 2+ buts{contexte_suffix}"
        elif type_pari == 5:  # T=5 → Victoire Équipe 1 avec +1
            return f"Handicap européen {team1} (+1) - {team1} gagne ou nul{contexte_suffix}"
        elif type_pari == 6:  # T=6 → Victoire Équipe 2 avec handicap 0
            return f"Handicap européen {team2} (0) - {team2} gagne ou nul{contexte_suffix}"
        else:
            return f"Handicap européen - Type T{type_pari}{contexte_suffix}"

    # Groupe 17 - Over/Under (MAPPING OFFICIEL)
    if groupe == 17:
        if param is not None:
            seuil = abs(float(param))
            total_text = "TOTAL du match" if contexte == "match_complet" else f"TOTAL {contexte.replace('_', ' ')}"
            if type_pari == 9:  # T=9 → Over (Plus de) - TOTAL
                return f"Plus de {seuil} buts ({total_text})"
            elif type_pari == 10:  # T=10 → Under (Moins de) - TOTAL
                return f"Moins de {seuil} buts ({total_text})"
            else:
                return f"Total {seuil} buts - Type T{type_pari}{contexte_suffix}"
        return f"Over/Under (TOTAL){contexte_suffix}"

    # Groupe 62 - Corners (MAPPING CANONIQUE)
    if groupe == 62:
        if param is not None:
            seuil = abs(float(param))
            if type_pari == 14:  # T=14 → Plus de X corners
                return f"Plus de {seuil} corners{contexte_suffix}"
            elif type_pari == 13:  # T=13 → Moins de X corners
                return f"Moins de {seuil} corners{contexte_suffix}"
            else:
                return f"Total {seuil} corners - T{type_pari}{contexte_suffix}"
        return f"Total corners{contexte_suffix}"

    # Autres groupes Over/Under possibles
    if groupe in [5, 12]:
        if param is not None:
            seuil = abs(float(param))
            if type_pari == 9:
                return f"Plus de {seuil} buts (TOTAL du match)"
            elif type_pari == 10:
                return f"Moins de {seuil} buts (TOTAL du match)"
            else:
                return f"Total {seuil} buts - G{groupe} T{type_pari}"
        return "Plus/Moins de buts"
    # Double chance - Groupe 3
    if groupe == 3:
        if type_pari == 1:
            return f"Double chance: {team1} ou Match nul"
        elif type_pari == 2:
            return f"Double chance: {team2} ou Match nul"
        elif type_pari == 3:
            return f"Double chance: {team1} ou {team2}"
        return "Double chance"

    # Score exact - Groupe 15
    if groupe == 15:
        if param is not None:
            return f"Score exact {param} ({team1} vs {team2})"
        return f"Score exact ({team1} vs {team2})"

    # Groupe 19 - Pair/Impair (MAPPING OFFICIEL)
    if groupe == 19:
        if type_pari == 180:  # T=180 → Total de buts pair
            return "Total de buts PAIR (0, 2, 4, 6...)"
        elif type_pari == 181:  # T=181 → Total de buts impair
            return "Total de buts IMPAIR (1, 3, 5, 7...)"
        elif type_pari == 1:  # Fallback pour ancienne logique
            return "Les deux équipes marquent: OUI"
        elif type_pari == 2:  # Fallback pour ancienne logique
            return "Les deux équipes marquent: NON"
        else:
            return f"Pair/Impair - Type T{type_pari}"

    # Nombre de buts par équipe - Groupes spécifiques
    if groupe in [20, 21, 22]:
        if param is not None:
            seuil = abs(float(param))
            if type_pari == 1:
                return f"Plus de {seuil} buts pour {team1}"
            elif type_pari == 2:
                return f"Moins de {seuil} buts pour {team1}"
        return f"Buts marqués par {team1}"

    if groupe in [23, 24, 25]:
        if param is not None:
            seuil = abs(float(param))
            if type_pari == 1:
                return f"Plus de {seuil} buts pour {team2}"
            elif type_pari == 2:
                return f"Moins de {seuil} buts pour {team2}"
        return f"Buts marqués par {team2}"

    # Mi-temps/Fin de match - Groupe 4
    if groupe == 4:
        if type_pari == 1:
            return f"Mi-temps: {team1} / Fin: {team1}"
        elif type_pari == 2:
            return f"Mi-temps: {team1} / Fin: Match nul"
        elif type_pari == 3:
            return f"Mi-temps: {team1} / Fin: {team2}"
        elif type_pari == 4:
            return f"Mi-temps: Match nul / Fin: {team1}"
        elif type_pari == 5:
            return f"Mi-temps: Match nul / Fin: Match nul"
        elif type_pari == 6:
            return f"Mi-temps: Match nul / Fin: {team2}"
        elif type_pari == 7:
            return f"Mi-temps: {team2} / Fin: {team1}"
        elif type_pari == 8:
            return f"Mi-temps: {team2} / Fin: Match nul"
        elif type_pari == 9:
            return f"Mi-temps: {team2} / Fin: {team2}"
        return "Mi-temps/Fin de match"

    # Fallback avec informations de debug
    return f"Pari G{groupe}-T{type_pari}" + (f"-P{param}" if param is not None else "")

@app.route('/match/<int:match_id>')
def match_details(match_id):
    try:
        # Récupérer les données de l'API 1xbet
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=100&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url)
        matches = response.json().get("Value", [])
        match = next((m for m in matches if m.get("I") == match_id), None)
        if not match:
            return f"Aucun match trouvé pour l'identifiant {match_id}"
        # Infos principales
        team1 = match.get("O1", "–")
        team2 = match.get("O2", "–")
        league = match.get("LE", "–")
        sport = detect_sport(league)
        # Scores (structure corrigée)
        sc = match.get("SC", {})
        fs = sc.get("FS", {})

        score1 = 0
        score2 = 0

        if isinstance(fs, dict):
            score1 = fs.get("S1", 0) or fs.get("1", 0) or 0
            score2 = fs.get("S2", 0) or fs.get("2", 0) or 0
        elif isinstance(fs, list) and len(fs) >= 2:
            score1 = fs[0] if fs[0] is not None else 0
            score2 = fs[1] if fs[1] is not None else 0

        try:
            score1 = int(score1) if score1 is not None else 0
        except (ValueError, TypeError):
            score1 = 0
        try:
            score2 = int(score2) if score2 is not None else 0
        except (ValueError, TypeError):
            score2 = 0
        # Statistiques avancées (structure corrigée)
        stats = []
        sc = match.get("SC", {})

        # Essayer différentes structures pour les statistiques
        if "ST" in sc:
            st = sc["ST"]
            if isinstance(st, list) and len(st) > 0:
                if isinstance(st[0], dict) and "Value" in st[0]:
                    for stat in st[0]["Value"]:
                        nom = stat.get("N", "Statistique")
                        s1 = stat.get("S1", "0")
                        s2 = stat.get("S2", "0")
                        stats.append({"nom": nom, "s1": s1, "s2": s2})
                elif isinstance(st[0], dict):
                    # Structure alternative
                    for key, value in st[0].items():
                        if isinstance(value, dict) and "S1" in value and "S2" in value:
                            stats.append({"nom": key, "s1": value["S1"], "s2": value["S2"]})

        # Si pas de statistiques, ajouter des stats basiques
        if not stats:
            stats = [
                {"nom": "Score", "s1": str(score1), "s2": str(score2)},
                {"nom": "Statut", "s1": "–", "s2": "–"}
            ]
        # Explication prédiction (simple)
        explication = "La prédiction est basée sur les cotes et les statistiques principales (tirs, possession, etc.)."  # Peut être enrichi
        # Prédiction 1X2
        odds_data = []
        for o in match.get("E", []):
            if o.get("G") == 1 and o.get("T") in [1, 2, 3] and o.get("C") is not None:
                odds_data.append({
                    "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                    "cote": o.get("C")
                })
        if not odds_data:
            for ae in match.get("AE", []):
                if ae.get("G") == 1:
                    for o in ae.get("ME", []):
                        if o.get("T") in [1, 2, 3] and o.get("C") is not None:
                            odds_data.append({
                                "type": {1: "1", 2: "2", 3: "X"}.get(o.get("T")),
                                "cote": o.get("C")
                            })
        # Prédiction intelligente pour la page de détails
        prediction = generer_prediction_intelligente(team1, team2, league, odds_data, sport)
        # --- Paris alternatifs ---
        paris_alternatifs = []
        # 1. E (marchés principaux et alternatifs)
        for o in match.get("E", []):
            if o.get("G") != 1 and o.get("C") is not None:
                type_pari = o.get("T")
                groupe = o.get("G")
                param = o.get("P") if "P" in o else None
                # Détecter le contexte du match
                contexte = detecter_contexte_pari(match)
                nom_traduit = traduire_pari_type_groupe(type_pari, groupe, param, team1, team2, contexte)
                valeur = param if param is not None else ""
                cote = o.get("C")

                # Debug info pour mieux comprendre les types
                debug_info = ""
                if groupe in [8, 17, 62, 5, 12]:  # Groupes Over/Under
                    debug_info = f" [G{groupe}-T{type_pari}-P{param}]"

                paris_alternatifs.append({
                    "nom": nom_traduit + debug_info,
                    "valeur": valeur,
                    "cote": cote,
                    "raw_data": {"G": groupe, "T": type_pari, "P": param}  # Pour debug
                })
        # 2. AE (marchés alternatifs étendus)
        for ae in match.get("AE", []):
            if ae.get("G") != 1:
                for o in ae.get("ME", []):
                    if o.get("C") is not None:
                        type_pari = o.get("T")
                        groupe = o.get("G")
                        param = o.get("P") if "P" in o else None
                        # Détecter le contexte du match
                        contexte = detecter_contexte_pari(match)
                        nom_traduit = traduire_pari_type_groupe(type_pari, groupe, param, team1, team2, contexte)
                        valeur = param if param is not None else ""
                        cote = o.get("C")

                        # Debug info pour mieux comprendre les types
                        debug_info = ""
                        if groupe in [8, 17, 62, 5, 12]:  # Groupes Over/Under
                            debug_info = f" [G{groupe}-T{type_pari}-P{param}]"

                        paris_alternatifs.append({
                            "nom": nom_traduit + debug_info,
                            "valeur": valeur,
                            "cote": cote,
                            "raw_data": {"G": groupe, "T": type_pari, "P": param}  # Pour debug
                        })
        # Filtrer les paris alternatifs selon la cote demandée
        paris_alternatifs = [p for p in paris_alternatifs if 1.499 <= float(p["cote"]) <= 3]
        # Filtrer les paris corners et pair/impair du tableau alternatif
        paris_alternatifs_filtres = []
        for p in paris_alternatifs:
            nom_lower = p['nom'].lower()
            # Exclure corners et pair/impair du tableau principal
            if not (('corner' in nom_lower) or ('pair' in nom_lower) or ('impair' in nom_lower)):
                paris_alternatifs_filtres.append(p)

        # Prédictions alternatives intelligentes (sans corners et pair/impair)
        prediction_alt = generer_predictions_alternatives(team1, team2, league, paris_alternatifs_filtres, odds_data)
        # HTML avec tableau des paris alternatifs
        return f'''
        <!DOCTYPE html>
        <html><head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Détails du match</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f4f4f4; }}
                .container {{ max-width: 800px; margin: auto; background: white; border-radius: 10px; box-shadow: 0 2px 8px #ccc; padding: 20px; }}
                h2 {{ text-align: center; }}
                .stats-table, .alt-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .stats-table th, .stats-table td, .alt-table th, .alt-table td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
                .back-btn {{ margin-bottom: 20px; display: inline-block; }}
                .highlight-pred {{ background: #eaf6fb; color: #2980b9; font-weight: bold; padding: 10px; border-radius: 6px; margin-bottom: 15px; }}
                .contact-box {{ background: #f0f8ff; border: 1.5px solid #2980b9; border-radius: 8px; margin-top: 30px; padding: 18px; text-align: center; font-size: 17px; }}
                .contact-box a {{ color: #1565c0; font-weight: bold; text-decoration: none; }}

                /* Styles pour les graphiques avancés */
                .chart-tabs {{ display: flex; margin: 20px 0; border-bottom: 2px solid #ddd; }}
                .tab-btn {{ background: none; border: none; padding: 12px 20px; cursor: pointer; font-size: 16px; font-weight: bold; color: #666; transition: all 0.3s; }}
                .tab-btn:hover {{ background: #f0f0f0; color: #2980b9; }}
                .tab-btn.active {{ color: #2980b9; border-bottom: 3px solid #2980b9; background: #f8f9fa; }}
                .chart-container {{ display: none; margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 8px; }}
                .chart-container.active {{ display: block; }}
                .chart-title {{ text-align: center; font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #2c3e50; }}
                .chart-legend {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 15px; }}
                .legend-item {{ display: flex; align-items: center; gap: 8px; }}
                .legend-color {{ width: 20px; height: 20px; border-radius: 3px; }}
                .chart-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }}
                .stat-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
                .stat-label {{ font-size: 14px; color: #666; margin-top: 5px; }}

                /* Styles pour les prédictions IA */
                .prediction-summary {{ margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white; }}
                .prediction-item {{ display: flex; justify-content: space-between; align-items: center; margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; }}
                .prediction-label {{ font-weight: bold; }}
                .prediction-value {{ font-size: 18px; font-weight: bold; }}
                .confidence-bar {{ width: 100%; height: 8px; background: rgba(255,255,255,0.3); border-radius: 4px; margin-top: 5px; }}
                .confidence-fill {{ height: 100%; background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3); border-radius: 4px; transition: width 0.5s ease; }}

                /* Styles pour les scénarios */
                .scenario-controls {{ text-align: center; margin-top: 20px; }}
                .sim-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 24px; margin: 0 10px; border-radius: 25px; cursor: pointer; font-weight: bold; transition: transform 0.2s; }}
                .sim-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
                .scenario-result {{ margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #2980b9; }}

                /* Styles pour les prédictions spécialisées */
                .prediction-tabs {{ display: flex; flex-wrap: wrap; margin: 20px 0; border-bottom: 2px solid #ddd; gap: 5px; }}
                .pred-tab-btn {{ background: none; border: none; padding: 10px 15px; cursor: pointer; font-size: 14px; font-weight: bold; color: #666; transition: all 0.3s; border-radius: 8px 8px 0 0; }}
                .pred-tab-btn:hover {{ background: #f0f0f0; color: #2980b9; }}
                .pred-tab-btn.active {{ color: #2980b9; border-bottom: 3px solid #2980b9; background: #f8f9fa; }}
                .prediction-container {{ display: none; margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 8px; }}
                .prediction-container.active {{ display: block; }}
                .pred-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                .pred-table th {{ background: #2980b9; color: white; padding: 12px; text-align: left; }}
                .pred-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                .pred-table tr:hover {{ background: #f0f8ff; }}
                .probability-bar {{ width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }}
                .probability-fill {{ height: 100%; background: linear-gradient(90deg, #e74c3c, #f39c12, #f1c40f, #2ecc71); transition: width 0.5s ease; }}
                .prediction-badge {{ padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; }}
                .badge-high {{ background: #27ae60; }}
                .badge-medium {{ background: #f39c12; }}
                .badge-low {{ background: #e74c3c; }}
            </style>
        </head><body>
            <div class="container">
                <a href="/" class="back-btn">&larr; Retour à la liste</a>
                <h2>{team1} vs {team2}</h2>
                <p><b>Ligue :</b> {league} | <b>Sport :</b> {sport}</p>
                <p><b>Score :</b> {score1} - {score2}</p>
                <p><b>Prédiction 1X2 du bot :</b> {prediction}</p>
                <p><b>Explication :</b> {explication}</p>
                <div class="highlight-pred">
                    <b>🤖 Analyse IA Unifiée :</b><br>
                    {prediction_alt if prediction_alt else 'Aucune prédiction alternative disponible'}
                </div>

                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; margin: 20px 0; color: white;">
                    <h4 style="text-align: center; margin-bottom: 15px;">🤖 DÉCISION COLLECTIVE DES SYSTÈMES IA</h4>
                    <p style="text-align: center; margin-bottom: 10px; font-size: 14px; opacity: 0.9;">
                        Tous les algorithmes délibèrent ensemble pour prendre une décision unique
                    </p>
                    <div id="unified-prediction-preview" style="text-align: center; font-weight: bold; font-size: 16px;">
                        ⏳ Délibération en cours...
                    </div>
                </div>
                <h3>Statistiques principales</h3>
                <table class="stats-table">
                    <tr><th>Statistique</th><th>{team1}</th><th>{team2}</th></tr>
                    {''.join(f'<tr><td>{s["nom"]}</td><td>{s["s1"]}</td><td>{s["s2"]}</td></tr>' for s in stats)}
                </table>
                <h3>📊 Analytics Avancées</h3>

                <!-- Onglets pour les différents graphiques -->
                <div class="chart-tabs">
                    <button class="tab-btn active" onclick="showChart('stats')">📊 Statistiques</button>
                    <button class="tab-btn" onclick="showChart('odds')">💰 Évolution Cotes</button>
                    <button class="tab-btn" onclick="showChart('predictions')">🎯 Prédictions</button>
                    <button class="tab-btn" onclick="showChart('comparison')">⚖️ Comparaison</button>
                    <button class="tab-btn" onclick="showChart('aiPredictions')">🤖 IA Prédictive</button>
                    <button class="tab-btn" onclick="showChart('scenarios')">🎲 Scénarios</button>
                </div>

                <!-- Conteneurs des graphiques -->
                <div id="statsChart-container" class="chart-container active">
                    <canvas id="statsChart" height="300"></canvas>
                </div>

                <div id="oddsChart-container" class="chart-container">
                    <canvas id="oddsChart" height="300"></canvas>
                </div>

                <div id="predictionsChart-container" class="chart-container">
                    <canvas id="predictionsChart" height="300"></canvas>
                </div>

                <div id="comparisonChart-container" class="chart-container">
                    <canvas id="comparisonChart" height="300"></canvas>
                </div>

                <div id="aiPredictionsChart-container" class="chart-container">
                    <div class="chart-title">🤖 Système de Prédiction IA Multi-Algorithmes</div>
                    <canvas id="aiPredictionsChart" height="300"></canvas>
                    <div class="prediction-summary" id="predictionSummary"></div>
                </div>

                <div id="scenariosChart-container" class="chart-container">
                    <div class="chart-title">🎲 Simulation de Scénarios de Match</div>
                    <canvas id="scenariosChart" height="300"></canvas>
                    <div class="scenario-controls">
                        <button onclick="runSimulation()" class="sim-btn">🔄 Nouvelle Simulation</button>
                        <button onclick="showProbabilities()" class="sim-btn">📊 Probabilités</button>
                    </div>
                </div>

                <h3>🎯 Centre de Prédictions Spécialisées</h3>

                <!-- Onglets pour les catégories de prédictions -->
                <div class="prediction-tabs">
                    <button class="pred-tab-btn active" onclick="showPredictionCategory('pair-impair')">🔢 Pair/Impair</button>
                    <button class="pred-tab-btn" onclick="showPredictionCategory('corners')">⚽ Corners</button>
                    <button class="pred-tab-btn" onclick="showPredictionCategory('mi-temps')">⏰ Mi-temps</button>
                    <button class="pred-tab-btn" onclick="showPredictionCategory('handicaps')">⚖️ Handicaps</button>
                    <button class="pred-tab-btn" onclick="showPredictionCategory('totaux')">📊 Totaux</button>
                    <button class="pred-tab-btn" onclick="showPredictionCategory('autres')">📋 Autres</button>
                </div>

                <!-- Conteneurs des prédictions par catégorie -->
                <div id="pair-impair-container" class="prediction-container active">
                    <h4>🔢 Prédictions Pair/Impair</h4>
                    <table class="pred-table">
                        <tr><th>Type</th><th>Valeur</th><th>Cote</th><th>Prédiction IA</th><th>Probabilité</th></tr>
                        <tbody id="pair-impair-content"></tbody>
                    </table>
                </div>

                <div id="corners-container" class="prediction-container">
                    <h4>⚽ Prédictions Corners</h4>
                    <table class="pred-table">
                        <tr><th>Type</th><th>Valeur</th><th>Cote</th><th>Prédiction IA</th><th>Probabilité</th></tr>
                        <tbody id="corners-content"></tbody>
                    </table>
                </div>

                <div id="mi-temps-container" class="prediction-container">
                    <h4>⏰ Prédictions Mi-temps</h4>
                    <table class="pred-table">
                        <tr><th>Type</th><th>Valeur</th><th>Cote</th><th>Prédiction IA</th><th>Probabilité</th></tr>
                        <tbody id="mi-temps-content"></tbody>
                    </table>
                </div>

                <div id="handicaps-container" class="prediction-container">
                    <h4>⚖️ Prédictions Handicaps</h4>
                    <table class="pred-table">
                        <tr><th>Type</th><th>Valeur</th><th>Cote</th><th>Prédiction IA</th><th>Probabilité</th></tr>
                        <tbody id="handicaps-content"></tbody>
                    </table>
                </div>

                <div id="totaux-container" class="prediction-container">
                    <h4>📊 Prédictions Totaux (Over/Under)</h4>
                    <table class="pred-table">
                        <tr><th>Type</th><th>Valeur</th><th>Cote</th><th>Prédiction IA</th><th>Probabilité</th></tr>
                        <tbody id="totaux-content"></tbody>
                    </table>
                </div>

                <div id="autres-container" class="prediction-container">
                    <h4>📋 Autres Prédictions</h4>
                    <table class="pred-table">
                        <tr><th>Type</th><th>Valeur</th><th>Cote</th><th>Prédiction IA</th><th>Probabilité</th></tr>
                        <tbody id="autres-content"></tbody>
                    </table>
                </div>

                <h3>📊 Tableau des Paris Alternatifs (Filtré)</h3>
                <table class="alt-table">
                    <tr><th>Type de pari</th><th>Valeur</th><th>Cote</th><th>Prédiction</th></tr>
                    {''.join(f'<tr><td>{p["nom"]}</td><td>{p["valeur"]}</td><td>{p["cote"]}</td><td>{generer_prediction_lisible(p["nom"], p["valeur"], team1, team2)}</td></tr>' for p in paris_alternatifs_filtres)}
                </table>
                <div class="contact-box">
                    <b>Contact & Services :</b><br>
                    📬 Inbox Telegram : <a href="https://t.me/Roidesombres225" target="_blank">@Roidesombres225</a><br>
                    📢 Canal Telegram : <a href="https://t.me/SOLITAIREHACK" target="_blank">SOLITAIREHACK</a><br>
                    🎨 Je suis aussi concepteur graphique et créateur de logiciels.<br>
                    <span style="color:#2980b9;">Vous avez un projet en tête ? Contactez-moi, je suis là pour vous !</span>
                </div>
            </div>
            <script>
                // Données pour tous les graphiques
                const labels = { [repr(s['nom']) for s in stats] };
                const data1 = { [float(s['s1']) if s['s1'].replace('.', '', 1).isdigit() else 0 for s in stats] };
                const data2 = { [float(s['s2']) if s['s2'].replace('.', '', 1).isdigit() else 0 for s in stats] };

                // Couleurs thématiques
                const colors = {{
                    team1: ['rgba(52, 152, 219, 0.8)', 'rgba(52, 152, 219, 0.3)'],
                    team2: ['rgba(231, 76, 60, 0.8)', 'rgba(231, 76, 60, 0.3)'],
                    accent: ['rgba(46, 204, 113, 0.8)', 'rgba(155, 89, 182, 0.8)', 'rgba(241, 196, 15, 0.8)']
                }};

                let charts = {{}};

                // Fonction pour changer d'onglet
                function showChart(chartType) {{
                    // Masquer tous les conteneurs
                    document.querySelectorAll('.chart-container').forEach(c => c.classList.remove('active'));
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

                    // Afficher le conteneur sélectionné
                    document.getElementById(chartType + 'Chart-container').classList.add('active');
                    event.target.classList.add('active');

                    // Créer le graphique si pas encore fait
                    if (!charts[chartType]) {{
                        createChart(chartType);
                    }}
                }}

                // Fonction pour créer les différents graphiques
                function createChart(type) {{
                    const ctx = document.getElementById(type + 'Chart').getContext('2d');

                    switch(type) {{
                        case 'stats':
                            charts.stats = new Chart(ctx, {{
                                type: 'bar',
                                data: {{
                                    labels: labels,
                                    datasets: [
                                        {{
                                            label: '{team1}',
                                            data: data1,
                                            backgroundColor: colors.team1[0],
                                            borderColor: colors.team1[0],
                                            borderWidth: 2
                                        }},
                                        {{
                                            label: '{team2}',
                                            data: data2,
                                            backgroundColor: colors.team2[0],
                                            borderColor: colors.team2[0],
                                            borderWidth: 2
                                        }}
                                    ]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{
                                        title: {{ display: true, text: '📊 Comparaison des Statistiques', font: {{ size: 16 }} }},
                                        legend: {{ position: 'top' }}
                                    }},
                                    scales: {{
                                        y: {{ beginAtZero: true }}
                                    }}
                                }}
                            }});
                            break;

                        case 'odds':
                            // Simulation d'évolution des cotes
                            const oddsData = {{
                                labels: ['Début', '15min', '30min', '45min', 'Mi-temps', '60min', '75min', '90min'],
                                team1Odds: [2.1, 2.0, 1.9, 1.8, 1.85, 1.9, 2.0, 2.1],
                                team2Odds: [3.2, 3.3, 3.4, 3.6, 3.5, 3.3, 3.1, 2.9],
                                drawOdds: [3.1, 3.2, 3.3, 3.4, 3.3, 3.2, 3.0, 3.1]
                            }};

                            charts.odds = new Chart(ctx, {{
                                type: 'line',
                                data: {{
                                    labels: oddsData.labels,
                                    datasets: [
                                        {{
                                            label: '{team1} Victoire',
                                            data: oddsData.team1Odds,
                                            borderColor: colors.team1[0],
                                            backgroundColor: colors.team1[1],
                                            tension: 0.4,
                                            fill: false
                                        }},
                                        {{
                                            label: '{team2} Victoire',
                                            data: oddsData.team2Odds,
                                            borderColor: colors.team2[0],
                                            backgroundColor: colors.team2[1],
                                            tension: 0.4,
                                            fill: false
                                        }},
                                        {{
                                            label: 'Match Nul',
                                            data: oddsData.drawOdds,
                                            borderColor: colors.accent[0],
                                            backgroundColor: 'rgba(46, 204, 113, 0.1)',
                                            tension: 0.4,
                                            fill: false
                                        }}
                                    ]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{
                                        title: {{ display: true, text: '💰 Évolution des Cotes en Temps Réel', font: {{ size: 16 }} }},
                                        legend: {{ position: 'top' }}
                                    }},
                                    scales: {{
                                        y: {{
                                            beginAtZero: false,
                                            title: {{ display: true, text: 'Cotes' }}
                                        }},
                                        x: {{
                                            title: {{ display: true, text: 'Temps de jeu' }}
                                        }}
                                    }}
                                }}
                            }});
                            break;

                        case 'predictions':
                            // Graphique radar pour les prédictions
                            const predictionData = {{
                                labels: ['Attaque', 'Défense', 'Milieu', 'Forme', 'Historique', 'Cotes'],
                                team1Values: [
                                    Math.max(0, Math.min(10, (data1.reduce((a,b) => a+b, 0) / data1.length) || 5)),
                                    Math.max(0, Math.min(10, 8 - (data2.reduce((a,b) => a+b, 0) / data2.length) || 3)),
                                    Math.max(0, Math.min(10, (data1[1] || 5))),
                                    Math.max(0, Math.min(10, 7)),
                                    Math.max(0, Math.min(10, 6)),
                                    Math.max(0, Math.min(10, 7))
                                ],
                                team2Values: [
                                    Math.max(0, Math.min(10, (data2.reduce((a,b) => a+b, 0) / data2.length) || 5)),
                                    Math.max(0, Math.min(10, 8 - (data1.reduce((a,b) => a+b, 0) / data1.length) || 3)),
                                    Math.max(0, Math.min(10, (data2[1] || 5))),
                                    Math.max(0, Math.min(10, 6)),
                                    Math.max(0, Math.min(10, 7)),
                                    Math.max(0, Math.min(10, 6))
                                ]
                            }};

                            charts.predictions = new Chart(ctx, {{
                                type: 'radar',
                                data: {{
                                    labels: predictionData.labels,
                                    datasets: [
                                        {{
                                            label: '{team1}',
                                            data: predictionData.team1Values,
                                            borderColor: colors.team1[0],
                                            backgroundColor: colors.team1[1],
                                            pointBackgroundColor: colors.team1[0],
                                            pointBorderColor: '#fff',
                                            pointHoverBackgroundColor: '#fff',
                                            pointHoverBorderColor: colors.team1[0]
                                        }},
                                        {{
                                            label: '{team2}',
                                            data: predictionData.team2Values,
                                            borderColor: colors.team2[0],
                                            backgroundColor: colors.team2[1],
                                            pointBackgroundColor: colors.team2[0],
                                            pointBorderColor: '#fff',
                                            pointHoverBackgroundColor: '#fff',
                                            pointHoverBorderColor: colors.team2[0]
                                        }}
                                    ]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{
                                        title: {{ display: true, text: '🎯 Analyse Prédictive Multi-Facteurs', font: {{ size: 16 }} }},
                                        legend: {{ position: 'top' }}
                                    }},
                                    scales: {{
                                        r: {{
                                            beginAtZero: true,
                                            max: 10,
                                            ticks: {{ stepSize: 2 }}
                                        }}
                                    }}
                                }}
                            }});
                            break;

                        case 'comparison':
                            // Graphique en secteurs pour la comparaison globale
                            const totalTeam1 = data1.reduce((a,b) => a+b, 0) || 1;
                            const totalTeam2 = data2.reduce((a,b) => a+b, 0) || 1;
                            const totalBoth = totalTeam1 + totalTeam2;

                            charts.comparison = new Chart(ctx, {{
                                type: 'doughnut',
                                data: {{
                                    labels: ['{team1}', '{team2}', 'Équilibré'],
                                    datasets: [{{
                                        data: [
                                            Math.round((totalTeam1 / totalBoth) * 100),
                                            Math.round((totalTeam2 / totalBoth) * 100),
                                            Math.round(Math.abs(totalTeam1 - totalTeam2) / totalBoth * 20)
                                        ],
                                        backgroundColor: [
                                            colors.team1[0],
                                            colors.team2[0],
                                            colors.accent[1]
                                        ],
                                        borderWidth: 3,
                                        borderColor: '#fff'
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{
                                        title: {{ display: true, text: '⚖️ Répartition des Forces', font: {{ size: 16 }} }},
                                        legend: {{ position: 'bottom' }},
                                        tooltip: {{
                                            callbacks: {{
                                                label: function(context) {{
                                                    return context.label + ': ' + context.parsed + '%';
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }});
                            break;

                        case 'aiPredictions':
                            // Système de prédiction IA unifié
                            const aiData = generateUnifiedAIPredictions(data1, data2);

                            charts.aiPredictions = new Chart(ctx, {{
                                type: 'bar',
                                data: {{
                                    labels: ['Statistique', 'Analyse Cotes', 'Machine Learning', 'Analyse Forme', 'CONSENSUS IA'],
                                    datasets: [
                                        {{
                                            label: 'Probabilité {team1} (%)',
                                            data: aiData.team1Probabilities,
                                            backgroundColor: colors.team1[0],
                                            borderColor: colors.team1[0],
                                            borderWidth: 2
                                        }},
                                        {{
                                            label: 'Probabilité {team2} (%)',
                                            data: aiData.team2Probabilities,
                                            backgroundColor: colors.team2[0],
                                            borderColor: colors.team2[0],
                                            borderWidth: 2
                                        }},
                                        {{
                                            label: 'Probabilité Match Nul (%)',
                                            data: aiData.drawProbabilities,
                                            backgroundColor: colors.accent[0],
                                            borderColor: colors.accent[0],
                                            borderWidth: 2
                                        }}
                                    ]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{
                                        title: {{ display: true, text: '🤖 Délibération Collective - Tous les Systèmes Votent Ensemble', font: {{ size: 16 }} }},
                                        legend: {{ position: 'top' }}
                                    }},
                                    scales: {{
                                        y: {{
                                            beginAtZero: true,
                                            max: 100,
                                            title: {{ display: true, text: 'Probabilité (%)' }}
                                        }}
                                    }},
                                    animation: {{
                                        duration: 2000,
                                        easing: 'easeInOutQuart'
                                    }}
                                }}
                            }});

                            // Afficher le résumé unifié des prédictions
                            displayPredictionSummary(aiData);
                            break;

                        case 'scenarios':
                            // Simulation de scénarios de match
                            const scenarioData = runMatchSimulation();

                            charts.scenarios = new Chart(ctx, {{
                                type: 'line',
                                data: {{
                                    labels: scenarioData.timeline,
                                    datasets: [
                                        {{
                                            label: 'Probabilité Victoire {team1}',
                                            data: scenarioData.team1Evolution,
                                            borderColor: colors.team1[0],
                                            backgroundColor: colors.team1[1],
                                            tension: 0.4,
                                            fill: true
                                        }},
                                        {{
                                            label: 'Probabilité Victoire {team2}',
                                            data: scenarioData.team2Evolution,
                                            borderColor: colors.team2[0],
                                            backgroundColor: colors.team2[1],
                                            tension: 0.4,
                                            fill: true
                                        }}
                                    ]
                                }},
                                options: {{
                                    responsive: true,
                                    plugins: {{
                                        title: {{ display: true, text: '🎲 Évolution des Probabilités en Temps Réel', font: {{ size: 16 }} }},
                                        legend: {{ position: 'top' }}
                                    }},
                                    scales: {{
                                        y: {{
                                            beginAtZero: true,
                                            max: 100,
                                            title: {{ display: true, text: 'Probabilité (%)' }}
                                        }},
                                        x: {{
                                            title: {{ display: true, text: 'Temps de jeu (minutes)' }}
                                        }}
                                    }}
                                }}
                            }});
                            break;
                    }}
                }}

                // Système de prédiction IA unifié
                function generateUnifiedAIPredictions(data1, data2) {{
                    const total1 = data1.reduce((a,b) => a+b, 0) || 1;
                    const total2 = data2.reduce((a,b) => a+b, 0) || 1;

                    // Système 1: Algorithme statistique
                    const statProb1 = Math.min(85, Math.max(15, (total1 / (total1 + total2)) * 100));
                    const statProb2 = Math.min(85, Math.max(15, (total2 / (total1 + total2)) * 100));
                    const statDraw = Math.max(10, 100 - statProb1 - statProb2);

                    // Système 2: Analyse des cotes (simulation)
                    const oddsProb1 = Math.min(80, Math.max(20, statProb1 + Math.random() * 20 - 10));
                    const oddsProb2 = Math.min(80, Math.max(20, statProb2 + Math.random() * 20 - 10));
                    const oddsDraw = Math.max(15, 100 - oddsProb1 - oddsProb2);

                    // Système 3: Machine Learning (simulation avancée)
                    const mlProb1 = Math.min(90, Math.max(10, statProb1 + Math.random() * 30 - 15));
                    const mlProb2 = Math.min(90, Math.max(10, statProb2 + Math.random() * 30 - 15));
                    const mlDraw = Math.max(5, 100 - mlProb1 - mlProb2);

                    // Système 4: Analyse de forme (simulation)
                    const formeProb1 = Math.min(85, Math.max(15, statProb1 + Math.random() * 25 - 12.5));
                    const formeProb2 = Math.min(85, Math.max(15, statProb2 + Math.random() * 25 - 12.5));
                    const formeDraw = Math.max(10, 100 - formeProb1 - formeProb2);

                    // Consensus IA unifié (moyenne pondérée avec poids optimisés)
                    const consensusProb1 = (statProb1 * 0.25 + oddsProb1 * 0.35 + mlProb1 * 0.25 + formeProb1 * 0.15);
                    const consensusProb2 = (statProb2 * 0.25 + oddsProb2 * 0.35 + mlProb2 * 0.25 + formeProb2 * 0.15);
                    const consensusDraw = (statDraw * 0.25 + oddsDraw * 0.35 + mlDraw * 0.25 + formeDraw * 0.15);

                    // Identifier les 2 meilleures options
                    const options = [
                        {{ name: '{team1}', prob: consensusProb1, type: 'team1' }},
                        {{ name: '{team2}', prob: consensusProb2, type: 'team2' }},
                        {{ name: 'Match Nul', prob: consensusDraw, type: 'draw' }}
                    ].sort((a, b) => b.prob - a.prob);

                    const option1 = options[0];
                    const option2 = options[1];

                    return {{
                        team1Probabilities: [statProb1, oddsProb1, mlProb1, formeProb1, consensusProb1],
                        team2Probabilities: [statProb2, oddsProb2, mlProb2, formeProb2, consensusProb2],
                        drawProbabilities: [statDraw, oddsDraw, mlDraw, formeDraw, consensusDraw],
                        consensus: {{
                            team1: consensusProb1,
                            team2: consensusProb2,
                            draw: consensusDraw,
                            confidence: Math.min(95, Math.max(60, 75 + Math.random() * 20))
                        }},
                        topOptions: {{
                            option1: {{ ...option1, confidence: Math.min(95, option1.prob * 0.9) }},
                            option2: {{ ...option2, confidence: Math.min(90, option2.prob * 0.85) }}
                        }}
                    }};
                }}

                // Fonction de compatibilité (garde l'ancien nom)
                function generateAIPredictions(data1, data2) {{
                    return generateUnifiedAIPredictions(data1, data2);
                }}

                function displayPredictionSummary(aiData) {{
                    const summary = document.getElementById('predictionSummary');

                    // Vérifier si nous avons les nouvelles données unifiées
                    if (aiData.topOptions) {{
                        displayUnifiedPredictionSummary(aiData);
                        return;
                    }}

                    // Affichage classique pour compatibilité
                    const winner = aiData.consensus.team1 > aiData.consensus.team2 ? '{team1}' : '{team2}';
                    const winnerProb = Math.max(aiData.consensus.team1, aiData.consensus.team2);

                    summary.innerHTML = `
                        <div class="prediction-item">
                            <span class="prediction-label">🏆 Vainqueur Prédit:</span>
                            <span class="prediction-value">${{winner}} (${{winnerProb.toFixed(1)}}%)</span>
                        </div>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${{aiData.consensus.confidence}}%"></div>
                        </div>
                        <div class="prediction-item">
                            <span class="prediction-label">🎯 Confiance IA:</span>
                            <span class="prediction-value">${{aiData.consensus.confidence.toFixed(1)}}%</span>
                        </div>
                        <div class="prediction-item">
                            <span class="prediction-label">⚖️ Probabilité Match Nul:</span>
                            <span class="prediction-value">${{aiData.consensus.draw.toFixed(1)}}%</span>
                        </div>
                    `;
                }}

                function displayUnifiedPredictionSummary(aiData) {{
                    const summary = document.getElementById('predictionSummary');

                    // Simuler une décision collective des systèmes
                    const collectiveDecision = simulateCollectiveDecision(aiData);

                    summary.innerHTML = `
                        <div style="text-align: center; margin-bottom: 20px;">
                            <h4 style="color: white; margin-bottom: 15px;">🤖 DÉCISION COLLECTIVE DES SYSTÈMES IA</h4>
                            <p style="font-size: 14px; opacity: 0.9; margin: 0;">Tous les algorithmes délibèrent ensemble pour une décision unique</p>
                        </div>

                        <div class="prediction-item" style="background: rgba(255,255,255,0.15); border-radius: 12px; margin-bottom: 15px; padding: 15px;">
                            <div style="text-align: center; margin-bottom: 10px;">
                                <span style="font-size: 24px;">${{collectiveDecision.icon}}</span>
                                <h5 style="color: white; margin: 5px 0;">${{collectiveDecision.status}}</h5>
                            </div>

                            <div style="text-align: center; margin-bottom: 15px;">
                                <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">
                                    ${{collectiveDecision.decision}}
                                </div>
                                <div style="font-size: 14px; opacity: 0.9;">
                                    Cote: ${{collectiveDecision.odds}} | Confiance: ${{collectiveDecision.confidence}}%
                                </div>
                            </div>

                            <div class="confidence-bar" style="margin: 10px 0;">
                                <div class="confidence-fill" style="width: ${{collectiveDecision.confidence}}%; background: ${{collectiveDecision.confidenceColor}};"></div>
                            </div>

                            <div style="text-align: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.3);">
                                <div style="font-weight: bold; margin-bottom: 8px;">🎯 ACTION RECOMMANDÉE:</div>
                                <div style="font-size: 16px; color: ${{collectiveDecision.actionColor}};">
                                    ${{collectiveDecision.action}}
                                </div>
                            </div>
                        </div>

                        <div class="prediction-item" style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 12px;">
                            <div style="text-align: center; margin-bottom: 10px;">
                                <strong>📊 VOTES DES SYSTÈMES:</strong>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 14px;">
                                ${{collectiveDecision.votes.map(vote => `
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span>${{vote.system}}:</span>
                                        <span>${{vote.vote}}</span>
                                    </div>
                                `).join('')}}
                            </div>
                        </div>
                    `;
                }}

                function simulateCollectiveDecision(aiData) {{
                    const option1 = aiData.topOptions.option1;
                    const option2 = aiData.topOptions.option2;

                    // Simuler les votes des 4 systèmes
                    const systems = ['Statistique', 'Cotes', 'ML', 'Forme'];
                    const votes = [];
                    let votesForOption1 = 0;

                    systems.forEach(system => {{
                        // Probabilité de voter pour option1 basée sur sa probabilité
                        const voteForOption1 = Math.random() < (option1.prob / 100);
                        if (voteForOption1) {{
                            votesForOption1++;
                            votes.push({{ system, vote: `✅ ${{option1.name}}` }});
                        }} else {{
                            votes.push({{ system, vote: `🔄 ${{option2.name}}` }});
                        }}
                    }});

                    // Déterminer le type de consensus
                    let status, icon, confidence, confidenceColor, action, actionColor;

                    if (votesForOption1 >= 4) {{
                        status = "CONSENSUS UNANIME";
                        icon = "🎯";
                        confidence = Math.min(95, option1.confidence + 15);
                        confidenceColor = "linear-gradient(90deg, #27ae60, #2ecc71)";
                        action = "MISE FORTEMENT RECOMMANDÉE";
                        actionColor = "#27ae60";
                    }} else if (votesForOption1 >= 3) {{
                        status = "MAJORITÉ FORTE";
                        icon = "✅";
                        confidence = Math.min(90, option1.confidence + 10);
                        confidenceColor = "linear-gradient(90deg, #2980b9, #3498db)";
                        action = "MISE RECOMMANDÉE";
                        actionColor = "#2980b9";
                    }} else if (votesForOption1 >= 2) {{
                        status = "MAJORITÉ SIMPLE";
                        icon = "⚖️";
                        confidence = Math.min(75, option1.confidence);
                        confidenceColor = "linear-gradient(90deg, #f39c12, #e67e22)";
                        action = "MISE MODÉRÉE";
                        actionColor = "#f39c12";
                    }} else {{
                        status = "SYSTÈMES DIVISÉS";
                        icon = "🤔";
                        confidence = Math.min(60, Math.max(option1.confidence, option2.confidence));
                        confidenceColor = "linear-gradient(90deg, #e74c3c, #c0392b)";
                        action = "PRUDENCE RECOMMANDÉE";
                        actionColor = "#e74c3c";
                    }}

                    const chosenOption = votesForOption1 >= 2 ? option1 : option2;

                    return {{
                        status,
                        icon,
                        decision: chosenOption.name,
                        odds: chosenOption.prob ? (1 / (chosenOption.prob / 100)).toFixed(2) : 'N/A',
                        confidence: confidence.toFixed(1),
                        confidenceColor,
                        action,
                        actionColor,
                        votes
                    }};
                }}

                function getRecommendationText(option1, option2) {{
                    const diff = option1.prob - option2.prob;

                    if (diff > 25) {{
                        return `Mise principale sur ${{option1.name}}`;
                    }} else if (diff > 15) {{
                        return `Favoriser ${{option1.name}}, surveiller ${{option2.name}}`;
                    }} else if (diff > 8) {{
                        return `Combinaison équilibrée possible`;
                    }} else {{
                        return `Match très ouvert, prudence recommandée`;
                    }}
                }}

                function runMatchSimulation() {{
                    const timeline = [];
                    const team1Evolution = [];
                    const team2Evolution = [];

                    // Simulation minute par minute
                    for (let minute = 0; minute <= 90; minute += 10) {{
                        timeline.push(minute);

                        // Facteurs d'évolution
                        const fatigue = minute / 90;
                        const pressure = minute > 70 ? (minute - 70) / 20 : 0;

                        // Probabilités évolutives
                        let prob1 = 45 + Math.sin(minute / 30) * 15 + Math.random() * 10 - 5;
                        let prob2 = 35 + Math.cos(minute / 25) * 10 + Math.random() * 10 - 5;

                        // Ajustements selon le contexte
                        if (minute > 60) {{
                            prob1 += pressure * 10;
                            prob2 -= fatigue * 5;
                        }}

                        team1Evolution.push(Math.min(80, Math.max(20, prob1)));
                        team2Evolution.push(Math.min(80, Math.max(20, prob2)));
                    }}

                    return {{ timeline, team1Evolution, team2Evolution }};
                }}

                function runSimulation() {{
                    if (charts.scenarios) {{
                        charts.scenarios.destroy();
                        createChart('scenarios');
                    }}
                }}

                function showProbabilities() {{
                    const finalProb1 = charts.scenarios.data.datasets[0].data.slice(-1)[0];
                    const finalProb2 = charts.scenarios.data.datasets[1].data.slice(-1)[0];
                    const drawProb = 100 - finalProb1 - finalProb2;

                    alert(`📊 Probabilités Finales:\\n\\n🔵 {team1}: ${{finalProb1.toFixed(1)}}%\\n🔴 {team2}: ${{finalProb2.toFixed(1)}}%\\n⚪ Match Nul: ${{drawProb.toFixed(1)}}%`);
                }}

                // Fonction pour changer de catégorie de prédiction
                function showPredictionCategory(category) {{
                    // Masquer tous les conteneurs
                    document.querySelectorAll('.prediction-container').forEach(c => c.classList.remove('active'));
                    document.querySelectorAll('.pred-tab-btn').forEach(b => b.classList.remove('active'));

                    // Afficher le conteneur sélectionné
                    document.getElementById(category + '-container').classList.add('active');
                    event.target.classList.add('active');
                }}

                // Données des prédictions générées côté serveur (toutes les prédictions pour le centre spécialisé)
                const predictionsData = [
                    {''.join([f'''{{
                        nom: "{p['nom']}",
                        valeur: "{p['valeur']}",
                        cote: {p['cote']}
                    }},''' for p in paris_alternatifs])}
                ];

                // Fonction pour organiser les prédictions par catégorie
                function organizePredictions() {{
                    console.log('📊 Données de prédictions:', predictionsData);

                    // Catégoriser les prédictions
                    const categories = {{
                        'pair-impair': [],
                        'corners': [],
                        'mi-temps': [],
                        'handicaps': [],
                        'totaux': [],
                        'autres': []
                    }};

                    predictionsData.forEach(pred => {{
                        const nom = pred.nom.toLowerCase();
                        console.log('🔍 Analyse prédiction:', nom);

                        // Catégorisation améliorée
                        if (nom.includes('pair') || nom.includes('impair')) {{
                            categories['pair-impair'].push(pred);
                            console.log('✅ Pair/Impair:', nom);
                        }} else if (nom.includes('corner')) {{
                            categories['corners'].push(pred);
                            console.log('✅ Corners:', nom);
                        }} else if (nom.includes('mi-temps') || nom.includes('mi temps') || nom.includes('(1ère') || nom.includes('(2ème') || nom.includes('première') || nom.includes('deuxième')) {{
                            categories['mi-temps'].push(pred);
                            console.log('✅ Mi-temps:', nom);
                        }} else if (nom.includes('handicap')) {{
                            categories['handicaps'].push(pred);
                            console.log('✅ Handicap:', nom);
                        }} else if (nom.includes('plus de') || nom.includes('moins de') || nom.includes('over') || nom.includes('under') || (nom.includes('total') && nom.includes('but'))) {{
                            categories['totaux'].push(pred);
                            console.log('✅ Totaux:', nom);
                        }} else {{
                            categories['autres'].push(pred);
                            console.log('✅ Autres:', nom);
                        }}
                    }});

                    // Remplir chaque catégorie
                    Object.keys(categories).forEach(category => {{
                        const container = document.getElementById(category + '-content');
                        if (container) {{
                            if (categories[category].length === 0) {{
                                container.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #666; font-style: italic;">Aucune prédiction disponible pour cette catégorie</td></tr>';
                            }} else {{
                                container.innerHTML = categories[category].map(pred => {{
                                    const probability = calculateProbability(pred.cote);
                                    const badge = getProbabilityBadge(probability);
                                    const predictionText = generateSmartPrediction(pred, '{team1}', '{team2}');

                                    return `
                                        <tr>
                                            <td><strong>${{pred.nom}}</strong></td>
                                            <td>${{pred.valeur || '–'}}</td>
                                            <td><span style="font-weight: bold; color: #2980b9;">${{pred.cote}}</span></td>
                                            <td>${{predictionText}}</td>
                                            <td>
                                                <div class="probability-bar">
                                                    <div class="probability-fill" style="width: ${{probability}}%"></div>
                                                </div>
                                                <span class="prediction-badge ${{badge.class}}">${{probability.toFixed(1)}}%</span>
                                            </td>
                                        </tr>
                                    `;
                                }}).join('');
                            }}
                        }}
                    }});

                    // Afficher le nombre de prédictions par catégorie dans les onglets
                    Object.keys(categories).forEach(category => {{
                        const tabBtn = document.querySelector(`[onclick="showPredictionCategory('${{category}}')"]`);
                        if (tabBtn) {{
                            const count = categories[category].length;
                            const originalText = tabBtn.textContent.split(' (')[0];
                            tabBtn.textContent = `${{originalText}} (${{count}})`;
                        }}
                    }});
                }}

                // Calculer la probabilité basée sur la cote
                function calculateProbability(cote) {{
                    return Math.min(95, Math.max(5, (1 / parseFloat(cote)) * 100));
                }}

                // Obtenir le badge de probabilité
                function getProbabilityBadge(probability) {{
                    if (probability >= 70) return {{ class: 'badge-high', text: 'Élevée' }};
                    if (probability >= 40) return {{ class: 'badge-medium', text: 'Moyenne' }};
                    return {{ class: 'badge-low', text: 'Faible' }};
                }}

                // Générer une prédiction intelligente
                function generateSmartPrediction(pred, team1, team2) {{
                    const nom = pred.nom.toLowerCase();
                    const cote = parseFloat(pred.cote);

                    if (nom.includes('pair')) {{
                        return cote < 2.0 ? "🔢 Résultat pair très probable" : "🔢 Résultat pair possible";
                    }} else if (nom.includes('impair')) {{
                        return cote < 2.0 ? "🔢 Résultat impair très probable" : "🔢 Résultat impair possible";
                    }} else if (nom.includes('corner')) {{
                        return cote < 2.0 ? "⚽ Prédiction corners favorable" : "⚽ Prédiction corners risquée";
                    }} else if (nom.includes('mi-temps')) {{
                        return cote < 2.5 ? "⏰ Prédiction mi-temps solide" : "⏰ Prédiction mi-temps incertaine";
                    }} else if (nom.includes('handicap')) {{
                        return cote < 2.0 ? "⚖️ Handicap avantageux" : "⚖️ Handicap risqué";
                    }} else if (nom.includes('plus de') || nom.includes('moins de')) {{
                        return cote < 1.8 ? "📊 Prédiction totaux très fiable" : "📊 Prédiction totaux modérée";
                    }}

                    return cote < 2.0 ? "✅ Prédiction favorable" : "⚠️ Prédiction risquée";
                }}

                // Initialiser le premier graphique et les prédictions
                document.addEventListener('DOMContentLoaded', function() {{
                    createChart('stats');
                    organizePredictions();
                    updateUnifiedPreview();
                    startAutoRefreshDetails();
                }});

                // Mettre à jour l'aperçu unifié avec décision collective
                function updateUnifiedPreview() {{
                    const preview = document.getElementById('unified-prediction-preview');
                    if (!preview) return;

                    // Simuler l'analyse collective
                    setTimeout(() => {{
                        const aiData = generateUnifiedAIPredictions(data1, data2);
                        const collectiveDecision = simulateCollectiveDecision(aiData);

                        preview.innerHTML = `
                            <div style="text-align: center; margin-bottom: 15px;">
                                <div style="font-size: 32px; margin-bottom: 8px;">${{collectiveDecision.icon}}</div>
                                <div style="font-size: 16px; font-weight: bold; margin-bottom: 5px;">
                                    ${{collectiveDecision.status}}
                                </div>
                                <div style="font-size: 18px; font-weight: bold; color: #fff;">
                                    ${{collectiveDecision.decision}}
                                </div>
                            </div>

                            <div style="display: flex; justify-content: space-around; align-items: center; margin: 15px 0; font-size: 14px;">
                                <div>
                                    <strong>Cote:</strong> ${{collectiveDecision.odds}}
                                </div>
                                <div>
                                    <strong>Confiance:</strong> ${{collectiveDecision.confidence}}%
                                </div>
                            </div>

                            <div style="margin: 15px 0;">
                                <div style="background: rgba(255,255,255,0.2); border-radius: 10px; height: 8px; overflow: hidden;">
                                    <div style="height: 100%; background: ${{collectiveDecision.confidenceColor}}; width: ${{collectiveDecision.confidence}}%; transition: width 1s ease;"></div>
                                </div>
                            </div>

                            <div style="text-align: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.3);">
                                <div style="font-size: 14px; font-weight: bold; color: ${{collectiveDecision.actionColor}};">
                                    🎯 ${{collectiveDecision.action}}
                                </div>
                            </div>
                        `;
                    }}, 1500);
                }}

                // Système de rafraîchissement automatique pour la page de détails
                let detailsRefreshInterval;
                let isRefreshingDetails = false;

                async function silentRefreshDetails() {{
                    if (isRefreshingDetails) return;
                    isRefreshingDetails = true;

                    try {{
                        // Récupérer l'ID du match depuis l'URL
                        const pathParts = window.location.pathname.split('/');
                        const matchId = pathParts[pathParts.length - 1];

                        // Faire la requête AJAX optimisée pour les détails
                        const response = await fetch(`/match/${{matchId}}`, {{
                            method: 'GET',
                            headers: {{
                                'X-Requested-With': 'XMLHttpRequest',
                                'Cache-Control': 'no-cache, no-store, must-revalidate',
                                'Pragma': 'no-cache',
                                'Expires': '0',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                            }},
                            cache: 'no-store',
                            credentials: 'same-origin',
                            timeout: 10000
                        }});

                        if (response.ok) {{
                            const newContent = await response.text();

                            // Parser le nouveau contenu
                            const parser = new DOMParser();
                            const newDoc = parser.parseFromString(newContent, 'text/html');

                            // Mettre à jour les éléments dynamiques
                            updateMatchDetails(newDoc);

                            // Indicateur visuel discret
                            showDetailsRefreshIndicator();
                        }}
                    }} catch (error) {{
                        console.log('Rafraîchissement détails échoué:', error);
                    }} finally {{
                        isRefreshingDetails = false;
                    }}
                }}

                function updateMatchDetails(newDoc) {{
                    // Mettre à jour le score (chercher dans le titre h1)
                    const currentTitle = document.querySelector('h1');
                    const newTitle = newDoc.querySelector('h1');
                    if (currentTitle && newTitle && currentTitle.textContent !== newTitle.textContent) {{
                        currentTitle.textContent = newTitle.textContent;
                        currentTitle.style.animation = 'pulse 0.5s ease-in-out';
                    }}

                    // Mettre à jour les informations du match
                    const currentMatchInfo = document.querySelector('.match-info');
                    const newMatchInfo = newDoc.querySelector('.match-info');
                    if (currentMatchInfo && newMatchInfo) {{
                        currentMatchInfo.innerHTML = newMatchInfo.innerHTML;
                    }}

                    // Mettre à jour les cotes principales (chercher dans le contenu)
                    const currentOddsSection = document.querySelector('h3:contains("Cotes principales")');
                    const newOddsSection = newDoc.querySelector('h3:contains("Cotes principales")');
                    if (currentOddsSection && newOddsSection) {{
                        const currentOddsContent = currentOddsSection.nextElementSibling;
                        const newOddsContent = newOddsSection.nextElementSibling;
                        if (currentOddsContent && newOddsContent) {{
                            currentOddsContent.innerHTML = newOddsContent.innerHTML;
                        }}
                    }}

                    // Mettre à jour le tableau des paris alternatifs
                    const currentAltTable = document.querySelector('.alt-table');
                    const newAltTable = newDoc.querySelector('.alt-table');
                    if (currentAltTable && newAltTable) {{
                        currentAltTable.innerHTML = newAltTable.innerHTML;
                    }}

                    // Mettre à jour les statistiques et recréer les graphiques
                    const currentStatsTable = document.querySelector('table');
                    const newStatsTable = newDoc.querySelector('table');
                    if (currentStatsTable && newStatsTable) {{
                        // Extraire les nouvelles données pour les graphiques
                        const newRows = newStatsTable.querySelectorAll('tr');
                        if (newRows.length > 1) {{
                            // Recréer tous les graphiques avec les nouvelles données
                            Object.keys(charts).forEach(chartKey => {{
                                if (charts[chartKey]) {{
                                    charts[chartKey].destroy();
                                    delete charts[chartKey];
                                }}
                            }});

                            // Recréer le graphique actuel
                            const activeTab = document.querySelector('.tab-btn.active');
                            if (activeTab) {{
                                const chartType = activeTab.onclick.toString().match(/showChart\('(.+?)'\)/)[1];
                                createChart(chartType);
                            }}
                        }}
                    }}
                }}

                function showDetailsRefreshIndicator() {{
                    const indicator = document.createElement('div');
                    indicator.style.cssText = `
                        position: fixed;
                        top: 10px;
                        right: 10px;
                        background: rgba(52, 152, 219, 0.9);
                        color: white;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 12px;
                        z-index: 9999;
                        opacity: 0;
                        transition: opacity 0.3s ease;
                    `;
                    indicator.textContent = '📊 Données mises à jour';
                    document.body.appendChild(indicator);

                    // Animation d'apparition/disparition
                    setTimeout(() => indicator.style.opacity = '1', 10);
                    setTimeout(() => {{
                        indicator.style.opacity = '0';
                        setTimeout(() => document.body.removeChild(indicator), 300);
                    }}, 2000);
                }}

                function startAutoRefreshDetails() {{
                    if (detailsRefreshInterval) {{
                        clearInterval(detailsRefreshInterval);
                    }}
                    detailsRefreshInterval = setInterval(silentRefreshDetails, 5000); // 5 secondes
                }}

                function stopAutoRefreshDetails() {{
                    if (detailsRefreshInterval) {{
                        clearInterval(detailsRefreshInterval);
                        detailsRefreshInterval = null;
                    }}
                }}

                // Gestion de la visibilité de la page
                document.addEventListener('visibilitychange', function() {{
                    if (document.hidden) {{
                        stopAutoRefreshDetails();
                    }} else {{
                        startAutoRefreshDetails();
                    }}
                }});

                // Arrêter avant de quitter la page
                window.addEventListener('beforeunload', function() {{
                    stopAutoRefreshDetails();
                }});
            </script>

            <style>
                @keyframes pulse {{
                    0% {{ transform: scale(1); }}
                    50% {{ transform: scale(1.05); }}
                    100% {{ transform: scale(1); }}
                }}
            </style>
        </body></html>
        '''
    except Exception as e:
        return f"Erreur lors de l'affichage des détails du match : {e}"

TEMPLATE = """<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Live Football & Sports | Prédictions & Stats</title>
    <link rel="icon" type="image/png" href="https://cdn-icons-png.flaticon.com/512/197/197604.png">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f4f4f4; }
        h2 { text-align: center; }
        form { text-align: center; margin-bottom: 20px; }
        label { font-weight: bold; margin-right: 10px; }
        select { padding: 12px; margin: 0 10px; font-size: 16px; border-radius: 6px; border: 1px solid #2c3e50; background: #fff; color: #2c3e50; }
        select:focus { outline: 2px solid #2980b9; }
        table { border-collapse: collapse; margin: auto; width: 98%; background: white; }
        th, td { padding: 14px; border: 1.5px solid #2c3e50; text-align: center; font-size: 16px; }
        th { background: #1a252f; color: #fff; font-size: 18px; }
        tr:nth-child(even) { background-color: #eaf6fb; }
        tr:nth-child(odd) { background-color: #f9f9f9; }
        .pagination { text-align: center; margin: 20px 0; }
        .pagination button { padding: 14px 24px; margin: 0 6px; font-size: 18px; border: none; background: #2980b9; color: #fff; border-radius: 6px; cursor: pointer; font-weight: bold; transition: background 0.2s; }
        .pagination button:disabled { background: #b2bec3; color: #636e72; cursor: not-allowed; }
        .pagination button:focus { outline: 2px solid #27ae60; }
        /* Responsive */
        @media (max-width: 800px) {
            table, thead, tbody, th, td, tr { display: block; }
            th { position: absolute; left: -9999px; top: -9999px; }
            tr { margin-bottom: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 6px #ccc; }
            td { border: none; border-bottom: 1px solid #eee; position: relative; padding-left: 50%; min-height: 40px; font-size: 16px; }
            td:before { position: absolute; top: 10px; left: 10px; width: 45%; white-space: nowrap; font-weight: bold; color: #2980b9; }
            td:nth-of-type(1):before { content: 'Équipe 1'; }
            td:nth-of-type(2):before { content: 'Score 1'; }
            td:nth-of-type(3):before { content: 'Score 2'; }
            td:nth-of-type(4):before { content: 'Équipe 2'; }
            td:nth-of-type(5):before { content: 'Sport'; }
            td:nth-of-type(6):before { content: 'Ligue'; }
            td:nth-of-type(7):before { content: 'Statut'; }
            td:nth-of-type(8):before { content: 'Date & Heure'; }
            td:nth-of-type(9):before { content: 'Température'; }
            td:nth-of-type(10):before { content: 'Humidité'; }
            td:nth-of-type(11):before { content: 'Cotes'; }
            td:nth-of-type(12):before { content: 'Prédiction'; }
            td:nth-of-type(13):before { content: 'Détails'; }
        }
        /* Loader */
        #loader { display: none; position: fixed; left: 0; top: 0; width: 100vw; height: 100vh; background: rgba(255,255,255,0.7); z-index: 9999; justify-content: center; align-items: center; }
        #loader .spinner { border: 8px solid #f3f3f3; border-top: 8px solid #2980b9; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        /* Focus visible for accessibility */
        a:focus, button:focus, select:focus { outline: 2px solid #27ae60; }
        .contact-box { background: #ff1744; border: 4px solid #ff1744; border-radius: 16px; margin: 40px auto 0 auto; padding: 28px; text-align: center; font-size: 22px; font-weight: bold; color: #fff; max-width: 650px; box-shadow: 0 0 24px 8px #ff1744, 0 0 60px 10px #fff3; text-shadow: 0 0 8px #fff, 0 0 16px #ff1744; letter-spacing: 1px; }
        .contact-box a { color: #fff; font-weight: bold; text-decoration: underline; font-size: 26px; text-shadow: 0 0 8px #fff, 0 0 16px #ff1744; }
        .contact-box .icon { font-size: 32px; vertical-align: middle; margin-right: 10px; filter: drop-shadow(0 0 6px #fff); }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            var forms = document.querySelectorAll('form');
            forms.forEach(function(form) {
                form.addEventListener('submit', function() {
                    document.getElementById('loader').style.display = 'flex';
                });
            });
        });
    </script>
</head><body>
    <div id="loader" role="status" aria-live="polite"><div class="spinner" aria-label="Chargement"></div></div>
    <h2>📊 Matchs en direct — {{ selected_sport }} / {{ selected_league }} / {{ selected_status }}</h2>

    <form method="get" aria-label="Filtres de matchs">
        <label for="sport-select">Sport :</label>
        <select id="sport-select" name="sport" onchange="this.form.submit()" aria-label="Filtrer par sport">
            <option value="">Tous</option>
            {% for s in sports %}
                <option value="{{s}}" {% if s == selected_sport %}selected{% endif %}>{{s}}</option>
            {% endfor %}
        </select>
        <label for="league-select">Ligue :</label>
        <select id="league-select" name="league" onchange="this.form.submit()" aria-label="Filtrer par ligue">
            <option value="">Toutes</option>
            {% for l in leagues %}
                <option value="{{l}}" {% if l == selected_league %}selected{% endif %}>{{l}}</option>
            {% endfor %}
        </select>
        <label for="status-select">Statut :</label>
        <select id="status-select" name="status" onchange="this.form.submit()" aria-label="Filtrer par statut">
            <option value="">Tous</option>
            <option value="live" {% if selected_status == "live" %}selected{% endif %}>En direct</option>
            <option value="upcoming" {% if selected_status == "upcoming" %}selected{% endif %}>À venir</option>
            <option value="finished" {% if selected_status == "finished" %}selected{% endif %}>Terminé</option>
        </select>
    </form>

    <div class="pagination">
        <form method="get" style="display:inline;" aria-label="Page précédente">
            <input type="hidden" name="sport" value="{{ selected_sport if selected_sport != 'Tous' else '' }}">
            <input type="hidden" name="league" value="{{ selected_league if selected_league != 'Toutes' else '' }}">
            <input type="hidden" name="status" value="{{ selected_status if selected_status != 'Tous' else '' }}">
            <button type="submit" name="page" value="{{ page-1 }}" {% if page <= 1 %}disabled{% endif %} aria-label="Page précédente">Page précédente</button>
        </form>
        <span aria-live="polite">Page {{ page }} / {{ total_pages }}</span>
        <form method="get" style="display:inline;" aria-label="Page suivante">
            <input type="hidden" name="sport" value="{{ selected_sport if selected_sport != 'Tous' else '' }}">
            <input type="hidden" name="league" value="{{ selected_league if selected_league != 'Toutes' else '' }}">
            <input type="hidden" name="status" value="{{ selected_status if selected_status != 'Tous' else '' }}">
            <button type="submit" name="page" value="{{ page+1 }}" {% if page >= total_pages %}disabled{% endif %} aria-label="Page suivante">Page suivante</button>
        </form>
    </div>

    <table class="matches-table">
        <thead>
            <tr>
                <th>Équipe 1</th><th>Score 1</th><th>Score 2</th><th>Équipe 2</th>
                <th>Sport</th><th>Ligue</th><th>Statut</th><th>Date & Heure</th>
                <th>Température</th><th>Humidité</th><th>Cotes</th><th>Prédiction</th><th>Détails</th>
            </tr>
        </thead>
        <tbody class="matches-content">
            {% for m in data %}
            <tr>
                <td>{{m.team1}}</td><td>{{m.score1}}</td><td>{{m.score2}}</td><td>{{m.team2}}</td>
                <td>{{m.sport}}</td><td>{{m.league}}</td><td>{{m.status}}</td><td>{{m.datetime}}</td>
                <td>{{m.temp}}°C</td><td>{{m.humid}}%</td><td>{{m.odds|join(" | ")}}</td><td>{{m.prediction}}</td>
                <td>{% if m.id %}<a href="/match/{{m.id}}"><button>Détails</button></a>{% else %}–{% endif %}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <div class="contact-box">
        <span class="icon">📬</span> Inbox Telegram : <a href="https://t.me/Roidesombres225" target="_blank">@Roidesombres225</a><br>
        <span class="icon">📢</span> Canal Telegram : <a href="https://t.me/SOLITAIREHACK" target="_blank">SOLITAIREHACK</a><br>
        <span class="icon">🎨</span> Je suis aussi concepteur graphique et créateur de logiciels.<br>
        <span style="color:#d84315; font-size:22px; font-weight:bold;">Vous avez un projet en tête ? Contactez-moi, je suis là pour vous !</span>
    </div>

    <!-- Système de rafraîchissement automatique silencieux -->
    <script>
        let refreshInterval;
        let isRefreshing = false;

        // Fonction de rafraîchissement silencieux
        async function silentRefresh() {
            if (isRefreshing) return;
            isRefreshing = true;

            console.log('🔄 Début du rafraîchissement...'); // Debug

            try {
                // Récupérer les paramètres actuels
                const urlParams = new URLSearchParams(window.location.search);
                const currentPage = urlParams.get('page') || '1';
                const currentSport = urlParams.get('sport') || '';
                const currentLeague = urlParams.get('league') || '';
                const currentStatus = urlParams.get('status') || '';

                // Construire l'URL de rafraîchissement
                const refreshUrl = `/?page=${currentPage}&sport=${currentSport}&league=${currentLeague}&status=${currentStatus}`;

                // Faire la requête AJAX optimisée
                const response = await fetch(refreshUrl, {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    },
                    cache: 'no-store',
                    credentials: 'same-origin'
                });

                if (response.ok) {
                    const newContent = await response.text();
                    console.log('✅ Réponse reçue, taille:', newContent.length); // Debug

                    // Parser le nouveau contenu
                    const parser = new DOMParser();
                    const newDoc = parser.parseFromString(newContent, 'text/html');

                    // Mettre à jour seulement le contenu des matchs
                    const currentMatchesContainer = document.querySelector('.matches-content');
                    const newMatchesContainer = newDoc.querySelector('.matches-content');

                    console.log('🔍 Conteneurs trouvés:', !!currentMatchesContainer, !!newMatchesContainer); // Debug

                    if (currentMatchesContainer && newMatchesContainer) {
                        // Sauvegarder la position de scroll
                        const scrollPosition = window.pageYOffset;

                        // Vérifier si le contenu a changé
                        if (currentMatchesContainer.innerHTML !== newMatchesContainer.innerHTML) {
                            // Remplacer le contenu
                            currentMatchesContainer.innerHTML = newMatchesContainer.innerHTML;
                            console.log('🔄 Contenu mis à jour!'); // Debug

                            // Restaurer la position de scroll
                            window.scrollTo(0, scrollPosition);

                            // Indicateur visuel de succès
                            showRefreshIndicator('success', '🔄 Données mises à jour');
                        } else {
                            console.log('📋 Aucun changement détecté'); // Debug
                        }
                    } else {
                        console.log('❌ Conteneurs non trouvés'); // Debug
                    }
                } else {
                    console.log('❌ Erreur HTTP:', response.status); // Debug
                }
            } catch (error) {
                console.log('❌ Rafraîchissement AJAX échoué:', error);

                // Indicateur d'erreur
                showRefreshIndicator('error', '❌ Erreur de connexion');

                // Mettre à jour le statut de connexion
                const statusIndicator = document.getElementById('connection-status');
                if (statusIndicator) {
                    statusIndicator.style.background = 'rgba(231, 76, 60, 0.8)';
                    statusIndicator.textContent = '🔴 Déconnecté';
                }

                // Retry automatique après 10 secondes en cas d'erreur
                setTimeout(() => {
                    if (!isRefreshing) {
                        console.log('🔄 Tentative de reconnexion...');
                        showRefreshIndicator('loading', '🔄 Reconnexion...');
                        silentRefresh();
                    }
                }, 10000);

            } finally {
                isRefreshing = false;
            }
        }

        // Indicateur visuel avec statut AJAX
        function showRefreshIndicator(type = 'success', message = '🔄 Mis à jour') {
            const indicator = document.createElement('div');

            const colors = {
                success: 'rgba(46, 204, 113, 0.9)',
                error: 'rgba(231, 76, 60, 0.9)',
                loading: 'rgba(52, 152, 219, 0.9)',
                warning: 'rgba(241, 196, 15, 0.9)'
            };

            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: ${colors[type]};
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: bold;
                z-index: 9999;
                opacity: 0;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            `;
            indicator.textContent = message;
            document.body.appendChild(indicator);

            // Animation d'apparition/disparition
            setTimeout(() => indicator.style.opacity = '1', 10);
            setTimeout(() => {
                indicator.style.opacity = '0';
                setTimeout(() => {
                    if (document.body.contains(indicator)) {
                        document.body.removeChild(indicator);
                    }
                }, 300);
            }, type === 'error' ? 3000 : 1500);
        }

        // Indicateur de statut de connexion
        function showConnectionStatus() {
            const statusIndicator = document.createElement('div');
            statusIndicator.id = 'connection-status';
            statusIndicator.style.cssText = `
                position: fixed;
                bottom: 10px;
                right: 10px;
                background: rgba(46, 204, 113, 0.8);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 11px;
                z-index: 9998;
                opacity: 0.7;
            `;
            statusIndicator.textContent = '🟢 Connecté';
            document.body.appendChild(statusIndicator);
        }

        // Démarrer le rafraîchissement automatique
        function startAutoRefresh() {
            // Arrêter le précédent interval s'il existe
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }

            // Démarrer le nouveau cycle de rafraîchissement
            refreshInterval = setInterval(silentRefresh, 5000); // 5 secondes
        }

        // Arrêter le rafraîchissement
        function stopAutoRefresh() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
            }
        }

        // Gestion de la visibilité de la page
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopAutoRefresh();
            } else {
                startAutoRefresh();
            }
        });

        // Démarrer au chargement de la page
        document.addEventListener('DOMContentLoaded', function() {
            showConnectionStatus();
            startAutoRefresh();
        });

        // Arrêter avant de quitter la page
        window.addEventListener('beforeunload', function() {
            stopAutoRefresh();
        });
    </script>
</body></html>"""

def generer_prediction_lisible(nom, valeur, team1, team2):
    """Génère une phrase prédictive claire pour chaque pari, en précisant l'équipe si besoin."""
    # Prédictions pour le TOTAL du match
    if "TOTAL du match" in nom:
        return f"✅ TOTAL MATCH: {nom}"

    # Prédictions spécifiques aux équipes
    if f"pour {team1}" in nom or f"{team1}" in nom:
        return f"🔵 ÉQUIPE {team1}: {nom}"
    if f"pour {team2}" in nom or f"{team2}" in nom:
        return f"🔴 ÉQUIPE {team2}: {nom}"

    # Types de paris avec icônes
    if nom.startswith("Victoire "):
        return f"🏆 VAINQUEUR: {nom}"
    if nom.startswith("Handicap "):
        return f"⚖️ HANDICAP: {nom}"
    if nom.startswith("Plus de") or nom.startswith("Moins de"):
        # Si pas de mention d'équipe, c'est probablement le total
        if team1 not in nom and team2 not in nom:
            return f"⚽ TOTAL BUTS: {nom}"
        return f"⚽ BUTS: {nom}"
    if nom.startswith("Score exact"):
        return f"🎯 SCORE EXACT: {nom} (Pari risqué)"
    if nom.startswith("Double chance"):
        return f"🛡️ SÉCURISÉ: {nom}"
    if nom.startswith("Nombre de buts"):
        return f"📊 STATISTIQUES: {nom}"
    if "PAIR" in nom or "IMPAIR" in nom:
        if "PAIR" in nom:
            return f"🔢 PAIR: {nom} (Résultat: 0, 2, 4, 6...)"
        else:
            return f"🔢 IMPAIR: {nom} (Résultat: 1, 3, 5, 7...)"
    if "corners" in nom.lower():
        return f"⚽ CORNERS: {nom}"
    if "Handicap européen" in nom:
        return f"🇪🇺 HANDICAP EU: {nom}"
    if "mi-temps" in nom.lower() or "Mi-temps" in nom:
        return f"⏰ MI-TEMPS: {nom}"

    return f"📋 AUTRE: {nom}"

# === SYSTÈME DE PRÉDICTION INTELLIGENT SANS HISTORIQUE ===

def calculer_force_equipe(nom_equipe, league):
    """Calcule la force d'une équipe basée sur son nom et sa ligue"""
    nom_lower = nom_equipe.lower()
    league_lower = league.lower()

    # Équipes très fortes (probabilités de marquer: [0, 1, 2, 3, 4+])
    equipes_tres_fortes = [
        "real madrid", "barcelona", "psg", "manchester city", "liverpool",
        "bayern", "juventus", "chelsea", "arsenal", "tottenham"
    ]

    # Équipes fortes
    equipes_fortes = [
        "atletico", "valencia", "sevilla", "milan", "inter", "napoli",
        "dortmund", "leipzig", "lyon", "marseille"
    ]

    # Ligues de haut niveau
    ligues_fortes = ["premier league", "la liga", "serie a", "bundesliga", "ligue 1"]

    if any(forte in nom_lower for forte in equipes_tres_fortes):
        return [5, 15, 30, 35, 15]  # Très offensive
    elif any(forte in nom_lower for forte in equipes_fortes):
        return [10, 25, 35, 25, 5]  # Offensive
    elif any(ligue in league_lower for ligue in ligues_fortes):
        return [20, 35, 30, 15, 0]  # Moyenne haute
    else:
        return [35, 40, 20, 5, 0]   # Défensive

def analyser_cotes(odds_data, team1, team2):
    """Analyse les cotes pour générer une prédiction"""
    if not odds_data:
        return "Match équilibré"

    cotes = {}
    for odd in odds_data:
        if isinstance(odd, dict) and 'type' in odd and 'cote' in odd:
            if odd['type'] in ['1', '2', 'X']:
                try:
                    cotes[odd['type']] = float(odd['cote'])
                except (ValueError, TypeError):
                    continue

    if not cotes:
        return "Données insuffisantes"

    # Trouver le favori (cote la plus basse)
    favori = min(cotes.items(), key=lambda x: x[1])

    if favori[0] == '1':
        confiance = min(90, int(100 - (favori[1] - 1) * 30))
        return f"{team1} favori (confiance: {confiance}%)"
    elif favori[0] == '2':
        confiance = min(90, int(100 - (favori[1] - 1) * 30))
        return f"{team2} favori (confiance: {confiance}%)"
    else:
        return "Match nul probable"

class SystemePredictionUnifie:
    """Système de prédiction unifié qui lie tous les algorithmes pour analyser 1-2 options principales"""

    def __init__(self, team1, team2, league, odds_data, sport, paris_alternatifs=None):
        self.team1 = team1
        self.team2 = team2
        self.league = league
        self.odds_data = odds_data or []
        self.sport = sport
        self.paris_alternatifs = paris_alternatifs or []

        # Calculer les forces des équipes une seule fois
        self.force1 = calculer_force_equipe(team1, league)
        self.force2 = calculer_force_equipe(team2, league)

        # Analyser les cotes une seule fois
        self.analyse_cotes = self._analyser_cotes_detaillee()

        # Identifier les 1-2 meilleures options
        self.options_principales = self._identifier_options_principales()

    def _analyser_cotes_detaillee(self):
        """Analyse détaillée des cotes pour tous les marchés"""
        analyse = {
            'cotes_1x2': {},
            'favori': None,
            'confiance_favori': 0,
            'equilibre_match': 'moyen'
        }

        # Analyser les cotes 1X2
        for odd in self.odds_data:
            if isinstance(odd, dict) and 'type' in odd and 'cote' in odd:
                if odd['type'] in ['1', '2', 'X']:
                    try:
                        analyse['cotes_1x2'][odd['type']] = float(odd['cote'])
                    except (ValueError, TypeError):
                        continue

        if analyse['cotes_1x2']:
            # Trouver le favori
            favori = min(analyse['cotes_1x2'].items(), key=lambda x: x[1])
            analyse['favori'] = favori[0]
            analyse['confiance_favori'] = min(95, int(100 - (favori[1] - 1) * 25))

            # Déterminer l'équilibre du match
            cotes_values = list(analyse['cotes_1x2'].values())
            ecart_max = max(cotes_values) - min(cotes_values)
            if ecart_max < 0.5:
                analyse['equilibre_match'] = 'très_equilibre'
            elif ecart_max < 1.0:
                analyse['equilibre_match'] = 'equilibre'
            elif ecart_max < 2.0:
                analyse['equilibre_match'] = 'moyen'
            else:
                analyse['equilibre_match'] = 'desequilibre'

        return analyse

    def _identifier_options_principales(self):
        """Identifie les 1-2 meilleures options à analyser ensemble"""
        options = []

        # Option 1: Résultat 1X2 (toujours inclus)
        if self.analyse_cotes['favori']:
            if self.analyse_cotes['favori'] == '1':
                option1 = {
                    'type': 'resultat_1x2',
                    'prediction': f"Victoire {self.team1}",
                    'cote': self.analyse_cotes['cotes_1x2'].get('1', 0),
                    'confiance': self.analyse_cotes['confiance_favori'],
                    'equipe_cible': self.team1
                }
            elif self.analyse_cotes['favori'] == '2':
                option1 = {
                    'type': 'resultat_1x2',
                    'prediction': f"Victoire {self.team2}",
                    'cote': self.analyse_cotes['cotes_1x2'].get('2', 0),
                    'confiance': self.analyse_cotes['confiance_favori'],
                    'equipe_cible': self.team2
                }
            else:
                option1 = {
                    'type': 'resultat_1x2',
                    'prediction': "Match nul",
                    'cote': self.analyse_cotes['cotes_1x2'].get('X', 0),
                    'confiance': self.analyse_cotes['confiance_favori'],
                    'equipe_cible': None
                }
            options.append(option1)

        # Option 2: Meilleur pari alternatif (si disponible)
        if self.paris_alternatifs:
            # Filtrer les paris intéressants (cote entre 1.5 et 3.0)
            paris_interessants = [
                p for p in self.paris_alternatifs
                if 1.5 <= float(p.get("cote", 999)) <= 3.0
            ]

            if paris_interessants:
                # Prendre le pari avec la meilleure cote (plus faible = plus probable)
                meilleur_pari = min(paris_interessants, key=lambda x: float(x["cote"]))

                option2 = {
                    'type': 'pari_alternatif',
                    'prediction': meilleur_pari['nom'],
                    'cote': float(meilleur_pari['cote']),
                    'confiance': min(90, int((1 / float(meilleur_pari['cote'])) * 100)),
                    'equipe_cible': self._detecter_equipe_cible(meilleur_pari['nom']),
                    'details': meilleur_pari
                }
                options.append(option2)

        return options[:2]  # Maximum 2 options

    def _detecter_equipe_cible(self, nom_pari):
        """Détecte quelle équipe est ciblée par un pari"""
        nom_lower = nom_pari.lower()
        if self.team1.lower() in nom_lower:
            return self.team1
        elif self.team2.lower() in nom_lower:
            return self.team2
        elif "o1" in nom_lower or "équipe 1" in nom_lower:
            return self.team1
        elif "o2" in nom_lower or "équipe 2" in nom_lower:
            return self.team2
        return None

    def generer_prediction_unifiee(self):
        """Génère une prédiction unifiée où tous les systèmes prennent une décision ensemble"""
        if not self.options_principales:
            return "Données insuffisantes pour une prédiction fiable"

        # PHASE 1: Collecte des données par tous les systèmes
        donnees_globales = self._collecter_donnees_tous_systemes()

        # PHASE 2: Délibération collective des systèmes
        decision_collective = self._deliberation_collective(donnees_globales)

        # PHASE 3: Génération de la recommandation finale unique
        return self._generer_decision_finale(decision_collective)

    def _analyser_option_complete(self, option):
        """Analyse complète d'une option avec tous les systèmes de prédiction"""
        analyse = {
            'option': option,
            'systemes': {}
        }

        # Système 1: Analyse statistique
        analyse['systemes']['statistique'] = self._analyse_statistique(option)

        # Système 2: Analyse des cotes
        analyse['systemes']['cotes'] = self._analyse_cotes_option(option)

        # Système 3: Simulation Monte Carlo
        analyse['systemes']['simulation'] = self._simulation_monte_carlo(option)

        # Système 4: Analyse de forme (basée sur la ligue et les équipes)
        analyse['systemes']['forme'] = self._analyse_forme(option)

        # Consensus final
        analyse['consensus'] = self._calculer_consensus(analyse['systemes'])

        return analyse

    def _analyse_statistique(self, option):
        """Système de prédiction statistique"""
        if option['type'] == 'resultat_1x2':
            # Calculer les probabilités basées sur les forces
            total_force = sum(self.force1) + sum(self.force2)
            prob_team1 = (sum(self.force1) / total_force) * 100
            prob_team2 = (sum(self.force2) / total_force) * 100

            if option['equipe_cible'] == self.team1:
                probabilite = prob_team1
            elif option['equipe_cible'] == self.team2:
                probabilite = prob_team2
            else:  # Match nul
                probabilite = max(15, 100 - prob_team1 - prob_team2)
        else:
            # Pour les paris alternatifs, utiliser la cote comme base
            probabilite = min(85, (1 / option['cote']) * 100)

        return {
            'probabilite': probabilite,
            'confiance': min(90, probabilite * 0.9),
            'recommandation': 'favorable' if probabilite > 60 else 'neutre' if probabilite > 40 else 'defavorable'
        }

    def _analyse_cotes_option(self, option):
        """Analyse basée sur les cotes du marché"""
        cote = option['cote']
        probabilite_implicite = (1 / cote) * 100

        # Ajuster selon l'équilibre du match
        if self.analyse_cotes['equilibre_match'] == 'très_equilibre':
            ajustement = 0.95
        elif self.analyse_cotes['equilibre_match'] == 'equilibre':
            ajustement = 1.0
        elif self.analyse_cotes['equilibre_match'] == 'desequilibre':
            ajustement = 1.1
        else:
            ajustement = 1.05

        probabilite_ajustee = min(95, probabilite_implicite * ajustement)

        return {
            'probabilite': probabilite_ajustee,
            'confiance': min(85, probabilite_ajustee * 0.85),
            'recommandation': 'favorable' if cote < 2.0 else 'neutre' if cote < 2.5 else 'defavorable'
        }

    def _simulation_monte_carlo(self, option):
        """Simulation Monte Carlo pour prédire l'issue"""
        simulations = 1000
        succes = 0

        for _ in range(simulations):
            # Simuler un match
            buts1 = random.choices([0, 1, 2, 3, 4], weights=self.force1)[0]
            buts2 = random.choices([0, 1, 2, 3, 4], weights=self.force2)[0]

            # Vérifier si l'option est réalisée
            if option['type'] == 'resultat_1x2':
                if option['equipe_cible'] == self.team1 and buts1 > buts2:
                    succes += 1
                elif option['equipe_cible'] == self.team2 and buts2 > buts1:
                    succes += 1
                elif option['equipe_cible'] is None and buts1 == buts2:
                    succes += 1
            else:
                # Pour les paris alternatifs, simulation simplifiée
                if random.random() < (1 / option['cote']):
                    succes += 1

        probabilite = (succes / simulations) * 100

        return {
            'probabilite': probabilite,
            'confiance': min(80, probabilite * 0.8),
            'recommandation': 'favorable' if probabilite > 55 else 'neutre' if probabilite > 35 else 'defavorable'
        }

    def _analyse_forme(self, option):
        """Analyse de la forme des équipes"""
        # Simuler une analyse de forme basée sur la ligue et les noms d'équipes
        if option['equipe_cible'] == self.team1:
            force_relative = sum(self.force1) / (sum(self.force1) + sum(self.force2))
        elif option['equipe_cible'] == self.team2:
            force_relative = sum(self.force2) / (sum(self.force1) + sum(self.force2))
        else:
            force_relative = 0.33  # Match nul

        probabilite = force_relative * 100

        return {
            'probabilite': probabilite,
            'confiance': min(75, probabilite * 0.75),
            'recommandation': 'favorable' if probabilite > 50 else 'neutre' if probabilite > 30 else 'defavorable'
        }

    def _calculer_consensus(self, systemes):
        """Calcule le consensus de tous les systèmes"""
        probabilites = [s['probabilite'] for s in systemes.values()]
        confiances = [s['confiance'] for s in systemes.values()]

        # Moyenne pondérée (plus de poids aux systèmes avec plus de confiance)
        poids_total = sum(confiances)
        if poids_total > 0:
            probabilite_consensus = sum(p * c for p, c in zip(probabilites, confiances)) / poids_total
            confiance_consensus = sum(confiances) / len(confiances)
        else:
            probabilite_consensus = sum(probabilites) / len(probabilites)
            confiance_consensus = 50

        # Déterminer la recommandation finale
        if probabilite_consensus > 65:
            recommandation = 'très_favorable'
        elif probabilite_consensus > 50:
            recommandation = 'favorable'
        elif probabilite_consensus > 35:
            recommandation = 'neutre'
        else:
            recommandation = 'defavorable'

        return {
            'probabilite': probabilite_consensus,
            'confiance': confiance_consensus,
            'recommandation': recommandation
        }

    def _collecter_donnees_tous_systemes(self):
        """Phase 1: Tous les systèmes collectent leurs données sur toutes les options"""
        donnees = {
            'options': self.options_principales,
            'systemes': {
                'statistique': {},
                'cotes': {},
                'simulation': {},
                'forme': {}
            },
            'contexte_match': {
                'equilibre': self.analyse_cotes['equilibre_match'],
                'favori': self.analyse_cotes['favori'],
                'confiance_favori': self.analyse_cotes['confiance_favori']
            }
        }

        # Chaque système analyse toutes les options
        for option in self.options_principales:
            option_id = option['type'] + '_' + str(option['cote'])

            donnees['systemes']['statistique'][option_id] = self._analyse_statistique(option)
            donnees['systemes']['cotes'][option_id] = self._analyse_cotes_option(option)
            donnees['systemes']['simulation'][option_id] = self._simulation_monte_carlo(option)
            donnees['systemes']['forme'][option_id] = self._analyse_forme(option)

        return donnees

    def _deliberation_collective(self, donnees):
        """Phase 2: Délibération collective où tous les systèmes débattent ensemble"""

        # Chaque système vote pour sa meilleure option
        votes_systemes = {}

        for nom_systeme, analyses in donnees['systemes'].items():
            # Trouver la meilleure option selon ce système
            meilleure_option = None
            meilleur_score = 0

            for option_id, analyse in analyses.items():
                score = analyse['probabilite'] * (analyse['confiance'] / 100)
                if score > meilleur_score:
                    meilleur_score = score
                    meilleure_option = option_id

            votes_systemes[nom_systeme] = {
                'option_preferee': meilleure_option,
                'score': meilleur_score,
                'confiance': analyses[meilleure_option]['confiance'] if meilleure_option else 0
            }

        # Négociation entre systèmes pour trouver un consensus
        consensus = self._negociation_consensus(votes_systemes, donnees)

        return consensus

    def _negociation_consensus(self, votes_systemes, donnees):
        """Négociation entre systèmes pour arriver à un consensus"""

        # Compter les votes pour chaque option
        compteur_votes = {}
        scores_cumules = {}

        for nom_systeme, vote in votes_systemes.items():
            option = vote['option_preferee']
            if option:
                compteur_votes[option] = compteur_votes.get(option, 0) + 1
                scores_cumules[option] = scores_cumules.get(option, 0) + vote['score']

        # Si unanimité ou majorité claire
        if compteur_votes:
            option_majoritaire = max(compteur_votes.items(), key=lambda x: x[1])

            # Vérifier si c'est un consensus fort (3+ systèmes d'accord)
            if option_majoritaire[1] >= 3:
                decision_type = "CONSENSUS_FORT"
                confiance_collective = 85 + (option_majoritaire[1] * 5)
            elif option_majoritaire[1] >= 2:
                decision_type = "MAJORITE"
                confiance_collective = 70 + (option_majoritaire[1] * 5)
            else:
                decision_type = "DIVISION"
                confiance_collective = 50

            # Trouver l'option correspondante
            option_choisie = None
            for option in donnees['options']:
                option_id = option['type'] + '_' + str(option['cote'])
                if option_id == option_majoritaire[0]:
                    option_choisie = option
                    break

            return {
                'option_finale': option_choisie,
                'type_decision': decision_type,
                'confiance_collective': min(95, confiance_collective),
                'votes_detail': votes_systemes,
                'score_final': scores_cumules.get(option_majoritaire[0], 0)
            }

        # Aucun consensus - prendre la première option par défaut
        return {
            'option_finale': donnees['options'][0] if donnees['options'] else None,
            'type_decision': "DEFAUT",
            'confiance_collective': 30,
            'votes_detail': votes_systemes,
            'score_final': 0
        }

    def _generer_decision_finale(self, decision_collective):
        """Phase 3: Génération de la décision finale unique"""

        if not decision_collective['option_finale']:
            return "❌ AUCUN CONSENSUS: Les systèmes n'arrivent pas à s'accorder"

        option = decision_collective['option_finale']
        type_decision = decision_collective['type_decision']
        confiance = decision_collective['confiance_collective']

        # Icône selon le type de décision
        if type_decision == "CONSENSUS_FORT":
            icone = "🎯"
            statut = "CONSENSUS UNANIME"
        elif type_decision == "MAJORITE":
            icone = "✅"
            statut = "MAJORITÉ D'ACCORD"
        elif type_decision == "DIVISION":
            icone = "⚖️"
            statut = "SYSTÈMES DIVISÉS"
        else:
            icone = "❓"
            statut = "DÉCISION PAR DÉFAUT"

        # Déterminer l'action recommandée
        if confiance >= 80:
            action = "MISE RECOMMANDÉE"
        elif confiance >= 65:
            action = "MISE MODÉRÉE"
        elif confiance >= 50:
            action = "MISE PRUDENTE"
        else:
            action = "ÉVITER CE PARI"

        # Équipe cible si applicable
        equipe_info = f" sur {option['equipe_cible']}" if option['equipe_cible'] else ""

        # Détail des votes pour transparence
        votes_detail = []
        for systeme, vote in decision_collective['votes_detail'].items():
            if vote['option_preferee']:
                votes_detail.append(f"{systeme.title()}: ✓")
            else:
                votes_detail.append(f"{systeme.title()}: ✗")

        return (f"{icone} {statut}: {option['prediction']}{equipe_info} | "
                f"Cote: {option['cote']} | Confiance: {confiance:.1f}% | "
                f"🎯 ACTION: {action} | "
                f"📊 Votes: [{', '.join(votes_detail)}]")

def generer_prediction_intelligente(team1, team2, league, odds_data, sport):
    """Génère une prédiction intelligente avec le système unifié"""
    systeme = SystemePredictionUnifie(team1, team2, league, odds_data, sport)
    return systeme.generer_prediction_unifiee()

def generer_predictions_alternatives(team1, team2, league, paris_alternatifs, odds_data):
    """Génère des prédictions alternatives intelligentes avec le système unifié"""

    # Utiliser le système unifié avec les paris alternatifs
    systeme = SystemePredictionUnifie(team1, team2, league, odds_data, "football", paris_alternatifs)
    prediction_unifiee = systeme.generer_prediction_unifiee()

    # Si pas de paris alternatifs, générer des prédictions par défaut
    if not paris_alternatifs:
        force1 = calculer_force_equipe(team1, league)
        force2 = calculer_force_equipe(team2, league)

        buts1 = random.choices([0, 1, 2, 3, 4], weights=force1)[0]
        buts2 = random.choices([0, 1, 2, 3, 4], weights=force2)[0]
        total = buts1 + buts2

        predictions_defaut = [
            f"🎯 Score prédit: {team1} {buts1}-{buts2} {team2}",
            f"⚽ Total buts: {total} ({'Plus' if total > 2.5 else 'Moins'} de 2.5)",
            f"🏆 Vainqueur probable: {team1 if buts1 > buts2 else team2 if buts2 > buts1 else 'Match nul'}"
        ]
        return " | ".join(predictions_defaut) + f" | 🤖 IA: {prediction_unifiee}"

    return f"🤖 ANALYSE IA UNIFIÉE: {prediction_unifiee}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
