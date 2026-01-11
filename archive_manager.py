"""
🗂️ GESTIONNAIRE D'ARCHIVAGE - ORACXPRED MÉTAPHORE
==================================================
Gère la sauvegarde et la mise à jour des données archivées pour la mémoire IA.
Système de mémoire fiable pour apprentissage supervisé.
"""

from models import db, MatchArchive, PredictionArchive, ModelPerformance, AnomalyLog, Prediction
from prediction_manager import log_action, create_alert
from datetime import datetime
import json


# ========== SAUVEGARDE AVANT MATCH ==========

def archive_match_before(match_id, jeu, ligue, equipe_1, equipe_2, date_heure_match, 
                         cote_1=None, cote_X=None, cote_2=None, mode=None, admin_id=None, extra_data=None):
    """
    Sauvegarde un match AVANT qu'il ne commence (archive obligatoire)
    
    Args:
        match_id: ID unique du match
        jeu: FIFA / FC / eFootball
        ligue: Nom de la ligue
        equipe_1, equipe_2: Noms des équipes
        date_heure_match: DateTime du match
        cote_1, cote_X, cote_2: Cotes initiales
        mode: Mode du match (3v3, 4v4, 5v5, Rush, etc.)
        admin_id: ID de l'admin qui archive (optionnel)
        extra_data: Données supplémentaires (dict)
    
    Returns:
        MatchArchive object
    """
    # Vérifier si le match existe déjà
    existing = MatchArchive.query.filter_by(match_id=match_id).first()
    
    if existing:
        # Mise à jour si match existe déjà
        existing.jeu = jeu
        existing.ligue = ligue
        existing.equipe_1 = equipe_1
        existing.equipe_2 = equipe_2
        existing.date_heure_match = date_heure_match
        existing.cote_1 = cote_1
        existing.cote_X = cote_X
        existing.cote_2 = cote_2
        existing.mode = mode
        existing.updated_at = datetime.utcnow()
        if extra_data:
            existing.extra_data = json.dumps(extra_data)
        
        match_archive = existing
    else:
        # Créer nouveau match archivé
        match_archive = MatchArchive(
            match_id=match_id,
            jeu=jeu,
            ligue=ligue,
            equipe_1=equipe_1,
            equipe_2=equipe_2,
            date_heure_match=date_heure_match,
            cote_1=cote_1,
            cote_X=cote_X,
            cote_2=cote_2,
            mode=mode,
            archived_by=admin_id,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        db.session.add(match_archive)
    
    try:
        db.session.commit()
        
        log_action('match_archived_before',
                  f"Match {match_id} archivé AVANT match: {equipe_1} vs {equipe_2}",
                  admin_id=admin_id,
                  severity='info',
                  extra_data={'match_id': match_id})
        
        return match_archive
    except Exception as e:
        db.session.rollback()
        log_action('archive_error', f"Erreur lors de l'archivage du match {match_id}: {str(e)}", severity='error')
        raise


def archive_prediction_before(match_id, prediction_id, consensus_type, choix, probabilite, confiance,
                              vote_statistique=False, vote_cotes=False, vote_simulation=False, vote_forme=False,
                              consensus=False, extra_data=None):
    """
    Archive une prédiction AVANT le match (mémoire pour apprentissage)
    
    Args:
        match_id: ID du match (doit exister dans MatchArchive)
        prediction_id: ID de la prédiction originale (optionnel)
        consensus_type: Type de consensus (1X2 ou alternatif)
        choix: Choix de la prédiction
        probabilite: Probabilité en %
        confiance: Confiance en %
        vote_*: Votes des modules
        consensus: Consensus atteint (booléen)
        extra_data: Données supplémentaires (dict)
    
    Returns:
        PredictionArchive object
    """
    # Vérifier que le match existe dans l'archive
    match_archive = MatchArchive.query.filter_by(match_id=match_id).first()
    if not match_archive:
        raise ValueError(f"Match {match_id} doit être archivé AVANT d'archiver sa prédiction")
    
    # Vérifier si prédiction existe déjà
    existing = PredictionArchive.query.filter_by(match_id=match_id, consensus_type=consensus_type).first()
    
    if existing:
        # Mise à jour
        existing.prediction_id = prediction_id
        existing.choix = choix
        existing.probabilite = probabilite
        existing.confiance = confiance
        existing.vote_statistique = vote_statistique
        existing.vote_cotes = vote_cotes
        existing.vote_simulation = vote_simulation
        existing.vote_forme = vote_forme
        existing.consensus = consensus
        existing.updated_at = datetime.utcnow()
        if extra_data:
            existing.extra_data = json.dumps(extra_data)
        
        pred_archive = existing
    else:
        # Créer nouvelle prédiction archivée
        pred_archive = PredictionArchive(
            match_id=match_id,
            prediction_id=prediction_id,
            consensus_type=consensus_type,
            choix=choix,
            probabilite=probabilite,
            confiance=confiance,
            vote_statistique=vote_statistique,
            vote_cotes=vote_cotes,
            vote_simulation=vote_simulation,
            vote_forme=vote_forme,
            consensus=consensus,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        db.session.add(pred_archive)
    
    try:
        db.session.commit()
        
        log_action('prediction_archived_before',
                  f"Prédiction archivée AVANT match {match_id}: {choix} (confiance: {confiance}%)",
                  severity='info',
                  extra_data={'match_id': match_id, 'prediction_archive_id': pred_archive.id})
        
        # Vérifier les anomalies de confiance
        if confiance > 95:
            create_anomaly_log('high_confidence',
                              f"Confiance anormalement élevée ({confiance}%) pour match {match_id}",
                              match_id=match_id,
                              prediction_archive_id=pred_archive.id,
                              severity='warning',
                              context_data={'confiance': confiance, 'probabilite': probabilite})
        
        return pred_archive
    except Exception as e:
        db.session.rollback()
        log_action('archive_error', f"Erreur lors de l'archivage de la prédiction: {str(e)}", severity='error')
        raise


# ========== MISE À JOUR APRÈS MATCH ==========

def update_match_after(match_id, score_final_equipe_1, score_final_equipe_2, 
                       resultat_reel, statut_final='terminé', anomalies_detectees=None, admin_id=None):
    """
    Met à jour un match APRÈS qu'il soit terminé (résultats finaux)
    
    Args:
        match_id: ID du match
        score_final_equipe_1, score_final_equipe_2: Scores finaux
        resultat_reel: Résultat réel (1, X, 2)
        statut_final: Statut final (terminé, annulé)
        anomalies_detectees: Description des anomalies (optionnel)
        admin_id: ID de l'admin qui met à jour (optionnel)
    
    Returns:
        MatchArchive object mis à jour
    """
    match_archive = MatchArchive.query.filter_by(match_id=match_id).first()
    if not match_archive:
        raise ValueError(f"Match {match_id} n'existe pas dans l'archive")
    
    # Vérifier si déjà verrouillé
    if match_archive.is_locked:
        log_action('archive_update_blocked',
                  f"Tentative de mise à jour d'un match verrouillé {match_id}",
                  admin_id=admin_id,
                  severity='warning')
        return match_archive
    
    # Mise à jour des résultats
    match_archive.score_final_equipe_1 = score_final_equipe_1
    match_archive.score_final_equipe_2 = score_final_equipe_2
    match_archive.resultat_reel = resultat_reel
    match_archive.statut_final = statut_final
    match_archive.updated_at = datetime.utcnow()
    match_archive.is_locked = True  # Verrouiller après mise à jour
    
    # Enregistrer anomalies si présentes
    if anomalies_detectees:
        extra_data = json.loads(match_archive.extra_data) if match_archive.extra_data else {}
        extra_data['anomalies_detectees'] = anomalies_detectees
        match_archive.extra_data = json.dumps(extra_data)
        
        create_anomaly_log('match_anomalies',
                          f"Anomalies détectées pour match {match_id}: {anomalies_detectees}",
                          match_id=match_id,
                          severity='warning',
                          context_data={'anomalies': anomalies_detectees})
    
    try:
        db.session.commit()
        
        log_action('match_updated_after',
                  f"Match {match_id} mis à jour APRÈS match: {score_final_equipe_1}-{score_final_equipe_2} ({resultat_reel})",
                  admin_id=admin_id,
                  severity='info',
                  extra_data={'match_id': match_id, 'resultat': resultat_reel})
        
        # Mettre à jour les prédictions archivées associées
        update_predictions_after_match(match_id, resultat_reel)
        
        return match_archive
    except Exception as e:
        db.session.rollback()
        log_action('archive_update_error', f"Erreur lors de la mise à jour du match {match_id}: {str(e)}", severity='error')
        raise


def update_predictions_after_match(match_id, resultat_reel):
    """
    Met à jour toutes les prédictions archivées APRÈS le match (calcule si correct)
    
    Args:
        match_id: ID du match
        resultat_reel: Résultat réel (1, X, 2)
    """
    predictions = PredictionArchive.query.filter_by(match_id=match_id).all()
    
    for pred in predictions:
        # Déterminer si la prédiction est correcte
        prediction_correcte = None
        ecart_probabilite = None
        
        if pred.consensus_type == '1X2':
            # Pour 1X2, comparer le choix avec le résultat réel
            choix_normalise = str(pred.choix).upper()
            resultat_normalise = str(resultat_reel).upper()
            
            # Extraire le résultat prédit (1, X, 2)
            if 'VICTOIRE' in choix_normalise or pred.choix.startswith('1'):
                choix_extrait = '1'
            elif 'NUL' in choix_normalise or 'X' in choix_normalise or pred.choix.startswith('X'):
                choix_extrait = 'X'
            elif pred.choix.startswith('2'):
                choix_extrait = '2'
            else:
                choix_extrait = None
            
            if choix_extrait:
                prediction_correcte = (choix_extrait == resultat_normalise)
                
                # Calculer l'écart de probabilité
                if resultat_normalise == '1':
                    prob_reel = 100.0
                elif resultat_normalise == 'X':
                    prob_reel = 100.0
                elif resultat_normalise == '2':
                    prob_reel = 100.0
                else:
                    prob_reel = 33.33  # Par défaut
                
                ecart_probabilite = abs(pred.probabilite - prob_reel)
        
        # Mettre à jour la prédiction
        pred.resultat_reel = resultat_reel
        pred.prediction_correcte = prediction_correcte
        pred.ecart_probabilite = ecart_probabilite
        pred.finalized_at = datetime.utcnow()
        pred.updated_at = datetime.utcnow()
        
        # Vérifier les anomalies
        if pred.consensus and not prediction_correcte:
            # Consensus annoncé mais résultat incohérent
            create_anomaly_log('consensus_incoherent',
                              f"Consensus annoncé mais prédiction incorrecte pour match {match_id}",
                              match_id=match_id,
                              prediction_archive_id=pred.id,
                              severity='error',
                              context_data={
                                  'choix': pred.choix,
                                  'resultat_reel': resultat_reel,
                                  'probabilite': pred.probabilite,
                                  'confiance': pred.confiance
                              })
    
    try:
        db.session.commit()
        
        log_action('predictions_updated_after',
                  f"Prédictions archivées mises à jour pour match {match_id}",
                  severity='info',
                  extra_data={'match_id': match_id, 'resultat': resultat_reel})
        
        # Recalculer les performances
        calculate_model_performance()
        
    except Exception as e:
        db.session.rollback()
        log_action('predictions_update_error', f"Erreur lors de la mise à jour des prédictions: {str(e)}", severity='error')


# ========== CALCUL DE PERFORMANCE ==========

def calculate_model_performance(date_debut=None, date_fin=None):
    """
    Calcule les performances du modèle sur une période donnée
    
    Args:
        date_debut: Date de début (par défaut: il y a 30 jours)
        date_fin: Date de fin (par défaut: maintenant)
    
    Returns:
        ModelPerformance object
    """
    from datetime import timedelta
    
    if not date_debut:
        date_fin = datetime.utcnow()
        date_debut = date_fin - timedelta(days=30)
    elif not date_fin:
        date_fin = datetime.utcnow()
    
    # Récupérer toutes les prédictions finalisées dans la période
    predictions = PredictionArchive.query.filter(
        PredictionArchive.finalized_at >= date_debut,
        PredictionArchive.finalized_at <= date_fin,
        PredictionArchive.prediction_correcte.isnot(None)
    ).all()
    
    if not predictions:
        return None
    
    total = len(predictions)
    correctes = sum(1 for p in predictions if p.prediction_correcte)
    taux_reussite = (correctes / total * 100) if total > 0 else 0
    
    # Calculer par module
    stats_statistique = [p for p in predictions if p.vote_statistique]
    stats_cotes = [p for p in predictions if p.vote_cotes]
    stats_simulation = [p for p in predictions if p.vote_simulation]
    stats_forme = [p for p in predictions if p.vote_forme]
    stats_consensus = [p for p in predictions if p.consensus]
    
    taux_reussite_statistique = (sum(1 for p in stats_statistique if p.prediction_correcte) / len(stats_statistique) * 100) if stats_statistique else None
    taux_reussite_cotes = (sum(1 for p in stats_cotes if p.prediction_correcte) / len(stats_cotes) * 100) if stats_cotes else None
    taux_reussite_simulation = (sum(1 for p in stats_simulation if p.prediction_correcte) / len(stats_simulation) * 100) if stats_simulation else None
    taux_reussite_forme = (sum(1 for p in stats_forme if p.prediction_correcte) / len(stats_forme) * 100) if stats_forme else None
    taux_reussite_consensus = (sum(1 for p in stats_consensus if p.prediction_correcte) / len(stats_consensus) * 100) if stats_consensus else None
    
    # Calculer moyennes de confiance
    moyenne_confiance = sum(p.confiance for p in predictions) / total if total > 0 else 0
    moyenne_probabilite = sum(p.probabilite for p in predictions) / total if total > 0 else 0
    ecart_moyen_probabilite = sum(p.ecart_probabilite for p in predictions if p.ecart_probabilite) / total if total > 0 else None
    
    # Par type
    preds_1x2 = [p for p in predictions if p.consensus_type == '1X2']
    preds_alternatifs = [p for p in predictions if p.consensus_type == 'alternatif']
    
    taux_reussite_1x2 = (sum(1 for p in preds_1x2 if p.prediction_correcte) / len(preds_1x2) * 100) if preds_1x2 else None
    taux_reussite_alternatifs = (sum(1 for p in preds_alternatifs if p.prediction_correcte) / len(preds_alternatifs) * 100) if preds_alternatifs else None
    
    # Créer ou mettre à jour la performance
    performance = ModelPerformance.query.filter_by(date_debut=date_debut, date_fin=date_fin).first()
    
    if not performance:
        performance = ModelPerformance(
            date_debut=date_debut,
            date_fin=date_fin,
            total_predictions=total,
            predictions_correctes=correctes,
            taux_reussite=taux_reussite,
            taux_reussite_statistique=taux_reussite_statistique,
            taux_reussite_cotes=taux_reussite_cotes,
            taux_reussite_simulation=taux_reussite_simulation,
            taux_reussite_forme=taux_reussite_forme,
            taux_reussite_consensus=taux_reussite_consensus,
            moyenne_confiance=moyenne_confiance,
            moyenne_probabilite=moyenne_probabilite,
            ecart_moyen_probabilite=ecart_moyen_probabilite,
            taux_reussite_1x2=taux_reussite_1x2,
            taux_reussite_alternatifs=taux_reussite_alternatifs
        )
        db.session.add(performance)
    else:
        performance.total_predictions = total
        performance.predictions_correctes = correctes
        performance.taux_reussite = taux_reussite
        performance.taux_reussite_statistique = taux_reussite_statistique
        performance.taux_reussite_cotes = taux_reussite_cotes
        performance.taux_reussite_simulation = taux_reussite_simulation
        performance.taux_reussite_forme = taux_reussite_forme
        performance.taux_reussite_consensus = taux_reussite_consensus
        performance.moyenne_confiance = moyenne_confiance
        performance.moyenne_probabilite = moyenne_probabilite
        performance.ecart_moyen_probabilite = ecart_moyen_probabilite
        performance.taux_reussite_1x2 = taux_reussite_1x2
        performance.taux_reussite_alternatifs = taux_reussite_alternatifs
        performance.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        log_action('performance_calculated',
                  f"Performance calculée: {taux_reussite:.2f}% ({correctes}/{total})",
                  severity='info',
                  extra_data={'date_debut': date_debut.isoformat(), 'date_fin': date_fin.isoformat(), 'taux_reussite': taux_reussite})
        
        return performance
    except Exception as e:
        db.session.rollback()
        log_action('performance_error', f"Erreur lors du calcul de performance: {str(e)}", severity='error')
        raise


# ========== GESTION DES ANOMALIES ==========

def create_anomaly_log(anomaly_type, description, match_id=None, prediction_archive_id=None,
                       severity='warning', context_data=None):
    """
    Crée un log d'anomalie
    
    Args:
        anomaly_type: Type d'anomalie (high_confidence, consensus_incoherent, odds_change, match_unlocked, etc.)
        description: Description de l'anomalie
        match_id: ID du match concerné
        prediction_archive_id: ID de la prédiction archivée concernée
        severity: Niveau de sévérité (info, warning, error, critical)
        context_data: Données contextuelles (dict)
    
    Returns:
        AnomalyLog object
    """
    anomaly = AnomalyLog(
        anomaly_type=anomaly_type,
        description=description,
        match_id=match_id,
        prediction_archive_id=prediction_archive_id,
        severity=severity,
        context_data=json.dumps(context_data) if context_data else None
    )
    
    db.session.add(anomaly)
    
    try:
        db.session.commit()
        
        log_action('anomaly_logged',
                  f"Anomalie enregistrée: {anomaly_type} - {description}",
                  severity=severity,
                  extra_data={'anomaly_id': anomaly.id, 'anomaly_type': anomaly_type})
        
        # Créer aussi une alerte pour l'admin
        create_alert(anomaly_type, description, severity=severity, match_id=match_id)
        
        return anomaly
    except Exception as e:
        db.session.rollback()
        log_action('anomaly_log_error', f"Erreur lors de la création du log d'anomalie: {str(e)}", severity='error')
        return None


def resolve_anomaly(anomaly_id, admin_id, resolution_notes):
    """
    Résout une anomalie (admin uniquement)
    
    Args:
        anomaly_id: ID de l'anomalie
        admin_id: ID de l'admin
        resolution_notes: Notes de résolution
    """
    anomaly = AnomalyLog.query.get(anomaly_id)
    if not anomaly:
        return False
    
    anomaly.is_resolved = True
    anomaly.resolved_by = admin_id
    anomaly.resolved_at = datetime.utcnow()
    anomaly.resolution_notes = resolution_notes
    
    try:
        db.session.commit()
        
        log_action('anomaly_resolved',
                  f"Anomalie {anomaly_id} résolue par admin {admin_id}",
                  admin_id=admin_id,
                  severity='info',
                  extra_data={'anomaly_id': anomaly_id})
        
        return True
    except Exception as e:
        db.session.rollback()
        log_action('anomaly_resolve_error', f"Erreur lors de la résolution de l'anomalie: {str(e)}", severity='error')
        return False


# ========== FONCTIONS UTILITAIRES ==========

def get_match_archive(match_id):
    """Récupère un match archivé"""
    return MatchArchive.query.filter_by(match_id=match_id).first()


def get_prediction_archives(match_id):
    """Récupère toutes les prédictions archivées pour un match"""
    return PredictionArchive.query.filter_by(match_id=match_id).all()


def get_recent_performance(days=30):
    """Récupère les performances récentes"""
    from datetime import timedelta
    date_debut = datetime.utcnow() - timedelta(days=days)
    return ModelPerformance.query.filter(ModelPerformance.date_debut >= date_debut).all()


def get_unresolved_anomalies():
    """Récupère toutes les anomalies non résolues"""
    return AnomalyLog.query.filter_by(is_resolved=False).order_by(AnomalyLog.detected_at.desc()).all()
