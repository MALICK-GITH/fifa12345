# 🛡️ Guide d'Accès au Panneau Administrateur

## 🚀 Accès Rapide

### URL du Panneau Admin
```
http://localhost:5000/admin/login
```

### Interface ORACX-ADMIN
```
http://localhost:5000/admin/oracx-admin
```

## 👤 Compte Administrateur

### Option 1 : Utiliser le script create_admin.py

Exécutez le script pour créer un compte admin :

```bash
python create_admin.py
```

Cela crée un compte avec :
- **Username** : `ADMIN`
- **Password** : `ADMIN123`
- **Statut** : Administrateur

### Option 2 : Créer manuellement via Python

Ouvrez un terminal Python dans le répertoire du projet :

```python
from fifa1 import app, db
from models import User
from datetime import datetime

with app.app_context():
    # Vérifier si admin existe
    admin = User.query.filter_by(username='admin').first()
    
    if not admin:
        admin = User(
            username='admin',
            email='admin@oracxpred.com',
            password='admin123',
            is_admin=True,
            is_approved=True,
            subscription_plan='vip',
            subscription_status='active'
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin créé ! Username: admin, Password: admin123")
    else:
        print("✅ Admin existe déjà")
```

## 🔑 Connexion

1. **Démarrez l'application** :
   ```bash
   python fifa1.py
   ```

2. **Accédez à la page de connexion admin** :
   - Ouvrez votre navigateur
   - Allez sur : `http://localhost:5000/admin/login`

3. **Connectez-vous** :
   - Username : `ADMIN` (ou `admin` selon ce que vous avez créé)
   - Password : `ADMIN123` (ou `admin123`)

4. **Redirection automatique** :
   - Après connexion, vous êtes redirigé vers `/admin/dashboard`

## 📊 Interfaces Disponibles

### 1. Dashboard Admin Classique
**URL** : `http://localhost:5000/admin/dashboard`
- Gestion des utilisateurs
- Approbation des comptes
- Modification des plans d'abonnement

### 2. Interface ORACX-ADMIN
**URL** : `http://localhost:5000/admin/oracx-admin`
- Statistiques complètes
- Logs système
- Vue d'ensemble du système

## 🔒 Sécurité

⚠️ **IMPORTANT** : Changez le mot de passe par défaut immédiatement après la première connexion !

## 🐛 Dépannage

### "Identifiants admin incorrects"
- Vérifiez que l'utilisateur existe : `is_admin=True`
- Vérifiez le mot de passe (pas de hashage, mot de passe en clair dans la base)
- Vérifiez que `is_approved=True` (optionnel mais recommandé)

### "Accès refusé"
- Vérifiez que `session['admin_logged_in']` est défini
- Vérifiez que l'utilisateur a `is_admin=True`

### Vérifier les admins existants

```python
from fifa1 import app, db
from models import User

with app.app_context():
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        print(f"Admin: {admin.username}, Approved: {admin.is_approved}")
```

## 📝 Notes

- Le système utilise des sessions Flask pour l'authentification admin
- Les mots de passe sont stockés en clair (pour ce système)
- L'admin a accès à toutes les fonctionnalités du système
- Toutes les actions admin sont journalisées dans SystemLog
