#!/usr/bin/env python3
"""
VÉRIFICATION DES STATISTIQUES - ORACXPRED
==================================
"""

import sqlite3

def check_stats():
    """Vérifie les statistiques des matchs collectés"""
    
    conn = sqlite3.connect("oracxpred.db")
    cursor = conn.cursor()
    
    # Total des matchs
    cursor.execute("SELECT COUNT(*) FROM collected_matches")
    total = cursor.fetchone()[0]
    print(f"Total matchs collectes: {total}")
    
    # Par jeu
    cursor.execute("SELECT jeu, COUNT(*) FROM collected_matches GROUP BY jeu")
    print("\nPar jeu:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # Par statut
    cursor.execute("SELECT statut, COUNT(*) FROM collected_matches GROUP BY statut")
    print("\nPar statut:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # Plus récents
    cursor.execute("SELECT equipe_domicile, equipe_exterieur, jeu, statut FROM collected_matches ORDER BY created_at DESC LIMIT 5")
    print("\nDerniers matchs:")
    for row in cursor.fetchall():
        print(f"  {row[0]} vs {row[1]} ({row[2]}) - {row[3]}")
    
    conn.close()

if __name__ == "__main__":
    check_stats()
