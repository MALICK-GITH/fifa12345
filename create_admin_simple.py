#!/usr/bin/env python3
"""
CRÉATION SIMPLE DE L'ADMINISTRATEUR PAR DÉFAUT - ORACXPRED
=========================================================
Version simplifiée sans dépendances complexes
"""

import sys
import os
from datetime import datetime

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash, check_password_hash

def create_admin_simple():
    """Crée l'administrateur par défaut MKINGS avec connexion directe à la BDD"""
    
    try:
        # Connexion directe à la base de données
        import sqlite3
        db_path = "oracxpred.db"
        
        print("Connexion a la base de donnees...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si l'admin existe déjà
        cursor.execute("SELECT * FROM users WHERE username = ?", ('MKINGS',))
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            print("L'administrateur MKINGS existe deja.")
            print(f"   ID: {existing_admin[0]}")
            print(f"   Username: {existing_admin[1]}")
            print(f"   Email: {existing_admin[2]}")
            print(f"   Admin: {existing_admin[6]}")
            print(f"   Approuve: {existing_admin[7]}")
            print(f"   Actif: {existing_admin[8]}")
            conn.close()
            return True
        
        # Vérifier si l'email existe
        cursor.execute("SELECT * FROM users WHERE email = ?", ('admin@oracxpred.com',))
        existing_email = cursor.fetchone()
        
        if existing_email:
            print("L'email admin@oracxpred.com existe deja. Utilisation d'un email alternatif.")
            email = f'admin_{datetime.now().strftime("%Y%m%d_%H%M%S")}@oracxpred.com'
        else:
            email = 'admin@oracxpred.com'
        
        # Générer le hash du mot de passe
        password_hash = generate_password_hash('66240702')
        
        # Insérer le nouvel admin
        cursor.execute("""
            INSERT INTO users (
                username, email, password, is_admin, is_approved, is_active,
                subscription_plan, subscription_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'MKINGS',
            email,
            password_hash,
            1,  # is_admin
            1,  # is_approved
            1,  # is_active
            'premium',
            'active',
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print("Administrateur par defaut cree avec succes!")
        print("Identifiants de connexion:")
        print("   Login: MKINGS")
        print("   Password: 66240702")
        print(f"   Email: {email}")
        print("Le mot de passe a ete hashe de maniere securisee")
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de la creation de l'admin: {e}")
        return False

def verify_admin_simple():
    """Vérifie l'accès admin avec connexion directe"""
    
    try:
        import sqlite3
        db_path = "oracxpred.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", ('MKINGS',))
        admin = cursor.fetchone()
        
        if not admin:
            print("Administrateur MKINGS non trouve")
            conn.close()
            return False
        
        # Vérifier le mot de passe
        if check_password_hash(admin[3], '66240702'):
            print("Mot de passe verifie avec succes")
        else:
            print("Erreur de verification du mot de passe")
            conn.close()
            return False
        
        # Vérifier les permissions
        checks = [
            ("Admin", bool(admin[6])),
            ("Approuve", bool(admin[7])),
            ("Actif", bool(admin[8]))
        ]
        
        print("Verification des permissions:")
        all_good = True
        for name, check in checks:
            status = "OK" if check else "ERREUR"
            print(f"   {status} {name}: {check}")
            if not check:
                all_good = False
        
        conn.close()
        return all_good
        
    except Exception as e:
        print(f"Erreur lors de la verification: {e}")
        return False

if __name__ == "__main__":
    print("Creation de l'administrateur par defaut ORACXPRED")
    print("=" * 50)
    
    # Créer l'admin
    if create_admin_simple():
        print("\n" + "=" * 50)
        print("Verification de l'acces admin:")
        if verify_admin_simple():
            print("\n" + "=" * 50)
            print("L'administrateur peut maintenant se connecter:")
            print("   URL: http://localhost:10000/login")
            print("   Login: MKINGS")
            print("   Password: 66240702")
            print("\nAcces au backoffice admin disponible!")
        else:
            print("\nErreur de verification de l'admin")
    else:
        print("\nEchec de la creation de l'administrateur")
        sys.exit(1)
