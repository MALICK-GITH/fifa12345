#!/usr/bin/env python3
"""
CRÉATION DE L'ADMINISTRATEUR PAR DÉFAUT - ORACXPRED
==================================================
Crée automatiquement l'administrateur MKINGS avec le mot de passe 66240702
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from models import db, User
from prediction_manager import log_action

def create_default_admin():
    """Crée l'administrateur par défaut MKINGS"""
    
    # Créer le contexte d'application Flask
    from fifa1 import app
    with app.app_context():
        # Vérifier si l'admin existe déjà
        existing_admin = User.query.filter_by(username='MKINGS').first()
        if existing_admin:
            print("L'administrateur MKINGS existe deja.")
            print(f"   ID: {existing_admin.id}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Admin: {existing_admin.is_admin}")
            print(f"   Approuve: {existing_admin.is_approved}")
            print(f"   Actif: {existing_admin.is_active}")
            return existing_admin
        
        # Créer le nouvel admin
        try:
            # Vérifier d'abord si l'email existe
            existing_email = User.query.filter_by(email='admin@oracxpred.com').first()
            if existing_email:
                print("L'email admin@oracxpred.com existe deja. Utilisation d'un email alternatif.")
                email = f'admin_{datetime.now().strftime("%Y%m%d_%H%M%S")}@oracxpred.com'
            else:
                email = 'admin@oracxpred.com'
            
            admin = User(
                username='MKINGS',
                email=email,
                password=generate_password_hash('66240702'),  # Hashage sécurisé du mot de passe
                is_admin=True,
                is_approved=True,
                is_active=True,
                subscription_plan='premium',
                subscription_status='active'
            )
            
            db.session.add(admin)
            db.session.commit()
            
            # Logger la création
            log_action("admin_creation", "Administrateur par défaut MKINGS créé", {
                "username": "MKINGS",
                "created_by": "system"
            })
            
            print("Administrateur par defaut cree avec succes!")
            print("Identifiants de connexion:")
            print("   Login: MKINGS")
            print("   Password: 66240702")
            print(f"   Email: {email}")
            print("Le mot de passe a ete hashe de maniere securisee")
            print(f"ID Utilisateur: {admin.id}")
            
            return admin
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de la creation de l'admin: {e}")
            return None

def verify_admin_access():
    """Vérifie que l'admin peut se connecter"""
    
    # Créer le contexte d'application Flask
    from fifa1 import app
    with app.app_context():
        admin = User.query.filter_by(username='MKINGS').first()
        if not admin:
            print("Administrateur MKINGS non trouve")
            return False
        
        # Vérifier le mot de passe
        from werkzeug.security import check_password_hash
        if check_password_hash(admin.password, '66240702'):
            print("Mot de passe verifie avec succes")
        else:
            print("Erreur de verification du mot de passe")
            return False
        
        # Vérifier les permissions
        checks = [
            ("Admin", admin.is_admin),
            ("Approuvé", admin.is_approved),
            ("Actif", admin.is_active),
            ("Accès payant", admin.has_paid_access())
        ]
        
        print("Verification des permissions:")
        all_good = True
        for name, check in checks:
            status = "OK" if check else "ERREUR"
            print(f"   {status} {name}: {check}")
            if not check:
                all_good = False
        
        return all_good

if __name__ == "__main__":
    print("Creation de l'administrateur par defaut ORACXPRED")
    print("=" * 50)
    
    # Creer l'admin
    admin = create_default_admin()
    
    if admin:
        print("\n" + "=" * 50)
        print("Verification de l'acces admin:")
        verify_admin_access()
        
        print("\n" + "=" * 50)
        print("L'administrateur peut maintenant se connecter:")
        print("   URL: http://localhost:10000/login")
        print("   Login: MKINGS")
        print("   Password: 66240702")
        print("\nAcces au backoffice admin disponible!")
    else:
        print("\nEchec de la creation de l'administrateur")
        sys.exit(1)
