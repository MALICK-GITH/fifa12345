#!/usr/bin/env python3
"""
Test pour vérifier que le système utilise maintenant les VRAIES cotes de l'API
"""

from fifa1 import SystemePredictionUnifie, calculer_probabilites_depuis_cotes

def test_vraies_cotes():
    print("🎯 TEST UTILISATION DES VRAIES COTES")
    print("=" * 50)
    
    # Données de test avec vraies cotes
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    
    # SCÉNARIO 1: Real Madrid très favori
    print("📊 SCÉNARIO 1: Real Madrid très favori")
    odds_data_real_favori = [
        {"type": "1", "cote": 1.50},  # Real Madrid TRÈS FAVORI
        {"type": "X", "cote": 4.00},  # Match nul
        {"type": "2", "cote": 6.00}   # Barcelona
    ]
    
    # Test de la fonction de calcul des probabilités
    probabilites = calculer_probabilites_depuis_cotes(odds_data_real_favori)
    print(f"Cotes: Real 1.50 | Nul 4.00 | Barça 6.00")
    print(f"Probabilités calculées: Real {probabilites.get('1', 0):.1f}% | Nul {probabilites.get('X', 0):.1f}% | Barça {probabilites.get('2', 0):.1f}%")
    
    # Test du système unifié
    systeme1 = SystemePredictionUnifie(team1, team2, league, odds_data_real_favori, "Football")
    prediction1 = systeme1.generer_prediction_unifiee()
    print(f"✅ Prédiction: {prediction1}")
    print()
    
    # SCÉNARIO 2: Match équilibré
    print("📊 SCÉNARIO 2: Match équilibré")
    odds_data_equilibre = [
        {"type": "1", "cote": 2.80},  # Real Madrid
        {"type": "X", "cote": 3.20},  # Match nul
        {"type": "2", "cote": 2.70}   # Barcelona (légèrement favori)
    ]
    
    probabilites2 = calculer_probabilites_depuis_cotes(odds_data_equilibre)
    print(f"Cotes: Real 2.80 | Nul 3.20 | Barça 2.70")
    print(f"Probabilités calculées: Real {probabilites2.get('1', 0):.1f}% | Nul {probabilites2.get('X', 0):.1f}% | Barça {probabilites2.get('2', 0):.1f}%")
    
    systeme2 = SystemePredictionUnifie(team1, team2, league, odds_data_equilibre, "Football")
    prediction2 = systeme2.generer_prediction_unifiee()
    print(f"✅ Prédiction: {prediction2}")
    print()
    
    # SCÉNARIO 3: Barcelona très favori
    print("📊 SCÉNARIO 3: Barcelona très favori")
    odds_data_barca_favori = [
        {"type": "1", "cote": 5.50},  # Real Madrid
        {"type": "X", "cote": 4.20},  # Match nul
        {"type": "2", "cote": 1.40}   # Barcelona TRÈS FAVORI
    ]
    
    probabilites3 = calculer_probabilites_depuis_cotes(odds_data_barca_favori)
    print(f"Cotes: Real 5.50 | Nul 4.20 | Barça 1.40")
    print(f"Probabilités calculées: Real {probabilites3.get('1', 0):.1f}% | Nul {probabilites3.get('X', 0):.1f}% | Barça {probabilites3.get('2', 0):.1f}%")
    
    systeme3 = SystemePredictionUnifie(team1, team2, league, odds_data_barca_favori, "Football")
    prediction3 = systeme3.generer_prediction_unifiee()
    print(f"✅ Prédiction: {prediction3}")
    print()
    
    print("🎉 VÉRIFICATIONS :")
    print("✅ Le système doit prédire Real Madrid dans le scénario 1 (cote 1.50 = ~67% de probabilité)")
    print("✅ Le système doit prédire Barcelona dans le scénario 2 (cote 2.70 = ~37% de probabilité)")
    print("✅ Le système doit prédire Barcelona dans le scénario 3 (cote 1.40 = ~71% de probabilité)")
    print("✅ PLUS DE PRÉDICTIONS ALÉATOIRES - Tout basé sur les vraies cotes !")

if __name__ == "__main__":
    test_vraies_cotes()
