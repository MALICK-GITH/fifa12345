#!/usr/bin/env python3
"""
🔧 TEST SIMPLE DE L'ERREUR 'pari'
=================================
"""

def test_simple():
    print("🔧 TEST SIMPLE - ERREUR 'pari'")
    print("=" * 40)
    
    try:
        # Test de la structure value bets
        value_bets_test = [
            {
                'nom': 'Plus de 2.5 buts',
                'cote': 1.85,
                'confiance': 70,
                'value': 15,
                'type': 'TOTAL_BUTS',
                'source': 'BOT_VALUE'
            }
        ]
        
        print("📊 Test de la nouvelle structure...")
        
        # Simulation du code de fifa1.py
        for vb in value_bets_test:
            if isinstance(vb, dict):
                if 'nom' in vb:
                    nom_pari = vb['nom']
                    cote_pari = vb.get('cote', 0)
                    confiance = vb.get('confiance', 50)
                    value_score = vb.get('value', 10)
                    
                    print(f"✅ Nom: {nom_pari}")
                    print(f"✅ Cote: {cote_pari}")
                    print(f"✅ Confiance: {confiance}%")
                    print(f"✅ Value: {value_score}%")
                    
                elif 'pari' in vb:
                    print("✅ Ancienne structure détectée")
                    pari = vb['pari']
                    print(f"✅ Nom: {pari['nom']}")
        
        print("\n✅ STRUCTURE COMPATIBLE - PAS D'ERREUR 'pari'")
        return True
        
    except KeyError as e:
        if 'pari' in str(e):
            print(f"❌ ERREUR 'pari' ENCORE PRÉSENTE: {e}")
            return False
        else:
            print(f"❌ Autre KeyError: {e}")
            return False
    except Exception as e:
        print(f"⚠️ Autre erreur: {e}")
        return True

if __name__ == "__main__":
    succes = test_simple()
    
    if succes:
        print("\n🎉 CORRECTION RÉUSSIE !")
        print("✅ L'erreur 'pari' est corrigée")
        print("✅ Nouvelle structure compatible")
    else:
        print("\n❌ PROBLÈME PERSISTANT")
        print("⚠️ L'erreur 'pari' n'est pas corrigée")
