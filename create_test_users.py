#!/usr/bin/env python3
"""
Script pour créer des utilisateurs de test pour l'administration
"""

import sys
import os

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_users():
    """Créer des utilisateurs de test"""
    try:
        # Importer l'application
        from fifa1 import app, db, User, admin_manager
        
        with app.app_context():
            print("🧪 Création d'utilisateurs de test...")
            
            # Utilisateurs de test
            test_users = [
                {
                    'username': 'user_test',
                    'email': 'user@test.com',
                    'password': 'test123',
                    'role': 'user',
                    'subscription': 'free',
                    'approved': False
                },
                {
                    'username': 'premium_user',
                    'email': 'premium@test.com',
                    'password': 'premium123',
                    'role': 'user',
                    'subscription': 'premium',
                    'approved': True
                },
                {
                    'username': 'vip_user',
                    'email': 'vip@test.com',
                    'password': 'vip123',
                    'role': 'user',
                    'subscription': 'vip',
                    'approved': True
                },
                {
                    'username': 'admin_test',
                    'email': 'admin@test.com',
                    'password': 'admin123',
                    'role': 'admin',
                    'subscription': 'vip',
                    'approved': True
                }
            ]
            
            created_count = 0
            
            for user_data in test_users:
                # Vérifier si l'utilisateur existe déjà
                existing = User.query.filter_by(username=user_data['username']).first()
                
                if not existing:
                    user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        role=user_data['role'],
                        subscription_level=user_data['subscription'],
                        is_approved=user_data['approved']
                    )
                    user.set_password(user_data['password'])
                    user.set_preferences({
                        'theme': 'light',
                        'notifications': True,
                        'auto_refresh': True,
                        'language': 'fr'
                    })
                    
                    db.session.add(user)
                    created_count += 1
                    
                    print(f"✅ Utilisateur créé: {user_data['username']} ({user_data['role']}, {user_data['subscription']})")
                else:
                    print(f"⚠️ Utilisateur existant: {user_data['username']}")
            
            if created_count > 0:
                db.session.commit()
                print(f"\n🎉 {created_count} utilisateurs de test créés avec succès !")
            else:
                print("\n📋 Tous les utilisateurs de test existent déjà")
            
            # Afficher le résumé
            print("\n📊 RÉSUMÉ DES COMPTES DE TEST :")
            print("=" * 50)
            
            for user_data in test_users:
                status = "Approuvé" if user_data['approved'] else "En attente"
                print(f"👤 {user_data['username']:<15} | 🔑 {user_data['password']:<10} | 🏷️ {user_data['role']:<10} | 💎 {user_data['subscription']:<8} | 📋 {status}")
            
            print("\n🛡️ COMPTE ADMINISTRATEUR PRINCIPAL :")
            print("👤 admin           | 🔑 admin123   | 🏷️ super_admin | 💎 vip      | 📋 Approuvé")
            
            print("\n🌐 Pour tester l'administration :")
            print("1. Démarrez l'application : python fifa1.py")
            print("2. Connectez-vous avec : admin / admin123")
            print("3. Accédez à l'admin via le bouton 🛡️ Admin")
            print("4. Approuvez les utilisateurs en attente")
            print("5. Changez les niveaux d'abonnement")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la création des utilisateurs de test: {e}")
        return False

def main():
    """Fonction principale"""
    print("🧪 CRÉATION D'UTILISATEURS DE TEST")
    print("=" * 40)
    
    success = create_test_users()
    
    if success:
        print("\n✅ Script terminé avec succès !")
    else:
        print("\n❌ Erreur lors de l'exécution du script")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
