#!/usr/bin/env python3
"""
🎲 SYSTÈME AVANCÉ POUR PARIS ALTERNATIFS
=======================================
Système spécialisé dans l'analyse approfondie des paris alternatifs
"""

import random
import math
from datetime import datetime

class SystemePredictionParisAlternatifsAvance:
    """🚀 SYSTÈME AVANCÉ SPÉCIALISÉ PARIS ALTERNATIFS"""
    
    def __init__(self, team1, team2, league, paris_alternatifs, score1, score2, minute):
        self.team1 = team1
        self.team2 = team2
        self.league = league
        self.paris_alternatifs = paris_alternatifs or []
        self.score1 = score1
        self.score2 = score2
        self.minute = minute
        self.version = "ALTERNATIFS-AVANCE-2024"
        
    def generer_analyse_complete(self):
        """🎯 ANALYSE COMPLÈTE DES PARIS ALTERNATIFS"""
        
        analyses = []
        
        for pari in self.paris_alternatifs:
            analyse = self._analyser_pari_en_profondeur(pari)
            analyses.append(analyse)
        
        # Tri par potentiel de gain
        analyses.sort(key=lambda x: x['potentiel_gain'], reverse=True)
        
        return {
            'analyses_detaillees': analyses,
            'top_3_recommandations': analyses[:3],
            'statistiques': self._generer_statistiques(analyses),
            'strategie_globale': self._generer_strategie_globale(analyses)
        }
    
    def _analyser_pari_en_profondeur(self, pari):
        """🔍 ANALYSE APPROFONDIE D'UN PARI ALTERNATIF"""
        
        nom = pari.get('nom', 'Pari inconnu')
        cote = float(pari.get('cote', 2.0))
        
        # Analyse multi-facteurs
        facteurs = {
            'contexte_match': self._analyser_contexte_match(nom),
            'historique_equipes': self._analyser_historique_equipes(nom),
            'tendances_temporelles': self._analyser_tendances_temporelles(nom),
            'facteur_ligue': self._analyser_facteur_ligue(nom),
            'momentum_actuel': self._analyser_momentum_actuel(nom)
        }
        
        # Score composite
        score_composite = sum(facteurs.values()) / len(facteurs)
        
        # Calcul du potentiel de gain
        probabilite_estimee = score_composite / 100
        probabilite_cote = 1 / cote
        value = (probabilite_estimee - probabilite_cote) / probabilite_cote * 100
        
        potentiel_gain = value * (cote - 1) if value > 0 else 0
        
        return {
            'pari': nom,
            'cote': cote,
            'score_composite': round(score_composite, 1),
            'facteurs': facteurs,
            'probabilite_estimee': round(probabilite_estimee * 100, 1),
            'value': round(value, 2),
            'potentiel_gain': round(potentiel_gain, 2),
            'recommandation': self._generer_recommandation(score_composite, value, cote),
            'risque': self._evaluer_risque(score_composite, cote)
        }
    
    def _analyser_contexte_match(self, nom_pari):
        """⚽ ANALYSE DU CONTEXTE ACTUEL DU MATCH"""
        
        score_base = 50
        total_buts = self.score1 + self.score2
        
        # Analyse selon le type de pari
        if 'Plus de' in nom_pari and 'buts' in nom_pari:
            if '2.5' in nom_pari:
                if total_buts >= 3:
                    score_base = 95
                elif total_buts == 2 and self.minute < 70:
                    score_base = 80
                elif total_buts == 1 and self.minute < 45:
                    score_base = 65
                elif total_buts == 0 and self.minute > 60:
                    score_base = 25
            
            elif '1.5' in nom_pari:
                if total_buts >= 2:
                    score_base = 95
                elif total_buts == 1 and self.minute < 70:
                    score_base = 75
                elif total_buts == 0 and self.minute > 70:
                    score_base = 20
        
        elif 'Moins de' in nom_pari and 'buts' in nom_pari:
            if '2.5' in nom_pari:
                if total_buts >= 3:
                    score_base = 5
                elif total_buts == 2 and self.minute > 75:
                    score_base = 70
                elif total_buts <= 1:
                    score_base = 80
        
        elif 'PAIR' in nom_pari.upper():
            if total_buts % 2 == 0:
                score_base = 70 if self.minute > 70 else 55
            else:
                score_base = 45 if self.minute > 80 else 60
        
        elif 'IMPAIR' in nom_pari.upper():
            if total_buts % 2 == 1:
                score_base = 70 if self.minute > 70 else 55
            else:
                score_base = 45 if self.minute > 80 else 60
        
        return score_base
    
    def _analyser_historique_equipes(self, nom_pari):
        """📊 ANALYSE BASÉE SUR L'HISTORIQUE DES ÉQUIPES"""
        
        score_base = 50
        
        # Équipes offensives connues
        equipes_offensives = {
            'manchester city': 85, 'psg': 82, 'bayern munich': 84,
            'real madrid': 83, 'barcelona': 81, 'liverpool': 80,
            'borussia dortmund': 78, 'ajax': 75, 'atalanta': 85
        }
        
        # Équipes défensives
        equipes_defensives = {
            'atletico madrid': 75, 'juventus': 70, 'chelsea': 72,
            'inter milan': 74, 'ac milan': 71
        }
        
        team1_lower = self.team1.lower()
        team2_lower = self.team2.lower()
        
        # Bonus pour équipes offensives
        if 'Plus de' in nom_pari and 'buts' in nom_pari:
            for equipe, bonus in equipes_offensives.items():
                if equipe in team1_lower or equipe in team2_lower:
                    score_base += (bonus - 50) * 0.3
        
        # Malus pour équipes défensives
        elif 'Moins de' in nom_pari and 'buts' in nom_pari:
            for equipe, bonus in equipes_defensives.items():
                if equipe in team1_lower or equipe in team2_lower:
                    score_base += (bonus - 50) * 0.2
        
        return min(score_base, 90)
    
    def _analyser_tendances_temporelles(self, nom_pari):
        """⏰ ANALYSE DES TENDANCES TEMPORELLES"""
        
        score_base = 50
        
        # Patterns selon la minute
        if self.minute <= 15:
            if 'premières' in nom_pari:
                score_base += 20
        elif 15 < self.minute <= 30:
            score_base += 5  # Période d'observation
        elif 30 < self.minute <= 45:
            if 'Plus de' in nom_pari:
                score_base += 10  # Fin de première mi-temps active
        elif 45 < self.minute <= 60:
            score_base += 8  # Début de seconde mi-temps
        elif 60 < self.minute <= 75:
            if 'Plus de' in nom_pari:
                score_base += 15  # Période cruciale
        elif self.minute > 75:
            if 'dernières' in nom_pari:
                score_base += 25
            elif 'Plus de' in nom_pari:
                score_base += 20  # Rush final
        
        return score_base
    
    def _analyser_facteur_ligue(self, nom_pari):
        """🏆 ANALYSE DU FACTEUR LIGUE"""
        
        score_base = 50
        league_lower = self.league.lower()
        
        # Ligues offensives
        if 'bundesliga' in league_lower or 'eredivisie' in league_lower:
            if 'Plus de' in nom_pari and 'buts' in nom_pari:
                score_base += 15
        
        # Ligues défensives
        elif 'serie a' in league_lower:
            if 'Moins de' in nom_pari and 'buts' in nom_pari:
                score_base += 10
        
        # Champions League (plus tactique)
        elif 'champions' in league_lower:
            if 'Moins de' in nom_pari:
                score_base += 8
            else:
                score_base -= 5
        
        return score_base
    
    def _analyser_momentum_actuel(self, nom_pari):
        """⚡ ANALYSE DU MOMENTUM ACTUEL"""
        
        score_base = 50
        total_buts = self.score1 + self.score2
        
        # Momentum offensif
        if total_buts >= 2 and self.minute < 60:
            if 'Plus de' in nom_pari:
                score_base += 20
        
        # Momentum défensif
        elif total_buts == 0 and self.minute > 45:
            if 'Moins de' in nom_pari:
                score_base += 15
        
        # Match équilibré
        elif abs(self.score1 - self.score2) <= 1:
            score_base += 5
        
        return score_base
    
    def _generer_recommandation(self, score, value, cote):
        """💡 GÉNÈRE UNE RECOMMANDATION"""
        
        if score >= 80 and value > 15:
            return "🔥 MISE FORTE RECOMMANDÉE - Excellente opportunité"
        elif score >= 70 and value > 10:
            return "⚡ MISE RECOMMANDÉE - Bonne opportunité"
        elif score >= 60 and value > 5:
            return "✨ MISE MODÉRÉE - Opportunité correcte"
        elif score >= 50:
            return "💫 MISE PRUDENTE - Risque modéré"
        else:
            return "❌ ÉVITER - Risque trop élevé"
    
    def _evaluer_risque(self, score, cote):
        """⚠️ ÉVALUE LE NIVEAU DE RISQUE"""
        
        if score >= 75 and cote < 2.5:
            return "FAIBLE"
        elif score >= 60 and cote < 3.5:
            return "MODÉRÉ"
        elif score >= 45:
            return "ÉLEVÉ"
        else:
            return "TRÈS ÉLEVÉ"
    
    def _generer_statistiques(self, analyses):
        """📈 GÉNÈRE DES STATISTIQUES GLOBALES"""
        
        if not analyses:
            return {}
        
        return {
            'total_paris_analyses': len(analyses),
            'score_moyen': round(sum(a['score_composite'] for a in analyses) / len(analyses), 1),
            'opportunities_positives': len([a for a in analyses if a['value'] > 0]),
            'potentiel_gain_total': round(sum(a['potentiel_gain'] for a in analyses), 2),
            'meilleure_value': max(a['value'] for a in analyses),
            'risque_moyen': self._calculer_risque_moyen(analyses)
        }
    
    def _calculer_risque_moyen(self, analyses):
        """📊 CALCULE LE RISQUE MOYEN"""
        
        risques = {'FAIBLE': 1, 'MODÉRÉ': 2, 'ÉLEVÉ': 3, 'TRÈS ÉLEVÉ': 4}
        total = sum(risques.get(a['risque'], 2) for a in analyses)
        moyenne = total / len(analyses)
        
        if moyenne <= 1.5:
            return "FAIBLE"
        elif moyenne <= 2.5:
            return "MODÉRÉ"
        elif moyenne <= 3.5:
            return "ÉLEVÉ"
        else:
            return "TRÈS ÉLEVÉ"
    
    def _generer_strategie_globale(self, analyses):
        """🎯 GÉNÈRE UNE STRATÉGIE GLOBALE"""
        
        if not analyses:
            return "Aucune stratégie disponible"
        
        opportunities = [a for a in analyses if a['value'] > 10]
        
        if len(opportunities) >= 3:
            return "🔥 STRATÉGIE AGRESSIVE - Plusieurs excellentes opportunités détectées"
        elif len(opportunities) >= 1:
            return "⚡ STRATÉGIE SÉLECTIVE - Focus sur les meilleures opportunités"
        else:
            return "💫 STRATÉGIE PRUDENTE - Attendre de meilleures conditions"
