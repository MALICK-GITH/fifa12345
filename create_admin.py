#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour créer le premier utilisateur administrateur
"""
import sys
import os

# Configurer l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from fifa1 import app, db
from models import User
from datetime import datetime

def create_admin():
    """Crée le premier utilisateur admin"""
    with app.app_context():
        # Vérifier si l'admin existe déjà
        admin = User.query.filter_by(username='ADMIN').first()
        if admin:
            print("OK - L'utilisateur ADMIN existe deja (ID: {})".format(admin.id))
            if not admin.is_admin:
                admin.is_admin = True
                db.session.commit()
                print("OK - Statut admin active")
            return admin
        
        # Créer le nouvel admin
        admin = User(
            username='ADMIN',
            email='admin@oracxpred.com',
            password='ADMIN123',
            is_admin=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("OK - Utilisateur ADMIN cree avec succes !")
        print("   Username: ADMIN")
        print("   Password: ADMIN123")
        print("   Statut: Administrateur")
        
        return admin

if __name__ == '__main__':
    print("Creation de l'utilisateur administrateur...")
    print("=" * 50)
    try:
        create_admin()
        print("=" * 50)
        print("Termine ! Vous pouvez maintenant vous connecter avec ADMIN / ADMIN123")
    except Exception as e:
        print("ERREUR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)
