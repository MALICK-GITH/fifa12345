#!/bin/bash
# 🚀 SCRIPT DE BUILD POUR RENDER
# ==============================

echo "🚀 Démarrage du build pour Render..."

# Mise à jour de pip
python -m pip install --upgrade pip

# Installation des dépendances minimales
echo "📦 Installation des dépendances..."
pip install Flask==2.3.3
pip install requests==2.31.0
pip install python-dateutil==2.8.2

echo "✅ Build terminé avec succès !"
echo "🎯 Application prête pour le déploiement"
