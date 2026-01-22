from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import uuid

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    profile_photo = db.Column(db.String(255), nullable=True)  # Chemin vers le fichier uploadé
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)  # Approuvé par admin
    is_active = db.Column(db.Boolean, default=True)  # Compte activé/désactivé par admin
    subscription_plan = db.Column(db.String(20), default='free')  # free, premium, vip (legacy)
    subscription_status = db.Column(db.String(20), default='inactive')  # inactive, active, expired (legacy)
    subscription_expires_at = db.Column(db.DateTime, nullable=True)  # Legacy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Pour traçabilité
    
    # ID unique immuable pour protection des données
    unique_id = db.Column(db.String(36), unique=True, nullable=True, index=True)  # UUID pour identification permanente (nullable au départ pour migration)

    def has_paid_access(self):
        """Vérifie si l'utilisateur a un accès payant actif (nouveau système)"""
        if self.is_admin:
            return True
        if not self.is_approved or not self.is_active:
            return False
        
        # Vérifier les abonnements actifs
        active_subscription = UserSubscription.query.filter_by(
            user_id=self.id,
            is_active=True
        ).filter(
            UserSubscription.expires_at > datetime.utcnow()
        ).first()
        
        if active_subscription:
            return True
        
        # Fallback sur l'ancien système (legacy)
        if self.subscription_status == 'active':
            if self.subscription_expires_at and self.subscription_expires_at < datetime.utcnow():
                return False
            return self.subscription_plan in ['premium', 'vip']
        
        return False

    def get_active_subscription(self):
        """Récupère l'abonnement actif de l'utilisateur"""
        return UserSubscription.query.filter_by(
            user_id=self.id,
            is_active=True
        ).filter(
            UserSubscription.expires_at > datetime.utcnow()
        ).first()

    def get_plan_limits(self):
        """Récupère les limites du plan actif"""
        subscription = self.get_active_subscription()
        if subscription and subscription.plan:
            return {
                'predictions_per_day': subscription.plan.predictions_per_day,
                'plan_name': subscription.plan.name
            }
        return None

    def can_view_predictions(self):
        """Vérifie si l'utilisateur peut voir les prédictions"""
        if self.is_admin:
            return True
        if not self.is_approved or not self.is_active:
            return False
        return self.has_paid_access()
    
    def get_predictions_viewed_today(self):
        """Compte le nombre de prédictions consultées aujourd'hui"""
        today = datetime.utcnow().date()
        return UserPredictionAccess.query.filter_by(
            user_id=self.id,
            access_date=today
        ).count()
    
    def can_view_more_predictions_today(self):
        """Vérifie si l'utilisateur peut encore voir des prédictions aujourd'hui"""
        if self.is_admin:
            return True
        
        plan_limits = self.get_plan_limits()
        if not plan_limits:
            return False
        
        viewed_today = self.get_predictions_viewed_today()
        return viewed_today < plan_limits['predictions_per_day']

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


# ========== MODÈLES SYSTÈME ORACXPRED COMPLET ==========

class SubscriptionPlan(db.Model):
    """Plans d'abonnement dynamiques créés par l'admin"""
    __tablename__ = "subscription_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Nom du plan
    description = db.Column(db.Text, nullable=True)
    
    # Limites du plan
    predictions_per_day = db.Column(db.Integer, nullable=False, default=3)  # Nombre de prédictions par jour
    duration_days = db.Column(db.Integer, nullable=False)  # Durée en jours (7, 30, etc.)
    duration_type = db.Column(db.String(20), nullable=False)  # 'week', 'month', 'long'
    
    # Tarif
    price_fcfa = db.Column(db.Float, nullable=False)  # Prix en FCFA
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)  # Plan actif ou non
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Admin créateur
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<SubscriptionPlan {self.name} - {self.predictions_per_day}/jour - {self.price_fcfa} FCFA>"


class UserSubscription(db.Model):
    """Abonnements actifs des utilisateurs"""
    __tablename__ = "user_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    
    # Dates
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    auto_renew = db.Column(db.Boolean, default=False)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.Text, nullable=True)  # JSON
    
    # Relation
    plan = db.relationship('SubscriptionPlan', backref='subscriptions')
    
    def is_expired(self):
        """Vérifie si l'abonnement est expiré"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self) -> str:
        return f"<UserSubscription user:{self.user_id} plan:{self.plan_id} expires:{self.expires_at}>"


class UserPredictionAccess(db.Model):
    """Suivi des accès aux prédictions par utilisateur (limitation par plan)"""
    __tablename__ = "user_prediction_access"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=False, index=True)
    access_date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)  # Date d'accès (pour compter par jour)
    accessed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<UserPredictionAccess user:{self.user_id} prediction:{self.prediction_id}>"


class Notification(db.Model):
    """Système de notifications (globale ou ciblée)"""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    
    # Destinataire
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # None = notification globale
    is_global = db.Column(db.Boolean, default=False)  # Notification pour tous les utilisateurs
    
    # Contenu
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    notification_type = db.Column(db.String(50), default='info')  # info, warning, success, error
    
    # Affichage
    display_duration = db.Column(db.Integer, default=5000)  # Durée d'affichage en ms
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Expiration
    expires_at = db.Column(db.DateTime, nullable=True)  # Date d'expiration de la notification
    
    # Créateur
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Admin créateur
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Canaux (prêt pour extension Telegram/WhatsApp)
    channels = db.Column(db.Text, nullable=True)  # JSON: ['internal', 'telegram', 'whatsapp']
    
    def __repr__(self) -> str:
        return f"<Notification {self.title} - {'global' if self.is_global else f'user:{self.user_id}'}>"


class PersistentSession(db.Model):
    """Sessions persistantes pour reconnexion automatique après redémarrage serveur"""
    __tablename__ = "persistent_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)  # Token unique pour la session
    session_data = db.Column(db.Text, nullable=True)  # JSON avec données de session
    
    # Expiration
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Métadonnées
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def is_expired(self):
        """Vérifie si la session est expirée"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self) -> str:
        return f"<PersistentSession user:{self.user_id} expires:{self.expires_at}>"


class BackupLog(db.Model):
    """Logs des sauvegardes automatiques"""
    __tablename__ = "backup_logs"

    id = db.Column(db.Integer, primary_key=True)
    backup_type = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'manual'
    backup_path = db.Column(db.String(500), nullable=False)  # Chemin du fichier de sauvegarde
    file_size = db.Column(db.BigInteger, nullable=True)  # Taille en octets
    
    # Statut
    status = db.Column(db.String(20), default='success')  # success, failed, partial
    error_message = db.Column(db.Text, nullable=True)
    
    # Métadonnées
    tables_backed_up = db.Column(db.Text, nullable=True)  # JSON avec liste des tables
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin si manuel
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<BackupLog {self.backup_type} - {self.status} - {self.created_at}>"


class PredictionSchedule(db.Model):
    """Planification des prédictions par l'admin"""
    __tablename__ = "prediction_schedules"

    id = db.Column(db.Integer, primary_key=True)
    
    # Configuration
    predictions_per_day = db.Column(db.Integer, nullable=False, default=3)
    publication_times = db.Column(db.Text, nullable=True)  # JSON avec heures de publication ["08:00", "14:00", "20:00"]
    publication_delays = db.Column(db.Text, nullable=True)  # JSON avec délais en minutes
    
    # Statut
    is_active = db.Column(db.Boolean, default=True)
    
    # Métadonnées
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PredictionSchedule {self.predictions_per_day}/jour - {'active' if self.is_active else 'inactive'}>"


# ========== SYSTÈME DE COLLECTE DES MATCHS EN TEMPS RÉEL ==========

class CollectedMatch(db.Model):
    """Matchs collectés en temps réel - Base de données vivante pour ORACXPRED"""
    __tablename__ = "collected_matches"

    id = db.Column(db.Integer, primary_key=True)
    
    # Identification unique
    unique_match_id = db.Column(db.String(100), unique=True, nullable=False, index=True)  # ID unique externe
    
    # Informations du match
    jeu = db.Column(db.String(50), nullable=False)  # FIFA / eFootball / FC
    equipe_domicile = db.Column(db.String(200), nullable=False)
    equipe_exterieur = db.Column(db.String(200), nullable=False)
    
    # Horodatage
    heure_debut = db.Column(db.DateTime, nullable=False)
    heure_fin = db.Column(db.DateTime, nullable=True)
    timestamp_enregistrement = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Scores et résultats
    score_domicile = db.Column(db.Integer, nullable=True)
    score_exterieur = db.Column(db.Integer, nullable=True)
    equipe_gagnante = db.Column(db.String(200), nullable=True)  # Nom de l'équipe gagnante ou "Match nul"
    
    # Statut du match
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, en_cours, termine, annule
    
    # Métadonnées de collecte
    source_donnees = db.Column(db.String(100), nullable=True)  # API, scraper, simulé
    collecte_par = db.Column(db.String(50), default='systeme_auto')  # système_auto, admin
    
    # Traçabilité
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convertit le match collecté en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'unique_match_id': self.unique_match_id,
            'jeu': self.jeu,
            'equipe_domicile': self.equipe_domicile,
            'equipe_exterieur': self.equipe_exterieur,
            'heure_debut': self.heure_debut.isoformat() if self.heure_debut else None,
            'heure_fin': self.heure_fin.isoformat() if self.heure_fin else None,
            'timestamp_enregistrement': self.timestamp_enregistrement.isoformat() if self.timestamp_enregistrement else None,
            'score_domicile': self.score_domicile,
            'score_exterieur': self.score_exterieur,
            'equipe_gagnante': self.equipe_gagnante,
            'statut': self.statut,
            'source_donnees': self.source_donnees,
            'collecte_par': self.collecte_par,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def determine_gagnant(self):
        """Détermine l'équipe gagnante basé sur le score"""
        if self.score_domicile is None or self.score_exterieur is None:
            return None
        
        if self.score_domicile > self.score_exterieur:
            return self.equipe_domicile
        elif self.score_exterieur > self.score_domicile:
            return self.equipe_exterieur
        else:
            return "Match nul"
    
    def __repr__(self) -> str:
        return f"<CollectedMatch {self.unique_match_id} - {self.equipe_domicile} vs {self.equipe_exterieur} - {self.statut}>"


class MatchCollectionLog(db.Model):
    """Logs du système de collecte pour monitoring et debugging"""
    __tablename__ = "match_collection_logs"

    id = db.Column(db.Integer, primary_key=True)
    
    # Action de collecte
    action_type = db.Column(db.String(50), nullable=False)  # detection_start, detection_end, collecte_success, erreur
    match_id = db.Column(db.String(100), nullable=True, index=True)  # Référence au unique_match_id
    
    # Description
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # info, warning, error, critical
    
    # Métadonnées
    source_donnees = db.Column(db.String(100), nullable=True)
    temps_execution = db.Column(db.Float, nullable=True)  # Temps d'exécution en secondes
    extra_data = db.Column(db.Text, nullable=True)  # JSON pour données supplémentaires
    
    # Horodatage
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<MatchCollectionLog {self.action_type} - {self.match_id} - {self.severity}>"
