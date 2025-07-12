#!/usr/bin/env python3
"""
Script pour initialiser la base de données
"""

from fifa1 import app, db, init_db

if __name__ == "__main__":
    print("Initialisation de la base de données...")
    init_db()
    print("Base de données initialisée avec succès!")
