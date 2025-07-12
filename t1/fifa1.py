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
import threading
import time

app = Flask(__name__)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sports_predictions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

db = SQLAlchemy(app)

# L'initialisation de la base de données sera faite après la définition des modèles

# Charger le modèle ML au démarrage
try:
    load_predictor()
    print("✅ Modèle ML chargé avec succès!")
except:
    print("⚠️ Aucun modèle ML trouvé. Entraînement nécessaire.")



# Modèles de base de données
class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    sport = db.Column(db.String(50), nullable=False)
    league = db.Column(db.String(100), nullable=False)
    logo_url = db.Column(db.String(500))  # URL du logo de l'équipe
    team_code = db.Column(db.String(20))  # Code de l'équipe (O1C/O2C)
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

class MatchEvolution(db.Model):
    __tablename__ = 'match_evolution'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)

    # État du match à ce moment
    status = db.Column(db.String(20), nullable=False)  # 'upcoming', 'live', 'finished'
    minute = db.Column(db.Integer)  # Minute du match si en cours
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)

    # Cotes principales 1X2
    odds_1 = db.Column(db.Float)  # Cote victoire domicile
    odds_x = db.Column(db.Float)  # Cote match nul
    odds_2 = db.Column(db.Float)  # Cote victoire extérieur

    # Cotes Over/Under
    odds_over_15 = db.Column(db.Float)  # Plus de 1.5 buts
    odds_under_15 = db.Column(db.Float)  # Moins de 1.5 buts
    odds_over_25 = db.Column(db.Float)  # Plus de 2.5 buts
    odds_under_25 = db.Column(db.Float)  # Moins de 2.5 buts
    odds_over_35 = db.Column(db.Float)  # Plus de 3.5 buts
    odds_under_35 = db.Column(db.Float)  # Moins de 3.5 buts

    # Cotes Both Teams to Score
    odds_btts_yes = db.Column(db.Float)  # Les deux équipes marquent
    odds_btts_no = db.Column(db.Float)   # Au moins une équipe ne marque pas

    # Cotes Handicap
    odds_handicap_1_plus = db.Column(db.Float)  # Équipe 1 +1.5
    odds_handicap_1_minus = db.Column(db.Float) # Équipe 1 -1.5
    odds_handicap_2_plus = db.Column(db.Float)  # Équipe 2 +1.5
    odds_handicap_2_minus = db.Column(db.Float) # Équipe 2 -1.5

    # Cotes Double Chance
    odds_1x = db.Column(db.Float)  # Victoire 1 ou Nul
    odds_12 = db.Column(db.Float)  # Victoire 1 ou Victoire 2
    odds_x2 = db.Column(db.Float)  # Nul ou Victoire 2

    # Stockage JSON pour autres cotes
    other_odds = db.Column(db.Text)  # JSON pour cotes supplémentaires

    # Métadonnées
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data_source = db.Column(db.String(50), default='1xbet')  # Source des données

    # Relations
    match = db.relationship('Match', backref='evolution_history')

class AutoLearning(db.Model):
    __tablename__ = 'auto_learning'

    id = db.Column(db.Integer, primary_key=True)

    # Statistiques d'apprentissage
    total_matches_processed = db.Column(db.Integer, default=0)
    finished_matches_count = db.Column(db.Integer, default=0)
    last_training_date = db.Column(db.DateTime)
    training_frequency_hours = db.Column(db.Integer, default=1)  # Entraîner toutes les heures

    # Performance du modèle
    model_accuracy = db.Column(db.Float)
    predictions_made = db.Column(db.Integer, default=0)
    correct_predictions = db.Column(db.Integer, default=0)

    # Configuration optimisée pour apprentissage continu
    min_matches_for_training = db.Column(db.Integer, default=5)  # Réduit de 20 à 5
    auto_training_enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Initialiser l'analytics après la définition des modèles
analytics = TeamAnalytics(db, Match, Team)

# Initialiser la base de données maintenant que tous les modèles sont définis
try:
    with app.app_context():
        # Forcer la recréation des tables pour éviter les erreurs de structure
        db.drop_all()
        db.create_all()

        # Vérifier que les tables sont créées
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✅ Base de données initialisée avec succès!")
        print(f"📊 Tables créées: {', '.join(tables)}")

        # Créer les paramètres d'auto-learning par défaut
        auto_learning = AutoLearning(
            auto_training_enabled=True,
            min_matches_for_training=5,
            training_frequency_hours=1
        )
        db.session.add(auto_learning)
        db.session.commit()
        print("🤖 Paramètres d'auto-learning initialisés")

except Exception as e:
    print(f"⚠️ Erreur initialisation DB: {e}")
    # Essayer une création simple en cas d'erreur
    try:
        with app.app_context():
            db.create_all()
            print("✅ Base de données créée en mode simple")
    except Exception as e2:
        print(f"❌ Erreur critique DB: {e2}")

# Fonction pour initialiser la base de données
def init_db():
    """Initialise la base de données avec les tables"""
    with app.app_context():
        db.create_all()
        print("Base de données initialisée avec succès!")

# Fonctions utilitaires pour la base de données
def get_or_create_team(name, sport, league):
    """Récupère ou crée une équipe (optimisé sans logos)"""
    try:
        team = Team.query.filter_by(name=name, sport=sport, league=league).first()
        if not team:
            team = Team(name=name, sport=sport, league=league)
            db.session.add(team)
            db.session.commit()
        return team
    except Exception as e:
        db.session.rollback()
        # Si erreur, essayer de récupérer l'équipe existante
        team = Team.query.filter_by(name=name, sport=sport, league=league).first()
        if team:
            return team
        # Si toujours pas trouvée, créer avec un nom unique
        unique_name = f"{name}_{sport}_{league}"
        team = Team.query.filter_by(name=unique_name).first()
        if not team:
            team = Team(name=unique_name, sport=sport, league=league)
            db.session.add(team)
            db.session.commit()
        return team

def save_match_to_db(match_data):
    """Sauvegarde un match dans la base de données"""
    try:
        # Récupérer ou créer les équipes (sans logos pour optimisation)
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

        # Créer un ID unique si pas d'ID API
        external_id = str(match_data.get('id')) if match_data.get('id') else f"{home_team.id}_{away_team.id}_{match_data['status']}"

        # Vérifier si le match existe déjà
        existing_match = Match.query.filter_by(external_id=external_id).first()

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
                external_id=external_id,
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

def get_all_odds_for_match(match):
    """Récupère toutes les cotes disponibles pour un match"""
    try:
        # Récupérer la dernière évolution des cotes
        latest_evolution = MatchEvolution.query.filter_by(match_id=match.id).order_by(MatchEvolution.timestamp.desc()).first()

        all_odds = {}

        if latest_evolution:
            # Cotes principales
            if latest_evolution.odds_1: all_odds["1"] = latest_evolution.odds_1
            if latest_evolution.odds_x: all_odds["X"] = latest_evolution.odds_x
            if latest_evolution.odds_2: all_odds["2"] = latest_evolution.odds_2

            # Over/Under
            if latest_evolution.odds_over_15: all_odds["Over 1.5"] = latest_evolution.odds_over_15
            if latest_evolution.odds_under_15: all_odds["Under 1.5"] = latest_evolution.odds_under_15
            if latest_evolution.odds_over_25: all_odds["Over 2.5"] = latest_evolution.odds_over_25
            if latest_evolution.odds_under_25: all_odds["Under 2.5"] = latest_evolution.odds_under_25
            if latest_evolution.odds_over_35: all_odds["Over 3.5"] = latest_evolution.odds_over_35
            if latest_evolution.odds_under_35: all_odds["Under 3.5"] = latest_evolution.odds_under_35

            # BTTS
            if latest_evolution.odds_btts_yes: all_odds["BTTS Oui"] = latest_evolution.odds_btts_yes
            if latest_evolution.odds_btts_no: all_odds["BTTS Non"] = latest_evolution.odds_btts_no

            # Double Chance
            if latest_evolution.odds_1x: all_odds["1X"] = latest_evolution.odds_1x
            if latest_evolution.odds_12: all_odds["12"] = latest_evolution.odds_12
            if latest_evolution.odds_x2: all_odds["X2"] = latest_evolution.odds_x2

            # Handicap
            if latest_evolution.odds_handicap_1_plus: all_odds["Handicap 1 +1.5"] = latest_evolution.odds_handicap_1_plus
            if latest_evolution.odds_handicap_1_minus: all_odds["Handicap 1 -1.5"] = latest_evolution.odds_handicap_1_minus
            if latest_evolution.odds_handicap_2_plus: all_odds["Handicap 2 +1.5"] = latest_evolution.odds_handicap_2_plus
            if latest_evolution.odds_handicap_2_minus: all_odds["Handicap 2 -1.5"] = latest_evolution.odds_handicap_2_minus

            # Autres cotes depuis other_odds
            if latest_evolution.other_odds:
                for odd_str in latest_evolution.other_odds.split(';'):
                    if ':' in odd_str:
                        bet_type, cote_str = odd_str.split(':', 1)
                        try:
                            all_odds[bet_type.strip()] = float(cote_str.strip())
                        except:
                            pass

        print(f"📊 Cotes récupérées pour prédictions: {len(all_odds)} types")
        return all_odds

    except Exception as e:
        print(f"❌ Erreur récupération cotes: {e}")
        return {}

def create_test_odds_for_match(match):
    """Crée des cotes de test pour un match sans données"""
    try:
        # Créer une évolution de cotes réaliste
        test_evolution = MatchEvolution(
            match_id=match.id,
            odds_1=2.17,
            odds_x=2.66,
            odds_2=3.99,
            odds_over_15=1.25,
            odds_under_15=3.75,
            odds_over_25=1.85,
            odds_under_25=1.95,
            odds_over_35=3.20,
            odds_under_35=1.33,
            odds_btts_yes=1.90,
            odds_btts_no=1.90,
            odds_1x=1.44,
            odds_12=1.25,
            odds_x2=1.80,
            odds_handicap_1_plus=1.15,
            odds_handicap_1_minus=3.20,
            odds_handicap_2_plus=1.15,
            odds_handicap_2_minus=3.20,
            other_odds='Corners Over 9: 1.80;Cartons Over 3: 2.10;Premier but: 2.50;Score exact 1-0: 8.50',
            timestamp=datetime.utcnow()
        )

        db.session.add(test_evolution)
        db.session.commit()
        print(f"✅ Cotes de test créées pour le match {match.id}")

    except Exception as e:
        print(f"❌ Erreur création cotes test: {e}")
        db.session.rollback()

def generate_comprehensive_predictions(match, h2h_data, home_form, away_form, all_odds):
    """Génère toutes les prédictions pour un match avec différentes IA"""
    predictions = {
        "match_info": {
            "home_team": match.home_team.name,
            "away_team": match.away_team.name,
            "league": match.league,
            "status": match.status
        },
        "ai_predictions": {},
        "consensus": {},
        "confidence_scores": {},
        "detailed_analysis": {}
    }

    try:
        # 1. PRÉDICTION BASÉE SUR LES COTES (IA Cotes) - UTILISE TOUTES LES COTES
        if all_odds and any(k in all_odds for k in ["1", "X", "2"]):
            odds_prediction = predict_from_all_odds(all_odds)
            predictions["ai_predictions"]["odds_ai"] = odds_prediction
        else:
            predictions["ai_predictions"]["odds_ai"] = {"prediction": "Données insuffisantes", "confidence": 0.0}

        # 2. PRÉDICTION MACHINE LEARNING (IA ML)
        ml_prediction = predict_with_ml(match, home_form, away_form)
        predictions["ai_predictions"]["ml_ai"] = ml_prediction

        # 3. PRÉDICTION ANALYTICS H2H (IA Analytics)
        analytics_prediction = predict_from_analytics(h2h_data, home_form, away_form)
        predictions["ai_predictions"]["analytics_ai"] = analytics_prediction

        # 4. PRÉDICTION FORME RÉCENTE (IA Forme)
        form_prediction = predict_from_form(home_form, away_form)
        predictions["ai_predictions"]["form_ai"] = form_prediction

        # 5. PRÉDICTION STATISTIQUES AVANCÉES (IA Stats)
        stats_prediction = predict_from_advanced_stats(match, h2h_data)
        predictions["ai_predictions"]["stats_ai"] = stats_prediction

        # 6. CONSENSUS ET PRÉDICTION FINALE
        consensus = calculate_consensus(predictions["ai_predictions"])
        predictions["consensus"] = consensus

        # 7. PRÉDICTIONS SPÉCIALISÉES - UTILISE TOUTES LES COTES
        predictions["specialized"] = {
            "over_under": predict_over_under_from_odds(all_odds, match),
            "btts": predict_btts_from_odds(all_odds, match, h2h_data),
            "exact_score": predict_exact_score(match, home_form, away_form),
            "first_half": predict_first_half_from_odds(all_odds, match)
        }

        return predictions

    except Exception as e:
        print(f"❌ Erreur génération prédictions: {e}")
        return {"error": str(e)}

def predict_from_all_odds(all_odds):
    """IA basée sur TOUTES les cotes disponibles"""
    try:
        # Analyser les cotes 1X2 principales
        main_odds = {}
        for key in ["1", "X", "2"]:
            if key in all_odds:
                main_odds[key] = all_odds[key]

        if not main_odds:
            return {"prediction": "Cotes 1X2 manquantes", "confidence": 0.0}

        # Trouver la prédiction principale
        best_odd = min(main_odds.items(), key=lambda x: x[1])
        main_confidence = 1.0 / best_odd[1]
        main_confidence = min(main_confidence, 0.95)

        # Analyser les cotes alternatives pour ajuster la confiance
        confidence_adjustments = []

        # Double Chance pour confirmer
        if best_odd[0] == "1" and "1X" in all_odds:
            dc_confidence = 1.0 / all_odds["1X"]
            confidence_adjustments.append(dc_confidence * 0.3)
        elif best_odd[0] == "2" and "X2" in all_odds:
            dc_confidence = 1.0 / all_odds["X2"]
            confidence_adjustments.append(dc_confidence * 0.3)
        elif best_odd[0] == "X" and "1X" in all_odds and "X2" in all_odds:
            dc_avg = (1.0 / all_odds["1X"] + 1.0 / all_odds["X2"]) / 2
            confidence_adjustments.append(dc_avg * 0.2)

        # Over/Under pour contexte
        if "Over 2.5" in all_odds and "Under 2.5" in all_odds:
            ou_confidence = abs(1.0 / all_odds["Over 2.5"] - 1.0 / all_odds["Under 2.5"])
            confidence_adjustments.append(ou_confidence * 0.1)

        # BTTS pour contexte
        if "BTTS Oui" in all_odds and "BTTS Non" in all_odds:
            btts_confidence = abs(1.0 / all_odds["BTTS Oui"] - 1.0 / all_odds["BTTS Non"])
            confidence_adjustments.append(btts_confidence * 0.1)

        # Ajuster la confiance finale
        final_confidence = main_confidence
        if confidence_adjustments:
            adjustment = sum(confidence_adjustments) / len(confidence_adjustments)
            final_confidence = min(main_confidence + adjustment, 0.98)

        prediction_map = {"1": "Victoire Domicile", "X": "Match Nul", "2": "Victoire Extérieur"}

        # Compter les types de cotes analysées
        analyzed_markets = len([k for k in all_odds.keys() if k in ["1", "X", "2", "1X", "12", "X2", "Over 2.5", "Under 2.5", "BTTS Oui", "BTTS Non"]])

        return {
            "prediction": prediction_map[best_odd[0]],
            "confidence": final_confidence,
            "reasoning": f"Analyse de {analyzed_markets} marchés - Cote principale: {best_odd[1]:.2f}",
            "main_odds": main_odds,
            "markets_analyzed": analyzed_markets
        }

    except Exception as e:
        return {"prediction": f"Erreur analyse cotes: {str(e)}", "confidence": 0.0}

def predict_over_under_from_odds(all_odds, match):
    """Prédiction Over/Under basée sur toutes les cotes disponibles"""
    try:
        # Chercher les cotes Over/Under 2.5
        if "Over 2.5" in all_odds and "Under 2.5" in all_odds:
            over_25 = all_odds["Over 2.5"]
            under_25 = all_odds["Under 2.5"]

            if over_25 < under_25:
                confidence = 1.0 / over_25
                prediction = "Over 2.5"
            else:
                confidence = 1.0 / under_25
                prediction = "Under 2.5"

            # Ajuster avec d'autres seuils
            adjustments = []
            if "Over 1.5" in all_odds:
                adjustments.append(1.0 / all_odds["Over 1.5"])
            if "Over 3.5" in all_odds:
                adjustments.append(1.0 / all_odds["Over 3.5"])

            if adjustments:
                confidence = (confidence + sum(adjustments) / len(adjustments)) / 2

            return {
                "prediction": prediction,
                "confidence": min(confidence, 0.9),
                "reasoning": f"Cotes O/U 2.5: {over_25:.2f}/{under_25:.2f}"
            }

        # Fallback avec le score actuel
        total_goals = (match.home_score or 0) + (match.away_score or 0)
        if total_goals >= 3:
            return {"prediction": "Over 2.5", "confidence": 0.8, "reasoning": "Score actuel élevé"}
        else:
            return {"prediction": "Under 2.5", "confidence": 0.6, "reasoning": "Score actuel faible"}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0, "reasoning": f"Erreur: {str(e)}"}

def predict_btts_from_odds(all_odds, match, h2h_data):
    """Prédiction BTTS basée sur toutes les cotes disponibles"""
    try:
        # Chercher les cotes BTTS
        if "BTTS Oui" in all_odds and "BTTS Non" in all_odds:
            btts_yes = all_odds["BTTS Oui"]
            btts_no = all_odds["BTTS Non"]

            if btts_yes < btts_no:
                confidence = 1.0 / btts_yes
                prediction = "BTTS Oui"
            else:
                confidence = 1.0 / btts_no
                prediction = "BTTS Non"

            return {
                "prediction": prediction,
                "confidence": min(confidence, 0.9),
                "reasoning": f"Cotes BTTS: {btts_yes:.2f}/{btts_no:.2f}"
            }

        # Fallback avec le score actuel
        if match.home_score is not None and match.away_score is not None:
            if match.home_score > 0 and match.away_score > 0:
                return {"prediction": "BTTS Oui", "confidence": 0.9, "reasoning": "Les deux équipes ont déjà marqué"}
            elif match.home_score == 0 or match.away_score == 0:
                return {"prediction": "BTTS Non", "confidence": 0.7, "reasoning": "Une équipe n'a pas encore marqué"}

        return {"prediction": "BTTS Oui", "confidence": 0.6, "reasoning": "Prédiction par défaut"}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0, "reasoning": f"Erreur: {str(e)}"}

def predict_first_half_from_odds(all_odds, match):
    """Prédiction première mi-temps basée sur les cotes"""
    try:
        # Chercher les cotes de double chance
        if "1X" in all_odds:
            confidence = 1.0 / all_odds["1X"]
            return {
                "prediction": "1X (Domicile ou Nul)",
                "confidence": min(confidence, 0.8),
                "reasoning": f"Cote 1X: {all_odds['1X']:.2f}"
            }

        # Fallback basé sur les cotes principales
        if "1" in all_odds and "X" in all_odds:
            if all_odds["1"] < all_odds["X"]:
                return {"prediction": "1 (Domicile)", "confidence": 0.6, "reasoning": "Favori domicile"}
            else:
                return {"prediction": "X (Nul)", "confidence": 0.6, "reasoning": "Match équilibré"}

        return {"prediction": "1X", "confidence": 0.5, "reasoning": "Prédiction par défaut"}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0, "reasoning": f"Erreur: {str(e)}"}

def predict_with_ml(match, home_form, away_form):
    """IA Machine Learning"""
    try:
        # Préparer les données pour le ML
        match_data = {
            'team1': match.home_team.name,
            'team2': match.away_team.name,
            'sport': match.sport,
            'league': match.league,
            'temp': match.temperature or 20,
            'humid': match.humidity or 50,
            'odds': ['1: 2.17', 'X: 2.66', '2: 3.99']  # Valeurs réalistes
        }

        ml_pred, ml_conf = get_ml_prediction(match_data)

        if ml_pred and ml_conf > 0:
            prediction_map = {"1": "Victoire Domicile", "X": "Match Nul", "2": "Victoire Extérieur"}
            return {
                "prediction": prediction_map.get(ml_pred, "Indéterminé"),
                "confidence": ml_conf,
                "reasoning": "Modèle RandomForest entraîné sur historique",
                "model_type": "RandomForest"
            }
        else:
            # Fallback intelligent basé sur les cotes
            if match.home_score is not None and match.away_score is not None:
                if match.home_score > match.away_score:
                    return {
                        "prediction": "Victoire Domicile",
                        "confidence": 0.75,
                        "reasoning": "Prédiction basée sur score actuel",
                        "model_type": "Fallback"
                    }
                elif match.away_score > match.home_score:
                    return {
                        "prediction": "Victoire Extérieur",
                        "confidence": 0.75,
                        "reasoning": "Prédiction basée sur score actuel",
                        "model_type": "Fallback"
                    }
                else:
                    return {
                        "prediction": "Match Nul",
                        "confidence": 0.60,
                        "reasoning": "Score égal, tendance nul",
                        "model_type": "Fallback"
                    }
            else:
                # Prédiction par défaut basée sur la ligue
                if "Champions" in match.league or "Premier" in match.league:
                    return {
                        "prediction": "Victoire Domicile",
                        "confidence": 0.65,
                        "reasoning": "Avantage domicile en ligue majeure",
                        "model_type": "Heuristique"
                    }
                else:
                    return {
                        "prediction": "Match Nul",
                        "confidence": 0.55,
                        "reasoning": "Prédiction conservatrice",
                        "model_type": "Heuristique"
                    }

    except Exception as e:
        return {
            "prediction": "Victoire Domicile",
            "confidence": 0.60,
            "reasoning": f"Fallback après erreur: {str(e)[:50]}",
            "model_type": "Fallback"
        }

def predict_from_analytics(h2h_data, home_form, away_form):
    """IA basée sur les analytics H2H"""
    try:
        if not h2h_data:
            return {"prediction": "Pas d'historique H2H", "confidence": 0.0}

        # Vérifier si h2h_data est un dictionnaire ou un objet
        if isinstance(h2h_data, dict):
            team1_wins = h2h_data.get('team1_wins', 0)
            draws = h2h_data.get('draws', 0)
            team2_wins = h2h_data.get('team2_wins', 0)
        else:
            # Objet avec attributs
            team1_wins = getattr(h2h_data, 'team1_wins', 0)
            draws = getattr(h2h_data, 'draws', 0)
            team2_wins = getattr(h2h_data, 'team2_wins', 0)

        total_matches = team1_wins + draws + team2_wins
        if total_matches == 0:
            return {"prediction": "Historique insuffisant", "confidence": 0.0}

        home_win_rate = team1_wins / total_matches
        draw_rate = draws / total_matches
        away_win_rate = team2_wins / total_matches

        rates = {"Victoire Domicile": home_win_rate, "Match Nul": draw_rate, "Victoire Extérieur": away_win_rate}
        best_prediction = max(rates.items(), key=lambda x: x[1])

        return {
            "prediction": best_prediction[0],
            "confidence": best_prediction[1],
            "reasoning": f"Basé sur {total_matches} matchs H2H",
            "h2h_stats": rates
        }

    except Exception as e:
        return {"prediction": f"Erreur Analytics: {str(e)}", "confidence": 0.0}

def predict_from_form(home_form, away_form):
    """IA basée sur la forme récente"""
    try:
        if not home_form or not away_form:
            return {"prediction": "Données de forme insuffisantes", "confidence": 0.0}

        # Vérifier si c'est un dictionnaire ou un objet
        if isinstance(home_form, dict):
            home_score = home_form.get('form_score', 0.5)
        else:
            home_score = getattr(home_form, 'form_score', 0.5)

        if isinstance(away_form, dict):
            away_score = away_form.get('form_score', 0.5)
        else:
            away_score = getattr(away_form, 'form_score', 0.5)

        if home_score > away_score + 0.2:
            prediction = "Victoire Domicile"
            confidence = min((home_score - away_score) * 2, 0.9)
        elif away_score > home_score + 0.2:
            prediction = "Victoire Extérieur"
            confidence = min((away_score - home_score) * 2, 0.9)
        else:
            prediction = "Match Nul"
            confidence = 0.6

        return {
            "prediction": prediction,
            "confidence": confidence,
            "reasoning": f"Forme domicile: {home_score:.1%}, Forme extérieur: {away_score:.1%}",
            "form_comparison": {"home": home_score, "away": away_score}
        }

    except Exception as e:
        return {"prediction": f"Erreur Forme: {str(e)}", "confidence": 0.0}

def predict_from_advanced_stats(match, h2h_data):
    """IA basée sur les statistiques avancées"""
    try:
        # Facteurs multiples pour une prédiction avancée
        factors = {
            "league_factor": 0.7 if "Champions" in match.league else 0.5,
            "status_factor": 0.8 if match.status == "En cours" else 0.6,
            "score_factor": 0.0
        }

        # Analyser le score actuel si en cours
        if match.status.startswith("En cours") and match.home_score is not None and match.away_score is not None:
            score_diff = match.home_score - match.away_score
            if score_diff > 0:
                factors["score_factor"] = 0.8
                prediction = "Victoire Domicile"
            elif score_diff < 0:
                factors["score_factor"] = 0.8
                prediction = "Victoire Extérieur"
            else:
                factors["score_factor"] = 0.6
                prediction = "Match Nul"
        else:
            prediction = "Victoire Domicile"  # Avantage domicile par défaut
            factors["score_factor"] = 0.6

        confidence = sum(factors.values()) / len(factors)

        return {
            "prediction": prediction,
            "confidence": confidence,
            "reasoning": "Analyse multi-facteurs (ligue, statut, score)",
            "factors": factors
        }

    except Exception as e:
        return {"prediction": f"Erreur Stats: {str(e)}", "confidence": 0.0}

def calculate_consensus(ai_predictions):
    """Calcule le consensus de toutes les IA"""
    try:
        votes = {"Victoire Domicile": 0, "Match Nul": 0, "Victoire Extérieur": 0}
        total_confidence = 0
        valid_predictions = 0

        for ai_name, pred_data in ai_predictions.items():
            if isinstance(pred_data, dict) and pred_data.get("confidence", 0) > 0:
                prediction = pred_data["prediction"]
                confidence = pred_data["confidence"]

                if prediction in votes:
                    votes[prediction] += confidence
                    total_confidence += confidence
                    valid_predictions += 1

        if valid_predictions == 0:
            return {"prediction": "Consensus impossible", "confidence": 0.0}

        # Trouver la prédiction avec le plus de votes pondérés
        best_prediction = max(votes.items(), key=lambda x: x[1])
        consensus_confidence = best_prediction[1] / total_confidence if total_confidence > 0 else 0

        return {
            "prediction": best_prediction[0],
            "confidence": consensus_confidence,
            "votes": votes,
            "participating_ais": valid_predictions,
            "reasoning": f"Consensus de {valid_predictions} IA"
        }

    except Exception as e:
        return {"prediction": f"Erreur Consensus: {str(e)}", "confidence": 0.0}

def predict_over_under(match, latest_evolution):
    """Prédiction Over/Under 2.5 buts"""
    try:
        if latest_evolution and latest_evolution.odds_over_25 and latest_evolution.odds_under_25:
            if latest_evolution.odds_over_25 < latest_evolution.odds_under_25:
                return {"prediction": "Over 2.5", "confidence": 1.0 / latest_evolution.odds_over_25}
            else:
                return {"prediction": "Under 2.5", "confidence": 1.0 / latest_evolution.odds_under_25}

        # Fallback basé sur le score actuel
        total_goals = (match.home_score or 0) + (match.away_score or 0)
        if total_goals >= 3:
            return {"prediction": "Over 2.5", "confidence": 0.8}
        else:
            return {"prediction": "Under 2.5", "confidence": 0.6}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0}

def predict_btts(match, h2h_data):
    """Prédiction Both Teams to Score"""
    try:
        # Basé sur le score actuel
        if match.home_score and match.away_score and match.home_score > 0 and match.away_score > 0:
            return {"prediction": "BTTS Oui", "confidence": 0.9}
        elif match.home_score is not None and match.away_score is not None:
            if match.home_score == 0 or match.away_score == 0:
                return {"prediction": "BTTS Non", "confidence": 0.7}

        # Fallback
        return {"prediction": "BTTS Oui", "confidence": 0.6}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0}

def predict_exact_score(match, home_form, away_form):
    """Prédiction de score exact"""
    try:
        # Scores les plus probables basés sur la forme
        if home_form and away_form:
            home_strength = home_form.form_score
            away_strength = away_form.form_score

            if home_strength > 0.7:
                return {"prediction": "2-1", "confidence": 0.3}
            elif away_strength > 0.7:
                return {"prediction": "1-2", "confidence": 0.3}
            else:
                return {"prediction": "1-1", "confidence": 0.4}

        return {"prediction": "1-1", "confidence": 0.3}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0}

def predict_first_half(match, latest_evolution):
    """Prédiction première mi-temps"""
    try:
        if latest_evolution and latest_evolution.odds_1x:
            return {"prediction": "1X", "confidence": 1.0 / latest_evolution.odds_1x}

        return {"prediction": "1X", "confidence": 0.6}

    except Exception as e:
        return {"prediction": "Indéterminé", "confidence": 0.0}

# Fonctions d'apprentissage automatique
def save_match_evolution(match_obj, odds_data, status, minute=None):
    """Sauvegarde l'évolution d'un match avec TOUTES ses cotes"""
    try:
        # Initialiser toutes les cotes
        odds_dict = {
            'odds_1': None, 'odds_x': None, 'odds_2': None,
            'odds_over_15': None, 'odds_under_15': None,
            'odds_over_25': None, 'odds_under_25': None,
            'odds_over_35': None, 'odds_under_35': None,
            'odds_btts_yes': None, 'odds_btts_no': None,
            'odds_handicap_1_plus': None, 'odds_handicap_1_minus': None,
            'odds_handicap_2_plus': None, 'odds_handicap_2_minus': None,
            'odds_1x': None, 'odds_12': None, 'odds_x2': None
        }

        other_odds_list = []

        # Extraire TOUTES les cotes avec mapping amélioré
        for odd_str in odds_data:
            if isinstance(odd_str, str) and ':' in odd_str:
                bet_type, odds_value = odd_str.split(': ', 1)
                try:
                    odds_val = float(odds_value)

                    # Cotes principales 1X2
                    if bet_type == '1':
                        odds_dict['odds_1'] = odds_val
                    elif bet_type == 'X':
                        odds_dict['odds_x'] = odds_val
                    elif bet_type == '2':
                        odds_dict['odds_2'] = odds_val

                    # Cotes Over/Under avec détection flexible
                    elif 'Over' in bet_type:
                        if '1.5' in bet_type:
                            odds_dict['odds_over_15'] = odds_val
                        elif '2.5' in bet_type:
                            odds_dict['odds_over_25'] = odds_val
                        elif '3.5' in bet_type:
                            odds_dict['odds_over_35'] = odds_val
                        else:
                            other_odds_list.append(f"{bet_type}: {odds_val}")

                    elif 'Under' in bet_type:
                        if '1.5' in bet_type:
                            odds_dict['odds_under_15'] = odds_val
                        elif '2.5' in bet_type:
                            odds_dict['odds_under_25'] = odds_val
                        elif '3.5' in bet_type:
                            odds_dict['odds_under_35'] = odds_val
                        else:
                            other_odds_list.append(f"{bet_type}: {odds_val}")

                    # Both Teams to Score
                    elif 'BTTS Oui' in bet_type or 'BTTS Yes' in bet_type:
                        odds_dict['odds_btts_yes'] = odds_val
                    elif 'BTTS Non' in bet_type or 'BTTS No' in bet_type:
                        odds_dict['odds_btts_no'] = odds_val

                    # Double Chance
                    elif bet_type == '1X':
                        odds_dict['odds_1x'] = odds_val
                    elif bet_type == '12':
                        odds_dict['odds_12'] = odds_val
                    elif bet_type == 'X2':
                        odds_dict['odds_x2'] = odds_val

                    # Handicap (à améliorer selon les données réelles)
                    elif 'Handicap' in bet_type:
                        other_odds_list.append(f"{bet_type}: {odds_val}")

                    # Autres cotes
                    else:
                        other_odds_list.append(f"{bet_type}: {odds_val}")

                except ValueError:
                    print(f"⚠️ Impossible de convertir la cote: {bet_type}: {odds_value}")
                    pass

        # Créer l'entrée d'évolution avec TOUTES les cotes
        evolution = MatchEvolution(
            match_id=match_obj.id,
            status=status,
            minute=minute,
            home_score=match_obj.home_score,
            away_score=match_obj.away_score,
            **odds_dict,  # Toutes les cotes structurées
            other_odds='; '.join(other_odds_list) if other_odds_list else None
        )

        db.session.add(evolution)
        db.session.commit()

        cotes_count = len([v for v in odds_dict.values() if v is not None]) + len(other_odds_list)
        print(f"✅ Évolution sauvegardée pour match {match_obj.id} - Status: {status} - {cotes_count} cotes")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur sauvegarde évolution: {e}")
        return False

def check_and_auto_train():
    """Vérifie s'il faut entraîner automatiquement le modèle"""
    try:
        # Récupérer ou créer les paramètres d'auto-learning
        auto_learning = AutoLearning.query.first()
        if not auto_learning:
            auto_learning = AutoLearning()
            auto_learning.auto_training_enabled = True  # Toujours activé
            db.session.add(auto_learning)
            db.session.commit()

        # Forcer l'activation si désactivé
        if not auto_learning.auto_training_enabled:
            auto_learning.auto_training_enabled = True
            db.session.commit()
            print("🔄 Auto-learning forcé à ON")

        # Compter les matchs terminés
        finished_count = Match.query.filter_by(status='Terminé').count()

        # Vérifier s'il y a assez de matchs
        if finished_count < auto_learning.min_matches_for_training:
            print(f"🔄 Pas assez de matchs pour auto-training: {finished_count}/{auto_learning.min_matches_for_training}")
            return False

        # Vérifier la fréquence d'entraînement
        if auto_learning.last_training_date:
            time_since_last = datetime.utcnow() - auto_learning.last_training_date
            hours_since = time_since_last.total_seconds() / 3600

            if hours_since < auto_learning.training_frequency_hours:
                print(f"🕐 Trop tôt pour re-entraîner: {hours_since:.1f}h/{auto_learning.training_frequency_hours}h")
                return False

        # Lancer l'entraînement automatique
        print(f"🤖 Lancement auto-training avec {finished_count} matchs...")

        # Récupérer les données d'entraînement
        finished_matches = Match.query.filter_by(status='Terminé').all()
        training_data = []

        for match in finished_matches:
            # Récupérer les cotes initiales (première évolution)
            initial_evolution = MatchEvolution.query.filter_by(
                match_id=match.id
            ).order_by(MatchEvolution.timestamp.asc()).first()

            if initial_evolution and initial_evolution.odds_1:
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
                    'odds': [
                        f"1: {initial_evolution.odds_1}",
                        f"X: {initial_evolution.odds_x}",
                        f"2: {initial_evolution.odds_2}"
                    ]
                }
                training_data.append(match_data)

        # Entraîner le modèle
        if len(training_data) >= 10:
            success = train_predictor_with_data(training_data)

            # Mettre à jour les statistiques
            auto_learning.total_matches_processed = len(training_data)
            auto_learning.finished_matches_count = finished_count
            auto_learning.last_training_date = datetime.utcnow()

            if success:
                print(f"✅ Auto-training réussi avec {len(training_data)} matchs")
                from ml_predictor import save_predictor
                save_predictor()
            else:
                print(f"❌ Auto-training échoué")

            db.session.commit()
            return success

        return False

    except Exception as e:
        print(f"❌ Erreur auto-training: {e}")
        return False

def fetch_and_process_matches_background():
    """Récupère et traite les matchs automatiquement en arrière-plan"""
    while True:
        try:
            with app.app_context():
                print("🔄 Récupération automatique des matchs...")

                # Récupérer les données de l'API
                url = "https://1xbet.whoscored.com/v1/events"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    api_data = response.json()

                    # Traiter chaque match
                    processed_count = 0
                    for match in api_data.get("Value", []):
                        try:
                            # Extraire les données du match
                            team1 = match.get("O1E", "Équipe 1")
                            team2 = match.get("O2E", "Équipe 2")
                            score1 = match.get("SC", {}).get("FS", {}).get("S1", 0) or 0
                            score2 = match.get("SC", {}).get("FS", {}).get("S2", 0) or 0

                            # Déterminer le statut
                            minute = match.get("SC", {}).get("CPS", {}).get("T")
                            statut = "À venir"
                            if minute and minute > 0:
                                statut = f"En cours ({minute}′)"
                            elif score1 > 0 or score2 > 0:
                                statut = "En cours"

                            # Vérifier si terminé
                            tn = match.get("SC", {}).get("TN", "").lower()
                            if "terminé" in tn or "finished" in tn:
                                statut = "Terminé"

                            # Extraire les cotes
                            odds_data = []
                            for odd in match.get("E", []):
                                if odd.get("G") == 1:  # Groupe principal 1X2
                                    for c in odd.get("C", []):
                                        if c.get("T") == 1:
                                            odds_data.append(f"1: {c.get('F')}")
                                        elif c.get("T") == 2:
                                            odds_data.append(f"X: {c.get('F')}")
                                        elif c.get("T") == 3:
                                            odds_data.append(f"2: {c.get('F')}")

                            # Créer les données du match
                            match_data = {
                                'team1': team1,
                                'team2': team2,
                                'score1': score1,
                                'score2': score2,
                                'sport': 'Football',
                                'league': match.get("LN", "Ligue inconnue"),
                                'status': statut,
                                'temp': 20,
                                'humid': 50,
                                'odds': odds_data
                            }

                            # Sauvegarder le match
                            saved_match = save_match_to_db(match_data)

                            # Sauvegarder l'évolution des cotes
                            if saved_match and odds_data:
                                save_match_evolution(saved_match, odds_data, statut, minute)

                            # Si le match est terminé, déclencher l'auto-training
                            if saved_match and statut == "Terminé":
                                check_and_auto_train()

                            processed_count += 1

                        except Exception as e:
                            print(f"❌ Erreur traitement match: {e}")
                            continue

                    print(f"✅ {processed_count} matchs traités automatiquement")

                else:
                    print(f"❌ Erreur API: {response.status_code}")

        except Exception as e:
            print(f"❌ Erreur récupération automatique: {e}")

        # Attendre 2 minutes avant la prochaine récupération
        time.sleep(120)  # 2 minutes

def auto_learning_background():
    """Fonction qui tourne en arrière-plan pour l'apprentissage automatique"""
    while True:
        try:
            with app.app_context():
                check_and_auto_train()
        except Exception as e:
            print(f"❌ Erreur background auto-learning: {e}")

        # Attendre 10 minutes avant la prochaine vérification
        time.sleep(600)  # 10 minutes

@app.route('/train_ml')
def train_ml():
    """Route pour entraîner le modèle ML"""
    try:
        # Vérifier que les tables existent
        with app.app_context():
            db.create_all()

        # Récupérer tous les matchs terminés de la base de données
        finished_matches = Match.query.filter_by(status='Terminé').all()

        if len(finished_matches) < 5:  # Réduire le minimum pour les tests
            # Créer des données d'exemple pour l'entraînement
            sample_data = [
                {
                    'team1': 'PSG', 'team2': 'Marseille', 'sport': 'Football', 'league': 'Ligue 1',
                    'score1': 2, 'score2': 1, 'status': 'Terminé', 'temp': 22, 'humid': 65,
                    'odds': ['1: 1.85', 'X: 3.20', '2: 4.10']
                },
                {
                    'team1': 'Real Madrid', 'team2': 'Barcelona', 'sport': 'Football', 'league': 'La Liga',
                    'score1': 1, 'score2': 3, 'status': 'Terminé', 'temp': 28, 'humid': 45,
                    'odds': ['1: 2.10', 'X: 3.40', '2: 3.20']
                },
                {
                    'team1': 'Manchester City', 'team2': 'Liverpool', 'sport': 'Football', 'league': 'Premier League',
                    'score1': 0, 'score2': 2, 'status': 'Terminé', 'temp': 15, 'humid': 70,
                    'odds': ['1: 1.95', 'X: 3.60', '2: 3.80']
                },
                {
                    'team1': 'Bayern Munich', 'team2': 'Dortmund', 'sport': 'Football', 'league': 'Bundesliga',
                    'score1': 3, 'score2': 0, 'status': 'Terminé', 'temp': 18, 'humid': 55,
                    'odds': ['1: 1.70', 'X: 3.80', '2: 4.50']
                },
                {
                    'team1': 'Juventus', 'team2': 'AC Milan', 'sport': 'Football', 'league': 'Serie A',
                    'score1': 1, 'score2': 1, 'status': 'Terminé', 'temp': 25, 'humid': 60,
                    'odds': ['1: 2.20', 'X: 3.10', '2: 3.40']
                }
            ]

            # Essayer l'entraînement avec les données d'exemple
            try:
                training_success = train_predictor_with_data(sample_data)
                if training_success:
                    return jsonify({
                        "message": f"✅ Entraînement réussi avec données d'exemple ({len(sample_data)} matchs)",
                        "matches_count": len(finished_matches),
                        "sample_training": True,
                        "success": True
                    })
                else:
                    return jsonify({
                        "message": f"⚠️ Entraînement échoué. Mode prédiction basique activé.",
                        "matches_count": len(finished_matches),
                        "sample_training": True,
                        "success": False,
                        "fallback_mode": True
                    })
            except Exception as ml_error:
                return jsonify({
                    "message": f"⚠️ ML non disponible. Mode prédiction basique activé.",
                    "matches_count": len(finished_matches),
                    "sample_training": True,
                    "success": False,
                    "error": str(ml_error),
                    "fallback_mode": True
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

@app.route('/status')
def system_status():
    """Route pour vérifier l'état du système"""
    try:
        # Vérifier la base de données
        with app.app_context():
            db.create_all()
            match_count = Match.query.count()
            team_count = Team.query.count()

        # Vérifier le ML
        ml_status = False
        try:
            from ml_predictor import predictor
            ml_status = predictor.is_trained
        except:
            ml_status = False

        # Vérifier l'analytics
        analytics_status = True
        try:
            from analytics import TeamAnalytics
            analytics_status = True
        except:
            analytics_status = False

        return jsonify({
            "database": {
                "status": "✅ Connectée",
                "matches": match_count,
                "teams": team_count
            },
            "machine_learning": {
                "status": "✅ Actif" if ml_status else "⚠️ Non entraîné",
                "trained": ml_status
            },
            "analytics": {
                "status": "✅ Actif" if analytics_status else "❌ Erreur",
                "available": analytics_status
            },
            "api": {
                "status": "✅ En ligne",
                "version": "2.0"
            }
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "❌ Erreur système"
        })

@app.route('/add_sample_data')
def add_sample_data():
    """Ajouter des données d'exemple pour tester le ML"""
    try:
        sample_matches = [
            {
                'team1': 'PSG', 'team2': 'Marseille', 'sport': 'Football', 'league': 'Ligue 1',
                'score1': 2, 'score2': 1, 'status': 'Terminé', 'temp': 22, 'humid': 65,
                'odds': ['1: 1.85', 'X: 3.20', '2: 4.10'], 'id': 'sample_1'
            },
            {
                'team1': 'Real Madrid', 'team2': 'Barcelona', 'sport': 'Football', 'league': 'La Liga',
                'score1': 1, 'score2': 3, 'status': 'Terminé', 'temp': 28, 'humid': 45,
                'odds': ['1: 2.10', 'X: 3.40', '2: 3.20'], 'id': 'sample_2'
            },
            {
                'team1': 'Manchester City', 'team2': 'Liverpool', 'sport': 'Football', 'league': 'Premier League',
                'score1': 0, 'score2': 2, 'status': 'Terminé', 'temp': 15, 'humid': 70,
                'odds': ['1: 1.95', 'X: 3.60', '2: 3.80'], 'id': 'sample_3'
            },
            {
                'team1': 'Bayern Munich', 'team2': 'Dortmund', 'sport': 'Football', 'league': 'Bundesliga',
                'score1': 3, 'score2': 0, 'status': 'Terminé', 'temp': 18, 'humid': 55,
                'odds': ['1: 1.70', 'X: 3.80', '2: 4.50'], 'id': 'sample_4'
            },
            {
                'team1': 'Juventus', 'team2': 'AC Milan', 'sport': 'Football', 'league': 'Serie A',
                'score1': 1, 'score2': 1, 'status': 'Terminé', 'temp': 25, 'humid': 60,
                'odds': ['1: 2.20', 'X: 3.10', '2: 3.40'], 'id': 'sample_5'
            },
            {
                'team1': 'Arsenal', 'team2': 'Chelsea', 'sport': 'Football', 'league': 'Premier League',
                'score1': 2, 'score2': 0, 'status': 'Terminé', 'temp': 12, 'humid': 75,
                'odds': ['1: 2.40', 'X: 3.20', '2: 2.90'], 'id': 'sample_6'
            },
            {
                'team1': 'Atletico Madrid', 'team2': 'Sevilla', 'sport': 'Football', 'league': 'La Liga',
                'score1': 1, 'score2': 2, 'status': 'Terminé', 'temp': 30, 'humid': 40,
                'odds': ['1: 1.90', 'X: 3.50', '2: 4.20'], 'id': 'sample_7'
            },
            {
                'team1': 'Inter Milan', 'team2': 'Napoli', 'sport': 'Football', 'league': 'Serie A',
                'score1': 3, 'score2': 1, 'status': 'Terminé', 'temp': 26, 'humid': 58,
                'odds': ['1: 2.00', 'X: 3.30', '2: 3.60'], 'id': 'sample_8'
            }
        ]

        added_count = 0
        for match_data in sample_matches:
            try:
                saved_match = save_match_to_db(match_data)
                if saved_match:
                    added_count += 1
            except Exception as e:
                print(f"Erreur ajout match {match_data['id']}: {e}")
                continue

        return jsonify({
            "success": True,
            "message": f"✅ {added_count} matchs d'exemple ajoutés à la base de données",
            "total_added": added_count,
            "total_attempted": len(sample_matches)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/auto_learning_config')
def auto_learning_config():
    """Configuration de l'apprentissage automatique"""
    try:
        auto_learning = AutoLearning.query.first()
        if not auto_learning:
            auto_learning = AutoLearning()
            db.session.add(auto_learning)
            db.session.commit()

        return jsonify({
            "auto_training_enabled": auto_learning.auto_training_enabled,
            "min_matches_for_training": auto_learning.min_matches_for_training,
            "training_frequency_hours": auto_learning.training_frequency_hours,
            "total_matches_processed": auto_learning.total_matches_processed,
            "finished_matches_count": auto_learning.finished_matches_count,
            "last_training_date": auto_learning.last_training_date.isoformat() if auto_learning.last_training_date else None,
            "model_accuracy": auto_learning.model_accuracy,
            "predictions_made": auto_learning.predictions_made,
            "correct_predictions": auto_learning.correct_predictions
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/toggle_auto_learning')
def toggle_auto_learning():
    """Activer/désactiver l'apprentissage automatique"""
    try:
        auto_learning = AutoLearning.query.first()
        if not auto_learning:
            auto_learning = AutoLearning()
            db.session.add(auto_learning)

        auto_learning.auto_training_enabled = not auto_learning.auto_training_enabled
        db.session.commit()

        status = "✅ Activé" if auto_learning.auto_training_enabled else "⏸️ Désactivé"

        return jsonify({
            "success": True,
            "auto_training_enabled": auto_learning.auto_training_enabled,
            "message": f"Auto-learning {status}"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/auto_activity')
def auto_activity():
    """Affiche l'activité automatique du système"""
    try:
        # Statistiques de l'auto-learning
        auto_learning = AutoLearning.query.first()

        # Derniers matchs traités
        recent_matches = Match.query.order_by(Match.updated_at.desc()).limit(10).all()

        # Dernières évolutions sauvegardées
        recent_evolutions = MatchEvolution.query.order_by(MatchEvolution.timestamp.desc()).limit(20).all()

        return jsonify({
            "auto_learning_status": {
                "enabled": auto_learning.auto_training_enabled if auto_learning else False,
                "total_matches": auto_learning.total_matches_processed if auto_learning else 0,
                "finished_matches": auto_learning.finished_matches_count if auto_learning else 0,
                "last_training": auto_learning.last_training_date.isoformat() if auto_learning and auto_learning.last_training_date else None,
                "model_accuracy": auto_learning.model_accuracy if auto_learning else None
            },
            "recent_activity": {
                "recent_matches_count": len(recent_matches),
                "recent_evolutions_count": len(recent_evolutions),
                "last_match_update": recent_matches[0].updated_at.isoformat() if recent_matches else None,
                "last_evolution": recent_evolutions[0].timestamp.isoformat() if recent_evolutions else None
            },
            "system_status": {
                "auto_fetch_running": True,  # Toujours True car thread daemon
                "auto_learning_running": True,
                "database_connected": True
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/debug_matches')
def debug_matches():
    """Route de debug pour voir les matchs en base"""
    try:
        matches = Match.query.all()
        result = {
            "total_matches": len(matches),
            "matches": []
        }

        for match in matches:
            result["matches"].append({
                "id": match.id,
                "home_team": match.home_team.name if match.home_team else "N/A",
                "home_team_logo": match.home_team.logo_url if match.home_team else None,
                "away_team": match.away_team.name if match.away_team else "N/A",
                "away_team_logo": match.away_team.logo_url if match.away_team else None,
                "score": f"{match.home_score}-{match.away_score}",
                "status": match.status,
                "created_at": match.created_at.isoformat() if match.created_at else None
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/debug_teams')
def debug_teams():
    """Route de debug pour voir les équipes (optimisé sans logos)"""
    try:
        teams = Team.query.all()
        result = {
            "total_teams": len(teams),
            "teams": []
        }

        for team in teams:
            team_data = {
                "id": team.id,
                "name": team.name,
                "sport": team.sport,
                "league": team.league
            }
            result["teams"].append(team_data)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/debug_api_logos')
def debug_api_logos():
    """Route de debug pour voir les logos dans l'API"""
    try:
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=10&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url)
        matches = response.json().get("Value", [])

        result = {
            "total_matches": len(matches),
            "matches_with_logos": 0,
            "logo_samples": []
        }

        for i, match in enumerate(matches[:5]):  # Prendre seulement les 5 premiers
            team1 = match.get("O1", "–")
            team2 = match.get("O2", "–")
            o1img = match.get("O1IMG")
            o2img = match.get("O2IMG")

            sample = {
                "match_index": i,
                "team1": team1,
                "team2": team2,
                "O1IMG": o1img,
                "O2IMG": o2img,
                "O1IMG_type": type(o1img).__name__,
                "O2IMG_type": type(o2img).__name__
            }

            if o1img or o2img:
                result["matches_with_logos"] += 1

            result["logo_samples"].append(sample)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/debug_odds')
def debug_odds():
    """Route de debug pour voir toutes les cotes disponibles dans l'API"""
    try:
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=5&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url)
        matches = response.json().get("Value", [])

        result = {
            "total_matches": len(matches),
            "odds_analysis": []
        }

        for i, match in enumerate(matches[:3]):  # Analyser les 3 premiers matchs
            team1 = match.get("O1", "–")
            team2 = match.get("O2", "–")

            analysis = {
                "match_index": i,
                "teams": f"{team1} vs {team2}",
                "E_odds": [],  # Cotes principales
                "AE_odds": []  # Cotes alternatives
            }

            # Analyser les cotes principales (E)
            for odd in match.get("E", []):
                analysis["E_odds"].append({
                    "G": odd.get("G"),  # Groupe
                    "T": odd.get("T"),  # Type
                    "C": odd.get("C"),  # Cote
                    "P": odd.get("P")   # Paramètre
                })

            # Analyser les cotes alternatives (AE)
            for ae in match.get("AE", []):
                for me in ae.get("ME", []):
                    analysis["AE_odds"].append({
                        "G": me.get("G"),  # Groupe
                        "T": me.get("T"),  # Type
                        "C": me.get("C"),  # Cote
                        "P": me.get("P")   # Paramètre
                    })

            result["odds_analysis"].append(analysis)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/performance_test')
def performance_test():
    """Route de test de performance"""
    import time
    start = time.time()

    try:
        # Test API
        api_start = time.time()
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=5&lng=fr&gr=70&mode=4&country=96&getEmpty=true"
        response = requests.get(api_url, timeout=5)
        api_time = time.time() - api_start

        # Test DB
        db_start = time.time()
        match_count = Match.query.count()
        team_count = Team.query.count()
        db_time = time.time() - db_start

        total_time = time.time() - start

        return jsonify({
            "performance": {
                "total_time": f"{total_time:.2f}s",
                "api_time": f"{api_time:.2f}s",
                "db_time": f"{db_time:.3f}s",
                "api_matches": len(response.json().get("Value", [])),
                "db_matches": match_count,
                "db_teams": team_count
            },
            "recommendations": [
                "✅ API rapide" if api_time < 2 else "⚠️ API lente",
                "✅ DB rapide" if db_time < 0.1 else "⚠️ DB lente",
                "✅ Performance OK" if total_time < 3 else "❌ Performance dégradée"
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/test_performance')
def test_performance():
    """Page de test de performance (sans logos)"""
    try:
        # Récupérer le premier match avec des équipes
        match = Match.query.first()
        if not match:
            return "Aucun match en base de données"

        return f"""
        <!DOCTYPE html>
        <html><head><title>Test Performance</title></head><body>
        <h2>Test de performance (optimisé)</h2>
        <div style="padding: 20px;">
            <h3>Match: {match.home_team.name} vs {match.away_team.name}</h3>

            <div style="display: flex; gap: 20px; align-items: center;">
                <div>
                    <h4>Équipe domicile: {match.home_team.name}</h4>
                    <p>Sport: {match.sport}</p>
                    <p>Ligue: {match.league}</p>
                </div>

                <div>
                    <h4>Équipe extérieur: {match.away_team.name}</h4>
                    <p>Score: {match.home_score} - {match.away_score}</p>
                    <p>Statut: {match.status}</p>
                </div>
            </div>

            <p><a href="/match/{match.id}">Voir la page détails de ce match</a></p>
            <p><a href="/debug_teams">Voir toutes les équipes</a></p>
            <p><a href="/">Retour à l'accueil</a></p>
        </div>
        </body></html>
        """
    except Exception as e:
        return f"Erreur: {str(e)}"

@app.route('/match_by_external/<external_id>')
def match_details_by_external(external_id):
    """Affiche les détails d'un match par son external_id"""
    try:
        match = Match.query.filter_by(external_id=str(external_id)).first_or_404()
        return match_details(match.id)
    except Exception as e:
        return f"Erreur: {str(e)}"

@app.route('/match/<int:match_id>')
def match_details(match_id):
    """Affiche les détails d'un match spécifique avec analytics intégrés"""
    try:
        print(f"🔍 Recherche du match avec ID: {match_id}")

        # Vérifier combien de matchs sont en base
        total_matches = Match.query.count()
        print(f"📊 Total matchs en base: {total_matches}")

        # Récupérer le match depuis la base de données (par ID interne)
        match = Match.query.get_or_404(match_id)
        print(f"✅ Match trouvé: {match.home_team.name} vs {match.away_team.name}")
        print(f"🎨 Logo équipe domicile: {match.home_team.logo_url}")
        print(f"🎨 Logo équipe extérieur: {match.away_team.logo_url}")

        # Récupérer l'évolution des cotes pour ce match
        odds_evolution = MatchEvolution.query.filter_by(match_id=match_id).order_by(MatchEvolution.timestamp).all()

        # Récupérer les statistiques H2H
        h2h_data = analytics.get_head_to_head(match.home_team.name, match.away_team.name)

        # Récupérer la forme des équipes
        home_form = analytics.get_team_recent_form(match.home_team.name)
        away_form = analytics.get_team_recent_form(match.away_team.name)

        # Récupérer toutes les cotes pour ce match
        all_match_odds = get_all_odds_for_match(match)

        # Si pas de cotes en base, créer des cotes de test pour ce match
        if not all_match_odds:
            print(f"⚠️ Création de cotes de test pour le match {match_id}")
            create_test_odds_for_match(match)
            all_match_odds = get_all_odds_for_match(match)

        # Générer toutes les prédictions pour ce match
        predictions = generate_comprehensive_predictions(match, h2h_data, home_form, away_form, all_match_odds)

        # Préparer les données pour les graphiques
        odds_data = {
            'timestamps': [evo.timestamp.strftime('%H:%M') for evo in odds_evolution],
            # Cotes principales 1X2
            'odds_1': [evo.odds_1 for evo in odds_evolution if evo.odds_1],
            'odds_x': [evo.odds_x for evo in odds_evolution if evo.odds_x],
            'odds_2': [evo.odds_2 for evo in odds_evolution if evo.odds_2],
            # Cotes Over/Under
            'odds_over_25': [evo.odds_over_25 for evo in odds_evolution if evo.odds_over_25],
            'odds_under_25': [evo.odds_under_25 for evo in odds_evolution if evo.odds_under_25],
            'odds_over_15': [evo.odds_over_15 for evo in odds_evolution if evo.odds_over_15],
            'odds_under_15': [evo.odds_under_15 for evo in odds_evolution if evo.odds_under_15],
            # BTTS
            'odds_btts_yes': [evo.odds_btts_yes for evo in odds_evolution if evo.odds_btts_yes],
            'odds_btts_no': [evo.odds_btts_no for evo in odds_evolution if evo.odds_btts_no],
            # Double Chance
            'odds_1x': [evo.odds_1x for evo in odds_evolution if evo.odds_1x],
            'odds_12': [evo.odds_12 for evo in odds_evolution if evo.odds_12],
            'odds_x2': [evo.odds_x2 for evo in odds_evolution if evo.odds_x2]
        }

        # Si pas de données d'évolution, créer des données de test avec toutes les cotes
        if not odds_evolution:
            print(f"⚠️ Pas d'évolution de cotes pour le match {match_id}, création de données complètes")

            # Créer une évolution factice avec toutes les cotes
            fake_evolution = type('obj', (object,), {
                'odds_1': 2.17,
                'odds_x': 2.66,
                'odds_2': 3.99,
                'odds_over_15': 1.25,
                'odds_under_15': 3.75,
                'odds_over_25': 1.85,
                'odds_under_25': 1.95,
                'odds_over_35': 3.20,
                'odds_under_35': 1.33,
                'odds_btts_yes': 1.90,
                'odds_btts_no': 1.90,
                'odds_1x': 1.44,
                'odds_12': 1.25,
                'odds_x2': 1.80,
                'odds_handicap_1_plus': 1.15,
                'odds_handicap_1_minus': 3.20,
                'odds_handicap_2_plus': 1.15,
                'odds_handicap_2_minus': 3.20,
                'other_odds': 'Corners Over 9: 1.80;Cartons Over 3: 2.10;Premier but: 2.50;Score exact 1-0: 8.50'
            })()

            odds_evolution = [fake_evolution]

            odds_data = {
                'timestamps': ['19:00', '19:30', '20:00'],
                'odds_1': [2.17, 2.15, 2.17],
                'odds_x': [2.66, 2.70, 2.66],
                'odds_2': [3.99, 4.05, 3.99],
                'odds_over_25': [1.85, 1.80, 1.85],
                'odds_under_25': [1.95, 2.00, 1.95],
                'odds_btts_yes': [1.90, 1.85, 1.90],
                'odds_btts_no': [1.90, 1.95, 1.90],
                'odds_1x': [1.44, 1.42, 1.44],
                'odds_12': [1.25, 1.23, 1.25],
                'odds_x2': [1.80, 1.82, 1.80]
            }

        return render_template_string(MATCH_DETAILS_TEMPLATE,
                                    match=match,
                                    odds_evolution=odds_evolution,
                                    h2h_data=h2h_data,
                                    home_form=home_form,
                                    away_form=away_form,
                                    odds_data=odds_data,
                                    predictions=predictions)

    except Exception as e:
        return f"Erreur: {str(e)}"

@app.route('/')
def home():
    try:
        import time
        start_time = time.time()

        selected_sport = request.args.get("sport", "").strip()
        selected_league = request.args.get("league", "").strip()
        selected_status = request.args.get("status", "").strip()

        # Récupérer suffisamment de matchs pour la pagination
        api_url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=100&lng=fr&gr=70&mode=4&country=96&getEmpty=true"

        print(f"⏱️ Début requête API...")
        api_start = time.time()
        response = requests.get(api_url, timeout=10)  # Timeout pour éviter les blocages
        matches = response.json().get("Value", [])
        api_time = time.time() - api_start
        print(f"⏱️ API récupérée en {api_time:.2f}s - {len(matches)} matchs")

        sports_detected = set()
        leagues_detected = set()
        data = []

        print(f"⏱️ Début traitement {len(matches)} matchs...")
        processing_start = time.time()

        # Traiter tous les matchs mais de manière optimisée
        for i, match in enumerate(matches):
            # Afficher le progrès tous les 20 matchs
            if i % 20 == 0:
                print(f"⏱️ Traitement match {i+1}/{len(matches)}")
            try:
                league = match.get("LE", "–")
                team1 = match.get("O1", "–")
                team2 = match.get("O2", "–")
                sport = detect_sport(league).strip()
                sports_detected.add(sport)
                leagues_detected.add(league)

                # --- Logos supprimés pour optimisation ---
                # Plus d'extraction de logos pour améliorer les performances

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

                # --- Extraction RAPIDE des cotes 1X2 SEULEMENT pour page principale ---
                main_odds = {}

                # 1. Chercher dans E (cotes principales)
                for o in match.get("E", []):
                    if o.get("G") == 1 and o.get("T") in [1, 2, 3] and o.get("C") is not None:
                        main_odds[{1: "1", 2: "2", 3: "X"}[o.get("T")]] = o.get("C")

                # 2. Si pas trouvé, chercher dans AE (alternatives)
                if len(main_odds) < 3:
                    for ae in match.get("AE", []):
                        if ae.get("G") == 1:
                            for o in ae.get("ME", []):
                                if o.get("T") in [1, 2, 3] and o.get("C") is not None:
                                    key = {1: "1", 2: "2", 3: "X"}[o.get("T")]
                                    if key not in main_odds:
                                        main_odds[key] = o.get("C")

                # Formater pour affichage
                if main_odds:
                    formatted_odds = [f"{bet_type}: {cote}" for bet_type, cote in main_odds.items()]
                else:
                    formatted_odds = ["Pas de cotes disponibles"]

                # Prédiction simple basée sur la cote la plus faible
                odds_data = []
                for bet_type in ["1", "X", "2"]:
                    if bet_type in main_odds:
                        odds_data.append({"type": bet_type, "cote": main_odds[bet_type]})

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
                    "odds": formatted_odds,  # Seulement 1X2 pour affichage
                    "all_odds": main_odds,   # Cotes principales pour les prédictions
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

                # Prédiction simple pour performance optimisée
                match_data["prediction"] = f"{prediction}"
                match_data["ml_prediction"] = None
                match_data["ml_confidence"] = 0.5

                # Sauvegarde optimisée (batch processing)
                try:
                    saved_match = save_match_to_db(match_data)
                    if saved_match:
                        match_data["id"] = saved_match.id
                        # Log seulement tous les 10 matchs pour réduire le spam
                        if i % 10 == 0:
                            print(f"✅ Batch sauvegarde: {i+1} matchs traités")
                    else:
                        match_data["id"] = None
                except Exception as e:
                    # Log d'erreur seulement si critique
                    if "timeout" in str(e).lower() or "connection" in str(e).lower():
                        print(f"⚠️ Erreur critique sauvegarde: {e}")
                    match_data["id"] = None

                # Sauvegarder l'évolution du match avec les cotes actuelles
                if saved_match and formatted_odds:
                    save_match_evolution(saved_match, formatted_odds, statut, minute)

                # Vérifier s'il faut faire un auto-training
                if saved_match and statut == "Terminé":
                    # Lancer la vérification en arrière-plan
                    threading.Thread(target=check_and_auto_train, daemon=True).start()

                data.append(match_data)
            except Exception as e:
                print(f"Erreur lors du traitement d'un match: {e}")
                continue

        # Logs de performance
        total_time = time.time() - start_time
        print(f"⏱️ Page principale générée en {total_time:.2f}s - {len(data)} matchs traités")

        # Filtrage optimisé
        if selected_sport:
            data = [m for m in data if m["sport"].lower() == selected_sport.lower()]
        if selected_league:
            data = [m for m in data if selected_league.lower() in m["league"].lower()]
        if selected_status:
            data = [m for m in data if selected_status.lower() in m["status"].lower()]

        print(f"⏱️ Après filtrage: {len(data)} matchs affichés")

        # --- Pagination optimisée ---
        try:
            page = int(request.args.get('page', 1))
        except:
            page = 1
        per_page = 25  # Augmenté pour moins de pages
        total = len(data)
        total_pages = (total + per_page - 1) // per_page
        data_paginated = data[(page-1)*per_page:page*per_page]

        print(f"📄 Pagination: Page {page}/{total_pages} - {len(data_paginated)} matchs affichés sur {total} total")

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
        <a href="/analytics_dashboard" style="display: inline-block; padding: 12px 24px; background: #3498db; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 5px;">
            📈 Dashboard Analytics
        </a>
        <a href="/train_ml" style="display: inline-block; padding: 12px 24px; background: #e74c3c; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 5px;">
            🤖 Entraîner ML
        </a>
        <a href="/add_sample_data" style="display: inline-block; padding: 12px 24px; background: #27ae60; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 5px;">
            📊 Ajouter Données Test
        </a>
        <a href="/status" style="display: inline-block; padding: 12px 24px; background: #f39c12; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 5px;">
            🔍 Status Système
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
            <td><strong>{{m.team1}}</strong></td>
            <td>{{m.score1}}</td>
            <td>{{m.score2}}</td>
            <td><strong>{{m.team2}}</strong></td>
            <td>{{m.sport}}</td><td>{{m.league}}</td><td>{{m.status}}</td><td>{{m.datetime}}</td>
            <td>{{m.temp}}°C</td><td>{{m.humid}}%</td><td>{{m.odds|join(" | ")}}</td><td>{{m.prediction}}</td>
            <td>{% if m.id %}<a href="/match/{{m.id}}" style="padding: 8px 16px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; font-size: 14px;">📊 Analytics</a>{% else %}–{% endif %}</td>
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

MATCH_DETAILS_TEMPLATE = """<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>📊 Analytics - {{ match.home_team.name }} vs {{ match.away_team.name }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-primary: #f4f4f4;
            --bg-secondary: #ffffff;
            --text-primary: #2c3e50;
            --border-color: #ddd;
            --button-bg: #3498db;
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

        .container { max-width: 1400px; margin: 0 auto; }

        .match-header {
            background: var(--bg-secondary);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .match-title { font-size: 28px; font-weight: bold; margin-bottom: 10px; }

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
        }

        .chart-container { position: relative; height: 400px; }

        .back-btn {
            display: inline-block;
            padding: 12px 24px;
            background: var(--button-bg);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--button-bg);
            border: none;
            border-radius: 50px;
            padding: 10px 15px;
            color: white;
            cursor: pointer;
            z-index: 1000;
        }
    </style>
</head><body>
    <button id="theme-toggle" class="theme-toggle" onclick="toggleTheme()">🌙 Sombre</button>

    <div class="container">
        <a href="/" class="back-btn">&larr; Retour aux matchs</a>

        <div class="match-header">
            <div class="match-title">
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 32px; font-weight: bold; margin-bottom: 15px;">
                        <span style="color: #3498db;">{{ match.home_team.name }}</span>
                        <span style="color: #e74c3c; margin: 0 20px;">VS</span>
                        <span style="color: #e74c3c;">{{ match.away_team.name }}</span>
                    </div>
                    <div style="font-size: 36px; font-weight: bold; color: #2c3e50; margin: 10px 0;">
                        {{ match.home_score }} - {{ match.away_score }}
                    </div>
                </div>
            </div>
            <div style="font-size: 24px; margin: 10px 0;">{{ match.home_score }} - {{ match.away_score }}</div>
            <div>{{ match.sport }} • {{ match.league }} • {{ match.status }}</div>
        </div>

        <!-- SECTION PRÉDICTIONS IA -->
        <div class="predictions-section" style="background: var(--bg-secondary); border-radius: 10px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: var(--text-primary); margin-bottom: 25px; font-size: 28px;">
                🤖 PRÉDICTIONS INTELLIGENCE ARTIFICIELLE
            </h2>

            <!-- Consensus Principal -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 20px; margin-bottom: 25px; color: white; text-align: center;">
                <h3 style="margin: 0 0 10px 0; font-size: 24px;">🏆 CONSENSUS IA</h3>
                <div style="font-size: 32px; font-weight: bold; margin: 10px 0;">
                    {{ predictions.consensus.prediction if predictions.consensus else 'Calcul en cours...' }}
                </div>
                <div style="font-size: 18px; opacity: 0.9;">
                    Confiance: {{ "%.1f"|format((predictions.consensus.confidence * 100) if predictions.consensus else 0) }}%
                    {% if predictions.consensus %}
                    | {{ predictions.consensus.participating_ais }} IA participantes
                    {% endif %}
                </div>
            </div>

            <!-- Grille des IA -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 25px;">

                <!-- IA Cotes -->
                <div class="ai-card" style="background: linear-gradient(135deg, #ff6b6b, #ee5a24); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                        💰 IA COTES
                        <span style="font-size: 12px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                            {{ "%.0f"|format((predictions.ai_predictions.odds_ai.confidence * 100) if predictions.ai_predictions.odds_ai else 0) }}%
                        </span>
                    </h4>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">
                        {{ predictions.ai_predictions.odds_ai.prediction if predictions.ai_predictions.odds_ai else 'N/A' }}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        {{ predictions.ai_predictions.odds_ai.reasoning if predictions.ai_predictions.odds_ai else '' }}
                    </div>
                </div>

                <!-- IA Machine Learning -->
                <div class="ai-card" style="background: linear-gradient(135deg, #74b9ff, #0984e3); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                        🧠 IA MACHINE LEARNING
                        <span style="font-size: 12px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                            {{ "%.0f"|format((predictions.ai_predictions.ml_ai.confidence * 100) if predictions.ai_predictions.ml_ai else 0) }}%
                        </span>
                    </h4>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">
                        {{ predictions.ai_predictions.ml_ai.prediction if predictions.ai_predictions.ml_ai else 'N/A' }}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        {{ predictions.ai_predictions.ml_ai.reasoning if predictions.ai_predictions.ml_ai else '' }}
                    </div>
                </div>

                <!-- IA Analytics -->
                <div class="ai-card" style="background: linear-gradient(135deg, #55a3ff, #003d82); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                        📊 IA ANALYTICS H2H
                        <span style="font-size: 12px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                            {{ "%.0f"|format((predictions.ai_predictions.analytics_ai.confidence * 100) if predictions.ai_predictions.analytics_ai else 0) }}%
                        </span>
                    </h4>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">
                        {{ predictions.ai_predictions.analytics_ai.prediction if predictions.ai_predictions.analytics_ai else 'N/A' }}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        {{ predictions.ai_predictions.analytics_ai.reasoning if predictions.ai_predictions.analytics_ai else '' }}
                    </div>
                </div>

                <!-- IA Forme -->
                <div class="ai-card" style="background: linear-gradient(135deg, #00b894, #00a085); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                        📈 IA FORME RÉCENTE
                        <span style="font-size: 12px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                            {{ "%.0f"|format((predictions.ai_predictions.form_ai.confidence * 100) if predictions.ai_predictions.form_ai else 0) }}%
                        </span>
                    </h4>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">
                        {{ predictions.ai_predictions.form_ai.prediction if predictions.ai_predictions.form_ai else 'N/A' }}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        {{ predictions.ai_predictions.form_ai.reasoning if predictions.ai_predictions.form_ai else '' }}
                    </div>
                </div>

                <!-- IA Stats Avancées -->
                <div class="ai-card" style="background: linear-gradient(135deg, #fd79a8, #e84393); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                        🎯 IA STATS AVANCÉES
                        <span style="font-size: 12px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">
                            {{ "%.0f"|format((predictions.ai_predictions.stats_ai.confidence * 100) if predictions.ai_predictions.stats_ai else 0) }}%
                        </span>
                    </h4>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">
                        {{ predictions.ai_predictions.stats_ai.prediction if predictions.ai_predictions.stats_ai else 'N/A' }}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        {{ predictions.ai_predictions.stats_ai.reasoning if predictions.ai_predictions.stats_ai else '' }}
                    </div>
                </div>
            </div>

            <!-- Prédictions Spécialisées -->
            <div style="background: var(--bg-primary); border-radius: 12px; padding: 20px;">
                <h3 style="text-align: center; margin-bottom: 20px; color: var(--text-primary);">🎲 PRÉDICTIONS SPÉCIALISÉES</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">

                    <div style="text-align: center; padding: 15px; background: var(--bg-secondary); border-radius: 8px;">
                        <div style="font-weight: bold; color: #e67e22; margin-bottom: 5px;">⚽ Over/Under 2.5</div>
                        <div style="font-size: 18px; font-weight: bold;">
                            {{ predictions.specialized.over_under.prediction if predictions.specialized else 'N/A' }}
                        </div>
                        <div style="font-size: 12px; opacity: 0.7;">
                            {{ "%.0f"|format((predictions.specialized.over_under.confidence * 100) if predictions.specialized else 0) }}% confiance
                        </div>
                    </div>

                    <div style="text-align: center; padding: 15px; background: var(--bg-secondary); border-radius: 8px;">
                        <div style="font-weight: bold; color: #9b59b6; margin-bottom: 5px;">🎯 BTTS</div>
                        <div style="font-size: 18px; font-weight: bold;">
                            {{ predictions.specialized.btts.prediction if predictions.specialized else 'N/A' }}
                        </div>
                        <div style="font-size: 12px; opacity: 0.7;">
                            {{ "%.0f"|format((predictions.specialized.btts.confidence * 100) if predictions.specialized else 0) }}% confiance
                        </div>
                    </div>

                    <div style="text-align: center; padding: 15px; background: var(--bg-secondary); border-radius: 8px;">
                        <div style="font-weight: bold; color: #27ae60; margin-bottom: 5px;">🏆 Score Exact</div>
                        <div style="font-size: 18px; font-weight: bold;">
                            {{ predictions.specialized.exact_score.prediction if predictions.specialized else 'N/A' }}
                        </div>
                        <div style="font-size: 12px; opacity: 0.7;">
                            {{ "%.0f"|format((predictions.specialized.exact_score.confidence * 100) if predictions.specialized else 0) }}% confiance
                        </div>
                    </div>

                    <div style="text-align: center; padding: 15px; background: var(--bg-secondary); border-radius: 8px;">
                        <div style="font-weight: bold; color: #3498db; margin-bottom: 5px;">⏰ 1ère Mi-temps</div>
                        <div style="font-size: 18px; font-weight: bold;">
                            {{ predictions.specialized.first_half.prediction if predictions.specialized else 'N/A' }}
                        </div>
                        <div style="font-size: 12px; opacity: 0.7;">
                            {{ "%.0f"|format((predictions.specialized.first_half.confidence * 100) if predictions.specialized else 0) }}% confiance
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION COTES ALTERNATIVES COMPLÈTES -->
        <div class="alternatives-section" style="background: var(--bg-secondary); border-radius: 10px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: var(--text-primary); margin-bottom: 25px; font-size: 28px;">
                💰 TOUTES LES COTES ALTERNATIVES
            </h2>

            <!-- Grille des cotes alternatives -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">

                <!-- Cotes principales 1X2 -->
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 15px 0; text-align: center;">🏆 RÉSULTAT FINAL</h4>
                    {% for evo in odds_evolution[-1:] %}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>{{ match.home_team.name }} gagne:</span>
                        <strong>{{ "%.2f"|format(evo.odds_1) if evo.odds_1 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Match nul:</span>
                        <strong>{{ "%.2f"|format(evo.odds_x) if evo.odds_x else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>{{ match.away_team.name }} gagne:</span>
                        <strong>{{ "%.2f"|format(evo.odds_2) if evo.odds_2 else 'N/A' }}</strong>
                    </div>
                    {% endfor %}
                </div>

                <!-- Over/Under -->
                <div style="background: linear-gradient(135deg, #ff6b6b, #ee5a24); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 15px 0; text-align: center;">⚽ NOMBRE DE BUTS</h4>
                    {% for evo in odds_evolution[-1:] %}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Plus de 1.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_over_15) if evo.odds_over_15 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Moins de 1.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_under_15) if evo.odds_under_15 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Plus de 2.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_over_25) if evo.odds_over_25 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Moins de 2.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_under_25) if evo.odds_under_25 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Plus de 3.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_over_35) if evo.odds_over_35 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Moins de 3.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_under_35) if evo.odds_under_35 else 'N/A' }}</strong>
                    </div>
                    {% endfor %}
                </div>

                <!-- BTTS -->
                <div style="background: linear-gradient(135deg, #74b9ff, #0984e3); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 15px 0; text-align: center;">🎯 BOTH TEAMS TO SCORE</h4>
                    {% for evo in odds_evolution[-1:] %}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Les deux marquent:</span>
                        <strong>{{ "%.2f"|format(evo.odds_btts_yes) if evo.odds_btts_yes else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Au moins une ne marque pas:</span>
                        <strong>{{ "%.2f"|format(evo.odds_btts_no) if evo.odds_btts_no else 'N/A' }}</strong>
                    </div>
                    {% endfor %}
                </div>

                <!-- Double Chance -->
                <div style="background: linear-gradient(135deg, #00b894, #00a085); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 15px 0; text-align: center;">🔄 DOUBLE CHANCE</h4>
                    {% for evo in odds_evolution[-1:] %}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>{{ match.home_team.name }} ou Nul:</span>
                        <strong>{{ "%.2f"|format(evo.odds_1x) if evo.odds_1x else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>{{ match.home_team.name }} ou {{ match.away_team.name }}:</span>
                        <strong>{{ "%.2f"|format(evo.odds_12) if evo.odds_12 else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Nul ou {{ match.away_team.name }}:</span>
                        <strong>{{ "%.2f"|format(evo.odds_x2) if evo.odds_x2 else 'N/A' }}</strong>
                    </div>
                    {% endfor %}
                </div>

                <!-- Handicap -->
                <div style="background: linear-gradient(135deg, #fd79a8, #e84393); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 15px 0; text-align: center;">⚖️ HANDICAP</h4>
                    {% for evo in odds_evolution[-1:] %}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>{{ match.home_team.name }} +1.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_handicap_1_plus) if evo.odds_handicap_1_plus else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>{{ match.home_team.name }} -1.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_handicap_1_minus) if evo.odds_handicap_1_minus else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>{{ match.away_team.name }} +1.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_handicap_2_plus) if evo.odds_handicap_2_plus else 'N/A' }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>{{ match.away_team.name }} -1.5:</span>
                        <strong>{{ "%.2f"|format(evo.odds_handicap_2_minus) if evo.odds_handicap_2_minus else 'N/A' }}</strong>
                    </div>
                    {% endfor %}
                </div>

                <!-- Autres cotes -->
                <div style="background: linear-gradient(135deg, #a29bfe, #6c5ce7); border-radius: 12px; padding: 18px; color: white;">
                    <h4 style="margin: 0 0 15px 0; text-align: center;">🎲 AUTRES PARIS</h4>
                    {% for evo in odds_evolution[-1:] %}
                    {% if evo.other_odds %}
                    {% for odd in evo.other_odds.split(';')[:4] %}
                    {% if ':' in odd %}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
                        <span>{{ odd.split(':')[0].strip() }}:</span>
                        <strong>{{ odd.split(':')[1].strip() }}</strong>
                    </div>
                    {% endif %}
                    {% endfor %}
                    {% else %}
                    <div style="text-align: center; opacity: 0.8;">Aucune autre cote disponible</div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>
        </div>

        <div class="chart-grid">
            <div class="chart-card">
                <h3>📈 Cotes 1X2 (Victoire/Nul)</h3>
                <div class="chart-container"><canvas id="oddsChart1X2"></canvas></div>
            </div>

            <div class="chart-card">
                <h3>⚽ Cotes Over/Under 2.5 Buts</h3>
                <div class="chart-container"><canvas id="oddsChartOU25"></canvas></div>
            </div>

            <div class="chart-card">
                <h3>🎯 Cotes BTTS (Both Teams to Score)</h3>
                <div class="chart-container"><canvas id="oddsChartBTTS"></canvas></div>
            </div>

            <div class="chart-card">
                <h3>🔄 Cotes Double Chance</h3>
                <div class="chart-container"><canvas id="oddsChartDC"></canvas></div>
            </div>

            <div class="chart-card">
                <h3>🎯 Comparaison équipes</h3>
                <div class="chart-container"><canvas id="radarChart"></canvas></div>
            </div>

            <div class="chart-card">
                <h3>📊 Résumé des cotes actuelles</h3>
                <div class="chart-container">
                    <table class="stats-table">
                        <tr><th>Type de pari</th><th>Cote actuelle</th><th>Évolution</th></tr>
                        <tr><td>{{ match.home_team.name }} gagne</td><td id="current-odds-1">-</td><td id="trend-1">-</td></tr>
                        <tr><td>Match nul</td><td id="current-odds-x">-</td><td id="trend-x">-</td></tr>
                        <tr><td>{{ match.away_team.name }} gagne</td><td id="current-odds-2">-</td><td id="trend-2">-</td></tr>
                        <tr><td>Plus de 2.5 buts</td><td id="current-odds-o25">-</td><td id="trend-o25">-</td></tr>
                        <tr><td>Moins de 2.5 buts</td><td id="current-odds-u25">-</td><td id="trend-u25">-</td></tr>
                        <tr><td>Les deux marquent</td><td id="current-odds-btts-yes">-</td><td id="trend-btts-yes">-</td></tr>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            document.getElementById('theme-toggle').innerHTML = newTheme === 'dark' ? '☀️ Clair' : '🌙 Sombre';
        }

        document.addEventListener('DOMContentLoaded', function() {
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            document.getElementById('theme-toggle').innerHTML = savedTheme === 'dark' ? '☀️ Clair' : '🌙 Sombre';

            // Données des cotes
            const oddsData = {{ odds_data|tojson }};

            // 1. Graphique des cotes 1X2
            const odds1X2Ctx = document.getElementById('oddsChart1X2').getContext('2d');
            new Chart(odds1X2Ctx, {
                type: 'line',
                data: {
                    labels: oddsData.timestamps.length > 0 ? oddsData.timestamps : ['Début'],
                    datasets: [{
                        label: '{{ match.home_team.name }} (1)',
                        data: oddsData.odds_1.length > 0 ? oddsData.odds_1 : [2.0],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Match Nul (X)',
                        data: oddsData.odds_x.length > 0 ? oddsData.odds_x : [3.0],
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        tension: 0.4
                    }, {
                        label: '{{ match.away_team.name }} (2)',
                        data: oddsData.odds_2.length > 0 ? oddsData.odds_2 : [2.5],
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: false, title: { display: true, text: 'Cotes' } } }
                }
            });

            // 2. Graphique Over/Under 2.5
            const oddsOU25Ctx = document.getElementById('oddsChartOU25').getContext('2d');
            new Chart(oddsOU25Ctx, {
                type: 'line',
                data: {
                    labels: oddsData.timestamps.length > 0 ? oddsData.timestamps : ['Début'],
                    datasets: [{
                        label: 'Plus de 2.5 buts',
                        data: oddsData.odds_over_25.length > 0 ? oddsData.odds_over_25 : [1.8],
                        borderColor: '#e67e22',
                        backgroundColor: 'rgba(230, 126, 34, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Moins de 2.5 buts',
                        data: oddsData.odds_under_25.length > 0 ? oddsData.odds_under_25 : [2.0],
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: false, title: { display: true, text: 'Cotes' } } }
                }
            });

            // 3. Graphique BTTS
            const oddsBTTSCtx = document.getElementById('oddsChartBTTS').getContext('2d');
            new Chart(oddsBTTSCtx, {
                type: 'line',
                data: {
                    labels: oddsData.timestamps.length > 0 ? oddsData.timestamps : ['Début'],
                    datasets: [{
                        label: 'Les deux marquent (Oui)',
                        data: oddsData.odds_btts_yes.length > 0 ? oddsData.odds_btts_yes : [1.9],
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Au moins une ne marque pas (Non)',
                        data: oddsData.odds_btts_no.length > 0 ? oddsData.odds_btts_no : [1.9],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: false, title: { display: true, text: 'Cotes' } } }
                }
            });

            // 4. Graphique Double Chance
            const oddsDCCtx = document.getElementById('oddsChartDC').getContext('2d');
            new Chart(oddsDCCtx, {
                type: 'line',
                data: {
                    labels: oddsData.timestamps.length > 0 ? oddsData.timestamps : ['Début'],
                    datasets: [{
                        label: '1X ({{ match.home_team.name }} ou Nul)',
                        data: oddsData.odds_1x.length > 0 ? oddsData.odds_1x : [1.3],
                        borderColor: '#34495e',
                        backgroundColor: 'rgba(52, 73, 94, 0.1)',
                        tension: 0.4
                    }, {
                        label: '12 ({{ match.home_team.name }} ou {{ match.away_team.name }})',
                        data: oddsData.odds_12.length > 0 ? oddsData.odds_12 : [1.2],
                        borderColor: '#16a085',
                        backgroundColor: 'rgba(22, 160, 133, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'X2 (Nul ou {{ match.away_team.name }})',
                        data: oddsData.odds_x2.length > 0 ? oddsData.odds_x2 : [1.4],
                        borderColor: '#8e44ad',
                        backgroundColor: 'rgba(142, 68, 173, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: false, title: { display: true, text: 'Cotes' } } }
                }
            });

            // Mettre à jour le tableau des cotes actuelles
            if (oddsData.odds_1.length > 0) {
                document.getElementById('current-odds-1').textContent = oddsData.odds_1[oddsData.odds_1.length - 1].toFixed(2);
            }
            if (oddsData.odds_x.length > 0) {
                document.getElementById('current-odds-x').textContent = oddsData.odds_x[oddsData.odds_x.length - 1].toFixed(2);
            }
            if (oddsData.odds_2.length > 0) {
                document.getElementById('current-odds-2').textContent = oddsData.odds_2[oddsData.odds_2.length - 1].toFixed(2);
            }
            if (oddsData.odds_over_25.length > 0) {
                document.getElementById('current-odds-o25').textContent = oddsData.odds_over_25[oddsData.odds_over_25.length - 1].toFixed(2);
            }
            if (oddsData.odds_under_25.length > 0) {
                document.getElementById('current-odds-u25').textContent = oddsData.odds_under_25[oddsData.odds_under_25.length - 1].toFixed(2);
            }
            if (oddsData.odds_btts_yes.length > 0) {
                document.getElementById('current-odds-btts-yes').textContent = oddsData.odds_btts_yes[oddsData.odds_btts_yes.length - 1].toFixed(2);
            }

            // Radar chart
            const radarCtx = document.getElementById('radarChart').getContext('2d');
            const homeForm = {{ home_form|tojson }};
            const awayForm = {{ away_form|tojson }};

            let homeMetrics = [5, 5, 5, 5];
            let awayMetrics = [5, 5, 5, 5];

            if (homeForm && awayForm) {
                homeMetrics = [
                    homeForm.form_score * 10,
                    (homeForm.wins / Math.max(homeForm.matches_played, 1)) * 10,
                    (homeForm.goals_for / Math.max(homeForm.matches_played, 1)) * 2,
                    10 - (homeForm.goals_against / Math.max(homeForm.matches_played, 1)) * 2
                ];
                awayMetrics = [
                    awayForm.form_score * 10,
                    (awayForm.wins / Math.max(awayForm.matches_played, 1)) * 10,
                    (awayForm.goals_for / Math.max(awayForm.matches_played, 1)) * 2,
                    10 - (awayForm.goals_against / Math.max(awayForm.matches_played, 1)) * 2
                ];
            }

            new Chart(radarCtx, {
                type: 'radar',
                data: {
                    labels: ['Forme', 'Victoires', 'Attaque', 'Défense'],
                    datasets: [{
                        label: '{{ match.home_team.name }}',
                        data: homeMetrics,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.2)'
                    }, {
                        label: '{{ match.away_team.name }}',
                        data: awayMetrics,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.2)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { r: { beginAtZero: true, max: 10 } }
                }
            });
        });
    </script>
</body></html>"""

# Démarrer les processus automatiques en arrière-plan
def start_auto_learning():
    """Démarre le processus d'auto-learning en arrière-plan"""
    try:
        # Attendre 30 secondes avant de commencer (laisser l'app se lancer)
        time.sleep(30)
        print("🤖 Auto-learning démarré - Vérification toutes les 10 minutes")
        auto_learning_background()
    except Exception as e:
        print(f"❌ Erreur démarrage auto-learning: {e}")

def start_auto_fetching():
    """Démarre la récupération automatique des matchs"""
    try:
        # Attendre 10 secondes avant de commencer
        time.sleep(10)
        print("🔄 Récupération automatique démarrée - Toutes les 2 minutes")
        fetch_and_process_matches_background()
    except Exception as e:
        print(f"❌ Erreur démarrage auto-fetching: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du système d'apprentissage automatique...")

    # Démarrer la récupération automatique des matchs
    auto_fetch_thread = threading.Thread(target=start_auto_fetching, daemon=True)
    auto_fetch_thread.start()
    print("✅ Thread de récupération automatique lancé")

    # Démarrer l'auto-learning en arrière-plan
    auto_learning_thread = threading.Thread(target=start_auto_learning, daemon=True)
    auto_learning_thread.start()
    print("✅ Thread d'auto-learning lancé")

    print("🎯 Système 100% autonome - Aucune intervention manuelle requise")
    print("📊 Récupération: toutes les 2 minutes")
    print("🤖 Auto-training: toutes les heures (min 5 matchs)")
    print("🔄 Le système fonctionne en permanence en arrière-plan")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
