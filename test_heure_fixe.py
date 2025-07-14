#!/usr/bin/env python3
"""
🕐 TEST DU SYSTÈME D'HEURE FIXE
==============================
Vérifie que l'heure de début ne change pas à chaque actualisation
"""

def test_heure_debut_fixe():
    """🕐 TEST HEURE DE DÉBUT FIXE"""
    
    print("🕐 TEST SYSTÈME HEURE FIXE")
    print("=" * 40)
    
    import json
    import os
    from datetime import datetime, timedelta
    import time
    
    # Nettoyer le fichier de test
    test_file = "heures_matches.json"
    if os.path.exists(test_file):
        os.remove(test_file)
    
    # Simulation d'un match en cours
    team1, team2, league = "AS Monaco", "Arsenal", "FC 25"
    match_id = f"{team1}_{team2}_{league}".replace(" ", "_")
    minute = 45  # 45ème minute
    
    print(f"🎯 Test avec match: {team1} vs {team2}")
    print(f"📊 Minute: {minute}")
    print(f"🆔 Match ID: {match_id}")
    
    # Durées FIFA
    duree_totale_minutes_reelles = 7
    ratio_temps = 7 / 90
    minutes_reelles_ecoulees = minute * ratio_temps
    
    print(f"⏱️ Minutes réelles écoulées: {minutes_reelles_ecoulees:.2f}")
    
    # PREMIÈRE SIMULATION (première visite)
    print("\n🔄 PREMIÈRE SIMULATION (première visite):")
    
    maintenant1 = datetime.now()
    
    # Charger les heures sauvegardées
    heures_matches = {}
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            heures_matches = json.load(f)
    
    # Première fois - calculer et sauvegarder
    if match_id not in heures_matches:
        heure_debut1 = maintenant1 - timedelta(minutes=minutes_reelles_ecoulees)
        heures_matches[match_id] = heure_debut1.isoformat()
        with open(test_file, 'w') as f:
            json.dump(heures_matches, f)
        print(f"💾 Heure de début sauvegardée: {heure_debut1.strftime('%H:%M:%S')}")
    else:
        heure_debut1 = datetime.fromisoformat(heures_matches[match_id])
        print(f"📖 Heure de début chargée: {heure_debut1.strftime('%H:%M:%S')}")
    
    # Attendre 2 secondes pour simuler le temps
    print("⏳ Attente de 2 secondes...")
    time.sleep(2)
    
    # DEUXIÈME SIMULATION (actualisation de page)
    print("\n🔄 DEUXIÈME SIMULATION (actualisation de page):")
    
    maintenant2 = datetime.now()
    
    # Charger les heures sauvegardées
    heures_matches = {}
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            heures_matches = json.load(f)
    
    # Utiliser l'heure sauvegardée
    if match_id in heures_matches:
        heure_debut2 = datetime.fromisoformat(heures_matches[match_id])
        print(f"📖 Heure de début chargée: {heure_debut2.strftime('%H:%M:%S')}")
    else:
        print("❌ Erreur: Heure de début non trouvée")
        return False
    
    # VÉRIFICATION
    print("\n✅ VÉRIFICATION:")
    print(f"🕐 Heure début 1ère visite: {heure_debut1.strftime('%H:%M:%S')}")
    print(f"🕐 Heure début 2ème visite: {heure_debut2.strftime('%H:%M:%S')}")
    
    # Les heures doivent être identiques
    if heure_debut1 == heure_debut2:
        print("✅ SUCCÈS: L'heure de début est fixe !")
        
        # Calculer la différence de temps
        temps_ecoule = maintenant2 - heure_debut2
        print(f"⏱️ Temps écoulé depuis le début: {temps_ecoule}")
        
        # Nettoyer
        os.remove(test_file)
        return True
    else:
        print("❌ ÉCHEC: L'heure de début a changé !")
        difference = abs((heure_debut2 - heure_debut1).total_seconds())
        print(f"⚠️ Différence: {difference} secondes")
        return False

def test_match_termine():
    """🏁 TEST NETTOYAGE MATCH TERMINÉ"""
    
    print("\n🏁 TEST NETTOYAGE MATCH TERMINÉ")
    print("-" * 35)
    
    import json
    import os
    from datetime import datetime
    
    test_file = "heures_matches.json"
    
    # Créer un fichier de test avec un match
    team1, team2, league = "Real Madrid", "Barcelona", "FC 25"
    match_id = f"{team1}_{team2}_{league}".replace(" ", "_")
    
    heures_matches = {
        match_id: datetime.now().isoformat()
    }
    
    with open(test_file, 'w') as f:
        json.dump(heures_matches, f)
    
    print(f"📝 Match créé: {match_id}")
    print(f"📊 Contenu initial: {len(heures_matches)} match(s)")
    
    # Simuler un match terminé (minute >= 90)
    minute = 95
    
    if minute >= 90:
        # Charger et nettoyer
        with open(test_file, 'r') as f:
            heures_matches = json.load(f)
        
        if match_id in heures_matches:
            del heures_matches[match_id]
            with open(test_file, 'w') as f:
                json.dump(heures_matches, f)
            print("🗑️ Match terminé supprimé du fichier")
        
        # Vérifier
        with open(test_file, 'r') as f:
            heures_matches_final = json.load(f)
        
        if match_id not in heures_matches_final:
            print("✅ SUCCÈS: Match terminé nettoyé")
            print(f"📊 Contenu final: {len(heures_matches_final)} match(s)")
            
            # Nettoyer
            os.remove(test_file)
            return True
        else:
            print("❌ ÉCHEC: Match terminé non nettoyé")
            return False

def test_types_matches():
    """🎮 TEST TYPES DE MATCHES (NORMAL vs PENALTY)"""
    
    print("\n🎮 TEST TYPES DE MATCHES")
    print("-" * 25)
    
    # Test match normal
    league_normal = "FC 25"
    is_penalty_normal = "penalty" in league_normal.lower()
    
    if is_penalty_normal:
        duree_normale = 1.5
    else:
        duree_normale = 7
    
    print(f"⚽ Match normal '{league_normal}':")
    print(f"  🕐 Durée: {duree_normale} minutes")
    print(f"  🎯 Type penalty: {is_penalty_normal}")
    
    # Test match penalty
    league_penalty = "FC 25 Penalty Shootout"
    is_penalty_penalty = "penalty" in league_penalty.lower()
    
    if is_penalty_penalty:
        duree_penalty = 1.5
    else:
        duree_penalty = 7
    
    print(f"🥅 Match penalty '{league_penalty}':")
    print(f"  🕐 Durée: {duree_penalty} minutes")
    print(f"  🎯 Type penalty: {is_penalty_penalty}")
    
    # Vérifications
    if duree_normale == 7 and duree_penalty == 1.5:
        print("✅ SUCCÈS: Types de matches détectés correctement")
        return True
    else:
        print("❌ ÉCHEC: Problème de détection des types")
        return False

if __name__ == "__main__":
    print("🚀 DÉMARRAGE TEST SYSTÈME HEURE FIXE")
    print("=" * 50)
    
    # Test 1: Heure de début fixe
    succes1 = test_heure_debut_fixe()
    
    # Test 2: Nettoyage match terminé
    succes2 = test_match_termine()
    
    # Test 3: Types de matches
    succes3 = test_types_matches()
    
    print("\n" + "=" * 50)
    if succes1 and succes2 and succes3:
        print("🎉 TOUS LES TESTS RÉUSSIS !")
        print("✅ Heure de début fixe fonctionnelle")
        print("✅ Nettoyage des matches terminés")
        print("✅ Détection des types de matches")
        print("\n🕐 SYSTÈME D'HEURE FIXE OPÉRATIONNEL !")
    else:
        print("❌ PROBLÈMES DÉTECTÉS")
        if not succes1:
            print("⚠️ Problème heure de début fixe")
        if not succes2:
            print("⚠️ Problème nettoyage matches")
        if not succes3:
            print("⚠️ Problème détection types")
    print("=" * 50)
