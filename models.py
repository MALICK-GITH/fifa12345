from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    profile_photo = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)  # Approuvé par admin
    subscription_plan = db.Column(db.String(20), default='free')  # free, premium, vip
    subscription_status = db.Column(db.String(20), default='inactive')  # inactive, active, expired
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Pour traçabilité

    def has_paid_access(self):
        """Vérifie si l'utilisateur a un accès payant actif"""
        if self.subscription_status != 'active':
            return False
        if self.subscription_expires_at and self.subscription_expires_at < datetime.utcnow():
            return False
        return self.subscription_plan in ['premium', 'vip']

    def can_view_predictions(self):
        """Vérifie si l'utilisateur peut voir les prédictions"""
        if self.is_admin:
            return True
        if not self.is_approved:
            return False
        return self.has_paid_access()

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Prediction(db.Model):
    """Prédictions générées par l'IA pour les matchs"""
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, nullable=False, index=True)  # ID du match depuis l'API
    team1 = db.Column(db.String(200), nullable=False)
    team2 = db.Column(db.String(200), nullable=False)
    league = db.Column(db.String(200), nullable=False)
    
    # Consensus et prédiction
    consensus_type = db.Column(db.String(50), nullable=False)  # 1X2 ou alternatif
    consensus_result = db.Column(db.Text, nullable=False)  # Résultat du consensus
    consensus_probability = db.Column(db.Float, nullable=False)  # Probabilité %
    confidence = db.Column(db.Float, nullable=False)  # Confiance en %
    
    # Cotes et action
    recommended_odd = db.Column(db.Float, nullable=True)  # Cote recommandée
    recommended_action = db.Column(db.String(100), nullable=False)  # MISE, PASSER, etc.
    
    # Votes des systèmes
    votes_statistique = db.Column(db.Boolean, default=False)
    votes_cotes = db.Column(db.Boolean, default=False)
    votes_simulation = db.Column(db.Boolean, default=False)
    votes_forme = db.Column(db.Boolean, default=False)
    
    # Statut
    is_valid = db.Column(db.Boolean, default=True)  # Admin peut invalider
    is_locked = db.Column(db.Boolean, default=False)  # Match verrouillé (commencé)
    invalidated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin qui a invalidé
    invalidated_at = db.Column(db.DateTime, nullable=True)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_data = db.Column(db.Text, nullable=True)  # JSON pour données supplémentaires
    
    def to_dict(self):
        """Convertit la prédiction en dictionnaire"""
        return {
            'id': self.id,
            'match_id': self.match_id,
            'team1': self.team1,
            'team2': self.team2,
            'league': self.league,
            'consensus_type': self.consensus_type,
            'consensus_result': self.consensus_result,
            'consensus_probability': self.consensus_probability,
            'confidence': self.confidence,
            'recommended_odd': self.recommended_odd,
            'recommended_action': self.recommended_action,
            'is_valid': self.is_valid,
            'is_locked': self.is_locked,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<Prediction {self.match_id} - {self.team1} vs {self.team2}>"


class Alert(db.Model):
    """Alertes système pour anomalies"""
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # low_confidence, odds_change, match_started, inconsistency
    severity = db.Column(db.String(20), default='warning')  # info, warning, error, critical
    message = db.Column(db.Text, nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=True)
    match_id = db.Column(db.Integer, nullable=True)
    
    # Statut
    is_acknowledged = db.Column(db.Boolean, default=False)  # Admin a-t-il vu ?
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    # Métadonnées
    extra_data = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type} - {self.severity}>"


class AccessLog(db.Model):
    """Logs d'accès pour traçabilité des revenus"""
    __tablename__ = "access_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # view_prediction, view_details, subscription_access
    match_id = db.Column(db.Integer, nullable=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=True)
    subscription_plan = db.Column(db.String(20), nullable=True)  # Plan utilisé pour l'accès
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.Text, nullable=True)  # JSON

    def __repr__(self) -> str:
        return f"<AccessLog {self.user_id} - {self.action_type}>"


class SystemLog(db.Model):
    """Logs système pour toutes les actions importantes"""
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)  # login, prediction, admin_action, alert
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # info, warning, error, critical
    extra_data = db.Column(db.Text, nullable=True)  # JSON pour données supplémentaires (renommé de metadata car réservé SQLAlchemy)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SystemLog {self.action_type} - {self.created_at}>"


# ========== MODÈLES D'ARCHIVAGE POUR MÉMOIRE IA ==========

class MatchArchive(db.Model):
    """Archive des matchs - Mémoire permanente pour l'IA"""
    __tablename__ = "matches_archive"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, unique=True, nullable=False, index=True)  # ID unique du match
    
    # Informations du match
    jeu = db.Column(db.String(50), nullable=False)  # FIFA / FC / eFootball
    mode = db.Column(db.String(50), nullable=True)  # 3v3, 4v4, 5v5, Rush, etc.
    ligue = db.Column(db.String(200), nullable=False)
    equipe_1 = db.Column(db.String(200), nullable=False)
    equipe_2 = db.Column(db.String(200), nullable=False)
    date_heure_match = db.Column(db.DateTime, nullable=False)
    
    # Cotes initiales (AVANT match)
    cote_1 = db.Column(db.Float, nullable=True)  # Cote équipe 1
    cote_X = db.Column(db.Float, nullable=True)  # Cote match nul
    cote_2 = db.Column(db.Float, nullable=True)  # Cote équipe 2
    
    # Résultats finaux (APRÈS match)
    score_final_equipe_1 = db.Column(db.Integer, nullable=True)
    score_final_equipe_2 = db.Column(db.Integer, nullable=True)
    resultat_reel = db.Column(db.String(50), nullable=True)  # 1, X, 2
    statut_final = db.Column(db.String(50), default='en_cours')  # terminé, annulé, en_cours
    
    # Horodatage et traçabilité
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin qui a archivé
    is_locked = db.Column(db.Boolean, default=False)  # Verrouillé après archivage complet
    
    # Métadonnées
    extra_data = db.Column(db.Text, nullable=True)  # JSON
    
    def __repr__(self) -> str:
        return f"<MatchArchive {self.match_id} - {self.equipe_1} vs {self.equipe_2}>"


class PredictionArchive(db.Model):
    """Archive des prédictions - Mémoire pour apprentissage IA"""
    __tablename__ = "predictions_archive"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches_archive.match_id'), nullable=False, index=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=True, index=True)
    
    # Données de prédiction (AVANT match)
    consensus_type = db.Column(db.String(50), nullable=False)  # 1X2 ou alternatif
    choix = db.Column(db.Text, nullable=False)  # Choix de la prédiction
    probabilite = db.Column(db.Float, nullable=False)  # Probabilité en %
    confiance = db.Column(db.Float, nullable=False)  # Confiance en %
    
    # Votes des modules
    vote_statistique = db.Column(db.Boolean, default=False)
    vote_cotes = db.Column(db.Boolean, default=False)
    vote_simulation = db.Column(db.Boolean, default=False)
    vote_forme = db.Column(db.Boolean, default=False)
    consensus = db.Column(db.Boolean, default=False)  # Consensus atteint ?
    
    # Résultat (APRÈS match)
    resultat_reel = db.Column(db.String(50), nullable=True)  # Résultat réel du match
    prediction_correcte = db.Column(db.Boolean, nullable=True)  # True/False/None
    ecart_probabilite = db.Column(db.Float, nullable=True)  # Écart entre probabilité et réalité
    
    # Horodatage
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Date de la prédiction
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Date de mise à jour
    finalized_at = db.Column(db.DateTime, nullable=True)  # Date de finalisation (après match)
    
    # Métadonnées
    extra_data = db.Column(db.Text, nullable=True)  # JSON
    
    def __repr__(self) -> str:
        return f"<PredictionArchive {self.match_id} - {self.choix}>"


class ModelPerformance(db.Model):
    """Performance du modèle IA - Statistiques pour ajustement"""
    __tablename__ = "model_performance"

    id = db.Column(db.Integer, primary_key=True)
    
    # Période d'analyse
    date_debut = db.Column(db.DateTime, nullable=False, index=True)
    date_fin = db.Column(db.DateTime, nullable=False, index=True)
    
    # Métriques globales
    total_predictions = db.Column(db.Integer, default=0)
    predictions_correctes = db.Column(db.Integer, default=0)
    taux_reussite = db.Column(db.Float, nullable=True)  # Taux de réussite en %
    
    # Métriques par module
    taux_reussite_statistique = db.Column(db.Float, nullable=True)
    taux_reussite_cotes = db.Column(db.Float, nullable=True)
    taux_reussite_simulation = db.Column(db.Float, nullable=True)
    taux_reussite_forme = db.Column(db.Float, nullable=True)
    taux_reussite_consensus = db.Column(db.Float, nullable=True)  # Quand consensus atteint
    
    # Métriques de confiance
    moyenne_confiance = db.Column(db.Float, nullable=True)
    moyenne_probabilite = db.Column(db.Float, nullable=True)
    ecart_moyen_probabilite = db.Column(db.Float, nullable=True)
    
    # Métriques par type
    taux_reussite_1x2 = db.Column(db.Float, nullable=True)
    taux_reussite_alternatifs = db.Column(db.Float, nullable=True)
    
    # Horodatage
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Métadonnées
    extra_data = db.Column(db.Text, nullable=True)  # JSON
    
    def __repr__(self) -> str:
        return f"<ModelPerformance {self.date_debut.date()} - {self.date_fin.date()} - {self.taux_reussite}%>"


class AnomalyLog(db.Model):
    """Logs d'anomalies détectées - Pour analyse et amélioration"""
    __tablename__ = "anomaly_logs"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches_archive.match_id'), nullable=True, index=True)
    prediction_archive_id = db.Column(db.Integer, db.ForeignKey('predictions_archive.id'), nullable=True)
    
    # Type d'anomalie
    anomaly_type = db.Column(db.String(50), nullable=False, index=True)  # high_confidence, consensus_incoherent, odds_change, match_unlocked, etc.
    severity = db.Column(db.String(20), default='warning')  # info, warning, error, critical
    
    # Description
    description = db.Column(db.Text, nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Données contextuelles
    context_data = db.Column(db.Text, nullable=True)  # JSON avec données contextuelles
    
    # Statut
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<AnomalyLog {self.anomaly_type} - {self.match_id}>"

