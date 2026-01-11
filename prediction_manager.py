"""
🎯 GESTIONNAIRE DE PRÉDICTIONS - ORACXPRED MÉTAPHORE
====================================================
Gère la génération, validation et alertes des prédictions
"""

from models import db, Prediction, Alert, SystemLog, AccessLog
from datetime import datetime
import json
from flask import request


def get_client_ip():
    """Récupère l'IP du client"""
    if request:
        return request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    return 'unknown'


def create_prediction(match_id, team1, team2, league, consensus_result, consensus_probability, 
                     confidence, recommended_odd, recommended_action, consensus_type='1X2',
                     votes_statistique=False, votes_cotes=False, votes_simulation=False, votes_forme=False,
                     extra_data=None):
    """
    Crée une prédiction et la sauvegarde en base de données
    
    Args:
        match_id: ID du match depuis l'API
        team1, team2: Noms des équipes
        league: Ligue
        consensus_result: Résultat du consensus
        consensus_probability: Probabilité en %
        confidence: Confiance en %
        recommended_odd: Cote recommandée
        recommended_action: Action recommandée (MISE, PASSER, etc.)
        consensus_type: Type de consensus (1X2 ou alternatif)
        votes_*: Votes des différents systèmes
        extra_data: Données supplémentaires (dict)
    
    Returns:
        Prediction object
    """
    # Vérifier si une prédiction existe déjà pour ce match
    existing = Prediction.query.filter_by(match_id=match_id, consensus_type=consensus_type).first()
    
    if existing:
        # Mettre à jour la prédiction existante
        existing.team1 = team1
        existing.team2 = team2
        existing.league = league
        existing.consensus_result = consensus_result
        existing.consensus_probability = consensus_probability
        existing.confidence = confidence
        existing.recommended_odd = recommended_odd
        existing.recommended_action = recommended_action
        existing.votes_statistique = votes_statistique
        existing.votes_cotes = votes_cotes
        existing.votes_simulation = votes_simulation
        existing.votes_forme = votes_forme
        existing.updated_at = datetime.utcnow()
        if extra_data:
            existing.extra_data = json.dumps(extra_data)
        
        prediction = existing
    else:
        # Créer une nouvelle prédiction
        prediction = Prediction(
            match_id=match_id,
            team1=team1,
            team2=team2,
            league=league,
            consensus_result=consensus_result,
            consensus_probability=consensus_probability,
            confidence=confidence,
            recommended_odd=recommended_odd,
            recommended_action=recommended_action,
            consensus_type=consensus_type,
            votes_statistique=votes_statistique,
            votes_cotes=votes_cotes,
            votes_simulation=votes_simulation,
            votes_forme=votes_forme,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        db.session.add(prediction)
    
    try:
        db.session.commit()
        
        # Logger la création/modification
        log_action('prediction_generated', 
                  f"Prédiction {'mise à jour' if existing else 'créée'} pour match {match_id}: {team1} vs {team2}",
                  severity='info',
                  extra_data={'match_id': match_id, 'prediction_id': prediction.id})
        
        # Vérifier les anomalies et créer des alertes
        check_prediction_anomalies(prediction)
        
        return prediction
    except Exception as e:
        db.session.rollback()
        log_action('prediction_error', f"Erreur lors de la création de prédiction: {str(e)}", severity='error')
        raise


def get_prediction_by_match(match_id, consensus_type='1X2'):
    """Récupère la prédiction pour un match donné"""
    return Prediction.query.filter_by(match_id=match_id, consensus_type=consensus_type, is_valid=True).first()


def invalidate_prediction(prediction_id, admin_id):
    """
    Invalide une prédiction (action admin)
    L'IA doit obéir et apprendre
    """
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return False
    
    prediction.is_valid = False
    prediction.invalidated_by = admin_id
    prediction.invalidated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Logger l'action admin
        log_action('prediction_invalidated',
                  f"Prédiction {prediction_id} invalidée par admin {admin_id}",
                  admin_id=admin_id,
                  severity='warning',
                  extra_data={'prediction_id': prediction_id, 'match_id': prediction.match_id})
        
        # Créer une alerte pour informer l'IA
        create_alert('prediction_invalidated',
                    f"Prédiction invalidée par admin pour match {prediction.match_id}: {prediction.team1} vs {prediction.team2}",
                    severity='warning',
                    prediction_id=prediction_id,
                    match_id=prediction.match_id)
        
        return True
    except Exception as e:
        db.session.rollback()
        log_action('prediction_invalidation_error', f"Erreur lors de l'invalidation: {str(e)}", severity='error')
        return False


def lock_prediction(prediction_id, reason="Match commencé"):
    """Verrouille une prédiction (match commencé)"""
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return False
    
    prediction.is_locked = True
    
    try:
        db.session.commit()
        
        log_action('prediction_locked',
                  f"Prédiction {prediction_id} verrouillée: {reason}",
                  severity='info',
                  extra_data={'prediction_id': prediction_id, 'match_id': prediction.match_id})
        
        return True
    except Exception as e:
        db.session.rollback()
        return False


def check_prediction_anomalies(prediction):
    """
    Vérifie les anomalies dans une prédiction et crée des alertes si nécessaire
    
    Alertes possibles:
    - Confiance anormalement faible (< 50%)
    - Confiance anormalement élevée (> 95%)
    - Changements brusques de cotes
    - Incohérences dans les votes
    """
    alerts_created = []
    
    # 1. Vérifier la confiance anormale
    if prediction.confidence < 50:
        alert = create_alert('low_confidence',
                            f"Confiance anormalement faible ({prediction.confidence}%) pour match {prediction.match_id}",
                            severity='warning',
                            prediction_id=prediction.id,
                            match_id=prediction.match_id,
                            extra_data={'confidence': prediction.confidence})
        alerts_created.append(alert)
    
    if prediction.confidence > 95:
        alert = create_alert('high_confidence',
                            f"Confiance anormalement élevée ({prediction.confidence}%) pour match {prediction.match_id}",
                            severity='info',
                            prediction_id=prediction.id,
                            match_id=prediction.match_id,
                            extra_data={'confidence': prediction.confidence})
        alerts_created.append(alert)
    
    # 2. Vérifier les incohérences dans les votes
    votes_count = sum([prediction.votes_statistique, prediction.votes_cotes, 
                      prediction.votes_simulation, prediction.votes_forme])
    if votes_count == 0:
        alert = create_alert('no_votes',
                            f"Aucun vote pour la prédiction du match {prediction.match_id}",
                            severity='error',
                            prediction_id=prediction.id,
                            match_id=prediction.match_id)
        alerts_created.append(alert)
    
    # 3. Vérifier les incohérences probabilité/confiance
    if prediction.consensus_probability < 20 and prediction.confidence > 70:
        alert = create_alert('inconsistency',
                            f"Incohérence probabilité ({prediction.consensus_probability}%) / confiance ({prediction.confidence}%) pour match {prediction.match_id}",
                            severity='warning',
                            prediction_id=prediction.id,
                            match_id=prediction.match_id,
                            extra_data={'probability': prediction.consensus_probability, 'confidence': prediction.confidence})
        alerts_created.append(alert)
    
    return alerts_created


def create_alert(alert_type, message, severity='warning', prediction_id=None, match_id=None, extra_data=None):
    """
    Crée une alerte système
    
    Args:
        alert_type: Type d'alerte (low_confidence, odds_change, match_started, inconsistency, etc.)
        message: Message de l'alerte
        severity: Niveau de sévérité (info, warning, error, critical)
        prediction_id: ID de la prédiction concernée (optionnel)
        match_id: ID du match concerné (optionnel)
        extra_data: Données supplémentaires (dict)
    
    Returns:
        Alert object
    """
    alert = Alert(
        alert_type=alert_type,
        message=message,
        severity=severity,
        prediction_id=prediction_id,
        match_id=match_id,
        extra_data=json.dumps(extra_data) if extra_data else None
    )
    
    db.session.add(alert)
    
    try:
        db.session.commit()
        
        # Logger l'alerte
        log_action('alert_created',
                  f"Alerte créée: {alert_type} - {message}",
                  severity=severity,
                  extra_data={'alert_id': alert.id, 'alert_type': alert_type})
        
        return alert
    except Exception as e:
        db.session.rollback()
        log_action('alert_creation_error', f"Erreur lors de la création d'alerte: {str(e)}", severity='error')
        return None


def check_match_started_alert(match_id, minute):
    """
    Vérifie si un match a commencé sans verrouillage de prédiction
    
    Args:
        match_id: ID du match
        minute: Minute du match (> 0 = match commencé)
    """
    if minute > 0:
        # Chercher les prédictions non verrouillées pour ce match
        predictions = Prediction.query.filter_by(match_id=match_id, is_locked=False, is_valid=True).all()
        
        for pred in predictions:
            # Créer une alerte
            create_alert('match_started',
                        f"Match {match_id} ({pred.team1} vs {pred.team2}) commencé ({minute}') sans verrouillage de prédiction",
                        severity='warning',
                        prediction_id=pred.id,
                        match_id=match_id,
                        extra_data={'minute': minute})
            
            # Verrouiller la prédiction
            lock_prediction(pred.id, f"Match commencé (minute {minute})")


def check_odds_change_alert(match_id, old_odds, new_odds, threshold=0.3):
    """
    Vérifie les changements brusques de cotes
    
    Args:
        match_id: ID du match
        old_odds: Anciennes cotes (dict)
        new_odds: Nouvelles cotes (dict)
        threshold: Seuil de changement (0.3 = 30%)
    """
    if not old_odds or not new_odds:
        return
    
    # Comparer les cotes
    for key in set(old_odds.keys()) & set(new_odds.keys()):
        old_val = float(old_odds[key])
        new_val = float(new_odds[key])
        
        if old_val > 0:
            change = abs((new_val - old_val) / old_val)
            
            if change >= threshold:
                # Changement significatif
                prediction = get_prediction_by_match(match_id)
                if prediction:
                    create_alert('odds_change',
                                f"Changement brusque de cote pour match {match_id}: {key} de {old_val} à {new_val} (changement: {change*100:.1f}%)",
                                severity='warning',
                                prediction_id=prediction.id,
                                match_id=match_id,
                                extra_data={'key': key, 'old_odds': old_val, 'new_odds': new_val, 'change_percent': change*100})


def log_action(action_type, message, user_id=None, admin_id=None, severity='info', extra_data=None):
    """
    Journalise une action dans le système
    
    Args:
        action_type: Type d'action
        message: Message de l'action
        user_id: ID de l'utilisateur (optionnel)
        admin_id: ID de l'admin (optionnel)
        severity: Niveau de sévérité
        extra_data: Données supplémentaires (dict)
    """
    try:
        log_entry = SystemLog(
            action_type=action_type,
            user_id=user_id,
            admin_id=admin_id,
            message=message,
            severity=severity,
            extra_data=json.dumps(extra_data) if extra_data else None,
            ip_address=get_client_ip()
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"❌ Erreur lors de la journalisation: {e}")
        db.session.rollback()


def log_access(user_id, action_type, match_id=None, prediction_id=None, subscription_plan=None, extra_data=None):
    """
    Journalise un accès utilisateur (pour traçabilité des revenus)
    
    Args:
        user_id: ID de l'utilisateur
        action_type: Type d'action (view_prediction, view_details, subscription_access)
        match_id: ID du match (optionnel)
        prediction_id: ID de la prédiction (optionnel)
        subscription_plan: Plan d'abonnement utilisé (optionnel)
        extra_data: Données supplémentaires (dict)
    """
    try:
        access_log = AccessLog(
            user_id=user_id,
            action_type=action_type,
            match_id=match_id,
            prediction_id=prediction_id,
            subscription_plan=subscription_plan,
            ip_address=get_client_ip(),
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        db.session.add(access_log)
        db.session.commit()
    except Exception as e:
        print(f"❌ Erreur lors de la journalisation d'accès: {e}")
        db.session.rollback()
