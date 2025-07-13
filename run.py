#!/usr/bin/env python3
"""
🚀 SCRIPT DE DÉMARRAGE SIMPLE POUR RENDER
========================================
"""

import os
import sys

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        print("🚀 Démarrage du système révolutionnaire...")
        from fifa1 import app
        
        port = int(os.environ.get("PORT", 10000))
        host = os.environ.get("HOST", "0.0.0.0")
        
        print(f"🌐 Serveur démarré sur {host}:{port}")
        app.run(host=host, port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
