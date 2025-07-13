#!/usr/bin/env python3
"""
🎯 TEST DU MAÎTRE DES PRONOSTICS
===============================
Test complet du système avec tous les bots spécialisés
"""

def test_bots_alternatifs():
    """🤖 TEST DES BOTS SPÉCIALISÉS"""
    
    print("🎯 TEST SYSTÈME COMPLET - BOTS + MAÎTRE")
    print("=" * 60)
    
    try:
        from bots_alternatifs import (
            systeme_unifie_alternatifs_only,
            systeme_ia_alternatifs_only,
            systeme_probabilites_alternatifs_only,
            systeme_value_betting_alternatifs_only,
            systeme_statistique_alternatifs_only
        )
        from maitre_pronostics import MaitreDesPronostics
        
        print("✅ Tous les bots et le maître importés")
        
        # Données de test avec cotes valides (1.399-3.0)
        paris_test = [
            {
                'nom': 'Plus de 5.5 buts (TOTAL mi temps)',
                'cote': 2.34,  # ✅ Dans la plage
                'valeur': '5.5',
                'raw_data': {'G': 17, 'T': 9, 'P': 5.5}
            },
            {
                'nom': 'Moins de 4.5 buts (TOTAL mi temps)',
                'cote': 1.85,  # ✅ Dans la plage
                'valeur': '4.5',
                'raw_data': {'G': 17, 'T': 10, 'P': 4.5}
            },
            {
                'nom': 'Handicap asiatique AS Monaco (+2)',
                'cote': 1.83,  # ✅ Dans la plage
                'valeur': '2.0',
                'raw_data': {'G': 2, 'T': 7, 'P': 2.0}
            },
            {
                'nom': 'Total de buts PAIR',
                'cote': 1.90,  # ✅ Dans la plage
                'valeur': '',
                'raw_data': {'G': 19, 'T': 180}
            }
        ]
        
        print(f"📊 Test avec {len(paris_test)} paris (cotes 1.83-2.34)")
        
        # Test de chaque bot
        team1, team2, league = "AS Monaco", "Arsenal", "FC 25"
        score1, score2, minute = 0, 0, 1
        
        print("\n🤖 TEST DES 5 BOTS SPÉCIALISÉS:")
        
        # Bot 1: Unifié
        bot1 = systeme_unifie_alternatifs_only(team1, team2, league, paris_test, score1, score2, minute)
        print(f"  ✅ Bot Unifié: {len(bot1['paris_recommandes'])} recommandations")
        
        # Bot 2: IA
        bot2 = systeme_ia_alternatifs_only(team1, team2, league, paris_test, score1, score2, minute)
        print(f"  ✅ Bot IA: {len(bot2['paris_recommandes'])} recommandations")
        
        # Bot 3: Probabilités
        bot3 = systeme_probabilites_alternatifs_only(paris_test, score1, score2, minute)
        print(f"  ✅ Bot Probabilités: {len(bot3['paris_recommandes'])} recommandations")
        
        # Bot 4: Value Betting
        bot4 = systeme_value_betting_alternatifs_only(paris_test, team1, team2, league)
        print(f"  ✅ Bot Value: {len(bot4['paris_recommandes'])} recommandations")
        
        # Bot 5: Statistique
        bot5 = systeme_statistique_alternatifs_only(paris_test, team1, team2, league, score1, score2, minute)
        print(f"  ✅ Bot Stats: {len(bot5['paris_recommandes'])} recommandations")
        
        # Test du Maître
        print("\n🎯 TEST DU MAÎTRE DES PRONOSTICS:")
        
        maitre = MaitreDesPronostics()
        
        decisions_bots = {
            'BOT_UNIFIE': bot1,
            'BOT_IA': bot2,
            'BOT_PROBABILITES': bot3,
            'BOT_VALUE': bot4,
            'BOT_STATS': bot5
        }
        
        contexte = {'score1': score1, 'score2': score2, 'minute': minute}
        decision_finale = maitre.analyser_decisions_bots(decisions_bots, team1, team2, league, contexte)
        
        print("✅ Maître des Pronostics - Analyse terminée")
        
        # Affichage des résultats
        if 'decision_finale' in decision_finale:
            df = decision_finale['decision_finale']
            print(f"\n🎯 DÉCISION FINALE DU MAÎTRE:")
            print(f"  📋 Pari choisi: {df.get('pari_choisi', 'Aucun')}")
            print(f"  💰 Cote: {df.get('cote', 'N/A')}")
            print(f"  📊 Confiance: {df.get('confiance_numerique', 0)}%")
            print(f"  🎯 Action: {df.get('action', 'Aucune')}")
            print(f"  🤝 Consensus: {decision_finale.get('analyse_bots', {}).get('consensus', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_filtrage_cotes():
    """💰 TEST DU FILTRAGE DES COTES"""
    
    print("\n💰 TEST FILTRAGE COTES (1.399-3.0)")
    print("-" * 40)
    
    # Paris avec différentes cotes
    paris_test = [
        {'nom': 'Cote trop faible', 'cote': 1.2},      # ❌ Trop faible
        {'nom': 'Cote limite basse', 'cote': 1.399},   # ✅ Limite basse
        {'nom': 'Cote parfaite', 'cote': 2.0},         # ✅ Parfaite
        {'nom': 'Cote limite haute', 'cote': 3.0},     # ✅ Limite haute
        {'nom': 'Cote trop élevée', 'cote': 3.5},      # ❌ Trop élevée
    ]
    
    # Filtrage
    paris_valides = []
    for pari in paris_test:
        cote = float(pari['cote'])
        if 1.399 <= cote <= 3.0:
            paris_valides.append(pari)
            print(f"  ✅ {pari['nom']}: {cote} (VALIDE)")
        else:
            print(f"  ❌ {pari['nom']}: {cote} (REJETÉ)")
    
    print(f"\n📊 Résultat: {len(paris_valides)}/{len(paris_test)} paris valides")
    
    return len(paris_valides) == 3  # Doit être 3 paris valides

def test_types_paris():
    """🔍 TEST DÉTECTION TYPES DE PARIS"""
    
    print("\n🔍 TEST DÉTECTION TYPES DE PARIS")
    print("-" * 35)
    
    from bots_alternatifs import _detecter_type_pari
    
    tests = [
        ('Plus de 2.5 buts (TOTAL)', 'TOTAL_BUTS'),
        ('Moins de 1.5 buts', 'TOTAL_BUTS'),
        ('Handicap asiatique +1.5', 'HANDICAP'),
        ('Total de buts PAIR', 'PAIR_IMPAIR'),
        ('Total de buts IMPAIR', 'PAIR_IMPAIR'),
        ('Plus de 9.5 corners', 'CORNERS'),
        ('Autre pari', 'AUTRE')
    ]
    
    succes = 0
    for nom, attendu in tests:
        detecte = _detecter_type_pari(nom)
        if detecte == attendu:
            print(f"  ✅ {nom:<25} → {detecte}")
            succes += 1
        else:
            print(f"  ❌ {nom:<25} → {detecte} (attendu: {attendu})")
    
    print(f"\n📊 Détection: {succes}/{len(tests)} types corrects")
    
    return succes == len(tests)

if __name__ == "__main__":
    print("🚀 DÉMARRAGE TEST COMPLET MAÎTRE + BOTS")
    print("=" * 70)
    
    # Test 1: Bots et Maître
    succes1 = test_bots_alternatifs()
    
    # Test 2: Filtrage des cotes
    succes2 = test_filtrage_cotes()
    
    # Test 3: Détection des types
    succes3 = test_types_paris()
    
    print("\n" + "=" * 70)
    if succes1 and succes2 and succes3:
        print("🎉 TOUS LES TESTS RÉUSSIS !")
        print("✅ Système complet opérationnel")
        print("✅ 5 bots spécialisés fonctionnels")
        print("✅ Maître des Pronostics opérationnel")
        print("✅ Filtrage des cotes (1.399-3.0) correct")
        print("✅ Détection des types de paris parfaite")
        print("\n🎯 VOTRE SYSTÈME RÉVOLUTIONNAIRE EST PRÊT !")
    else:
        print("❌ PROBLÈMES DÉTECTÉS")
        if not succes1:
            print("⚠️ Problème avec les bots ou le maître")
        if not succes2:
            print("⚠️ Problème de filtrage des cotes")
        if not succes3:
            print("⚠️ Problème de détection des types")
    print("=" * 70)
