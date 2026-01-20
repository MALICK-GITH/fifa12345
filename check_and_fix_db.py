"""
🔧 VÉRIFICATION ET CORRECTION DE LA BASE DE DONNÉES
===================================================
Vérifie et corrige les problèmes de base de données au démarrage
"""

import os
import sqlite3
from flask import Flask

def check_and_fix_database(app):
    """Vérifie et corrige la base de données"""
    with app.app_context():
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        
        if not db_uri.startswith("sqlite:///"):
            print("⚠️ Migration supportée uniquement pour SQLite")
            return
        
        db_path = db_uri.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            if not os.path.exists(app.instance_path):
                os.makedirs(app.instance_path, exist_ok=True)
            db_path = os.path.join(app.instance_path, db_path)
        
        # Si la base n'existe pas, elle sera créée par db.create_all()
        if not os.path.exists(db_path):
            print("✅ Base de données n'existe pas, sera créée automatiquement")
            from models import db
            db.create_all()
            return
        
        # Vérifier et corriger les colonnes manquantes
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Vérifier la table users
            cursor.execute("PRAGMA table_info(users)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            # Ajouter is_active si manquante
            if 'is_active' not in columns:
                print("➕ Ajout de la colonne 'is_active'...")
                cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
                # Mettre tous les utilisateurs existants comme actifs
                cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
                conn.commit()
                print("✅ Colonne 'is_active' ajoutée")
            
            # Ajouter unique_id si manquante
            if 'unique_id' not in columns:
                print("➕ Ajout de la colonne 'unique_id'...")
                cursor.execute("ALTER TABLE users ADD COLUMN unique_id VARCHAR(36)")
                
                # Générer des unique_id pour les utilisateurs existants
                cursor.execute("SELECT id FROM users WHERE unique_id IS NULL OR unique_id = ''")
                users_without_id = cursor.fetchall()
                
                import uuid
                for (user_id,) in users_without_id:
                    new_uuid = str(uuid.uuid4())
                    cursor.execute(
                        "UPDATE users SET unique_id = ? WHERE id = ?",
                        (new_uuid, user_id)
                    )
                
                # Créer un index unique
                try:
                    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_unique_id ON users(unique_id)")
                except:
                    pass
                
                conn.commit()
                print(f"✅ Colonne 'unique_id' ajoutée ({len(users_without_id)} utilisateurs mis à jour)")
            
            conn.close()
            print("✅ Vérification de la base de données terminée")
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la vérification: {e}")
            import traceback
            traceback.print_exc()
