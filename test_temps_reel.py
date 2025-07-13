#!/usr/bin/env python3
"""
Test du système avec données temps réel
"""

from fifa1 import SystemePredictionParisAlternatifs, generer_predictions_alternatives

def test_temps_reel():
    print("⏱️ TEST SYSTÈME AVEC DONNÉES TEMPS RÉEL")
    print("=" * 50)
    
    # Données de test
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    
    # Paris alternatifs avec seuils
    paris_alternatifs = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.75},
        {"nom": "Moins de 3.5 buts (TOTAL du match)", "cote": 1.65},
        {"nom": "Plus de 9 corners", "cote": 1.90}
    ]
    
    # SCÉNARIO 1: Début de match (0-0, 10ème minute)
    print("📊 SCÉNARIO 1: Début de match")
    print("Score: 0-0, 10ème minute")
    systeme1 = SystemePredictionParisAlternatifs(team1, team2, league, paris_alternatifs, "Football", 0, 0, 10)
    decision1 = systeme1.generer_decision_collective_alternative()
    print(f"Décision: {decision1}")
    print()
    
    # SCÉNARIO 2: Match avec beaucoup de buts (3-2, 70ème minute)
    print("📊 SCÉNARIO 2: Match avec beaucoup de buts")
    print("Score: 3-2 (5 buts), 70ème minute")
    systeme2 = SystemePredictionParisAlternatifs(team1, team2, league, paris_alternatifs, "Football", 3, 2, 70)
    decision2 = systeme2.generer_decision_collective_alternative()
    print(f"Décision: {decision2}")
    print()
    
    # SCÉNARIO 3: Match défensif (0-1, 85ème minute)
    print("📊 SCÉNARIO 3: Match défensif en fin de partie")
    print("Score: 0-1 (1 but), 85ème minute")
    systeme3 = SystemePredictionParisAlternatifs(team1, team2, league, paris_alternatifs, "Football", 0, 1, 85)
    decision3 = systeme3.generer_decision_collective_alternative()
    print(f"Décision: {decision3}")
    print()
    
    # Test avec la fonction intégrée
    print("🤖 TEST FONCTION INTÉGRÉE AVEC TEMPS RÉEL")
    print("Score: 2-1 (3 buts), 60ème minute")
    prediction_complete = generer_predictions_alternatives(team1, team2, league, paris_alternatifs, [], 2, 1, 60)
    print(f"Prédiction complète: {prediction_complete}")
    print()
    
    print("✅ LE SYSTÈME PREND MAINTENANT EN COMPTE:")
    print("   ⏱️ Le temps de jeu écoulé")
    print("   ⚽ Le score actuel")
    print("   📊 Les seuils déjà atteints ou non")
    print("   🎯 L'estimation du reste du match")

if __name__ == "__main__":
    test_temps_reel()
