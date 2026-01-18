"""
⏰ TÂCHES AUTOMATIQUES ORACXPRED
=================================
Sauvegardes quotidiennes/hebdomadaires, nettoyage, etc.
"""

import os
import schedule
import time
from datetime import datetime
from flask import Flask

from models import db, BackupLog, UserSubscription, PersistentSession
from oracxpred_utils import create_backup, cleanup_expired_sessions, check_and_expire_subscriptions, cleanup_old_backups


def run_daily_backup():
    """Sauvegarde quotidienne"""
    print(f"[{datetime.now()}] Démarrage sauvegarde quotidienne...")
    try:
        with app.app_context():
            backup_path = create_backup('daily')
            if backup_path:
                print(f"[{datetime.now()}] ✅ Sauvegarde quotidienne créée: {backup_path}")
            else:
                print(f"[{datetime.now()}] ❌ Échec sauvegarde quotidienne")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Erreur sauvegarde quotidienne: {e}")


def run_weekly_backup():
    """Sauvegarde hebdomadaire"""
    print(f"[{datetime.now()}] Démarrage sauvegarde hebdomadaire...")
    try:
        with app.app_context():
            backup_path = create_backup('weekly')
            if backup_path:
                print(f"[{datetime.now()}] ✅ Sauvegarde hebdomadaire créée: {backup_path}")
            else:
                print(f"[{datetime.now()}] ❌ Échec sauvegarde hebdomadaire")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Erreur sauvegarde hebdomadaire: {e}")


def run_cleanup_tasks():
    """Nettoyage des sessions expirées et abonnements"""
    print(f"[{datetime.now()}] Démarrage tâches de nettoyage...")
    try:
        with app.app_context():
            expired_sessions = cleanup_expired_sessions()
            expired_subscriptions = check_and_expire_subscriptions()
            deleted_backups = cleanup_old_backups(keep_days=30)
            
            print(f"[{datetime.now()}] ✅ Nettoyage terminé:")
            print(f"  - Sessions expirées supprimées: {expired_sessions}")
            print(f"  - Abonnements expirés: {expired_subscriptions}")
            print(f"  - Sauvegardes anciennes supprimées: {deleted_backups}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Erreur nettoyage: {e}")


def setup_scheduled_tasks(app_instance):
    """Configure les tâches planifiées"""
    global app
    app = app_instance
    
    # Sauvegarde quotidienne à 2h du matin
    schedule.every().day.at("02:00").do(run_daily_backup)
    
    # Sauvegarde hebdomadaire le dimanche à 3h du matin
    schedule.every().sunday.at("03:00").do(run_weekly_backup)
    
    # Nettoyage quotidien à 4h du matin
    schedule.every().day.at("04:00").do(run_cleanup_tasks)
    
    print("✅ Tâches planifiées configurées:")
    print("  - Sauvegarde quotidienne: 02:00")
    print("  - Sauvegarde hebdomadaire: Dimanche 03:00")
    print("  - Nettoyage: 04:00")


def run_scheduler():
    """Lance le planificateur de tâches"""
    print("🚀 Démarrage du planificateur de tâches ORACXPRED...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes


if __name__ == "__main__":
    # Pour tester les tâches manuellement
    from fifa1 import app
    setup_scheduled_tasks(app)
    
    # Exécuter une fois immédiatement pour test
    print("\n🧪 Exécution des tâches de test...")
    run_cleanup_tasks()
    
    # Lancer le planificateur
    # run_scheduler()
