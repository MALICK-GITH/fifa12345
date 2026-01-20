"""
🔐 ROUTES ADMINISTRATEUR ORACXPRED
==================================
Gestion complète de l'administration : utilisateurs, plans, prédictions, notifications
"""

from flask import Blueprint, request, render_template_string, session, redirect, url_for, jsonify, send_from_directory
from datetime import datetime, timedelta
import json
import os
from functools import wraps

from models import (
    db, User, Prediction, SystemLog, SubscriptionPlan, UserSubscription,
    UserPredictionAccess, Notification, PersistentSession, BackupLog,
    PredictionSchedule, Alert
)
from oracxpred_utils import (
    save_profile_photo, delete_profile_photo, create_persistent_session,
    get_user_from_session_token, create_backup, cleanup_expired_sessions,
    ensure_user_unique_id, check_and_expire_subscriptions
)
from prediction_manager import log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def require_admin(f):
    """Décorateur pour exiger les droits admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Compatibilité avec l'ancien système
        admin_logged_in = session.get('admin_logged_in')
        admin_id = session.get('admin_id')
        user_id = session.get('user_id')
        
        # Vérifier via l'ancien système ou le nouveau
        if admin_logged_in and admin_id:
            try:
                user = User.query.get(admin_id)
                if user and user.is_admin and user.is_active:
                    return f(*args, **kwargs)
            except Exception as e:
                print(f"❌ Erreur lors de la vérification admin: {e}")
        
        if user_id:
            try:
                user = User.query.get(user_id)
                if user and user.is_admin and user.is_active:
                    return f(*args, **kwargs)
            except Exception as e:
                print(f"❌ Erreur lors de la vérification admin: {e}")
        
        return redirect(url_for('admin.admin_login'))
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Connexion admin séparée"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember_me = request.form.get('remember_me') == 'on'

        try:
            user = User.query.filter_by(username=username).first()
            if user and user.password == password and user.is_admin:
                # Vérifier que le compte est actif
                if not user.is_active:
                    log_action('admin_login_failed', f"Tentative de connexion admin désactivé: {username}", severity='warning')
                    return render_template_string(ADMIN_LOGIN_TEMPLATE, error="Compte admin désactivé")
                
                # Compatibilité avec l'ancien système
                session['admin_logged_in'] = True
                session['admin_username'] = username
                session['admin_id'] = user.id
                
                # Nouveau système
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = True
                
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
                db.session.commit()
                log_action('admin_login', f"Connexion admin: {username}", user_id=user.id, severity='info')
                return redirect(url_for('admin.admin_dashboard'))
            
            log_action('admin_login_failed', f"Tentative de connexion admin échouée: {username}", severity='warning')
            return render_template_string(ADMIN_LOGIN_TEMPLATE, error="Identifiants admin incorrects")
        except Exception as e:
            print(f"❌ Erreur lors de la connexion admin: {e}")
            import traceback
            traceback.print_exc()
            return render_template_string(ADMIN_LOGIN_TEMPLATE, error=f"Erreur: {str(e)}")
    
    return render_template_string(ADMIN_LOGIN_TEMPLATE)


@admin_bp.route('/logout')
def admin_logout():
    """Déconnexion admin"""
    user = User.query.get(session.get('user_id'))
    if user:
        log_action('admin_logout', f"Déconnexion admin: {user.username}", user_id=user.id, severity='info')
    
    # Supprimer la session persistante si elle existe
    token = session.get('persistent_token')
    if token:
        delete_persistent_session(token)
    
    session.clear()
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/dashboard')
@require_admin
def admin_dashboard():
    """Tableau de bord admin principal"""
    admin_user = User.query.get(session.get('user_id'))
    
    # Statistiques
    total_users = User.query.count()
    active_subscriptions = UserSubscription.query.filter(
        UserSubscription.is_active == True,
        UserSubscription.expires_at > datetime.utcnow()
    ).count()
    pending_approvals = User.query.filter_by(is_approved=False).count()
    total_predictions = Prediction.query.count()
    active_predictions = Prediction.query.filter_by(is_valid=True, is_locked=False).count()
    
    # Abonnements expirés récemment
    recently_expired = UserSubscription.query.filter(
        UserSubscription.is_active == False,
        UserSubscription.expires_at > datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # Notifications non lues
    unread_notifications = Notification.query.filter_by(is_read=False).count()
    
    # Logs récents
    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(20).all()
    
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE,
        admin_user=admin_user,
        total_users=total_users,
        active_subscriptions=active_subscriptions,
        pending_approvals=pending_approvals,
        total_predictions=total_predictions,
        active_predictions=active_predictions,
        recently_expired=recently_expired,
        unread_notifications=unread_notifications,
        recent_logs=recent_logs
    )


# ========== GESTION DES UTILISATEURS ==========

@admin_bp.route('/users')
@require_admin
def admin_users():
    """Liste des utilisateurs"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template_string(ADMIN_USERS_TEMPLATE, users=users)


@admin_bp.route('/user/<int:user_id>/toggle_active', methods=['POST'])
@require_admin
def admin_toggle_user_active(user_id):
    """Activer/désactiver un utilisateur"""
    admin_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    if user.is_admin and user.id != admin_id:
        return jsonify({'error': 'Impossible de désactiver un autre admin'}), 403
    
    user.is_active = not user.is_active
    db.session.commit()
    
    action = 'activé' if user.is_active else 'désactivé'
    log_action('admin_action', f"Utilisateur {user.username} {action}", 
               user_id=user_id, admin_id=admin_id, severity='info')
    
    return jsonify({'success': True, 'is_active': user.is_active})


@admin_bp.route('/user/<int:user_id>/approve', methods=['POST'])
@require_admin
def admin_approve_user(user_id):
    """Approuver un utilisateur"""
    admin_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    user.is_approved = True
    ensure_user_unique_id(user)  # Assurer l'ID unique
    db.session.commit()
    
    log_action('admin_action', f"Utilisateur {user.username} approuvé", 
               user_id=user_id, admin_id=admin_id, severity='info')
    
    return jsonify({'success': True})


@admin_bp.route('/user/<int:user_id>/set_subscription', methods=['POST'])
@require_admin
def admin_set_subscription(user_id):
    """Attribuer un abonnement à un utilisateur"""
    admin_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    plan_id = request.json.get('plan_id')
    if not plan_id:
        return jsonify({'error': 'Plan ID requis'}), 400
    
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan or not plan.is_active:
        return jsonify({'error': 'Plan invalide'}), 400
    
    # Désactiver les anciens abonnements actifs
    old_subscriptions = UserSubscription.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    for sub in old_subscriptions:
        sub.is_active = False
    
    # Créer le nouvel abonnement
    start_date = datetime.utcnow()
    expires_at = start_date + timedelta(days=plan.duration_days)
    
    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan_id,
        start_date=start_date,
        expires_at=expires_at,
        is_active=True
    )
    db.session.add(subscription)
    db.session.commit()
    
    log_action('admin_action', f"Abonnement {plan.name} attribué à {user.username}", 
               user_id=user_id, admin_id=admin_id, severity='info')
    
    return jsonify({'success': True, 'expires_at': expires_at.isoformat()})


# ========== GESTION DES PLANS TARIFAIRES ==========

@admin_bp.route('/plans')
@require_admin
def admin_plans():
    """Gestion des plans tarifaires"""
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.created_at.desc()).all()
    return render_template_string(ADMIN_PLANS_TEMPLATE, plans=plans)


@admin_bp.route('/plan/create', methods=['POST'])
@require_admin
def admin_create_plan():
    """Créer un nouveau plan tarifaire"""
    admin_id = session.get('user_id')
    
    name = request.json.get('name', '').strip()
    description = request.json.get('description', '').strip()
    predictions_per_day = int(request.json.get('predictions_per_day', 3))
    duration_days = int(request.json.get('duration_days', 7))
    duration_type = request.json.get('duration_type', 'week')
    price_fcfa = float(request.json.get('price_fcfa', 0))
    
    if not name or price_fcfa <= 0:
        return jsonify({'error': 'Données invalides'}), 400
    
    # Vérifier si le nom existe déjà
    if SubscriptionPlan.query.filter_by(name=name).first():
        return jsonify({'error': 'Un plan avec ce nom existe déjà'}), 400
    
    plan = SubscriptionPlan(
        name=name,
        description=description,
        predictions_per_day=predictions_per_day,
        duration_days=duration_days,
        duration_type=duration_type,
        price_fcfa=price_fcfa,
        is_active=True,
        created_by=admin_id
    )
    db.session.add(plan)
    db.session.commit()
    
    log_action('admin_action', f"Plan créé: {name}", admin_id=admin_id, severity='info')
    
    return jsonify({'success': True, 'plan_id': plan.id})


@admin_bp.route('/plan/<int:plan_id>/update', methods=['POST'])
@require_admin
def admin_update_plan(plan_id):
    """Modifier un plan tarifaire"""
    admin_id = session.get('user_id')
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    plan.name = request.json.get('name', plan.name).strip()
    plan.description = request.json.get('description', plan.description).strip()
    plan.predictions_per_day = int(request.json.get('predictions_per_day', plan.predictions_per_day))
    plan.duration_days = int(request.json.get('duration_days', plan.duration_days))
    plan.duration_type = request.json.get('duration_type', plan.duration_type)
    plan.price_fcfa = float(request.json.get('price_fcfa', plan.price_fcfa))
    plan.is_active = request.json.get('is_active', plan.is_active)
    
    db.session.commit()
    
    log_action('admin_action', f"Plan modifié: {plan.name}", admin_id=admin_id, severity='info')
    
    return jsonify({'success': True})


@admin_bp.route('/plan/<int:plan_id>/delete', methods=['POST'])
@require_admin
def admin_delete_plan(plan_id):
    """Supprimer un plan tarifaire"""
    admin_id = session.get('user_id')
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    # Vérifier s'il y a des abonnements actifs
    active_subs = UserSubscription.query.filter_by(plan_id=plan_id, is_active=True).count()
    if active_subs > 0:
        return jsonify({'error': f'Impossible de supprimer: {active_subs} abonnements actifs'}), 400
    
    plan.is_active = False
    db.session.commit()
    
    log_action('admin_action', f"Plan désactivé: {plan.name}", admin_id=admin_id, severity='info')
    
    return jsonify({'success': True})


# ========== GESTION DES PRÉDICTIONS ==========

@admin_bp.route('/predictions')
@require_admin
def admin_predictions():
    """Gestion des prédictions"""
    predictions = Prediction.query.order_by(Prediction.created_at.desc()).limit(100).all()
    schedule = PredictionSchedule.query.filter_by(is_active=True).first()
    
    return render_template_string(ADMIN_PREDICTIONS_TEMPLATE,
        predictions=predictions,
        schedule=schedule
    )


@admin_bp.route('/predictions/schedule', methods=['POST'])
@require_admin
def admin_set_prediction_schedule():
    """Configurer le planning des prédictions"""
    admin_id = session.get('user_id')
    
    predictions_per_day = int(request.json.get('predictions_per_day', 3))
    publication_times = request.json.get('publication_times', [])
    publication_delays = request.json.get('publication_delays', [])
    
    # Désactiver l'ancien planning
    old_schedules = PredictionSchedule.query.filter_by(is_active=True).all()
    for sched in old_schedules:
        sched.is_active = False
    
    # Créer le nouveau planning
    schedule = PredictionSchedule(
        predictions_per_day=predictions_per_day,
        publication_times=json.dumps(publication_times),
        publication_delays=json.dumps(publication_delays),
        is_active=True,
        created_by=admin_id
    )
    db.session.add(schedule)
    db.session.commit()
    
    log_action('admin_action', f"Planning prédictions configuré: {predictions_per_day}/jour", 
               admin_id=admin_id, severity='info')
    
    return jsonify({'success': True})


@admin_bp.route('/prediction/<int:prediction_id>/invalidate', methods=['POST'])
@require_admin
def admin_invalidate_prediction(prediction_id):
    """Invalider une prédiction"""
    admin_id = session.get('user_id')
    prediction = Prediction.query.get_or_404(prediction_id)
    
    prediction.is_valid = False
    prediction.invalidated_by = admin_id
    prediction.invalidated_at = datetime.utcnow()
    db.session.commit()
    
    log_action('admin_action', f"Prédiction {prediction_id} invalidée", 
               admin_id=admin_id, severity='warning')
    
    return jsonify({'success': True})


# ========== GESTION DES NOTIFICATIONS ==========

@admin_bp.route('/notifications')
@require_admin
def admin_notifications():
    """Gestion des notifications"""
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    return render_template_string(ADMIN_NOTIFICATIONS_TEMPLATE, notifications=notifications)


@admin_bp.route('/notification/create', methods=['POST'])
@require_admin
def admin_create_notification():
    """Créer une notification"""
    admin_id = session.get('user_id')
    
    title = request.json.get('title', '').strip()
    message = request.json.get('message', '').strip()
    priority = request.json.get('priority', 'normal')
    notification_type = request.json.get('type', 'info')
    display_duration = int(request.json.get('display_duration', 5000))
    is_global = request.json.get('is_global', True)
    user_id = request.json.get('user_id') if not is_global else None
    
    if not title or not message:
        return jsonify({'error': 'Titre et message requis'}), 400
    
    # Si notification globale, créer pour tous les utilisateurs
    if is_global:
        users = User.query.filter_by(is_approved=True, is_active=True).all()
        for user in users:
            notification = Notification(
                user_id=user.id,
                is_global=True,
                title=title,
                message=message,
                priority=priority,
                notification_type=notification_type,
                display_duration=display_duration,
                created_by=admin_id
            )
            db.session.add(notification)
    else:
        if not user_id:
            return jsonify({'error': 'user_id requis pour notification ciblée'}), 400
        notification = Notification(
            user_id=user_id,
            is_global=False,
            title=title,
            message=message,
            priority=priority,
            notification_type=notification_type,
            display_duration=display_duration,
            created_by=admin_id
        )
        db.session.add(notification)
    
    db.session.commit()
    
    log_action('admin_action', f"Notification créée: {title}", admin_id=admin_id, severity='info')
    
    return jsonify({'success': True})


# ========== SAUVEGARDES ==========

@admin_bp.route('/backup/create', methods=['POST'])
@require_admin
def admin_create_backup():
    """Créer une sauvegarde manuelle"""
    admin_id = session.get('user_id')
    backup_path = create_backup('manual', admin_id)
    
    if backup_path:
        log_action('admin_action', f"Sauvegarde créée: {backup_path}", admin_id=admin_id, severity='info')
        return jsonify({'success': True, 'backup_path': backup_path})
    else:
        return jsonify({'error': 'Échec de la sauvegarde'}), 500


@admin_bp.route('/backups')
@require_admin
def admin_backups():
    """Liste des sauvegardes"""
    backups = BackupLog.query.order_by(BackupLog.created_at.desc()).limit(50).all()
    return render_template_string(ADMIN_BACKUPS_TEMPLATE, backups=backups)


# ========== TASKS AUTOMATIQUES ==========

@admin_bp.route('/tasks/cleanup', methods=['POST'])
@require_admin
def admin_run_cleanup():
    """Exécuter les tâches de nettoyage"""
    admin_id = session.get('user_id')
    
    expired_sessions = cleanup_expired_sessions()
    expired_subscriptions = check_and_expire_subscriptions()
    
    log_action('admin_action', 
               f"Nettoyage: {expired_sessions} sessions, {expired_subscriptions} abonnements", 
               admin_id=admin_id, severity='info')
    
    return jsonify({
        'success': True,
        'expired_sessions': expired_sessions,
        'expired_subscriptions': expired_subscriptions
    })


# Templates seront définis dans un fichier séparé ou dans fifa1.py
ADMIN_LOGIN_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
ADMIN_DASHBOARD_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
ADMIN_USERS_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
ADMIN_PLANS_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
ADMIN_PREDICTIONS_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
ADMIN_NOTIFICATIONS_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
ADMIN_BACKUPS_TEMPLATE = """<!-- Template sera défini dans fifa1.py -->"""
