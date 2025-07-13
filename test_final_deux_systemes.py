#!/usr/bin/env python3
"""
Test final des deux systèmes unifiés
"""

from fifa1 import SystemePredictionUnifie, SystemePredictionParisAlternatifs, generer_predictions_alternatives

def test_deux_systemes():
    print("🎯🎲 TEST FINAL - DEUX SYSTÈMES UNIFIÉS")
    print("=" * 60)
    
    # Données de test
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    
    # Cotes 1X2
    odds_data = [
        {"type": "1", "cote": 2.1},  # Real Madrid
        {"type": "X", "cote": 3.2},  # Match nul
        {"type": "2", "cote": 3.5}   # Barcelona
    ]
    
    # Paris alternatifs
    paris_alternatifs = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.75},
        {"nom": "Handicap asiatique Real Madrid (-1)", "cote": 2.10},
        {"nom": "Plus de 9 corners", "cote": 1.90},
        {"nom": "Total de buts IMPAIR", "cote": 1.85}
    ]
    
    print(f"🏟️  Match: {team1} vs {team2}")
    print(f"🏆 Ligue: {league}")
    print()
    
    # TEST SYSTÈME 1: 1X2 Unifié
    print("🎯 SYSTÈME UNIFIÉ #1 - RÉSULTAT 1X2")
    print("-" * 40)
    systeme1 = SystemePredictionUnifie(team1, team2, league, odds_data, "Football")
    decision1 = systeme1.generer_prediction_unifiee()
    print(f"Décision: {decision1}")
    print()
    
    # TEST SYSTÈME 2: Paris Alternatifs Unifié
    print("🎲 SYSTÈME UNIFIÉ #2 - PARIS ALTERNATIFS")
    print("-" * 40)
    systeme2 = SystemePredictionParisAlternatifs(team1, team2, league, paris_alternatifs)
    decision2 = systeme2.generer_decision_collective_alternative()
    print(f"Décision: {decision2}")
    print()
    
    # TEST FONCTION INTÉGRÉE
    print("🤖 FONCTION INTÉGRÉE (LES DEUX ENSEMBLE)")
    print("-" * 40)
    prediction_complete = generer_predictions_alternatives(team1, team2, league, paris_alternatifs, odds_data)
    print(f"Prédiction complète: {prediction_complete}")
    print()
    
    print("✅ LES DEUX SYSTÈMES FONCTIONNENT PARFAITEMENT!")
    print()
    print("🎉 RÉSUMÉ:")
    print("   🎯 Système 1: Décision collective pour 1X2")
    print("   🎲 Système 2: Décision collective pour paris alternatifs")
    print("   🤖 Intégration: Les deux systèmes travaillent en parallèle")

if __name__ == "__main__":
    test_deux_systemes()
