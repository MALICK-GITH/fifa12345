"""
🔧 UTILITAIRES SYSTÈME ORACXPRED
================================
Gestion des uploads, sessions persistantes, sauvegardes, etc.
"""

import os
import uuid
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import current_app
from models import db, User, PersistentSession, BackupLog, UserSubscription


# ========== GESTION DES UPLOADS ==========

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = 'uploads/profiles'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    """Vérifie si le fichier a une extension autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_profile_photo(file, user_id):
    """
    Sauvegarde une photo de profil uploadée
    Retourne le chemin relatif du fichier ou None en cas d'erreur
    """
    if not file or not file.filename:
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Vérifier la taille
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return None
    
    # Créer le dossier si nécessaire
    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    os.makedirs(upload_path, exist_ok=True)
    
    # Générer un nom de fichier unique
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filename = secure_filename(filename)
    
    filepath = os.path.join(upload_path, filename)
    
    try:
        file.save(filepath)
        # Retourner le chemin relatif depuis le dossier static ou root
        return os.path.join(UPLOAD_FOLDER, filename).replace('\\', '/')
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la photo: {e}")
        return None


def delete_profile_photo(photo_path):
    """Supprime une photo de profil"""
    if not photo_path:
        return
    
    try:
        full_path = os.path.join(current_app.root_path, photo_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception as e:
        print(f"Erreur lors de la suppression de la photo: {e}")


# ========== GESTION DES SESSIONS PERSISTANTES ==========

def create_persistent_session(user_id, ip_address=None, user_agent=None, duration_days=30):
    """
    Crée une session persistante pour un utilisateur
    Retourne le token de session
    """
    # Générer un token unique
    token = hashlib.sha256(
        f"{user_id}{datetime.utcnow().isoformat()}{uuid.uuid4()}".encode()
    ).hexdigest()
    
    expires_at = datetime.utcnow() + timedelta(days=duration_days)
    
    session = PersistentSession(
        user_id=user_id,
        session_token=token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        session_data=json.dumps({'created_at': datetime.utcnow().isoformat()})
    )
    
    db.session.add(session)
    db.session.commit()
    
    return token


def get_user_from_session_token(token):
    """
    Récupère l'utilisateur à partir d'un token de session
    Retourne l'utilisateur ou None
    """
    session = PersistentSession.query.filter_by(session_token=token).first()
    
    if not session or session.is_expired():
        return None
    
    # Mettre à jour la dernière activité
    session.last_activity = datetime.utcnow()
    db.session.commit()
    
    return User.query.get(session.user_id)


def delete_persistent_session(token):
    """Supprime une session persistante"""
    session = PersistentSession.query.filter_by(session_token=token).first()
    if session:
        db.session.delete(session)
        db.session.commit()


def cleanup_expired_sessions():
    """Nettoie les sessions expirées"""
    expired = PersistentSession.query.filter(
        PersistentSession.expires_at < datetime.utcnow()
    ).all()
    
    for session in expired:
        db.session.delete(session)
    
    db.session.commit()
    return len(expired)


# ========== GESTION DES SAUVEGARDES ==========

def create_backup(backup_type='manual', admin_id=None):
    """
    Crée une sauvegarde de la base de données
    Retourne le chemin du fichier de sauvegarde ou None
    """
    try:
        # Créer le dossier de sauvegarde
        backup_dir = os.path.join(current_app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nom du fichier de sauvegarde
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"oracxpred_backup_{backup_type}_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copier la base de données SQLite
        db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        if not db_path:
            db_path = os.path.join(current_app.instance_path, 'oracxpred.db')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            file_size = os.path.getsize(backup_path)
            
            # Enregistrer dans les logs
            backup_log = BackupLog(
                backup_type=backup_type,
                backup_path=backup_path,
                file_size=file_size,
                status='success',
                tables_backed_up=json.dumps(['all']),
                created_by=admin_id
            )
            db.session.add(backup_log)
            db.session.commit()
            
            return backup_path
        else:
            raise Exception(f"Base de données introuvable: {db_path}")
            
    except Exception as e:
        # Enregistrer l'erreur
        backup_log = BackupLog(
            backup_type=backup_type,
            backup_path='',
            status='failed',
            error_message=str(e),
            created_by=admin_id
        )
        db.session.add(backup_log)
        db.session.commit()
        
        print(f"Erreur lors de la sauvegarde: {e}")
        return None


def cleanup_old_backups(keep_days=30):
    """Supprime les sauvegardes anciennes"""
    backup_dir = os.path.join(current_app.root_path, 'backups')
    if not os.path.exists(backup_dir):
        return 0
    
    deleted_count = 0
    cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
    
    for filename in os.listdir(backup_dir):
        filepath = os.path.join(backup_dir, filename)
        if os.path.isfile(filepath):
            file_time = datetime.utcnow() - timedelta(
                days=os.path.getmtime(filepath) / 86400
            )
            if file_time < cutoff_date:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except Exception as e:
                    print(f"Erreur lors de la suppression de {filename}: {e}")
    
    return deleted_count


# ========== GESTION DES UTILISATEURS ==========

def ensure_user_unique_id(user):
    """Assure qu'un utilisateur a un unique_id"""
    if not user.unique_id:
        user.unique_id = str(uuid.uuid4())
        db.session.commit()
    return user.unique_id


def initialize_user_unique_ids():
    """Initialise les unique_id pour tous les utilisateurs qui n'en ont pas"""
    users_without_id = User.query.filter_by(unique_id=None).all()
    for user in users_without_id:
        user.unique_id = str(uuid.uuid4())
    db.session.commit()
    return len(users_without_id)


# ========== GESTION DES ABONNEMENTS ==========

def check_and_expire_subscriptions():
    """Vérifie et expire les abonnements arrivés à échéance"""
    expired = UserSubscription.query.filter(
        UserSubscription.is_active == True,
        UserSubscription.expires_at < datetime.utcnow()
    ).all()
    
    count = 0
    for subscription in expired:
        subscription.is_active = False
        # Mettre à jour le statut de l'utilisateur
        user = User.query.get(subscription.user_id)
        if user:
            user.subscription_status = 'expired'
        count += 1
    
    db.session.commit()
    return count
