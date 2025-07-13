#!/usr/bin/env python3
"""
🎯 MAÎTRE DES PRONOSTICS
=======================
Bot central qui reçoit toutes les décisions des bots spécialisés
et prend la décision finale pour les paris alternatifs
"""

import random
from datetime import datetime

class MaitreDesPronostics:
    """🎯 MAÎTRE CENTRAL DES PRONOSTICS ALTERNATIFS"""
    
    def __init__(self):
        self.version = "MAITRE-PRONOSTICS-2024"
        self.decisions_historiques = []
        self.precision_moyenne = 0.0
        
    def analyser_decisions_bots(self, decisions_bots, team1, team2, league, contexte_temps_reel=None):
        """🎯 ANALYSE TOUTES LES DÉCISIONS DES BOTS ET PREND LA DÉCISION FINALE"""
        
        print(f"🎯 MAÎTRE DES PRONOSTICS - Analyse de {len(decisions_bots)} bots")
        
        # Validation des cotes (1.399 - 3.0)
        decisions_valides = self._filtrer_cotes_valides(decisions_bots)
        
        if not decisions_valides:
            return self._generer_decision_aucune()
        
        # Analyse des consensus
        consensus = self._analyser_consensus(decisions_valides)
        
        # Calcul de la confiance globale
        confiance_globale = self._calculer_confiance_globale(decisions_valides, consensus)
        
        # Sélection de la meilleure décision
        decision_finale = self._selectionner_meilleure_decision(decisions_valides, consensus, confiance_globale)
        
        # Génération du rapport final
        rapport = self._generer_rapport_final(decision_finale, decisions_valides, consensus, confiance_globale, team1, team2)
        
        # Sauvegarde pour apprentissage
        self._sauvegarder_decision(rapport, team1, team2, league)
        
        return rapport
    
    def _filtrer_cotes_valides(self, decisions_bots):
        """💰 FILTRE LES DÉCISIONS AVEC COTES ENTRE 1.399 ET 3.0"""
        
        decisions_valides = []
        
        for bot_name, decision in decisions_bots.items():
            if isinstance(decision, dict) and 'paris_recommandes' in decision:
                paris_valides = []
                
                for pari in decision['paris_recommandes']:
                    try:
                        cote = float(pari.get('cote', 0))
                        if 1.399 <= cote <= 3.0:
                            paris_valides.append(pari)
                            print(f"  ✅ {bot_name}: {pari['nom']} | Cote: {cote} | Confiance: {pari.get('confiance', 0)}%")
                        else:
                            print(f"  ❌ {bot_name}: {pari['nom']} | Cote: {cote} (hors limites)")
                    except:
                        continue
                
                if paris_valides:
                    decisions_valides.append({
                        'bot': bot_name,
                        'paris': paris_valides,
                        'confiance_bot': decision.get('confiance_globale', 50)
                    })
        
        print(f"💰 {len(decisions_valides)} bots avec décisions valides")
        return decisions_valides
    
    def _analyser_consensus(self, decisions_valides):
        """🤝 ANALYSE LE CONSENSUS ENTRE LES BOTS"""
        
        # Comptage des types de paris
        types_paris = {}
        paris_specifiques = {}
        
        for decision in decisions_valides:
            for pari in decision['paris']:
                # Type de pari
                type_pari = self._detecter_type_pari(pari['nom'])
                if type_pari not in types_paris:
                    types_paris[type_pari] = []
                types_paris[type_pari].append({
                    'bot': decision['bot'],
                    'pari': pari,
                    'confiance': pari.get('confiance', 50)
                })
                
                # Pari spécifique
                nom_pari = pari['nom']
                if nom_pari not in paris_specifiques:
                    paris_specifiques[nom_pari] = []
                paris_specifiques[nom_pari].append({
                    'bot': decision['bot'],
                    'pari': pari,
                    'confiance': pari.get('confiance', 50)
                })
        
        # Calcul des consensus
        consensus = {
            'types_populaires': sorted(types_paris.items(), key=lambda x: len(x[1]), reverse=True),
            'paris_populaires': sorted(paris_specifiques.items(), key=lambda x: len(x[1]), reverse=True),
            'nb_bots_total': len(decisions_valides)
        }
        
        print(f"🤝 CONSENSUS ANALYSÉ:")
        for type_pari, votes in consensus['types_populaires'][:3]:
            print(f"  📊 {type_pari}: {len(votes)} bots")
        
        return consensus
    
    def _detecter_type_pari(self, nom_pari):
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
        elif 'mi-temps' in nom_lower:
            return 'MI_TEMPS'
        else:
            return 'AUTRE'
    
    def _calculer_confiance_globale(self, decisions_valides, consensus):
        """📊 CALCULE LA CONFIANCE GLOBALE"""
        
        if not decisions_valides:
            return 0
        
        # Confiance basée sur le consensus
        confiance_consensus = 0
        if consensus['paris_populaires']:
            meilleur_consensus = consensus['paris_populaires'][0]
            nb_votes = len(meilleur_consensus[1])
            confiance_consensus = min((nb_votes / consensus['nb_bots_total']) * 100, 90)
        
        # Confiance moyenne des bots
        confiance_moyenne = sum(d['confiance_bot'] for d in decisions_valides) / len(decisions_valides)
        
        # Confiance finale (pondérée)
        confiance_finale = (confiance_consensus * 0.6) + (confiance_moyenne * 0.4)
        
        print(f"📊 CONFIANCE GLOBALE: {confiance_finale:.1f}% (Consensus: {confiance_consensus:.1f}%, Moyenne: {confiance_moyenne:.1f}%)")
        
        return confiance_finale
    
    def _selectionner_meilleure_decision(self, decisions_valides, consensus, confiance_globale):
        """🎯 SÉLECTIONNE LA MEILLEURE DÉCISION"""
        
        if not consensus['paris_populaires']:
            return None
        
        # Prendre le pari avec le plus de consensus
        meilleur_pari_data = consensus['paris_populaires'][0]
        nom_pari = meilleur_pari_data[0]
        votes = meilleur_pari_data[1]
        
        # Calculer la confiance moyenne pour ce pari
        confiance_pari = sum(v['confiance'] for v in votes) / len(votes)
        
        # Prendre les détails du pari le mieux noté
        meilleur_vote = max(votes, key=lambda x: x['confiance'])
        pari_details = meilleur_vote['pari']
        
        decision = {
            'nom': nom_pari,
            'cote': pari_details['cote'],
            'type': self._detecter_type_pari(nom_pari),
            'confiance': confiance_pari,
            'nb_bots_accord': len(votes),
            'bots_supporters': [v['bot'] for v in votes],
            'details': pari_details
        }
        
        print(f"🎯 DÉCISION SÉLECTIONNÉE: {nom_pari}")
        print(f"  💰 Cote: {decision['cote']}")
        print(f"  🤝 {decision['nb_bots_accord']} bots d'accord")
        print(f"  📊 Confiance: {decision['confiance']:.1f}%")
        
        return decision
    
    def _generer_decision_aucune(self):
        """❌ GÉNÈRE UNE DÉCISION QUAND AUCUN PARI VALIDE"""
        
        return {
            'decision_finale': {
                'action': 'AUCUN_PARI',
                'raison': 'Aucun pari avec cotes valides (1.399-3.0)',
                'confiance': 0,
                'recommandation': 'ATTENDRE DE MEILLEURES OPPORTUNITÉS'
            },
            'analyse_bots': {
                'nb_bots_consultes': 0,
                'consensus': 'AUCUN',
                'paris_analyses': 0
            },
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'version': self.version,
                'type': 'AUCUNE_DECISION'
            }
        }
    
    def _generer_rapport_final(self, decision, decisions_valides, consensus, confiance_globale, team1, team2):
        """📋 GÉNÈRE LE RAPPORT FINAL DU MAÎTRE"""
        
        if not decision:
            return self._generer_decision_aucune()
        
        # Détermination de l'action
        if confiance_globale >= 80:
            action = "MISE FORTE RECOMMANDÉE"
            niveau = "🔥 TRÈS ÉLEVÉE"
        elif confiance_globale >= 70:
            action = "MISE RECOMMANDÉE"
            niveau = "⚡ ÉLEVÉE"
        elif confiance_globale >= 60:
            action = "MISE MODÉRÉE"
            niveau = "✨ MODÉRÉE"
        elif confiance_globale >= 50:
            action = "MISE PRUDENTE"
            niveau = "💫 FAIBLE"
        else:
            action = "ÉVITER"
            niveau = "❌ TRÈS FAIBLE"
        
        rapport = {
            'decision_finale': {
                'pari_choisi': decision['nom'],
                'cote': decision['cote'],
                'type_pari': decision['type'],
                'action': action,
                'niveau_confiance': niveau,
                'confiance_numerique': round(confiance_globale, 1),
                'recommandation': f"MAÎTRE RECOMMANDE: {action}",
                'equipes': f"{team1} vs {team2}"
            },
            'analyse_bots': {
                'nb_bots_consultes': len(decisions_valides),
                'nb_bots_accord': decision['nb_bots_accord'],
                'consensus': f"{decision['nb_bots_accord']}/{len(decisions_valides)} bots",
                'bots_supporters': decision['bots_supporters'],
                'types_paris_analyses': len(consensus['types_populaires'])
            },
            'details_technique': {
                'confiance_pari': round(decision['confiance'], 1),
                'confiance_globale': round(confiance_globale, 1),
                'cote_valide': f"✅ {decision['cote']} (dans 1.399-3.0)",
                'type_detecte': decision['type']
            },
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'version': self.version,
                'maitre': 'MAÎTRE DES PRONOSTICS',
                'type': 'DECISION_FINALE'
            }
        }
        
        return rapport
    
    def _sauvegarder_decision(self, rapport, team1, team2, league):
        """💾 SAUVEGARDE LA DÉCISION POUR APPRENTISSAGE"""
        
        decision_data = {
            'match': f"{team1} vs {team2}",
            'league': league,
            'decision': rapport['decision_finale'],
            'timestamp': datetime.now().isoformat(),
            'confiance': rapport['decision_finale']['confiance_numerique']
        }
        
        self.decisions_historiques.append(decision_data)
        
        # Calcul de la précision moyenne
        if len(self.decisions_historiques) > 0:
            precision_totale = sum(d['confiance'] for d in self.decisions_historiques)
            self.precision_moyenne = precision_totale / len(self.decisions_historiques)
    
    def obtenir_statistiques_maitre(self):
        """📈 STATISTIQUES DU MAÎTRE DES PRONOSTICS"""
        
        return {
            'decisions_totales': len(self.decisions_historiques),
            'precision_moyenne': round(self.precision_moyenne, 2),
            'version': self.version,
            'specialite': 'PARIS ALTERNATIFS UNIQUEMENT',
            'cotes_acceptees': '1.399 - 3.0'
        }
