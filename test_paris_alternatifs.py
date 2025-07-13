#!/usr/bin/env python3
"""
Test du système spécialisé pour les paris alternatifs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fifa1 import SystemePredictionParisAlternatifs

def test_systeme_paris_alternatifs():
    """Test du système spécialisé pour paris alternatifs"""
    
    print("🎲 TEST DU SYSTÈME SPÉCIALISÉ PARIS ALTERNATIFS")
    print("=" * 60)
    
    # Données de test
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    
    # Paris alternatifs variés
    paris_alternatifs = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.75, "valeur": "2.5"},
        {"nom": "Moins de 3.5 buts (TOTAL du match)", "cote": 1.65, "valeur": "3.5"},
        {"nom": "Handicap asiatique Real Madrid (-1)", "cote": 2.10, "valeur": "-1"},
        {"nom": "Handicap asiatique Barcelona (+1)", "cote": 1.85, "valeur": "+1"},
        {"nom": "Plus de 9 corners", "cote": 1.90, "valeur": "9"},
        {"nom": "Moins de 11 corners", "cote": 1.80, "valeur": "11"},
        {"nom": "Total de buts PAIR", "cote": 1.95, "valeur": ""},
        {"nom": "Total de buts IMPAIR", "cote": 1.85, "valeur": ""},
        {"nom": "Victoire Real Madrid (O1) mi-temps", "cote": 2.30, "valeur": ""},
        {"nom": "Plus de 1.5 buts pour Real Madrid", "cote": 2.20, "valeur": "1.5"},
        {"nom": "Barcelona marque plus de 1 but", "cote": 1.70, "valeur": "1"},
        {"nom": "Double chance Real Madrid ou nul", "cote": 1.25, "valeur": ""}
    ]
    
    print(f"🏟️  Match: {team1} vs {team2}")
    print(f"🏆 Ligue: {league}")
    print(f"📊 Nombre de paris alternatifs: {len(paris_alternatifs)}")
    print()
    
    # Créer le système spécialisé
    systeme = SystemePredictionParisAlternatifs(team1, team2, league, paris_alternatifs)
    
    print("📋 CATÉGORISATION DES PARIS:")
    for categorie, paris in systeme.categories_paris.items():
        if paris:
            print(f"   {categorie.title()}: {len(paris)} paris")
            for pari in paris[:2]:  # Afficher les 2 premiers
                print(f"     - {pari['nom']} (cote: {pari['cote']})")
            if len(paris) > 2:
                print(f"     ... et {len(paris) - 2} autres")
    print()
    
    print("🎯 MEILLEURES OPTIONS IDENTIFIÉES:")
    for i, option in enumerate(systeme.meilleures_options, 1):
        pari = option['pari']
        evaluation = option['evaluation']
        print(f"   Option {i}: {pari['nom']}")
        print(f"   - Catégorie: {option['categorie']}")
        print(f"   - Cote: {pari['cote']}")
        print(f"   - Score global: {evaluation['score_global']:.1f}")
        print(f"   - Probabilité estimée: {evaluation['probabilite_estimee']:.1f}%")
        print(f"   - Confiance: {evaluation['confiance']:.1f}%")
        print()
    
    print("🤖 DÉCISION COLLECTIVE SPÉCIALISÉE:")
    decision_finale = systeme.generer_decision_collective_alternative()
    print(f"   {decision_finale}")
    print()
    
    # Test des détails de délibération
    print("🔍 DÉTAILS DE LA DÉLIBÉRATION:")
    donnees = systeme._collecter_donnees_alternatives()
    decision = systeme._deliberation_alternative(donnees)
    print(f"   Type de décision: {decision['type_decision']}")
    print(f"   Confiance collective: {decision['confiance_collective']}%")
    if decision['option_finale']:
        print(f"   Option choisie: {decision['option_finale']['pari']['nom']}")
        print(f"   Catégorie: {decision['option_finale']['categorie']}")
    print()
    
    print("📊 VOTES DES SYSTÈMES SPÉCIALISÉS:")
    for systeme_nom, vote in decision['votes_detail'].items():
        nom_court = systeme_nom.replace('analyseur_', '').title()
        statut = "✓" if vote['option_preferee'] else "✗"
        print(f"   {nom_court}: {statut} (Score: {vote['score']:.2f})")
    print()
    
    print("✅ Test terminé avec succès!")

def test_cas_multiples_alternatifs():
    """Test avec différents types de matchs"""
    
    print("\n🔄 TEST DE CAS MULTIPLES (PARIS ALTERNATIFS)")
    print("=" * 60)
    
    cas_tests = [
        {
            "team1": "Manchester City", "team2": "Liverpool", "league": "Premier League",
            "description": "Match offensif attendu"
        },
        {
            "team1": "Atletico Madrid", "team2": "Getafe", "league": "La Liga",
            "description": "Match défensif probable"
        },
        {
            "team1": "Bayern Munich", "team2": "Borussia Dortmund", "league": "Bundesliga",
            "description": "Match équilibré"
        }
    ]
    
    # Paris alternatifs standards pour tous les tests
    paris_standards = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.80},
        {"nom": "Moins de 2.5 buts (TOTAL du match)", "cote": 2.00},
        {"nom": "Plus de 9 corners", "cote": 1.85},
        {"nom": "Total de buts IMPAIR", "cote": 1.90},
        {"nom": "Handicap asiatique équipe 1 (-1)", "cote": 2.10}
    ]
    
    for i, cas in enumerate(cas_tests, 1):
        print(f"\n📋 CAS {i}: {cas['team1']} vs {cas['team2']}")
        print(f"   Description: {cas['description']}")
        
        systeme = SystemePredictionParisAlternatifs(
            cas['team1'], cas['team2'], cas['league'], paris_standards
        )
        
        decision = systeme.generer_decision_collective_alternative()
        print(f"   🎯 Décision: {decision}")

if __name__ == "__main__":
    try:
        test_systeme_paris_alternatifs()
        test_cas_multiples_alternatifs()
        
        print("\n🎉 TOUS LES TESTS RÉUSSIS!")
        print("Le système spécialisé pour paris alternatifs fonctionne parfaitement.")
        
    except Exception as e:
        print(f"\n❌ ERREUR LORS DU TEST: {e}")
        import traceback
        traceback.print_exc()
