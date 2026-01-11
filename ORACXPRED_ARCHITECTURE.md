# 🎯 ORACXPRED MÉTAPHORE - Architecture et Spécifications

## 📋 Vue d'Ensemble

ORACXPRED Métaphore est une plateforme de prédictions FIFA avec deux systèmes séparés et sécurisés :
- **ORACXPRED Métaphore** : Interface utilisateur (accès payant)
- **ORACX-ADMIN** : Interface administrateur (sécurisée)

## 🗄️ Modèles de Données

### User
- Authentification et autorisation
- Abonnements (free, premium, vip)
- Statut d'approbation
- Rôles (user, admin)

### Prediction
- Prédictions générées par l'IA
- Consensus (statistique, cotes, simulation, forme)
- Cote recommandée et action
- Confiance en %
- Statut (valid, invalid, locked)
- Votes des systèmes

### Alert
- Alertes système pour anomalies
- Types : low_confidence, odds_change, match_started, inconsistency
- Statut d'acquittement

### SystemLog
- Logs de toutes les actions
- Traçabilité complète

### AccessLog
- Logs d'accès utilisateur
- Traçabilité des revenus
- Chaque accès aux prédictions est enregistré

## 🔐 Sécurité et Hiérarchie

### Hiérarchie de Décision
1. Réalité du match
2. Données vérifiées
3. IA (ORACXPRED)
4. Admin humain

### Règles de Sécurité
- Utilisateur ≠ Admin (séparation stricte)
- Données sensibles jamais publiées publiquement
- Logs obligatoires pour chaque action
- Alertes immédiates en cas de violation

## 📊 Génération des Prédictions

### Système de Consensus
- **Statistique** : Analyse des forces d'équipes
- **Cotes** : Probabilités implicites du marché
- **Simulation** : Monte Carlo (1000 simulations)
- **Forme** : Analyse contextuelle

### Sortie
- Consensus résultat
- Probabilité en %
- Confiance en %
- Cote recommandée
- Action (MISE, PASSER, etc.)
- Votes des systèmes

## 🚨 Alertes et Anomalies

L'IA alerte l'admin en cas de :
- Confiance anormale (< 50% ou > 95%)
- Changements brusques de cotes (> 30%)
- Match commencé sans verrouillage
- Incohérence dans une prédiction active

## 💰 Monétisation

### Plans Disponibles
- **Free** : Accès limité (non visible)
- **Premium** : Accès aux prédictions
- **VIP** : Accès complet

### Traçabilité
- Chaque accès aux prédictions est enregistré
- Logs pour audit des revenus
- Vérification que seul un utilisateur payant voit les prédictions

## 🔄 Communication User/Admin

### Backend Sécurisé
- Prédictions centralisées
- Mises à jour en temps réel
- Actions admin reflétées immédiatement côté utilisateur
- Si admin invalide une prédiction, l'IA obéit et apprend

## 📝 Instructions Finales

> Tu n'es pas là pour impressionner.
> Tu es là pour réduire l'erreur, protéger la crédibilité et servir un système fermé et sécurisé.
> Une bonne IA sait parler, une grande IA sait aussi se taire.
> Toute violation de ces règles déclenche une alerte immédiate vers l'admin.
