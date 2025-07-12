from flask import Flask, request, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import os
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from ml_predictor import get_ml_prediction, train_predictor_with_data, load_predictor
from analytics import TeamAnalytics

app = Flask(__name__)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sports_predictions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

db = SQLAlchemy(app)

# Charger le modèle ML au démarrage
try:
    load_predictor()
    print("Modèle ML chargé avec succès!")
except:
    print("Aucun modèle ML trouvé. Entraînement nécessaire.")



# Modèles de base de données
class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    sport = db.Column(db.String(50), nullable=False)
    league = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    home_matches = db.relationship('Match', foreign_keys='Match.home_team_id', backref='home_team')
    away_matches = db.relationship('Match', foreign_keys='Match.away_team_id', backref='away_team')

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(50), unique=True)  # ID de l'API 1xbet
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    sport = db.Column(db.String(50), nullable=False)
    league = db.Column(db.String(100), nullable=False)

    # Scores
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)

    # Statut et timing
    status = db.Column(db.String(20), nullable=False)  # 'upcoming', 'live', 'finished'
    match_time = db.Column(db.DateTime)
    minute = db.Column(db.Integer)

    # Météo
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)

    # Prédictions
    predicted_winner = db.Column(db.String(10))  # '1', 'X', '2'
    prediction_confidence = db.Column(db.Float)
    ml_prediction = db.Column(db.String(10))  # Prédiction ML
    ml_confidence = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    odds = db.relationship('Odds', backref='match', cascade='all, delete-orphan')
    statistics = db.relationship('MatchStatistic', backref='match', cascade='all, delete-orphan')

class Odds(db.Model):
    __tablename__ = 'odds'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    bet_type = db.Column(db.String(50), nullable=False)  # '1X2', 'Over/Under', etc.
    bet_value = db.Column(db.String(20))  # '1', 'X', '2', 'Over 2.5', etc.
    odds_value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class MatchStatistic(db.Model):
    __tablename__ = 'match_statistics'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    stat_name = db.Column(db.String(50), nullable=False)
    home_value = db.Column(db.String(20))
    away_value = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class TeamPerformance(db.Model):
    __tablename__ = 'team_performance'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

    # Métriques de performance
    matches_played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    goals_for = db.Column(db.Integer, default=0)
    goals_against = db.Column(db.Integer, default=0)

    # Forme récente (derniers 5 matchs)
    recent_form = db.Column(db.String(10))  # 'WWDLL' par exemple
    form_score = db.Column(db.Float)  # Score numérique de la forme

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialiser l'analytics après la définition des modèles
analytics = TeamAnalytics(db, Match, Team)

# Fonction pour initialiser la base de données
def init_db():
    """Initialise la base de données avec les tables"""
    with app.app_context():
        db.create_all()
        print("Base de données initialisée avec succès!")

# Fonctions utilitaires pour la base de données
def get_or_create_team(name, sport, league):
    """Récupère ou crée une équipe"""
    team = Team.query.filter_by(name=name, sport=sport, league=league).first()
    if not team:
        team = Team(name=name, sport=sport, league=league)
        db.session.add(team)
        db.session.commit()
    return team

def save_match_to_db(match_data):
    """Sauvegarde un match dans la base de données"""
    try:
        # Récupérer ou créer les équipes
        home_team = get_or_create_team(
            match_data['team1'],
            match_data['sport'],
            match_data['league']
        )
        away_team = get_or_create_team(
            match_data['team2'],
            match_data['sport'],
            match_data['league']
        )

        # Vérifier si le match existe déjà
        existing_match = Match.query.filter_by(external_id=str(match_data.get('id'))).first()

        if existing_match:
            # Mettre à jour le match existant
            existing_match.home_score = match_data['score1']
            existing_match.away_score = match_data['score2']
            existing_match.status = match_data['status']
            existing_match.temperature = match_data.get('temp', 0) if match_data.get('temp') != '–' else None
            existing_match.humidity = match_data.get('humid', 0) if match_data.get('humid') != '–' else None
            existing_match.updated_at = datetime.utcnow()
            match_obj = existing_match
        else:
            # Créer un nouveau match
            match_obj = Match(
                external_id=str(match_data.get('id')),
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                sport=match_data['sport'],
                league=match_data['league'],
                home_score=match_data['score1'],
                away_score=match_data['score2'],
                status=match_data['status'],
                temperature=match_data.get('temp', 0) if match_data.get('temp') != '–' else None,
                humidity=match_data.get('humid', 0) if match_data.get('humid') != '–' else None,
                predicted_winner=match_data.get('prediction_type'),
                prediction_confidence=match_data.get('prediction_confidence', 0.5)
            )
            db.session.add(match_obj)

        # Sauvegarder les cotes
        if match_data.get('odds') and isinstance(match_data['odds'], list):
            for odd_str in match_data['odds']:
                if ':' in odd_str and odd_str != "Pas de cotes disponibles":
                    bet_value, odds_value = odd_str.split(': ')

                    # Vérifier si cette cote existe déjà pour ce match
                    existing_odd = Odds.query.filter_by(
                        match_id=match_obj.id,
                        bet_type='1X2',
                        bet_value=bet_value
                    ).first()

                    if not existing_odd:
                        odd = Odds(
                            match_id=match_obj.id,
                            bet_type='1X2',
                            bet_value=bet_value,
                            odds_value=float(odds_value)
                        )
                        db.session.add(odd)

        db.session.commit()
        return match_obj

    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la sauvegarde du match: {e}")
        return None

def calculate_team_form(team_id, days=30):
    """Calcule la forme récente d'une équipe"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    recent_matches = Match.query.filter(
        db.or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
        Match.created_at >= cutoff_date,
        Match.status == 'finished'
    ).order_by(Match.created_at.desc()).limit(10).all()

    form_string = ""
    wins = draws = losses = 0

    for match in recent_matches:
        if match.home_team_id == team_id:
            if match.home_score > match.away_score:
                form_string += "W"
                wins += 1
            elif match.home_score == match.away_score:
                form_string += "D"
                draws += 1
            else:
                form_string += "L"
                losses += 1
        else:
            if match.away_score > match.home_score:
                form_string += "W"
                wins += 1
            elif match.away_score == match.home_score:
                form_string += "D"
                draws += 1
            else:
                form_string += "L"
                losses += 1

    # Calculer un score de forme (3 points pour victoire, 1 pour nul, 0 pour défaite)
    total_matches = len(recent_matches)
    if total_matches > 0:
        form_score = (wins * 3 + draws * 1) / (total_matches * 3)
    else:
        form_score = 0.5

    return form_string, form_score

@app.route('/train_ml')
def train_ml():
    """Route pour entraîner le modèle ML"""
    try:
        # Récupérer tous les matchs terminés de la base de données
        finished_matches = Match.query.filter_by(status='Terminé').all()

        if len(finished_matches) < 10:
            return jsonify({
                "error": "Pas assez de matchs terminés pour entraîner le modèle (minimum 10)",
                "matches_count": len(finished_matches)
            })

        # Convertir en format pour le ML
        matches_data = []
        for match in finished_matches:
            match_data = {
                'team1': match.home_team.name,
                'team2': match.away_team.name,
                'sport': match.sport,
                'league': match.league,
                'score1': match.home_score,
                'score2': match.away_score,
                'status': 'Terminé',
                'temp': match.temperature or 20,
                'humid': match.humidity or 50,
                'odds': []  # On pourrait récupérer les cotes de la DB
            }
            matches_data.append(match_data)

        # Entraîner le modèle
        success = train_predictor_with_data(matches_data)

        if success:
            from ml_predictor import save_predictor
            save_predictor()
            return jsonify({
                "success": True,
                "message": f"Modèle entraîné avec succès sur {len(matches_data)} matchs",
                "matches_count": len(matches_data)
            })
        else:
            return jsonify({
                "error": "Échec de l'entraînement du modèle"
            })

    except Exception as e:
        return jsonify({
            "error": f"Erreur lors de l'entraînement: {str(e)}"
        })

@app.route('/ml_stats')
def ml_stats():
    """Route pour afficher les statistiques du modèle ML"""
    try:
        from ml_predictor import predictor

        if not predictor.is_trained:
            return jsonify({
                "error": "Modèle non entraîné"
            })

        feature_importance = predictor.get_feature_importance()

        return jsonify({
            "is_trained": predictor.is_trained,
            "feature_importance": feature_importance,
            "feature_count": len(predictor.feature_names)
        })

    except Exception as e:
        return jsonify({
            "error": f"Erreur: {str(e)}"
        })

@app.route('/team_form/<team_name>')
def team_form(team_name):
    """Route pour obtenir la forme d'une équipe"""
    try:
        form_data = analytics.get_team_recent_form(team_name)
        if form_data:
            return jsonify(form_data)
        else:
            return jsonify({"error": "Équipe non trouvée"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/h2h/<team1>/<team2>')
def head_to_head(team1, team2):
    """Route pour obtenir l'historique H2H entre deux équipes"""
    try:
        h2h_data = analytics.get_head_to_head(team1, team2)
        if h2h_data:
            return jsonify(h2h_data)
        else:
            return jsonify({"error": "Équipes non trouvées"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/league_stats/<league_name>')
def league_stats(league_name):
    """Route pour obtenir les statistiques d'une ligue"""
    try:
        league_data = analytics.get_league_performance(league_name)
        if league_data:
            return jsonify(league_data)
        else:
            return jsonify({"error": "Ligue non trouvée ou pas de données"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/analytics_dashboard')
def analytics_dashboard():
    """Page de dashboard avec graphiques avancés"""
    return render_template_string(ANALYTICS_TEMPLATE)

@app.route('/api/odds_evolution/<int:match_id>')
def odds_evolution(match_id):
    """API pour l'évolution des cotes d'un match"""
    try:
        odds_history = Odds.query.filter_by(match_id=match_id).order_by(Odds.timestamp).all()

        data = {
            'timestamps': [odd.timestamp.isoformat() for odd in odds_history],
            'odds_1': [odd.odds_value for odd in odds_history if odd.bet_value == '1'],
            'odds_x': [odd.odds_value for odd in odds_history if odd.bet_value == 'X'],
            'odds_2': [odd.odds_value for odd in odds_history if odd.bet_value == '2']
        }

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/league_heatmap/<league_name>')
def league_heatmap(league_name):
    """API pour la heatmap des performances par ligue"""
    try:
        league_data = analytics.get_league_performance(league_name)
        if not league_data:
            return jsonify({"error": "Pas de données"})

        heatmap_data = []
        for team_name, stats in league_data['team_standings']:
            heatmap_data.append({
                'team': team_name,
                'matches': stats['matches'],
                'points': stats['points'],
                'goals_for': stats['goals_for'],
                'goals_against': stats['goals_against'],
                'goal_difference': stats['goals_for'] - stats['goals_against']
            })

        return jsonify(heatmap_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/')
def home():
    try:
        selected_sport = request.args.get("sport", "").strip()
        selected_league = request.args.get("league", "").strip()
        selected_status = request.args.get("status", "").strip()

        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
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

                # --- Score ---
                score1 = match.get("SC", {}).get("FS", {}).get("S1")
                score2 = match.get("SC", {}).get("FS", {}).get("S2")
                try:
                    score1 = int(score1) if score1 is not None else 0
                except:
                    score1 = 0
                try:
                    score2 = int(score2) if score2 is not None else 0
                except:
                    score2 = 0

                # --- Minute ---
                minute = None
                # Prendre d'abord SC.TS (temps écoulé en secondes)
                sc = match.get("SC", {})
                if "TS" in sc and isinstance(sc["TS"], int):
                    minute = sc["TS"] // 60
                elif "ST" in sc and isinstance(sc["ST"], int):
                    minute = sc["ST"]
                elif "T" in match and isinstance(match["T"], int):
                    minute = match["T"] // 60

                # --- Statut ---
                tn = match.get("TN", "").lower()
                tns = match.get("TNS", "").lower()
                tt = match.get("SC", {}).get("TT")
                statut = "À venir"
                is_live = False
                is_finished = False
                is_upcoming = False
                if (minute is not None and minute > 0) or (score1 > 0 or score2 > 0):
                    statut = f"En cours ({minute}′)" if minute else "En cours"
                    is_live = True
                if ("terminé" in tn or "terminé" in tns) or (tt == 3):
                    statut = "Terminé"
                    is_live = False
                    is_finished = True
                if statut == "À venir":
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
                match_time = datetime.utcfromtimestamp(match_ts).strftime('%d/%m/%Y %H:%M') if match_ts else "–"

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

                prediction = "–"
                if odds_data:
                    best = min(odds_data, key=lambda x: x["cote"])
                    prediction = {
                        "1": f"{team1} gagne",
                        "2": f"{team2} gagne",
                        "X": "Match nul"
                    }.get(best["type"], "–")

                # --- Météo ---
                meteo_data = match.get("MIS", [])
                temp = next((item["V"] for item in meteo_data if item.get("K") == 9), "–")
                humid = next((item["V"] for item in meteo_data if item.get("K") == 27), "–")

                match_data = {
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
                }

                # Déterminer le type de prédiction pour la base de données
                if odds_data:
                    best = min(odds_data, key=lambda x: x["cote"])
                    match_data["prediction_type"] = best["type"]
                    match_data["prediction_confidence"] = 1.0 / best["cote"]  # Plus la cote est faible, plus la confiance est élevée

                # Analyse H2H et forme des équipes
                try:
                    h2h_data = analytics.get_head_to_head(team1, team2)
                    team1_form = analytics.get_team_recent_form(team1)
                    team2_form = analytics.get_team_recent_form(team2)
                    confidence_score = analytics.calculate_prediction_confidence(team1, team2)

                    match_data["h2h_data"] = h2h_data
                    match_data["team1_form"] = team1_form
                    match_data["team2_form"] = team2_form
                    match_data["analytics_confidence"] = confidence_score
                except Exception as e:
                    print(f"Erreur analyse H2H: {e}")
                    match_data["analytics_confidence"] = 0.5

                # Prédiction ML
                try:
                    ml_prediction, ml_confidence = get_ml_prediction(match_data)
                    if ml_prediction:
                        match_data["ml_prediction"] = ml_prediction
                        match_data["ml_confidence"] = ml_confidence

                        # Améliorer la prédiction affichée avec le ML et l'analytics
                        ml_prediction_text = {
                            "1": f"{team1} gagne (ML)",
                            "2": f"{team2} gagne (ML)",
                            "X": "Match nul (ML)"
                        }.get(ml_prediction, prediction)

                        # Combiner ML et analytics pour une confiance globale
                        combined_confidence = (ml_confidence + match_data.get("analytics_confidence", 0.5)) / 2

                        # Si la confiance combinée est élevée, utiliser la prédiction ML
                        if combined_confidence > 0.6:
                            match_data["prediction"] = f"{ml_prediction_text} ({combined_confidence:.1%})"
                        else:
                            match_data["prediction"] = f"{prediction} | {ml_prediction_text} ({combined_confidence:.1%})"
                except Exception as e:
                    print(f"Erreur prédiction ML: {e}")
                    match_data["ml_prediction"] = None
                    match_data["ml_confidence"] = 0.5

                # Sauvegarder dans la base de données
                save_match_to_db(match_data)

                data.append(match_data)
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

def traduire_pari_type_groupe(type_pari, groupe, param, team1=None, team2=None):
    """Traduit le type de pari selon T, G et P (structure 1xbet) avec mapping explicite, noms d'équipes et distinction Over/Under."""
    # 1X2
    if groupe == 1 and type_pari in [1, 2, 3]:
        return {1: f"Victoire {team1}", 2: f"Victoire {team2}", 3: "Match nul"}.get(type_pari, "1X2")
    # Handicap
    if groupe == 2:
        if param is not None:
            if type_pari == 1 and team1:
                return f"Handicap {team1} {param}"
            elif type_pari == 2 and team2:
                return f"Handicap {team2} {param}"
            else:
                return f"Handicap {param}"
        return "Handicap"
    # Over/Under (souvent G8 ou G17 ou G62)
    if groupe in [8, 17, 62]:
        if param is not None:
            seuil = abs(float(param))
            if type_pari in [9]:  # T=9 = Over (Plus de)
                return f"Plus de {seuil} buts"
            elif type_pari in [10]:  # T=10 = Under (Moins de)
                return f"Moins de {seuil} buts"
            # fallback si on ne sait pas
            if float(param) > 0:
                return f"Plus de {seuil} buts"
            else:
                return f"Moins de {seuil} buts"
        return "Plus/Moins de buts"
    # Score exact
    if groupe == 15:
        if param is not None:
            return f"Score exact {param}"
        return "Score exact"
    # Double chance
    if groupe == 3:
        if type_pari == 1 and team1 and team2:
            return f"Double chance {team1} ou {team2}"
        elif type_pari == 2 and team1:
            return f"Double chance {team1} ou Nul"
        elif type_pari == 3 and team2:
            return f"Double chance {team2} ou Nul"
        return "Double chance"
    # Nombre de buts
    if groupe in [19, 180, 181]:
        return "Nombre de buts"
    # Ajoute d'autres mappings selon tes observations
    return f"Pari spécial (G{groupe} T{type_pari})"

@app.route('/match/<int:match_id>')
def match_details(match_id):
    try:
        # Récupérer les données de l'API (ou brute.json si besoin)
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
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
        # Scores
        score1 = match.get("SC", {}).get("FS", {}).get("S1")
        score2 = match.get("SC", {}).get("FS", {}).get("S2")
        try:
            score1 = int(score1) if score1 is not None else 0
        except:
            score1 = 0
        try:
            score2 = int(score2) if score2 is not None else 0
        except:
            score2 = 0
        # Statistiques avancées
        stats = []
        st = match.get("SC", {}).get("ST", [])
        if st and isinstance(st, list) and len(st) > 0 and "Value" in st[0]:
            for stat in st[0]["Value"]:
                nom = stat.get("N", "?")
                s1 = stat.get("S1", "0")
                s2 = stat.get("S2", "0")
                stats.append({"nom": nom, "s1": s1, "s2": s2})
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
        prediction = "–"
        if odds_data:
            best = min(odds_data, key=lambda x: x["cote"])
            prediction = {
                "1": f"{team1} gagne",
                "2": f"{team2} gagne",
                "X": "Match nul"
            }.get(best["type"], "–")
        # --- Paris alternatifs ---
        paris_alternatifs = []
        # 1. E (marchés principaux et alternatifs)
        for o in match.get("E", []):
            if o.get("G") != 1 and o.get("C") is not None:
                type_pari = o.get("T")
                groupe = o.get("G")
                param = o.get("P") if "P" in o else None
                nom_traduit = traduire_pari_type_groupe(type_pari, groupe, param, team1, team2)
                valeur = param if param is not None else ""
                cote = o.get("C")
                paris_alternatifs.append({
                    "nom": nom_traduit,
                    "valeur": valeur,
                    "cote": cote
                })
        # 2. AE (marchés alternatifs étendus)
        for ae in match.get("AE", []):
            if ae.get("G") != 1:
                for o in ae.get("ME", []):
                    if o.get("C") is not None:
                        type_pari = o.get("T")
                        groupe = o.get("G")
                        param = o.get("P") if "P" in o else None
                        nom_traduit = traduire_pari_type_groupe(type_pari, groupe, param, team1, team2)
                        valeur = param if param is not None else ""
                        cote = o.get("C")
                        paris_alternatifs.append({
                            "nom": nom_traduit,
                            "valeur": valeur,
                            "cote": cote
                        })
        # Filtrer les paris alternatifs selon la cote demandée
        paris_alternatifs = [p for p in paris_alternatifs if 1.499 <= float(p["cote"]) <= 3]
        # Sélection de la prédiction alternative la plus probable (cote la plus basse)
        prediction_alt = None
        if paris_alternatifs:
            meilleur_pari = min(paris_alternatifs, key=lambda x: x["cote"])
            prediction_alt = f"{meilleur_pari['nom']} ({meilleur_pari['valeur']}) à {meilleur_pari['cote']}"
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
                    <b>Prédiction alternative du bot :</b><br>
                    {prediction_alt if prediction_alt else 'Aucune prédiction alternative disponible'}
                </div>
                <h3>Statistiques principales</h3>
                <table class="stats-table">
                    <tr><th>Statistique</th><th>{team1}</th><th>{team2}</th></tr>
                    {''.join(f'<tr><td>{s["nom"]}</td><td>{s["s1"]}</td><td>{s["s2"]}</td></tr>' for s in stats)}
                </table>
                <h3>Tableau des paris alternatifs</h3>
                <table class="alt-table">
                    <tr><th>Type de pari</th><th>Valeur</th><th>Cote</th><th>Prédiction</th></tr>
                    {''.join(f'<tr><td>{p["nom"]}</td><td>{p["valeur"]}</td><td>{p["cote"]}</td><td>{generer_prediction_lisible(p["nom"], p["valeur"], team1, team2)}</td></tr>' for p in paris_alternatifs)}
                </table>
                <canvas id="statsChart" height="200"></canvas>
                <div class="contact-box">
                    <b>Contact & Services :</b><br>
                    📬 Inbox Telegram : <a href="https://t.me/Roidesombres225" target="_blank">@Roidesombres225</a><br>
                    📢 Canal Telegram : <a href="https://t.me/SOLITAIREHACK" target="_blank">SOLITAIREHACK</a><br>
                    🎨 Je suis aussi concepteur graphique et créateur de logiciels.<br>
                    <span style="color:#2980b9;">Vous avez un projet en tête ? Contactez-moi, je suis là pour vous !</span>
                </div>
            </div>
            <script>
                const labels = { [repr(s['nom']) for s in stats] };
                const data1 = { [float(s['s1']) if s['s1'].replace('.', '', 1).isdigit() else 0 for s in stats] };
                const data2 = { [float(s['s2']) if s['s2'].replace('.', '', 1).isdigit() else 0 for s in stats] };
                new Chart(document.getElementById('statsChart'), {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [
                            {{ label: '{team1}', data: data1, backgroundColor: 'rgba(44,62,80,0.7)' }},
                            {{ label: '{team2}', data: data2, backgroundColor: 'rgba(39,174,96,0.7)' }}
                        ]
                    }},
                    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }}
                }});
            </script>
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
        :root {
            /* Thème clair */
            --bg-primary: #f4f4f4;
            --bg-secondary: #ffffff;
            --bg-table-even: #eaf6fb;
            --bg-table-odd: #f9f9f9;
            --text-primary: #2c3e50;
            --text-secondary: #ffffff;
            --border-color: #2c3e50;
            --header-bg: #1a252f;
            --button-bg: #2980b9;
            --button-hover: #3498db;
            --contact-bg: #ff1744;
            --contact-border: #ff1744;
        }

        [data-theme="dark"] {
            /* Thème sombre */
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --bg-table-even: #3a3a3a;
            --bg-table-odd: #2d2d2d;
            --text-primary: #e0e0e0;
            --text-secondary: #ffffff;
            --border-color: #555555;
            --header-bg: #0f1419;
            --button-bg: #3498db;
            --button-hover: #2980b9;
            --contact-bg: #e74c3c;
            --contact-border: #e74c3c;
        }

        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            background: var(--bg-primary);
            color: var(--text-primary);
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background: var(--button-bg);
            border: none;
            border-radius: 50px;
            padding: 10px 15px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .theme-toggle:hover {
            background: var(--button-hover);
            transform: scale(1.05);
        }

        h2 { text-align: center; color: var(--text-primary); }
        form { text-align: center; margin-bottom: 20px; }
        label { font-weight: bold; margin-right: 10px; color: var(--text-primary); }
        select {
            padding: 12px;
            margin: 0 10px;
            font-size: 16px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-primary);
            transition: all 0.3s ease;
        }
        select:focus { outline: 2px solid var(--button-bg); }
        table {
            border-collapse: collapse;
            margin: auto;
            width: 98%;
            background: var(--bg-secondary);
            transition: background-color 0.3s ease;
        }
        th, td {
            padding: 14px;
            border: 1.5px solid var(--border-color);
            text-align: center;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        th {
            background: var(--header-bg);
            color: var(--text-secondary);
            font-size: 18px;
        }
        tr:nth-child(even) { background-color: var(--bg-table-even); }
        tr:nth-child(odd) { background-color: var(--bg-table-odd); }
        .pagination { text-align: center; margin: 20px 0; }
        .pagination button {
            padding: 14px 24px;
            margin: 0 6px;
            font-size: 18px;
            border: none;
            background: var(--button-bg);
            color: var(--text-secondary);
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .pagination button:hover { background: var(--button-hover); }
        .pagination button:disabled {
            background: var(--border-color);
            color: var(--text-primary);
            cursor: not-allowed;
            opacity: 0.6;
        }
        .pagination button:focus { outline: 2px solid var(--button-hover); }
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
        .contact-box {
            background: var(--contact-bg);
            border: 4px solid var(--contact-border);
            border-radius: 16px;
            margin: 40px auto 0 auto;
            padding: 28px;
            text-align: center;
            font-size: 22px;
            font-weight: bold;
            color: var(--text-secondary);
            max-width: 650px;
            box-shadow: 0 0 24px 8px var(--contact-bg), 0 0 60px 10px rgba(255,255,255,0.2);
            text-shadow: 0 0 8px rgba(255,255,255,0.8);
            letter-spacing: 1px;
            transition: all 0.3s ease;
        }
        .contact-box a {
            color: var(--text-secondary);
            font-weight: bold;
            text-decoration: underline;
            font-size: 26px;
            text-shadow: 0 0 8px rgba(255,255,255,0.8);
            transition: all 0.3s ease;
        }
        .contact-box .icon {
            font-size: 32px;
            vertical-align: middle;
            margin-right: 10px;
            filter: drop-shadow(0 0 6px rgba(255,255,255,0.8));
        }
    </style>
    <script>
        // Gestion du thème sombre/clair
        document.addEventListener('DOMContentLoaded', function() {
            // Charger le thème sauvegardé
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateThemeButton(savedTheme);

            // Gestion des formulaires
            var forms = document.querySelectorAll('form');
            forms.forEach(function(form) {
                form.addEventListener('submit', function() {
                    document.getElementById('loader').style.display = 'flex';
                });
            });
        });

        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeButton(newTheme);
        }

        function updateThemeButton(theme) {
            const button = document.getElementById('theme-toggle');
            if (button) {
                button.innerHTML = theme === 'dark' ? '☀️ Clair' : '🌙 Sombre';
                button.setAttribute('aria-label', theme === 'dark' ? 'Passer au thème clair' : 'Passer au thème sombre');
            }
        }
    </script>
</head><body>
    <button id="theme-toggle" class="theme-toggle" onclick="toggleTheme()" aria-label="Basculer le thème">🌙 Sombre</button>
    <div id="loader" role="status" aria-live="polite"><div class="spinner" aria-label="Chargement"></div></div>
    <h2>📊 Matchs en direct — {{ selected_sport }} / {{ selected_league }} / {{ selected_status }}</h2>

    <div style="text-align: center; margin-bottom: 20px;">
        <a href="/analytics_dashboard" style="display: inline-block; padding: 12px 24px; background: #3498db; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">
            📈 Dashboard Analytics Avancé
        </a>
        <a href="/train_ml" style="display: inline-block; padding: 12px 24px; background: #e74c3c; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">
            🤖 Entraîner le ML
        </a>
    </div>

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

    <table>
        <tr>
            <th>Équipe 1</th><th>Score 1</th><th>Score 2</th><th>Équipe 2</th>
            <th>Sport</th><th>Ligue</th><th>Statut</th><th>Date & Heure</th>
            <th>Température</th><th>Humidité</th><th>Cotes</th><th>Prédiction</th><th>Détails</th>
        </tr>
        {% for m in data %}
        <tr>
            <td>{{m.team1}}</td><td>{{m.score1}}</td><td>{{m.score2}}</td><td>{{m.team2}}</td>
            <td>{{m.sport}}</td><td>{{m.league}}</td><td>{{m.status}}</td><td>{{m.datetime}}</td>
            <td>{{m.temp}}°C</td><td>{{m.humid}}%</td><td>{{m.odds|join(" | ")}}</td><td>{{m.prediction}}</td>
            <td>{% if m.id %}<a href="/match/{{m.id}}"><button>Détails</button></a>{% else %}–{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
    <div class="contact-box">
        <span class="icon">📬</span> Inbox Telegram : <a href="https://t.me/Roidesombres225" target="_blank">@Roidesombres225</a><br>
        <span class="icon">📢</span> Canal Telegram : <a href="https://t.me/SOLITAIREHACK" target="_blank">SOLITAIREHACK</a><br>
        <span class="icon">🎨</span> Je suis aussi concepteur graphique et créateur de logiciels.<br>
        <span style="color:#d84315; font-size:22px; font-weight:bold;">Vous avez un projet en tête ? Contactez-moi, je suis là pour vous !</span>
    </div>
</body></html>"""

def generer_prediction_lisible(nom, valeur, team1, team2):
    """Génère une phrase prédictive claire pour chaque pari, en précisant l'équipe si besoin."""
    if nom.startswith("Victoire "):
        return f"{nom}"
    if nom.startswith("Handicap "):
        return f"{nom}"
    if nom.startswith("Plus de") or nom.startswith("Moins de"):
        return f"{nom}"
    if nom.startswith("Score exact"):
        return f"{nom}"
    if nom.startswith("Double chance"):
        return f"{nom}"
    if nom.startswith("Nombre de buts"):
        return f"{nom}"
    if team1 and team1 in nom:
        return f"{nom} ({team1})"
    if team2 and team2 in nom:
        return f"{nom} ({team2})"
    return nom

ANALYTICS_TEMPLATE = """<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Analytics Dashboard | Sports Predictions</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        :root {
            --bg-primary: #f4f4f4;
            --bg-secondary: #ffffff;
            --text-primary: #2c3e50;
            --border-color: #ddd;
        }

        [data-theme="dark"] {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --text-primary: #e0e0e0;
            --border-color: #555;
        }

        body {
            font-family: Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            margin: 0;
            padding: 20px;
            transition: all 0.3s ease;
        }

        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .chart-card {
            background: var(--bg-secondary);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }

        .chart-card h3 {
            margin-top: 0;
            color: var(--text-primary);
        }

        .chart-container {
            position: relative;
            height: 400px;
        }

        .back-btn {
            display: inline-block;
            padding: 10px 20px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-bottom: 20px;
        }

        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #3498db;
            border: none;
            border-radius: 50px;
            padding: 10px 15px;
            color: white;
            cursor: pointer;
            font-size: 16px;
        }
    </style>
</head><body>
    <button id="theme-toggle" class="theme-toggle" onclick="toggleTheme()">🌙 Sombre</button>

    <div class="dashboard-container">
        <a href="/" class="back-btn">&larr; Retour aux matchs</a>
        <h1>📊 Dashboard Analytics Avancé</h1>

        <div class="chart-grid">
            <!-- Évolution des cotes -->
            <div class="chart-card">
                <h3>📈 Évolution des cotes en temps réel</h3>
                <div class="chart-container">
                    <canvas id="oddsChart"></canvas>
                </div>
            </div>

            <!-- Heatmap des performances -->
            <div class="chart-card">
                <h3>🔥 Heatmap des performances par ligue</h3>
                <div class="chart-container">
                    <canvas id="heatmapChart"></canvas>
                </div>
            </div>

            <!-- Radar chart de comparaison -->
            <div class="chart-card">
                <h3>🎯 Comparaison radar des équipes</h3>
                <div class="chart-container">
                    <canvas id="radarChart"></canvas>
                </div>
            </div>

            <!-- Timeline des événements -->
            <div class="chart-card">
                <h3>⏱️ Timeline des événements</h3>
                <div class="chart-container">
                    <canvas id="timelineChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Gestion du thème
        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeButton(newTheme);
        }

        function updateThemeButton(theme) {
            const button = document.getElementById('theme-toggle');
            button.innerHTML = theme === 'dark' ? '☀️ Clair' : '🌙 Sombre';
        }

        // Charger le thème sauvegardé
        document.addEventListener('DOMContentLoaded', function() {
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateThemeButton(savedTheme);

            initCharts();
        });

        function initCharts() {
            // 1. Graphique d'évolution des cotes
            const oddsCtx = document.getElementById('oddsChart').getContext('2d');
            new Chart(oddsCtx, {
                type: 'line',
                data: {
                    labels: ['10:00', '10:30', '11:00', '11:30', '12:00'],
                    datasets: [{
                        label: 'Victoire Équipe 1',
                        data: [2.1, 2.0, 1.95, 1.9, 1.85],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Match Nul',
                        data: [3.2, 3.3, 3.4, 3.5, 3.6],
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Victoire Équipe 2',
                        data: [3.8, 3.9, 4.0, 4.1, 4.2],
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Évolution des cotes 1X2'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Cotes'
                            }
                        }
                    }
                }
            });

            // 2. Heatmap des performances
            const heatmapCtx = document.getElementById('heatmapChart').getContext('2d');
            new Chart(heatmapCtx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Équipes',
                        data: [
                            {x: 15, y: 8, r: 10},
                            {x: 12, y: 6, r: 8},
                            {x: 18, y: 12, r: 12},
                            {x: 9, y: 4, r: 6},
                            {x: 21, y: 15, r: 15}
                        ],
                        backgroundColor: [
                            'rgba(231, 76, 60, 0.6)',
                            'rgba(243, 156, 18, 0.6)',
                            'rgba(39, 174, 96, 0.6)',
                            'rgba(52, 152, 219, 0.6)',
                            'rgba(155, 89, 182, 0.6)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Performance des équipes (Buts marqués vs Points)'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Buts marqués'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Points'
                            }
                        }
                    }
                }
            });

            // 3. Radar chart de comparaison
            const radarCtx = document.getElementById('radarChart').getContext('2d');
            new Chart(radarCtx, {
                type: 'radar',
                data: {
                    labels: ['Attaque', 'Défense', 'Forme', 'H2H', 'Domicile', 'Extérieur'],
                    datasets: [{
                        label: 'Équipe 1',
                        data: [8, 6, 7, 5, 8, 6],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.2)',
                        pointBackgroundColor: '#e74c3c'
                    }, {
                        label: 'Équipe 2',
                        data: [6, 8, 5, 7, 6, 8],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.2)',
                        pointBackgroundColor: '#3498db'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Comparaison des forces des équipes'
                        }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 10
                        }
                    }
                }
            });

            // 4. Timeline des événements
            const timelineCtx = document.getElementById('timelineChart').getContext('2d');
            new Chart(timelineCtx, {
                type: 'bar',
                data: {
                    labels: ['0-15min', '15-30min', '30-45min', '45-60min', '60-75min', '75-90min'],
                    datasets: [{
                        label: 'Buts Équipe 1',
                        data: [1, 0, 1, 0, 1, 0],
                        backgroundColor: '#e74c3c'
                    }, {
                        label: 'Buts Équipe 2',
                        data: [0, 1, 0, 1, 0, 1],
                        backgroundColor: '#3498db'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Timeline des buts par période'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Nombre de buts'
                            }
                        }
                    }
                }
            });
        }
    </script>
</body></html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
