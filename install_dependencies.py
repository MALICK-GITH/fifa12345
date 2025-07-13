#!/usr/bin/env python3
"""
Script d'installation des dépendances pour le projet Sports Betting
"""

import subprocess
import sys
import os

def install_package(package):
    """Installer un package avec pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installé avec succès")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Erreur lors de l'installation de {package}")
        return False

def main():
    print("🚀 Installation des dépendances pour Sports Betting...")
    print("=" * 50)
    
    # Liste des packages requis
    packages = [
        "Flask==2.3.3",
        "Flask-SQLAlchemy==3.0.5", 
        "Flask-Login==0.6.3",
        "Flask-WTF==1.1.1",
        "WTForms==3.0.1",
        "Werkzeug==2.3.7",
        "requests==2.31.0"
    ]
    
    # Packages optionnels
    optional_packages = [
        "redis==4.6.0"
    ]
    
    success_count = 0
    total_count = len(packages)
    
    # Installation des packages requis
    print("\n📦 Installation des packages requis...")
    for package in packages:
        if install_package(package):
            success_count += 1
    
    # Installation des packages optionnels
    print("\n📦 Installation des packages optionnels...")
    for package in optional_packages:
        if install_package(package):
            print(f"✅ {package} installé (cache Redis disponible)")
        else:
            print(f"⚠️ {package} non installé (cache Redis désactivé)")
    
    print("\n" + "=" * 50)
    print(f"📊 Résultat: {success_count}/{total_count} packages requis installés")
    
    if success_count == total_count:
        print("🎉 Installation terminée avec succès !")
        print("\n🚀 Pour démarrer l'application :")
        print("   python fifa1.py")
        print("\n🌐 L'application sera disponible sur :")
        print("   http://localhost:5000")
        print("   http://127.0.0.1:5000")
    else:
        print("❌ Certains packages n'ont pas pu être installés")
        print("Veuillez vérifier votre connexion internet et réessayer")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
