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

