#!/usr/bin/env python3
"""
🚀 SCRIPT DE DÉMARRAGE ROBUSTE POUR RENDER
==========================================
Démarre l'application avec gestion d'erreurs optimisée pour le déploiement
"""

import os
import sys

def demarrer_application():
    """Démarre l'application avec gestion d'erreurs"""
    
    print("🚀 DÉMARRAGE DU SYSTÈME RÉVOLUTIONNAIRE")
    print("=" * 50)
    
    # Vérification des dépendances essentielles
    try:
        import flask
        print("✅ Flask disponible")
    except ImportError:
        print("❌ Flask manquant - Installation requise")
        sys.exit(1)
    
    try:
        import requests
        print("✅ Requests disponible")
    except ImportError:
        print("❌ Requests manquant - Installation requise")
        sys.exit(1)
    
    # Dépendances optionnelles
    try:
        import numpy
        print("✅ NumPy disponible - Calculs avancés activés")
    except ImportError:
        print("⚠️ NumPy non disponible - Calculs simplifiés")
    
    print("-" * 50)
    print("🎯 Lancement de l'application...")
    
    # Import et lancement de l'application
    try:
        from fifa1 import app
        port = int(os.environ.get("PORT", 5000))
        
        print(f"🌐 Application disponible sur port {port}")
        print("🎉 Système révolutionnaire opérationnel !")
        
        app.run(host="0.0.0.0", port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Erreur lors du démarrage : {e}")
        sys.exit(1)

if __name__ == "__main__":
    demarrer_application()
