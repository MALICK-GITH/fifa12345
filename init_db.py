#!/usr/bin/env python3
"""
INITIALISATION DE LA BASE DE DONNÉES - ORACXPRED
===============================================
Crée les tables nécessaires sans dépendances complexes
"""

import sys
import os
from datetime import datetime

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """Initialise la base de données avec les tables nécessaires"""
    
    try:
        import sqlite3
        db_path = "oracxpred.db"
        
        print("Connexion a la base de donnees...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Créer la table users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE,
                password VARCHAR(255) NOT NULL,
                profile_photo VARCHAR(255),
                is_admin BOOLEAN DEFAULT 0,
                is_approved BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                subscription_plan VARCHAR(20) DEFAULT 'free',
                subscription_status VARCHAR(20) DEFAULT 'inactive',
                subscription_expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login_at DATETIME,
                ip_address VARCHAR(45),
                unique_id VARCHAR(36) UNIQUE
            )
        """)
        
        # Créer la table collected_matches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collected_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_match_id VARCHAR(100) UNIQUE NOT NULL,
                jeu VARCHAR(50) NOT NULL,
                equipe_domicile VARCHAR(200) NOT NULL,
                equipe_exterieur VARCHAR(200) NOT NULL,
                heure_debut DATETIME NOT NULL,
                heure_fin DATETIME,
                timestamp_enregistrement DATETIME DEFAULT CURRENT_TIMESTAMP,
                score_domicile INTEGER,
                score_exterieur INTEGER,
                equipe_gagnante VARCHAR(200),
                statut VARCHAR(20) DEFAULT 'en_attente',
                source_donnees VARCHAR(100),
                collecte_par VARCHAR(50) DEFAULT 'systeme_auto',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table match_collection_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_collection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type VARCHAR(50) NOT NULL,
                match_id VARCHAR(100),
                message TEXT NOT NULL,
                severity VARCHAR(20) DEFAULT 'info',
                source_donnees VARCHAR(100),
                temps_execution REAL,
                extra_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table predictions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                team1 VARCHAR(200) NOT NULL,
                team2 VARCHAR(200) NOT NULL,
                league VARCHAR(200) NOT NULL,
                consensus_type VARCHAR(50) NOT NULL,
                consensus_result TEXT NOT NULL,
                consensus_probability REAL NOT NULL,
                confidence REAL NOT NULL,
                recommended_odd REAL,
                recommended_action VARCHAR(100),
                votes_statistique BOOLEAN DEFAULT 0,
                votes_cotes BOOLEAN DEFAULT 0,
                votes_simulation BOOLEAN DEFAULT 0,
                votes_forme BOOLEAN DEFAULT 0,
                is_valid BOOLEAN DEFAULT 1,
                is_locked BOOLEAN DEFAULT 0,
                invalidated_by INTEGER,
                invalidated_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT
            )
        """)
        
        # Créer la table system_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type VARCHAR(50) NOT NULL,
                user_id INTEGER,
                admin_id INTEGER,
                message TEXT NOT NULL,
                severity VARCHAR(20) DEFAULT 'info',
                extra_data TEXT,
                ip_address VARCHAR(45),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table subscription_plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                predictions_per_day INTEGER DEFAULT 3,
                duration_days INTEGER NOT NULL,
                duration_type VARCHAR(20) NOT NULL,
                price_fcfa REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table user_subscriptions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                auto_renew BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT
            )
        """)
        
        # Créer la table user_prediction_access
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_prediction_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prediction_id INTEGER NOT NULL,
                access_date DATE NOT NULL,
                accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                is_global BOOLEAN DEFAULT 0,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                priority VARCHAR(20) DEFAULT 'normal',
                notification_type VARCHAR(50) DEFAULT 'info',
                display_duration INTEGER DEFAULT 5000,
                is_read BOOLEAN DEFAULT 0,
                read_at DATETIME,
                expires_at DATETIME,
                created_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                channels TEXT
            )
        """)
        
        # Créer la table persistent_sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persistent_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                session_data TEXT,
                expires_at DATETIME NOT NULL,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table backup_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_type VARCHAR(20) NOT NULL,
                backup_path VARCHAR(500) NOT NULL,
                file_size BIGINT,
                status VARCHAR(20) DEFAULT 'success',
                error_message TEXT,
                tables_backed_up TEXT,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table prediction_schedules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                predictions_per_day INTEGER DEFAULT 3,
                publication_times TEXT,
                publication_delays TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) DEFAULT 'warning',
                message TEXT NOT NULL,
                prediction_id INTEGER,
                match_id INTEGER,
                is_acknowledged BOOLEAN DEFAULT 0,
                acknowledged_by INTEGER,
                acknowledged_at DATETIME,
                extra_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Créer la table access_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                match_id INTEGER,
                prediction_id INTEGER,
                subscription_plan VARCHAR(20),
                ip_address VARCHAR(45),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT
            )
        """)
        
        # Créer la table matches_archive
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER UNIQUE NOT NULL,
                jeu VARCHAR(50) NOT NULL,
                mode VARCHAR(50),
                ligue VARCHAR(200) NOT NULL,
                equipe_1 VARCHAR(200) NOT NULL,
                equipe_2 VARCHAR(200) NOT NULL,
                date_heure_match DATETIME NOT NULL,
                cote_1 REAL,
                cote_X REAL,
                cote_2 REAL,
                score_final_equipe_1 INTEGER,
                score_final_equipe_2 INTEGER,
                resultat_reel VARCHAR(50),
                statut_final VARCHAR(50) DEFAULT 'en_cours',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archived_by INTEGER,
                is_locked BOOLEAN DEFAULT 0,
                extra_data TEXT
            )
        """)
        
        # Créer la table predictions_archive
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                prediction_id INTEGER,
                consensus_type VARCHAR(50) NOT NULL,
                choix TEXT NOT NULL,
                probabilite REAL NOT NULL,
                confiance REAL NOT NULL,
                vote_statistique BOOLEAN DEFAULT 0,
                vote_cotes BOOLEAN DEFAULT 0,
                vote_simulation BOOLEAN DEFAULT 0,
                vote_forme BOOLEAN DEFAULT 0,
                consensus BOOLEAN DEFAULT 0,
                resultat_reel VARCHAR(50),
                prediction_correcte BOOLEAN,
                ecart_probabilite REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                finalized_at DATETIME,
                extra_data TEXT
            )
        """)
        
        # Créer la table model_performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_debut DATETIME NOT NULL,
                date_fin DATETIME NOT NULL,
                total_predictions INTEGER DEFAULT 0,
                predictions_correctes INTEGER DEFAULT 0,
                taux_reussite REAL,
                taux_reussite_statistique REAL,
                taux_reussite_cotes REAL,
                taux_reussite_simulation REAL,
                taux_reussite_forme REAL,
                taux_reussite_consensus REAL,
                moyenne_confiance REAL,
                moyenne_probabilite REAL,
                ecart_moyen_probabilite REAL,
                taux_reussite_1x2 REAL,
                taux_reussite_alternatifs REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT
            )
        """)
        
        # Créer la table anomaly_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                prediction_archive_id INTEGER,
                anomaly_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) DEFAULT 'warning',
                description TEXT NOT NULL,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                context_data TEXT,
                is_resolved BOOLEAN DEFAULT 0,
                resolved_by INTEGER,
                resolved_at DATETIME,
                resolution_notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("Base de donnees initialisee avec succes!")
        print("Toutes les tables ont ete creees.")
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'initialisation: {e}")
        return False

if __name__ == "__main__":
    print("Initialisation de la base de donnees ORACXPRED")
    print("=" * 50)
    
    if init_database():
        print("\nBase de donnees prete pour l'utilisation!")
        print("Vous pouvez maintenant creer l'administrateur.")
    else:
        print("\nEchec de l'initialisation")
        sys.exit(1)
