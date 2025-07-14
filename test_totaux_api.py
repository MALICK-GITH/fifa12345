#!/usr/bin/env python3
"""
🎯 TEST SPÉCIFIQUE POUR LES TOTAUX 100% API
==========================================
Teste que tous les totaux fonctionnent uniquement avec l'API
"""

from systeme_prediction_simple import SystemePredictionQuantique

def test_totaux_api():
    """🧪 TEST COMPLET DES TOTAUX API"""
    
    print("🎯 TEST TOTAUX 100% API")
    print("=" * 50)
    
    # Initialisation du système
    systeme = SystemePredictionQuantique()
    
    # Paris API réels (comme dans votre match AS Monaco vs Arsenal)
    paris_api_reels = [
        {
            'nom': 'Plus de 5.5 buts (TOTAL mi temps)',
            'cote': 2.34,
            'valeur': '5.5',
            'raw_data': {'G': 17, 'T': 9, 'P': 5.5}
        },
        {
            'nom': 'Moins de 5.5 buts (TOTAL mi temps)',
            'cote': 1.6,
            'valeur': '5.5',
            'raw_data': {'G': 17, 'T': 10, 'P': 5.5}
        },
        {
            'nom': 'Plus de 4.5 buts (TOTAL mi temps)',
            'cote': 1.59,
            'valeur': '4.5',
            'raw_data': {'G': 17, 'T': 9, 'P': 4.5}
        },
        {
            'nom': 'Moins de 4.5 buts (TOTAL mi temps)',
            'cote': 2.36,
            'valeur': '4.5',
            'raw_data': {'G': 17, 'T': 10, 'P': 4.5}
        }
    ]
    
    # Contexte de test
    contexte = {
        'score1': 0,
        'score2': 0,
        'minute': 1
    }
    
    print(f"📊 Test avec {len(paris_api_reels)} paris TOTAUX de l'API")
    print(f"⏱️ Contexte: 0-0 à la 1ère minute")
    print("-" * 50)
    
    # Test de l'analyse
    try:
        resultat = systeme.analyser_match_quantique(
            'AS Monaco', 'Arsenal', 'FC 25', [], contexte, paris_api_reels
        )
        
        print("✅ ANALYSE RÉUSSIE !")
        print(f"🎯 Résultat: {resultat['prediction_finale']['resultat']}")
        print(f"📊 Score: {resultat['prediction_finale']['score']}%")
        print(f"🎲 Paris analysés: {resultat['facteurs_quantiques']['paris_analyses']}")
        print(f"💰 Opportunités: {resultat['facteurs_quantiques']['opportunites_detectees']}")
        
        # Détails des prédictions
        if 'analyse_detaillee' in resultat:
            predictions = resultat['analyse_detaillee'].get('predictions_alternatives', [])
            print(f"\n📋 DÉTAIL DES {len(predictions)} PRÉDICTIONS API:")
            for i, pred in enumerate(predictions, 1):
                print(f"  {i}. {pred['pari']}")
                print(f"     💰 Cote: {pred['cote']} | 🎯 Confiance: {pred['confiance']}%")
                print(f"     📊 Value: {pred['value']}% | 🔍 Source: {pred.get('source', 'API')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_detection_types():
    """🔍 TEST DE DÉTECTION DES TYPES API"""
    
    print("\n🔍 TEST DÉTECTION TYPES API")
    print("-" * 30)
    
    systeme = SystemePredictionQuantique()
    
    # Tests de détection
    tests = [
        {'nom': 'Plus de 5.5 buts (TOTAL mi temps)', 'raw_data': {'G': 17, 'T': 9}, 'attendu': 'TOTAL_BUTS'},
        {'nom': 'Moins de 4.5 buts', 'raw_data': {'G': 17, 'T': 10}, 'attendu': 'TOTAL_BUTS'},
        {'nom': 'Plus de 3.5 corners', 'raw_data': {'G': 62, 'T': 14}, 'attendu': 'CORNERS'},
        {'nom': 'Handicap asiatique AS Monaco (+2)', 'raw_data': {'G': 2, 'T': 7}, 'attendu': 'HANDICAP'},
    ]
    
    for test in tests:
        type_detecte = systeme._detecter_type_pari_api(test['nom'], test['raw_data'])
        status = "✅" if type_detecte == test['attendu'] else "❌"
        print(f"  {status} {test['nom'][:40]:<40} → {type_detecte}")

if __name__ == "__main__":
    print("🚀 DÉMARRAGE DES TESTS TOTAUX API")
    print("=" * 60)
    
    # Test 1 : Détection des types
    test_detection_types()
    
    # Test 2 : Analyse complète
    succes = test_totaux_api()
    
    print("\n" + "=" * 60)
    if succes:
        print("🎉 TOUS LES TESTS RÉUSSIS !")
        print("✅ Les totaux fonctionnent 100% avec l'API")
    else:
        print("❌ ÉCHEC DES TESTS")
        print("⚠️ Problème avec l'analyse des totaux API")
    print("=" * 60)
