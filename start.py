#!/usr/bin/env python3
"""
Script de démarrage rapide pour l'application Sports Betting
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Vérifier les dépendances"""
    print("🔍 Vérification des dépendances...")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy', 
        'flask_login',
        'flask_wtf',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} manquant")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Packages manquants: {', '.join(missing_packages)}")
        print("🔧 Installation automatique...")
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "Flask", "Flask-SQLAlchemy", "Flask-Login", 
                "Flask-WTF", "requests"
            ])
            print("✅ Dépendances installées avec succès")
        except subprocess.CalledProcessError:
            print("❌ Erreur lors de l'installation")
            return False
    
    return True

def start_application():
    """Démarrer l'application"""
    print("\n🚀 Démarrage de l'application...")
    
    try:
        # Importer et démarrer l'application
        import fifa1
        
        print("✅ Application chargée")
        print("🌐 Serveur démarré sur:")
        print("   - http://localhost:5000")
        print("   - http://127.0.0.1:5000")
        print("\n📱 Fonctionnalités disponibles:")
        print("   🔐 Comptes utilisateurs (Gratuit/Premium/VIP)")
        print("   🎨 Mode sombre/clair")
        print("   ⭐ Système de favoris")
        print("   📊 6 graphiques interactifs")
        print("   🤖 Prédictions IA avancées")
        print("   🔄 Rafraîchissement temps réel")
        print("   💾 Base de données SQLite")
        print("   ⚡ Cache intelligent")
        print("   📱 Interface responsive")
        print("   🔗 API REST complète")
        
        print("\n⚠️ Appuyez sur Ctrl+C pour arrêter le serveur")
        
        # Démarrer le serveur
        fifa1.app.run(host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Serveur arrêté par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        return False
    
    return True

def main():
    """Fonction principale"""
    print("🏆 SPORTS BETTING - DÉMARRAGE RAPIDE")
    print("=" * 40)
    
    # Vérifier les dépendances
    if not check_dependencies():
        print("❌ Impossible de démarrer sans les dépendances")
        return False
    
    # Démarrer l'application
    return start_application()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Au revoir !")
        sys.exit(0)
