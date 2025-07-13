#!/usr/bin/env python3
"""
📦 INSTALLATION AUTOMATIQUE DES DÉPENDANCES
===========================================
Script d'installation intelligent pour votre système révolutionnaire
"""

import subprocess
import sys
import os

def installer_dependances():
    print("📦 INSTALLATION DES DÉPENDANCES - SYSTÈME RÉVOLUTIONNAIRE")
    print("=" * 70)
    
    # Dépendances essentielles (minimum requis)
    dependances_essentielles = [
        "Flask==2.3.3",
        "requests==2.31.0", 
        "numpy==1.24.3",
        "python-dateutil==2.8.2"
    ]
    
    # Dépendances recommandées (pour toutes les fonctionnalités)
    dependances_recommandees = [
        "scipy==1.11.2",
        "pandas==2.0.3",
        "scikit-learn==1.3.0",
        "matplotlib==3.7.2",
        "plotly==5.15.0",
        "beautifulsoup4==4.12.2",
        "redis==4.6.0",
        "colorama==0.4.6"
    ]
    
    print("🎯 ÉTAPE 1 : INSTALLATION DES DÉPENDANCES ESSENTIELLES")
    print("-" * 60)
    
    for package in dependances_essentielles:
        try:
            print(f"📦 Installation de {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installé avec succès !")
        except subprocess.CalledProcessError:
            print(f"❌ Erreur lors de l'installation de {package}")
    
    print(f"\n🚀 ÉTAPE 2 : INSTALLATION DES DÉPENDANCES RECOMMANDÉES")
    print("-" * 60)
    
    for package in dependances_recommandees:
        try:
            print(f"📦 Installation de {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installé avec succès !")
        except subprocess.CalledProcessError:
            print(f"⚠️ Erreur lors de l'installation de {package} (optionnel)")
    
    print(f"\n🎉 INSTALLATION TERMINÉE !")
    print("=" * 70)
    print("✅ Votre système révolutionnaire est prêt à fonctionner !")
    print("🚀 Lancez votre application avec : python fifa1.py")
    print("=" * 70)

def verifier_dependances():
    """Vérifie si les dépendances essentielles sont installées"""
    print("🔍 VÉRIFICATION DES DÉPENDANCES")
    print("-" * 40)
    
    dependances_a_verifier = [
        ("flask", "Flask"),
        ("requests", "Requests"),
        ("numpy", "NumPy"),
        ("dateutil", "Python-dateutil")
    ]
    
    toutes_installees = True
    
    for module, nom in dependances_a_verifier:
        try:
            __import__(module)
            print(f"✅ {nom} : Installé")
        except ImportError:
            print(f"❌ {nom} : Non installé")
            toutes_installees = False
    
    if toutes_installees:
        print("\n🎉 Toutes les dépendances essentielles sont installées !")
        return True
    else:
        print("\n⚠️ Certaines dépendances manquent. Lancez l'installation.")
        return False

def installation_rapide():
    """Installation rapide via requirements.txt"""
    print("⚡ INSTALLATION RAPIDE VIA REQUIREMENTS.TXT")
    print("-" * 50)
    
    if os.path.exists("requirements.txt"):
        try:
            print("📦 Installation de toutes les dépendances...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Installation terminée avec succès !")
            return True
        except subprocess.CalledProcessError:
            print("❌ Erreur lors de l'installation via requirements.txt")
            return False
    else:
        print("❌ Fichier requirements.txt non trouvé")
        return False

def menu_principal():
    """Menu principal d'installation"""
    print("📦 GESTIONNAIRE D'INSTALLATION - SYSTÈME RÉVOLUTIONNAIRE")
    print("=" * 70)
    print("Choisissez une option :")
    print("1. 🔍 Vérifier les dépendances")
    print("2. ⚡ Installation rapide (requirements.txt)")
    print("3. 🎯 Installation guidée étape par étape")
    print("4. 🚪 Quitter")
    print("-" * 70)
    
    choix = input("Votre choix (1-4): ").strip()
    
    if choix == "1":
        verifier_dependances()
    elif choix == "2":
        installation_rapide()
    elif choix == "3":
        installer_dependances()
    elif choix == "4":
        print("👋 Au revoir !")
        sys.exit(0)
    else:
        print("❌ Choix invalide. Veuillez choisir entre 1 et 4.")
        menu_principal()

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n👋 Installation interrompue par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")
        sys.exit(1)
