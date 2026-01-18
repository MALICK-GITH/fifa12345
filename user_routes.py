"""
👤 ROUTES UTILISATEUR ORACXPRED
================================
Gestion des utilisateurs : inscription, connexion, notifications, etc.
"""

from flask import Blueprint, request, render_template_string, session, redirect, url_for, jsonify, send_from_directory
from datetime import datetime
import os

from models import (
    db, User, Prediction, Notification, UserPredictionAccess,
    UserSubscription, SubscriptionPlan
)
from oracxpred_utils import (
    save_profile_photo, delete_profile_photo, create_persistent_session,
    get_user_from_session_token, ensure_user_unique_id
)
from prediction_manager import log_action

user_bp = Blueprint('user', __name__)


@user_bp.route('/register', methods=['GET', 'POST'])
def user_register():
    """Inscription utilisateur avec upload de photo"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Upload de photo de profil
        profile_photo_file = request.files.get('profile_photo')
        profile_photo_path = None
        
        # Charger le template
        template = get_template('register')
        if not template:
            from fifa1 import USER_REGISTER_TEMPLATE as template
        
        if not username or not password:
            return render_template_string(template, 
                error="Nom d'utilisateur et mot de passe requis")
        
        if password != confirm_password:
            return render_template_string(template, 
                error="Les mots de passe ne correspondent pas")
        
        if User.query.filter_by(username=username).first():
            return render_template_string(template, 
                error="Nom d'utilisateur déjà pris")
        
        # Créer l'utilisateur
        user = User(
            username=username,
            email=email or None,
            password=password,  # NOTE: en prod, hasher le mot de passe (bcrypt)
            is_admin=False,
            is_approved=False,
            is_active=True,
            unique_id=str(uuid.uuid4())
        )
        db.session.add(user)
        db.session.commit()
        
        # Sauvegarder la photo de profil si fournie
        if profile_photo_file and profile_photo_file.filename:
            profile_photo_path = save_profile_photo(profile_photo_file, user.id)
            if profile_photo_path:
                user.profile_photo = profile_photo_path
                db.session.commit()
        
        log_action('user_register', f"Inscription: {username}", user_id=user.id, severity='info')
        return redirect(url_for('user.user_login'))
    
    template = get_template('register')
    if not template:
        from fifa1 import USER_REGISTER_TEMPLATE as template
    return render_template_string(template)


@user_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    """Connexion utilisateur avec session persistante"""
    # Vérifier si une session persistante existe
    persistent_token = request.cookies.get('persistent_session_token')
    if persistent_token and not session.get('user_id'):
        user = get_user_from_session_token(persistent_token)
        if user and user.is_approved and user.is_active:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember_me = request.form.get('remember_me') == 'on'
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            template = get_template('login')
            if not template:
                from fifa1 import USER_LOGIN_TEMPLATE as template
            
            if not user.is_approved:
                return render_template_string(template, 
                    error="Votre compte n'est pas encore approuvé par un administrateur. Veuillez patienter.")
            
            if not user.is_active:
                return render_template_string(template, 
                    error="Votre compte a été désactivé. Contactez l'administrateur.")
            
            # Créer la session
            session['user_id'] = user.id
            session['username'] = user.username
            
            # Créer une session persistante si "Se souvenir de moi"
            if remember_me:
                token = create_persistent_session(
                    user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    duration_days=30
                )
                session['persistent_token'] = token
            
            user.last_login_at = datetime.utcnow()
            ensure_user_unique_id(user)
            db.session.commit()
            
            log_action('user_login', f"Connexion utilisateur: {username}", user_id=user.id, severity='info')
            return redirect(url_for('home'))
        
        template = get_template('login')
        if not template:
            from fifa1 import USER_LOGIN_TEMPLATE as template
        
        log_action('user_login_failed', f"Tentative de connexion échouée: {username}", severity='warning')
        return render_template_string(template, error="Identifiants incorrects")
    
    template = get_template('login')
    if not template:
        from fifa1 import USER_LOGIN_TEMPLATE as template
    return render_template_string(template)


@user_bp.route('/logout')
def user_logout():
    """Déconnexion utilisateur"""
    user = User.query.get(session.get('user_id'))
    if user:
        log_action('user_logout', f"Déconnexion utilisateur: {user.username}", user_id=user.id, severity='info')
    
    # Supprimer la session persistante
    token = session.get('persistent_token')
    if token:
        from oracxpred_utils import delete_persistent_session
        delete_persistent_session(token)
    
    session.clear()
    return redirect(url_for('home'))


@user_bp.route('/notifications')
def user_notifications():
    """Notifications de l'utilisateur"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user.user_login'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('user.user_login'))
    
    # Récupérer les notifications non lues et récentes
    notifications = Notification.query.filter(
        (Notification.user_id == user_id) | (Notification.is_global == True)
    ).filter(
        Notification.is_read == False
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'priority': n.priority,
            'display_duration': n.display_duration,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    })


@user_bp.route('/notification/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Marquer une notification comme lue"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Non authentifié'}), 401
    
    notification = Notification.query.get_or_404(notification_id)
    
    # Vérifier que la notification appartient à l'utilisateur ou est globale
    if notification.user_id != user_id and not notification.is_global:
        return jsonify({'error': 'Non autorisé'}), 403
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})


@user_bp.route('/profile')
def user_profile():
    """Profil utilisateur"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user.user_login'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('user.user_login'))
    
    # Récupérer l'abonnement actif
    subscription = UserSubscription.query.filter_by(
        user_id=user_id,
        is_active=True
    ).filter(
        UserSubscription.expires_at > datetime.utcnow()
    ).first()
    
    plan_info = None
    if subscription and subscription.plan:
        plan_info = {
            'name': subscription.plan.name,
            'predictions_per_day': subscription.plan.predictions_per_day,
            'expires_at': subscription.expires_at.isoformat()
        }
    
    # Statistiques
    predictions_viewed_today = UserPredictionAccess.query.filter_by(
        user_id=user_id,
        access_date=datetime.utcnow().date()
    ).count()
    
    return render_template_string(USER_PROFILE_TEMPLATE,
        user=user,
        subscription=subscription,
        plan_info=plan_info,
        predictions_viewed_today=predictions_viewed_today
    )


@user_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Servir les fichiers uploadés"""
    from flask import current_app
    upload_folder = os.path.join(current_app.root_path, 'uploads/profiles')
    return send_from_directory(upload_folder, filename)


import uuid

# Templates - seront chargés depuis fifa1.py ou définis ici
# Pour l'instant, on utilise les templates de fifa1.py
def get_template(name):
    """Récupère un template depuis fifa1.py"""
    try:
        from fifa1 import USER_REGISTER_TEMPLATE, USER_LOGIN_TEMPLATE
        templates = {
            'register': USER_REGISTER_TEMPLATE,
            'login': USER_LOGIN_TEMPLATE,
        }
        return templates.get(name, '')
    except ImportError:
        return f"<!-- Template {name} non trouvé -->"

USER_REGISTER_TEMPLATE = None  # Sera chargé dynamiquement
USER_LOGIN_TEMPLATE = None  # Sera chargé dynamiquement
USER_PROFILE_TEMPLATE = """<!-- Template profil à définir -->"""
