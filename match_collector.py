#!/usr/bin/env python3
"""
SYSTÈME DE COLLECTE AUTOMATIQUE DES MATCHS - ORACXPRED
============================================
Système autonome de surveillance et de collecte des matchs en temps réel.
Capable de détecter automatiquement les débuts et fins de matchs.
"""

import time
import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import random
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import des modèles
try:
    from models import db, CollectedMatch, MatchCollectionLog
    from prediction_manager import log_action
    MODELS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Modèles non disponibles: {e}")
    MODELS_AVAILABLE = False


class MatchDataSource:
    """Source de données pour les matchs (API, scraper, ou simulé)"""
    
    def __init__(self, source_type: str = "simulated"):
        self.source_type = source_type
        self.base_url = "https://api.example.com/matches"  # URL fictive pour API réelle
        
    def get_live_matches(self) -> List[Dict]:
        """Récupère les matchs en cours depuis la source"""
        if self.source_type == "simulated":
            return self._generate_simulated_matches()
        elif self.source_type == "api":
            return self._fetch_from_api()
        else:
            return []
    
    def _generate_simulated_matches(self) -> List[Dict]:
        """Génère des matchs simulés pour démonstration"""
        teams_fifa = [
            "Real Madrid", "Barcelona", "Manchester City", "Liverpool", 
            "PSG", "Bayern Munich", "Chelsea", "Arsenal",
            "Inter Milan", "AC Milan", "Juventus", "Napoli"
        ]
        
        teams_efootball = [
            "Team Alpha", "Team Beta", "Team Gamma", "Team Delta",
            "Team Omega", "Team Sigma", "Team Theta", "Team Lambda"
        ]
        
        matches = []
        
        # Générer 5-10 matchs aléatoires
        num_matches = random.randint(5, 10)
        
        for i in range(num_matches):
            # Choisir le jeu
            jeu = random.choice(["FIFA", "eFootball", "FC"])
            
            # Choisir les équipes selon le jeu
            if jeu == "FIFA":
                equipe1, equipe2 = random.sample(teams_fifa, 2)
            else:
                equipe1, equipe2 = random.sample(teams_efootball, 2)
            
            # Générer l'heure de début (dans les 24 dernières heures ou prochaines 24h)
            heures_offset = random.randint(-24, 24)
            heure_debut = datetime.now() + timedelta(hours=heures_offset)
            
            # Déterminer le statut
            if heures_offset < -2:
                statut = random.choice(["termine", "annule"])
                if statut == "termine":
                    # Générer un score final
                    score1 = random.randint(0, 5)
                    score2 = random.randint(0, 5)
                    heure_fin = heure_debut + timedelta(minutes=random.randint(90, 120))
                else:
                    score1 = score2 = None
                    heure_fin = None
            elif heures_offset < 0:
                statut = "en_cours"
                # Match en cours - score partiel
                score1 = random.randint(0, 3)
                score2 = random.randint(0, 3)
                heure_fin = None
            else:
                statut = "en_attente"
                score1 = score2 = None
                heure_fin = None
            
            match = {
                "unique_match_id": f"{jeu.lower()}_{uuid.uuid4().hex[:8]}",
                "jeu": jeu,
                "equipe_domicile": equipe1,
                "equipe_exterieur": equipe2,
                "heure_debut": heure_debut,
                "heure_fin": heure_fin,
                "score_domicile": score1,
                "score_exterieur": score2,
                "statut": statut,
                "source_donnees": "simulated"
            }
            
            matches.append(match)
        
        return matches
    
    def _fetch_from_api(self) -> List[Dict]:
        """Récupère les matchs depuis une API réelle (à implémenter)"""
        try:
            # Implémentation future pour API réelle
            response = requests.get(f"{self.base_url}/live", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur API: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Exception lors de l'appel API: {e}")
            return []


class MatchCollector:
    """Collecteur principal de matchs - Cœur du système"""
    
    def __init__(self, source_type: str = "simulated", check_interval: int = 30):
        self.source = MatchDataSource(source_type)
        self.check_interval = check_interval  # Secondes entre chaque vérification
        self.running = False
        self.processed_matches = set()  # Pour éviter les doublons
        
        logger.info(f"Collecteur initialisé avec source: {source_type}")
        logger.info(f"Intervalle de vérification: {check_interval} secondes")
    
    def start_collection(self):
        """Démarre la collecte continue"""
        self.running = True
        logger.info("🚀 Démarrage de la collecte automatique des matchs")
        
        self._log_collection("detection_start", "Système de collecte démarré", "info")
        
        try:
            while self.running:
                self._collect_and_process_matches()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Arrêt manuel du collecteur")
        except Exception as e:
            logger.error(f"Erreur critique dans la collecte: {e}")
            self._log_collection("erreur", f"Erreur critique: {e}", "error")
        finally:
            self.running = False
            logger.info("🛑 Système de collecte arrêté")
    
    def stop_collection(self):
        """Arrête la collecte"""
        self.running = False
        logger.info("Signal d'arrêt envoyé au collecteur")
    
    def _collect_and_process_matches(self):
        """Collecte et traite les matchs depuis la source"""
        try:
            start_time = time.time()
            matches = self.source.get_live_matches()
            temps_execution = time.time() - start_time
            
            logger.info(f"📊 {len(matches)} matchs récupérés depuis la source")
            
            processed_count = 0
            new_matches = 0
            updated_matches = 0
            
            for match_data in matches:
                match_id = match_data["unique_match_id"]
                
                # Vérifier si le match a déjà été traité récemment
                if match_id in self.processed_matches:
                    processed_count += 1
                    continue
                
                # Traiter le match
                result = self._process_match(match_data)
                if result == "new":
                    new_matches += 1
                elif result == "updated":
                    updated_matches += 1
                
                # Ajouter aux matchs traités
                self.processed_matches.add(match_id)
            
            # Nettoyer les anciens matchs traités (garder 1000 derniers)
            if len(self.processed_matches) > 1000:
                self.processed_matches = set(list(self.processed_matches)[-1000:])
            
            message = f"Collecte terminée: {new_matches} nouveaux, {updated_matches} mis à jour, {processed_count} déjà traités"
            logger.info(f"✅ {message}")
            
            self._log_collection("collecte_success", message, "info", {
                "temps_execution": temps_execution,
                "total_matches": len(matches),
                "new_matches": new_matches,
                "updated_matches": updated_matches
            })
            
        except Exception as e:
            error_msg = f"Erreur lors de la collecte: {e}"
            logger.error(error_msg)
            self._log_collection("erreur", error_msg, "error")
    
    def _process_match(self, match_data: Dict) -> str:
        """Traite un match individuel (création ou mise à jour)"""
        if not MODELS_AVAILABLE:
            logger.warning(f"Modeles non disponibles, traitement simulé: {match_data['unique_match_id']}")
            return "simulated"
        
        try:
            # Vérifier si le match existe déjà
            existing_match = CollectedMatch.query.filter_by(
                unique_match_id=match_data["unique_match_id"]
            ).first()
            
            if existing_match:
                # Mettre à jour le match existant
                return self._update_existing_match(existing_match, match_data)
            else:
                # Créer un nouveau match
                return self._create_new_match(match_data)
                
        except Exception as e:
            logger.error(f"Erreur traitement match {match_data['unique_match_id']}: {e}")
            return "error"
    
    def _create_new_match(self, match_data: Dict) -> str:
        """Crée un nouveau match dans la base de données"""
        try:
            match = CollectedMatch(
                unique_match_id=match_data["unique_match_id"],
                jeu=match_data["jeu"],
                equipe_domicile=match_data["equipe_domicile"],
                equipe_exterieur=match_data["equipe_exterieur"],
                heure_debut=match_data["heure_debut"],
                heure_fin=match_data.get("heure_fin"),
                score_domicile=match_data.get("score_domicile"),
                score_exterieur=match_data.get("score_exterieur"),
                statut=match_data["statut"],
                source_donnees=match_data.get("source_donnees", "unknown"),
                collecte_par="systeme_auto"
            )
            
            # Déterminer le gagnant si le match est terminé
            if match.statut == "termine" and match.score_domicile is not None:
                match.equipe_gagnante = match.determine_gagnant()
            
            db.session.add(match)
            db.session.commit()
            
            logger.info(f"🆕 Nouveau match créé: {match.unique_match_id} - {match.equipe_domicile} vs {match.equipe_exterieur}")
            
            # Logger l'action
            if MODELS_AVAILABLE:
                log_action("match_collecte", f"Nouveau match collecté: {match.unique_match_id}", {
                    "match_id": match.unique_match_id,
                    "equipes": f"{match.equipe_domicile} vs {match.equipe_exterieur}",
                    "statut": match.statut
                })
            
            return "new"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur création match: {e}")
            return "error"
    
    def _update_existing_match(self, match: CollectedMatch, match_data: Dict) -> str:
        """Met à jour un match existant"""
        try:
            # Vérifier si les données ont changé
            has_changes = False
            
            if match.statut != match_data["statut"]:
                old_statut = match.statut
                match.statut = match_data["statut"]
                has_changes = True
                
                # Logger les changements de statut importants
                if old_statut == "en_attente" and match_data["statut"] == "en_cours":
                    self._log_collection("detection_start", f"Match commencé: {match.unique_match_id}", "info", {
                        "match_id": match.unique_match_id
                    })
                elif old_statut == "en_cours" and match_data["statut"] == "termine":
                    self._log_collection("detection_end", f"Match terminé: {match.unique_match_id}", "info", {
                        "match_id": match.unique_match_id
                    })
            
            # Mettre à jour les autres champs
            if match_data.get("heure_fin") and match.heure_fin != match_data["heure_fin"]:
                match.heure_fin = match_data["heure_fin"]
                has_changes = True
            
            if match_data.get("score_domicile") is not None and match.score_domicile != match_data["score_domicile"]:
                match.score_domicile = match_data["score_domicile"]
                has_changes = True
            
            if match_data.get("score_exterieur") is not None and match.score_exterieur != match_data["score_exterieur"]:
                match.score_exterieur = match_data["score_exterieur"]
                has_changes = True
            
            # Recalculer le gagnant si le match est terminé
            if match.statut == "termine" and match.score_domicile is not None:
                new_gagnant = match.determine_gagnant()
                if match.equipe_gagnante != new_gagnant:
                    match.equipe_gagnante = new_gagnant
                    has_changes = True
            
            if has_changes:
                db.session.commit()
                logger.info(f"🔄 Match mis à jour: {match.unique_match_id} - Nouveau statut: {match.statut}")
                return "updated"
            else:
                return "unchanged"
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur mise à jour match: {e}")
            return "error"
    
    def _log_collection(self, action_type: str, message: str, severity: str = "info", extra_data: Dict = None):
        """Enregistre un log de collecte"""
        if not MODELS_AVAILABLE:
            logger.info(f"[COLLECTION LOG] {action_type}: {message}")
            return
        
        try:
            log = MatchCollectionLog(
                action_type=action_type,
                message=message,
                severity=severity,
                source_donnees=self.source.source_type,
                temps_execution=extra_data.get("temps_execution") if extra_data else None,
                extra_data=json.dumps(extra_data) if extra_data else None
            )
            
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erreur logging collecte: {e}")
    
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur la collecte"""
        if not MODELS_AVAILABLE:
            return {"error": "Modèles non disponibles"}
        
        try:
            stats = {}
            
            # Total des matchs collectés
            stats["total_matches"] = CollectedMatch.query.count()
            
            # Matchs par statut
            stats["by_status"] = {}
            for status in ["en_attente", "en_cours", "termine", "annule"]:
                count = CollectedMatch.query.filter_by(statut=status).count()
                stats["by_status"][status] = count
            
            # Matchs par jeu
            stats["by_game"] = {}
            games = db.session.query(CollectedMatch.jeu, db.func.count(CollectedMatch.id)).group_by(CollectedMatch.jeu).all()
            for game, count in games:
                stats["by_game"][game] = count
            
            # Matchs des dernières 24h
            yesterday = datetime.now() - timedelta(days=1)
            stats["last_24h"] = CollectedMatch.query.filter(CollectedMatch.created_at >= yesterday).count()
            
            # Logs récents
            recent_logs = MatchCollectionLog.query.filter(
                MatchCollectionLog.created_at >= yesterday
            ).order_by(MatchCollectionLog.created_at.desc()).limit(10).all()
            
            stats["recent_logs"] = [
                {
                    "action_type": log.action_type,
                    "message": log.message,
                    "severity": log.severity,
                    "created_at": log.created_at.isoformat()
                }
                for log in recent_logs
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques: {e}")
            return {"error": str(e)}


# Fonctions utilitaires pour le démarrage/arrêt
def start_collector_daemon(source_type: str = "simulated", check_interval: int = 30):
    """Démarre le collecteur en mode démon"""
    collector = MatchCollector(source_type, check_interval)
    
    try:
        collector.start_collection()
    except KeyboardInterrupt:
        collector.stop_collection()
    
    return collector


if __name__ == "__main__":
    print("🚀 Démarrage du système de collecte ORACXPRED")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    # Démarrer avec des données simulées par défaut
    collector = start_collector_daemon("simulated", 30)
