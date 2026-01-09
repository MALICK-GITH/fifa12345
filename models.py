from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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


class SystemLog(db.Model):
    """Logs système pour toutes les actions importantes"""
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)  # login, prediction, admin_action, alert
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # info, warning, error, critical
    metadata = db.Column(db.Text, nullable=True)  # JSON pour données supplémentaires
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SystemLog {self.action_type} - {self.created_at}>"

