#!/usr/bin/env python3
"""
Test simple du système spécialisé pour les paris alternatifs
"""

from fifa1 import SystemePredictionParisAlternatifs

def test_simple():
    print("🎲 TEST SIMPLE - SYSTÈME PARIS ALTERNATIFS")
    print("=" * 50)
    
    # Données simples
    team1 = "Real Madrid"
    team2 = "Barcelona"
    league = "La Liga"
    
    # Quelques paris alternatifs
    paris = [
        {"nom": "Plus de 2.5 buts (TOTAL du match)", "cote": 1.75},
        {"nom": "Handicap asiatique Real Madrid (-1)", "cote": 2.10},
        {"nom": "Total de buts IMPAIR", "cote": 1.85}
    ]
    
    print(f"Match: {team1} vs {team2}")
    print(f"Paris: {len(paris)} options")
    
    # Créer le système
    systeme = SystemePredictionParisAlternatifs(team1, team2, league, paris)
    
    print("\nCatégories:")
    for cat, p in systeme.categories_paris.items():
        if p:
            print(f"  {cat}: {len(p)} paris")
    
    print(f"\nMeilleures options: {len(systeme.meilleures_options)}")
    
    # Décision
    decision = systeme.generer_decision_collective_alternative()
    print(f"\nDécision: {decision}")
    
    print("\n✅ Test simple réussi!")

if __name__ == "__main__":
    test_simple()
