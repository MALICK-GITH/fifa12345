#!/usr/bin/env python3
"""
Script pour créer le premier utilisateur administrateur
"""
from fifa1 import app, db
from models import User
from datetime import datetime

def create_admin():
    """Crée le premier utilisateur admin"""
    with app.app_context():
        # Vérifier si l'admin existe déjà
        admin = User.query.filter_by(username='ADMIN').first()
        if admin:
            print(f"✅ L'utilisateur ADMIN existe déjà (ID: {admin.id})")
            if not admin.is_admin:
                admin.is_admin = True
                db.session.commit()
                print("✅ Statut admin activé")
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
        
        print("✅ Utilisateur ADMIN créé avec succès !")
        print(f"   👤 Username: ADMIN")
        print(f"   🔑 Password: ADMIN123")
        print(f"   👑 Statut: Administrateur")
        
        return admin

if __name__ == '__main__':
    print("🚀 Création de l'utilisateur administrateur...")
    print("=" * 50)
    create_admin()
    print("=" * 50)
    print("✨ Terminé ! Vous pouvez maintenant vous connecter avec ADMIN / ADMIN123")
