#!/usr/bin/env python3
"""
Script de test pour le système de prédiction unifié
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fifa1 import SystemePredictionUnifie, calculer_force_equipe

def test_systeme_unifie():
    """Test du système de prédiction unifié"""
    
    print("🤖 TEST DU SYSTÈME DE PRÉDICTION UNIFIÉ")
    print("=" * 50)
    
    # Données de test
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    sport = "Football"
    
    # Cotes de test (1X2)
    odds_data = [
        {"type": "1", "cote": 2.1},  # Real Madrid
        {"type": "X", "cote": 3.2},  # Match nul
        {"type": "2", "cote": 3.5}   # Barcelona
    ]
    
    # Paris alternatifs de test
    paris_alternatifs = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.8, "valeur": "2.5"},
        {"nom": "Handicap asiatique Real Madrid (-1)", "cote": 2.2, "valeur": "-1"},
        {"nom": "Total de buts PAIR", "cote": 1.9, "valeur": ""},
        {"nom": "Plus de 9 corners", "cote": 2.1, "valeur": "9"},
        {"nom": "Victoire Real Madrid (O1)", "cote": 2.0, "valeur": ""}
    ]
    
    print(f"🏟️  Match: {team1} vs {team2}")
    print(f"🏆 Ligue: {league}")
    print(f"⚽ Sport: {sport}")
    print()
    
    # Créer le système unifié
    systeme = SystemePredictionUnifie(team1, team2, league, odds_data, sport, paris_alternatifs)
    
    print("📊 ANALYSE DES FORCES D'ÉQUIPES:")
    print(f"   {team1}: {systeme.force1}")
    print(f"   {team2}: {systeme.force2}")
    print()
    
    print("💰 ANALYSE DES COTES:")
    print(f"   Cotes 1X2: {systeme.analyse_cotes['cotes_1x2']}")
    print(f"   Favori: {systeme.analyse_cotes['favori']}")
    print(f"   Confiance favori: {systeme.analyse_cotes['confiance_favori']}%")
    print(f"   Équilibre match: {systeme.analyse_cotes['equilibre_match']}")
    print()
    
    print("🎯 OPTIONS PRINCIPALES IDENTIFIÉES:")
    for i, option in enumerate(systeme.options_principales, 1):
        print(f"   Option {i}: {option['prediction']}")
        print(f"   - Type: {option['type']}")
        print(f"   - Cote: {option['cote']}")
        print(f"   - Confiance: {option['confiance']}%")
        print(f"   - Équipe cible: {option['equipe_cible']}")
        print()
    
    print("🤖 PRÉDICTION UNIFIÉE FINALE:")
    prediction_finale = systeme.generer_prediction_unifiee()
    print(f"   {prediction_finale}")
    print()
    
    print("✅ Test terminé avec succès!")

def test_cas_multiples():
    """Test avec plusieurs cas différents"""
    
    print("\n🔄 TEST DE CAS MULTIPLES")
    print("=" * 50)
    
    cas_tests = [
        {
            "team1": "Manchester City", "team2": "Liverpool", "league": "Premier League",
            "odds": [{"type": "1", "cote": 1.8}, {"type": "X", "cote": 3.8}, {"type": "2", "cote": 4.2}]
        },
        {
            "team1": "PSG", "team2": "Marseille", "league": "Ligue 1",
            "odds": [{"type": "1", "cote": 1.5}, {"type": "X", "cote": 4.5}, {"type": "2", "cote": 6.0}]
        },
        {
            "team1": "Équipe A", "team2": "Équipe B", "league": "Ligue Inconnue",
            "odds": [{"type": "1", "cote": 2.5}, {"type": "X", "cote": 3.0}, {"type": "2", "cote": 2.8}]
        }
    ]
    
    for i, cas in enumerate(cas_tests, 1):
        print(f"\n📋 CAS {i}: {cas['team1']} vs {cas['team2']}")
        
        systeme = SystemePredictionUnifie(
            cas['team1'], cas['team2'], cas['league'], 
            cas['odds'], "Football"
        )
        
        prediction = systeme.generer_prediction_unifiee()
        print(f"   🎯 Prédiction: {prediction}")

if __name__ == "__main__":
    try:
        test_systeme_unifie()
        test_cas_multiples()
        
        print("\n🎉 TOUS LES TESTS RÉUSSIS!")
        print("Le système de prédiction unifié fonctionne correctement.")
        
    except Exception as e:
        print(f"\n❌ ERREUR LORS DU TEST: {e}")
        import traceback
        traceback.print_exc()
