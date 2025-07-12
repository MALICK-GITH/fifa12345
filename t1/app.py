#!/usr/bin/env python3
"""
Point d'entrée pour le déploiement sur Render
"""

import os
import sys

# Ajouter le dossier t1 au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 't1'))

# Importer l'application depuis t1/fifa1.py
from fifa1 import app, init_db

# Initialiser la base de données au démarrage
try:
    with app.app_context():
        init_db()
    print("✅ Base de données initialisée")
except Exception as e:
    print(f"⚠️ Erreur init DB: {e}")

if __name__ == "__main__":
    # Configuration pour Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
