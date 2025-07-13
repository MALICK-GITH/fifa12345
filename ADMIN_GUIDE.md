# 🛡️ Guide d'Administration - Sports Betting

Guide complet pour les administrateurs de l'application Sports Betting.

## 🚀 Démarrage Rapide

### 1. Premier Démarrage
```bash
# Démarrer l'application
python fifa1.py

# Le super administrateur est créé automatiquement :
# 👤 Nom d'utilisateur : admin
# 🔑 Mot de passe : admin123
```

### 2. Première Connexion Admin
1. Allez sur http://localhost:5000
2. Cliquez sur "🔑 Connexion"
3. Connectez-vous avec `admin` / `admin123`
4. **CHANGEZ IMMÉDIATEMENT LE MOT DE PASSE !**
5. Cliquez sur "🛡️ Admin" dans la barre de navigation

## 👥 Gestion des Utilisateurs

### Niveaux d'Utilisateur

#### 🆓 **Gratuit (Free)**
- Accès de base aux prédictions
- Fonctionnalités limitées
- Pas de favoris illimités

#### 💎 **Premium**
- Toutes les prédictions avancées
- Historique personnel complet
- Favoris illimités
- Graphiques complets

#### 👑 **VIP**
- Toutes les fonctionnalités Premium
- Support prioritaire
- Accès API
- Analytics avancés

### Rôles d'Administration

#### 👤 **Utilisateur (User)**
- Utilisateur standard
- Pas d'accès admin

#### 🛡️ **Administrateur (Admin)**
- Peut approuver les utilisateurs
- Peut changer les niveaux d'abonnement
- Accès aux logs et statistiques
- Ne peut pas créer d'autres admins

#### 👑 **Super Administrateur (Super Admin)**
- Tous les pouvoirs d'admin
- Peut créer/modifier des administrateurs
- Accès complet au système

## 📋 Processus d'Approbation

### Nouveaux Utilisateurs
1. **Inscription** : Les utilisateurs s'inscrivent normalement
2. **Statut** : Compte créé mais `is_approved = False`
3. **Connexion** : Impossible tant que non approuvé
4. **Notification** : Message d'attente d'approbation
5. **Approbation** : Admin clique sur "✅ Approuver"
6. **Accès** : L'utilisateur peut maintenant se connecter

### Workflow d'Approbation
```
Inscription → En Attente → Approbation Admin → Accès Autorisé
```

## 🛠️ Fonctionnalités d'Administration

### 📊 Tableau de Bord
- **Statistiques générales** : Total utilisateurs, en attente, premium
- **Utilisateurs récents** : 10 dernières inscriptions
- **Actions récentes** : 10 dernières actions admin

### 👥 Gestion Utilisateurs
- **Filtrage** : Par statut (tous, en attente, approuvés, premium)
- **Pagination** : 20 utilisateurs par page
- **Actions rapides** :
  - ✅ Approuver un utilisateur
  - 💎 Changer le niveau d'abonnement
  - 🛡️ Changer le rôle (super admin seulement)

### 📋 Logs d'Administration
- **Traçabilité complète** de toutes les actions admin
- **Informations** : Date, admin, action, utilisateur cible, détails, IP
- **Historique permanent** pour audit

### 📈 Statistiques Détaillées
- **Utilisateurs** : Répartition par statut et abonnement
- **Prédictions** : Total, correctes, taux de réussite
- **Activité** : Nouveaux utilisateurs et prédictions du jour

## 🔧 Actions Administratives

### Approuver un Utilisateur
```python
# Via l'interface web
POST /admin/users/{user_id}/approve

# Ou via code
admin_manager.approve_user(admin_user, target_user)
```

### Changer un Abonnement
```python
# Via l'interface web
POST /admin/users/{user_id}/subscription
# Form data: subscription_level = 'premium'

# Ou via code
admin_manager.change_subscription(admin_user, target_user, 'premium')
```

### Changer un Rôle (Super Admin)
```python
# Via l'interface web
POST /admin/users/{user_id}/role
# Form data: role = 'admin'

# Ou via code
admin_manager.change_user_role(admin_user, target_user, 'admin')
```

## 🔒 Sécurité

### Permissions
- **Décorateurs** : `@admin_required`, `@super_admin_required`
- **Vérifications** : `current_user.can_access_admin()`
- **Logs** : Toutes les actions sont enregistrées

### Bonnes Pratiques
1. **Changez le mot de passe admin par défaut**
2. **Créez des admins avec parcimonie**
3. **Surveillez les logs régulièrement**
4. **Approuvez les utilisateurs après vérification**
5. **Documentez les changements importants**

## 📊 API d'Administration

### Endpoints Disponibles
```bash
# Statistiques
GET /api/admin/stats

# Liste des utilisateurs
GET /api/admin/users

# Toutes les routes nécessitent l'authentification admin
```

### Exemple d'Utilisation
```javascript
// Récupérer les statistiques
fetch('/api/admin/stats', {
    headers: {
        'X-Requested-With': 'XMLHttpRequest'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

## 🧪 Tests et Développement

### Créer des Utilisateurs de Test
```bash
python create_test_users.py
```

Cela crée :
- `user_test` / `test123` (Gratuit, non approuvé)
- `premium_user` / `premium123` (Premium, approuvé)
- `vip_user` / `vip123` (VIP, approuvé)
- `admin_test` / `admin123` (Admin, approuvé)

### Scénarios de Test
1. **Test d'approbation** : Connectez-vous avec `user_test` (refusé)
2. **Approuver l'utilisateur** : Via l'admin
3. **Test de connexion** : `user_test` peut maintenant se connecter
4. **Test de changement d'abonnement** : Passer `user_test` en Premium
5. **Test de création d'admin** : Promouvoir un utilisateur en admin

## 🚨 Dépannage

### Problèmes Courants

#### "Accès refusé" pour l'admin
- Vérifiez que `is_approved = True`
- Vérifiez que `role` est 'admin' ou 'super_admin'

#### Utilisateur ne peut pas se connecter
- Vérifiez `is_approved` dans la base de données
- Approuvez via l'interface admin

#### Erreur lors de l'approbation
- Vérifiez les logs de l'application
- Vérifiez la connexion à la base de données

### Commandes de Debug
```python
# Dans la console Python
from fifa1 import app, db, User

with app.app_context():
    # Voir tous les admins
    admins = User.query.filter(User.role.in_(['admin', 'super_admin'])).all()
    
    # Voir les utilisateurs en attente
    pending = User.query.filter_by(is_approved=False).all()
    
    # Approuver manuellement un utilisateur
    user = User.query.filter_by(username='user_test').first()
    user.is_approved = True
    db.session.commit()
```

## 📞 Support

### Logs à Vérifier
- **Application** : Console de l'application
- **Admin** : Table `admin_logs` dans la base de données
- **Prédictions** : Fichier `predictions.log`

### Informations Utiles pour le Support
1. Version de l'application
2. Logs d'erreur
3. Actions effectuées avant le problème
4. Navigateur et système d'exploitation

---

**🛡️ Administration responsable = Application sécurisée et performante**
