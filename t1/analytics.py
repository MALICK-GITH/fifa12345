"""
Module d'analyse des tendances et statistiques H2H
"""

from datetime import datetime, timedelta
import statistics
from collections import defaultdict

class TeamAnalytics:
    def __init__(self, db, Match, Team):
        self.db = db
        self.Match = Match
        self.Team = Team
    
    def get_team_recent_form(self, team_name, days=30, limit=10):
        """Analyse la forme récente d'une équipe"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Récupérer l'équipe
        team = self.Team.query.filter_by(name=team_name).first()
        if not team:
            return None
        
        # Récupérer les matchs récents
        recent_matches = self.Match.query.filter(
            self.db.or_(
                self.Match.home_team_id == team.id,
                self.Match.away_team_id == team.id
            ),
            self.Match.created_at >= cutoff_date,
            self.Match.status == 'Terminé'
        ).order_by(self.Match.created_at.desc()).limit(limit).all()
        
        if not recent_matches:
            return {
                'form_string': '',
                'form_score': 0.5,
                'matches_played': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_difference': 0,
                'points': 0,
                'avg_goals_for': 0,
                'avg_goals_against': 0
            }
        
        form_string = ""
        wins = draws = losses = 0
        goals_for = goals_against = 0
        
        for match in recent_matches:
            is_home = match.home_team_id == team.id
            team_score = match.home_score if is_home else match.away_score
            opponent_score = match.away_score if is_home else match.home_score
            
            goals_for += team_score
            goals_against += opponent_score
            
            if team_score > opponent_score:
                form_string += "W"
                wins += 1
            elif team_score == opponent_score:
                form_string += "D"
                draws += 1
            else:
                form_string += "L"
                losses += 1
        
        matches_played = len(recent_matches)
        points = wins * 3 + draws
        form_score = points / (matches_played * 3) if matches_played > 0 else 0.5
        
        return {
            'form_string': form_string,
            'form_score': form_score,
            'matches_played': matches_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goals_for - goals_against,
            'points': points,
            'avg_goals_for': goals_for / matches_played if matches_played > 0 else 0,
            'avg_goals_against': goals_against / matches_played if matches_played > 0 else 0
        }
    
    def get_head_to_head(self, team1_name, team2_name, limit=10):
        """Analyse l'historique face-à-face entre deux équipes"""
        team1 = self.Team.query.filter_by(name=team1_name).first()
        team2 = self.Team.query.filter_by(name=team2_name).first()
        
        if not team1 or not team2:
            return None
        
        # Récupérer les matchs entre ces deux équipes
        h2h_matches = self.Match.query.filter(
            self.db.or_(
                self.db.and_(
                    self.Match.home_team_id == team1.id,
                    self.Match.away_team_id == team2.id
                ),
                self.db.and_(
                    self.Match.home_team_id == team2.id,
                    self.Match.away_team_id == team1.id
                )
            ),
            self.Match.status == 'Terminé'
        ).order_by(self.Match.created_at.desc()).limit(limit).all()
        
        if not h2h_matches:
            return {
                'matches_played': 0,
                'team1_wins': 0,
                'team2_wins': 0,
                'draws': 0,
                'team1_goals': 0,
                'team2_goals': 0,
                'avg_goals_per_match': 0,
                'recent_results': []
            }
        
        team1_wins = team2_wins = draws = 0
        team1_goals = team2_goals = 0
        recent_results = []
        
        for match in h2h_matches:
            is_team1_home = match.home_team_id == team1.id
            team1_score = match.home_score if is_team1_home else match.away_score
            team2_score = match.away_score if is_team1_home else match.home_score
            
            team1_goals += team1_score
            team2_goals += team2_score
            
            if team1_score > team2_score:
                team1_wins += 1
                result = f"{team1_name} {team1_score}-{team2_score} {team2_name}"
            elif team1_score == team2_score:
                draws += 1
                result = f"{team1_name} {team1_score}-{team2_score} {team2_name} (Nul)"
            else:
                team2_wins += 1
                result = f"{team1_name} {team1_score}-{team2_score} {team2_name}"
            
            recent_results.append({
                'date': match.created_at.strftime('%d/%m/%Y'),
                'result': result,
                'team1_score': team1_score,
                'team2_score': team2_score
            })
        
        matches_played = len(h2h_matches)
        total_goals = team1_goals + team2_goals
        
        return {
            'matches_played': matches_played,
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'draws': draws,
            'team1_goals': team1_goals,
            'team2_goals': team2_goals,
            'avg_goals_per_match': total_goals / matches_played if matches_played > 0 else 0,
            'recent_results': recent_results
        }
    
    def get_league_performance(self, league_name, days=30):
        """Analyse les performances par ligue"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        matches = self.Match.query.filter(
            self.Match.league == league_name,
            self.Match.created_at >= cutoff_date,
            self.Match.status == 'Terminé'
        ).all()
        
        if not matches:
            return None
        
        team_stats = defaultdict(lambda: {
            'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
            'goals_for': 0, 'goals_against': 0, 'points': 0
        })
        
        total_goals = 0
        total_matches = len(matches)
        
        for match in matches:
            home_team = match.home_team.name
            away_team = match.away_team.name
            home_score = match.home_score
            away_score = match.away_score
            
            total_goals += home_score + away_score
            
            # Stats équipe domicile
            team_stats[home_team]['matches'] += 1
            team_stats[home_team]['goals_for'] += home_score
            team_stats[home_team]['goals_against'] += away_score
            
            # Stats équipe extérieur
            team_stats[away_team]['matches'] += 1
            team_stats[away_team]['goals_for'] += away_score
            team_stats[away_team]['goals_against'] += home_score
            
            if home_score > away_score:
                team_stats[home_team]['wins'] += 1
                team_stats[home_team]['points'] += 3
                team_stats[away_team]['losses'] += 1
            elif home_score == away_score:
                team_stats[home_team]['draws'] += 1
                team_stats[home_team]['points'] += 1
                team_stats[away_team]['draws'] += 1
                team_stats[away_team]['points'] += 1
            else:
                team_stats[away_team]['wins'] += 1
                team_stats[away_team]['points'] += 3
                team_stats[home_team]['losses'] += 1
        
        # Calculer les moyennes
        avg_goals_per_match = total_goals / total_matches if total_matches > 0 else 0
        
        # Trier les équipes par points
        sorted_teams = sorted(
            team_stats.items(),
            key=lambda x: (x[1]['points'], x[1]['goals_for'] - x[1]['goals_against']),
            reverse=True
        )
        
        return {
            'league': league_name,
            'total_matches': total_matches,
            'avg_goals_per_match': avg_goals_per_match,
            'team_standings': sorted_teams[:10],  # Top 10
            'period_days': days
        }
    
    def calculate_prediction_confidence(self, team1_name, team2_name):
        """Calcule un score de confiance pour une prédiction"""
        team1_form = self.get_team_recent_form(team1_name)
        team2_form = self.get_team_recent_form(team2_name)
        h2h = self.get_head_to_head(team1_name, team2_name)
        
        if not team1_form or not team2_form:
            return 0.5
        
        # Score basé sur la forme récente
        form_diff = team1_form['form_score'] - team2_form['form_score']
        
        # Score basé sur l'historique H2H
        h2h_score = 0.5
        if h2h and h2h['matches_played'] > 0:
            team1_win_rate = h2h['team1_wins'] / h2h['matches_played']
            h2h_score = team1_win_rate
        
        # Score basé sur les buts
        goal_diff_score = 0.5
        if team1_form['matches_played'] > 0 and team2_form['matches_played'] > 0:
            team1_avg = team1_form['avg_goals_for'] - team1_form['avg_goals_against']
            team2_avg = team2_form['avg_goals_for'] - team2_form['avg_goals_against']
            goal_diff = team1_avg - team2_avg
            goal_diff_score = 0.5 + (goal_diff / 10)  # Normaliser
            goal_diff_score = max(0, min(1, goal_diff_score))
        
        # Moyenne pondérée
        confidence = (form_diff * 0.4 + (h2h_score - 0.5) * 0.3 + (goal_diff_score - 0.5) * 0.3) + 0.5
        confidence = max(0.1, min(0.9, confidence))
        
        return confidence
