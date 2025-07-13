#!/usr/bin/env python3
"""
🤖 BOTS SPÉCIALISÉS PARIS ALTERNATIFS UNIQUEMENT
===============================================
Tous les bots se concentrent uniquement sur :
- Totaux (Plus/Moins de X buts)
- Pair/Impair
- Handicaps
- Cotes entre 1.399 et 3.0
"""

import random
import math
from datetime import datetime

def systeme_unifie_alternatifs_only(team1, team2, league, paris_cotes_valides, score1, score2, minute):
    """🎲 BOT 1: SYSTÈME UNIFIÉ ALTERNATIFS UNIQUEMENT"""
    
    print(f"🎲 BOT UNIFIÉ - Analyse de {len(paris_cotes_valides)} paris alternatifs")
    
    paris_recommandes = []
    
    for pari in paris_cotes_valides:
        confiance = _analyser_pari_unifie(pari, team1, team2, league, score1, score2, minute)
        
        if confiance >= 60:  # Seuil de recommandation
            paris_recommandes.append({
                'nom': pari['nom'],
                'cote': pari['cote'],
                'confiance': confiance,
                'type': _detecter_type_pari(pari['nom']),
                'source': 'BOT_UNIFIE'
            })
    
    # Tri par confiance
    paris_recommandes.sort(key=lambda x: x['confiance'], reverse=True)
    
    return {
        'bot_name': 'SYSTÈME UNIFIÉ ALTERNATIFS',
        'paris_recommandes': paris_recommandes[:3],  # Top 3
        'confiance_globale': max([p['confiance'] for p in paris_recommandes], default=0),
        'specialite': 'ANALYSE UNIFIÉE ALTERNATIFS'
    }

def systeme_ia_alternatifs_only(team1, team2, league, paris_cotes_valides, score1, score2, minute):
    """🤖 BOT 2: IA SPÉCIALISÉE ALTERNATIFS UNIQUEMENT"""
    
    print(f"🤖 BOT IA - Analyse intelligente de {len(paris_cotes_valides)} paris")
    
    paris_recommandes = []
    
    for pari in paris_cotes_valides:
        confiance = _analyser_pari_ia(pari, team1, team2, league, score1, score2, minute)
        
        if confiance >= 65:  # Seuil IA plus strict
            paris_recommandes.append({
                'nom': pari['nom'],
                'cote': pari['cote'],
                'confiance': confiance,
                'type': _detecter_type_pari(pari['nom']),
                'source': 'BOT_IA'
            })
    
    paris_recommandes.sort(key=lambda x: x['confiance'], reverse=True)
    
    return {
        'bot_name': 'IA SPÉCIALISÉE ALTERNATIFS',
        'paris_recommandes': paris_recommandes[:3],
        'confiance_globale': max([p['confiance'] for p in paris_recommandes], default=0),
        'specialite': 'INTELLIGENCE ARTIFICIELLE ALTERNATIFS'
    }

def systeme_probabilites_alternatifs_only(paris_cotes_valides, score1, score2, minute):
    """📊 BOT 3: PROBABILITÉS ALTERNATIVES UNIQUEMENT"""
    
    print(f"📊 BOT PROBABILITÉS - Calcul probabiliste de {len(paris_cotes_valides)} paris")
    
    paris_recommandes = []
    
    for pari in paris_cotes_valides:
        confiance = _analyser_pari_probabilites(pari, score1, score2, minute)
        
        if confiance >= 55:  # Seuil probabilités
            paris_recommandes.append({
                'nom': pari['nom'],
                'cote': pari['cote'],
                'confiance': confiance,
                'type': _detecter_type_pari(pari['nom']),
                'source': 'BOT_PROBABILITES'
            })
    
    paris_recommandes.sort(key=lambda x: x['confiance'], reverse=True)
    
    return {
        'bot_name': 'PROBABILITÉS ALTERNATIVES',
        'paris_recommandes': paris_recommandes[:3],
        'confiance_globale': max([p['confiance'] for p in paris_recommandes], default=0),
        'specialite': 'CALCULS PROBABILISTES ALTERNATIFS'
    }

def systeme_value_betting_alternatifs_only(paris_cotes_valides, team1, team2, league):
    """💰 BOT 4: VALUE BETTING ALTERNATIFS UNIQUEMENT"""
    
    print(f"💰 BOT VALUE - Détection de value sur {len(paris_cotes_valides)} paris")
    
    paris_recommandes = []
    
    for pari in paris_cotes_valides:
        value_score = _calculer_value_pari(pari, team1, team2, league)
        
        if value_score >= 10:  # Value positive de 10%+
            confiance = min(50 + value_score, 95)  # Confiance basée sur la value
            
            paris_recommandes.append({
                'nom': pari['nom'],
                'cote': pari['cote'],
                'confiance': confiance,
                'value': value_score,
                'type': _detecter_type_pari(pari['nom']),
                'source': 'BOT_VALUE'
            })
    
    paris_recommandes.sort(key=lambda x: x['value'], reverse=True)
    
    return {
        'bot_name': 'VALUE BETTING ALTERNATIFS',
        'paris_recommandes': paris_recommandes[:3],
        'confiance_globale': max([p['confiance'] for p in paris_recommandes], default=0),
        'specialite': 'DÉTECTION VALUE ALTERNATIFS',
        'opportunities': paris_recommandes  # Compatibilité
    }

def systeme_statistique_alternatifs_only(paris_cotes_valides, team1, team2, league, score1, score2, minute):
    """📈 BOT 5: ANALYSE STATISTIQUE ALTERNATIFS UNIQUEMENT"""
    
    print(f"📈 BOT STATS - Analyse statistique de {len(paris_cotes_valides)} paris")
    
    paris_recommandes = []
    
    for pari in paris_cotes_valides:
        confiance = _analyser_pari_statistique(pari, team1, team2, league, score1, score2, minute)
        
        if confiance >= 58:  # Seuil statistique
            paris_recommandes.append({
                'nom': pari['nom'],
                'cote': pari['cote'],
                'confiance': confiance,
                'type': _detecter_type_pari(pari['nom']),
                'source': 'BOT_STATS'
            })
    
    paris_recommandes.sort(key=lambda x: x['confiance'], reverse=True)
    
    return {
        'bot_name': 'ANALYSE STATISTIQUE ALTERNATIFS',
        'paris_recommandes': paris_recommandes[:3],
        'confiance_globale': max([p['confiance'] for p in paris_recommandes], default=0),
        'specialite': 'STATISTIQUES AVANCÉES ALTERNATIFS'
    }

# ========== FONCTIONS D'ANALYSE SPÉCIALISÉES ==========

def _detecter_type_pari(nom_pari):
    """🔍 DÉTECTE LE TYPE D'UN PARI"""
    nom_lower = nom_pari.lower()
    
    if 'total' in nom_lower and ('plus' in nom_lower or 'moins' in nom_lower):
        return 'TOTAL_BUTS'
    elif 'handicap' in nom_lower:
        return 'HANDICAP'
    elif 'pair' in nom_lower or 'impair' in nom_lower:
        return 'PAIR_IMPAIR'
    elif 'corner' in nom_lower:
        return 'CORNERS'
    else:
        return 'AUTRE'

def _analyser_pari_unifie(pari, team1, team2, league, score1, score2, minute):
    """🎲 ANALYSE UNIFIÉE D'UN PARI"""
    confiance = 50
    nom = pari['nom'].lower()
    cote = float(pari['cote'])
    
    # Bonus équipes offensives
    equipes_offensives = ['arsenal', 'manchester city', 'psg', 'real madrid', 'barcelona']
    if any(eq in team1.lower() for eq in equipes_offensives):
        confiance += 8
    if any(eq in team2.lower() for eq in equipes_offensives):
        confiance += 8
    
    # Analyse selon le type
    if 'plus' in nom and 'total' in nom:
        if score1 + score2 >= 2 and minute < 60:
            confiance += 15
    elif 'moins' in nom and 'total' in nom:
        if score1 + score2 <= 1 and minute > 60:
            confiance += 15
    
    # Bonus cote attractive
    if 1.8 <= cote <= 2.5:
        confiance += 10
    
    return min(confiance, 95)

def _analyser_pari_ia(pari, team1, team2, league, score1, score2, minute):
    """🤖 ANALYSE IA D'UN PARI"""
    confiance = 55
    nom = pari['nom'].lower()
    
    # IA analyse contextuelle
    total_buts = score1 + score2
    
    if 'total' in nom:
        if 'plus' in nom:
            # IA prédit plus de buts
            if total_buts >= 1 and minute < 45:
                confiance += 20
            elif total_buts == 0 and minute > 70:
                confiance -= 20
        elif 'moins' in nom:
            # IA prédit moins de buts
            if total_buts <= 1 and minute > 60:
                confiance += 18
    
    # IA analyse des équipes
    if 'arsenal' in team1.lower() or 'arsenal' in team2.lower():
        if 'plus' in nom:
            confiance += 12  # Arsenal offensif
    
    return min(confiance, 95)

def _analyser_pari_probabilites(pari, score1, score2, minute):
    """📊 ANALYSE PROBABILISTE D'UN PARI"""
    confiance = 50
    nom = pari['nom'].lower()
    cote = float(pari['cote'])
    
    # Probabilité implicite de la cote
    prob_implicite = (1 / cote) * 100
    
    # Estimation probabiliste
    if 'total' in nom:
        if 'plus' in nom:
            # Probabilité basée sur le contexte
            if score1 + score2 >= 2:
                prob_estimee = 75
            elif score1 + score2 == 1:
                prob_estimee = 60
            else:
                prob_estimee = 45
        else:
            prob_estimee = 100 - prob_estimee if 'prob_estimee' in locals() else 55
    else:
        prob_estimee = 50
    
    # Confiance basée sur l'écart
    if prob_estimee > prob_implicite:
        confiance += (prob_estimee - prob_implicite) * 0.5
    
    return min(confiance, 95)

def _calculer_value_pari(pari, team1, team2, league):
    """💰 CALCULE LA VALUE D'UN PARI"""
    cote = float(pari['cote'])
    nom = pari['nom'].lower()
    
    # Probabilité estimée
    if 'total' in nom:
        if 'moins' in nom:
            prob_estimee = 65  # Généralement plus probable
        else:
            prob_estimee = 45
    elif 'handicap' in nom:
        prob_estimee = 55
    else:
        prob_estimee = 50
    
    # Calcul de la value
    prob_implicite = (1 / cote) * 100
    value = ((prob_estimee - prob_implicite) / prob_implicite) * 100
    
    return max(value, -50)  # Limiter les values négatives

def _analyser_pari_statistique(pari, team1, team2, league, score1, score2, minute):
    """📈 ANALYSE STATISTIQUE D'UN PARI"""
    confiance = 52
    nom = pari['nom'].lower()
    
    # Statistiques basées sur le contexte
    total_buts = score1 + score2
    
    # Tendances statistiques
    if 'total' in nom:
        if minute <= 30:
            if 'plus' in nom:
                confiance += 8  # Début de match favorable aux buts
            else:
                confiance += 3
        elif minute > 70:
            if 'moins' in nom and total_buts <= 2:
                confiance += 15  # Fin de match avec peu de buts
    
    # Statistiques des équipes (simulées)
    hash_teams = hash(team1 + team2) % 100
    if hash_teams > 60:
        confiance += 8  # "Statistiques favorables"
    
    return min(confiance, 95)
