#!/usr/bin/env python3
"""
Test rapide pour vérifier la correction du module re
"""

from fifa1 import SystemePredictionParisAlternatifs, generer_predictions_alternatives

def test_correction():
    print("🔧 TEST DE CORRECTION - MODULE RE")
    print("=" * 40)
    
    # Données de test
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    
    # Paris alternatifs avec des seuils numériques
    paris_alternatifs = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.75},
        {"nom": "Moins de 3.5 buts (TOTAL du match)", "cote": 1.65},
        {"nom": "Plus de 9 corners", "cote": 1.90},
        {"nom": "Moins de 11 corners", "cote": 1.80}
    ]
    
    print(f"Match: {team1} vs {team2}")
    print(f"Paris avec seuils numériques: {len(paris_alternatifs)}")
    print()
    
    try:
        # Test du système spécialisé
        print("🎲 Test Système Spécialisé...")
        systeme = SystemePredictionParisAlternatifs(team1, team2, league, paris_alternatifs)
        decision = systeme.generer_decision_collective_alternative()
        print(f"✅ Décision: {decision}")
        print()
        
        # Test de la fonction intégrée
        print("🤖 Test Fonction Intégrée...")
        prediction = generer_predictions_alternatives(team1, team2, league, paris_alternatifs, [])
        print(f"✅ Prédiction: {prediction}")
        print()
        
        print("🎉 CORRECTION RÉUSSIE!")
        print("Le module 're' fonctionne maintenant correctement.")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_correction()
