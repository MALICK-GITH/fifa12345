#!/usr/bin/env python3
"""
TEST SIMPLE DU COLLECTEUR - ORACXPRED
==================================
Version simplifiée pour tester la collecte sans dépendances Flask
"""

import sys
import os
import sqlite3
import uuid
import random
from datetime import datetime, timedelta

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def generate_test_matches():
    """Génère des matchs de test"""
    
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

def insert_match_simple(match_data):
    """Insère un match dans la base de données"""
    
    try:
        conn = sqlite3.connect("oracxpred.db")
        cursor = conn.cursor()
        
        # Déterminer le gagnant si le match est terminé
        equipe_gagnante = None
        if match_data["statut"] == "termine" and match_data["score_domicile"] is not None:
            if match_data["score_domicile"] > match_data["score_exterieur"]:
                equipe_gagnante = match_data["equipe_domicile"]
            elif match_data["score_exterieur"] > match_data["score_domicile"]:
                equipe_gagnante = match_data["equipe_exterieur"]
            else:
                equipe_gagnante = "Match nul"
        
        cursor.execute("""
            INSERT INTO collected_matches (
                unique_match_id, jeu, equipe_domicile, equipe_exterieur,
                heure_debut, heure_fin, score_domicile, score_exterieur,
                equipe_gagnante, statut, source_donnees, collecte_par,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_data["unique_match_id"],
            match_data["jeu"],
            match_data["equipe_domicile"],
            match_data["equipe_exterieur"],
            match_data["heure_debut"].isoformat(),
            match_data["heure_fin"].isoformat() if match_data["heure_fin"] else None,
            match_data["score_domicile"],
            match_data["score_exterieur"],
            equipe_gagnante,
            match_data["statut"],
            match_data["source_donnees"],
            "systeme_auto",
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erreur insertion match {match_data['unique_match_id']}: {e}")
        return False

def insert_log_simple(action_type, message, severity="info"):
    """Insère un log de collecte"""
    
    try:
        conn = sqlite3.connect("oracxpred.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO match_collection_logs (
                action_type, message, severity, source_donnees, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            action_type,
            message,
            severity,
            "simulated",
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erreur insertion log: {e}")
        return False

def test_collecte():
    """Test du système de collecte"""
    
    print("Test du systeme de collecte ORACXPRED")
    print("=" * 50)
    
    # Générer des matchs de test
    matches = generate_test_matches()
    print(f"Generation de {len(matches)} matchs de test")
    
    # Insérer les logs de début
    insert_log_simple("detection_start", "Systeme de collecte demarre", "info")
    
    # Insérer chaque match
    success_count = 0
    for match in matches:
        if insert_match_simple(match):
            success_count += 1
            print(f"OK Match insere: {match['unique_match_id']} - {match['equipe_domicile']} vs {match['equipe_exterieur']}")
        else:
            print(f"ERREUR insertion: {match['unique_match_id']}")
    
    # Insérer le log de fin
    insert_log_simple("collecte_success", f"Collecte terminee: {success_count} matchs inseres", "info")
    
    print("=" * 50)
    print(f"Collecte terminee: {success_count}/{len(matches)} matchs inseres avec succes")
    
    # Vérifier le total
    conn = sqlite3.connect("oracxpred.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM collected_matches")
    total = cursor.fetchone()[0]
    conn.close()
    
    print(f"Total matchs en base: {total}")
    
    return success_count > 0

if __name__ == "__main__":
    if test_collecte():
        print("\nSysteme de collecte fonctionnel!")
        print("Vous pouvez maintenant acceder a la page /matchs-collectes")
    else:
        print("\nErreur dans le systeme de collecte")
        sys.exit(1)
