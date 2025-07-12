"""
Module de Machine Learning pour les prédictions sportives
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from datetime import datetime, timedelta

class SportsPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.is_trained = False
        
    def create_features(self, match_data):
        """Crée les features pour le modèle ML"""
        features = {}
        
        # Features basiques
        features['home_team_encoded'] = hash(match_data.get('team1', '')) % 1000
        features['away_team_encoded'] = hash(match_data.get('team2', '')) % 1000
        features['sport_encoded'] = hash(match_data.get('sport', '')) % 100
        features['league_encoded'] = hash(match_data.get('league', '')) % 100
        
        # Features des cotes (si disponibles)
        odds = match_data.get('odds', [])
        features['home_odds'] = 2.0  # Valeur par défaut
        features['draw_odds'] = 3.0
        features['away_odds'] = 2.0
        
        for odd_str in odds:
            if isinstance(odd_str, str) and ':' in odd_str:
                bet_type, odds_value = odd_str.split(': ')
                try:
                    odds_val = float(odds_value)
                    if bet_type == '1':
                        features['home_odds'] = odds_val
                    elif bet_type == 'X':
                        features['draw_odds'] = odds_val
                    elif bet_type == '2':
                        features['away_odds'] = odds_val
                except:
                    pass
        
        # Features calculées
        features['odds_ratio_home_away'] = features['home_odds'] / features['away_odds']
        features['total_odds_sum'] = features['home_odds'] + features['draw_odds'] + features['away_odds']
        features['home_probability'] = 1 / features['home_odds']
        features['draw_probability'] = 1 / features['draw_odds']
        features['away_probability'] = 1 / features['away_odds']
        
        # Features météo
        temp = match_data.get('temp', 20)
        humid = match_data.get('humid', 50)
        
        try:
            features['temperature'] = float(temp) if temp != '–' else 20.0
        except:
            features['temperature'] = 20.0
            
        try:
            features['humidity'] = float(humid) if humid != '–' else 50.0
        except:
            features['humidity'] = 50.0
        
        # Features temporelles
        now = datetime.now()
        features['hour'] = now.hour
        features['day_of_week'] = now.weekday()
        features['month'] = now.month
        
        return features
    
    def prepare_training_data(self, matches_data):
        """Prépare les données d'entraînement"""
        features_list = []
        labels = []
        
        for match in matches_data:
            if match.get('status') == 'Terminé':
                features = self.create_features(match)
                features_list.append(features)
                
                # Déterminer le label (résultat)
                score1 = match.get('score1', 0)
                score2 = match.get('score2', 0)
                
                if score1 > score2:
                    label = '1'  # Victoire domicile
                elif score1 == score2:
                    label = 'X'  # Match nul
                else:
                    label = '2'  # Victoire extérieur
                
                labels.append(label)
        
        if not features_list:
            return None, None
        
        # Convertir en DataFrame
        df = pd.DataFrame(features_list)
        self.feature_names = df.columns.tolist()
        
        return df.values, labels
    
    def train_model(self, matches_data):
        """Entraîne le modèle ML"""
        X, y = self.prepare_training_data(matches_data)
        
        if X is None or len(X) < 10:
            print("Pas assez de données pour entraîner le modèle")
            return False
        
        # Encoder les labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Diviser les données
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42
        )
        
        # Normaliser les features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entraîner le modèle (ensemble de modèles)
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Évaluer le modèle
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Précision du modèle: {accuracy:.2%}")
        
        # Validation croisée
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
        print(f"Score de validation croisée: {cv_scores.mean():.2%} (+/- {cv_scores.std() * 2:.2%})")
        
        self.is_trained = True
        return True
    
    def predict(self, match_data):
        """Fait une prédiction pour un match"""
        if not self.is_trained:
            return None, 0.5
        
        features = self.create_features(match_data)
        
        # Créer un DataFrame avec les mêmes colonnes que l'entraînement
        feature_vector = []
        for feature_name in self.feature_names:
            feature_vector.append(features.get(feature_name, 0))
        
        X = np.array(feature_vector).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Prédiction
        prediction_proba = self.model.predict_proba(X_scaled)[0]
        prediction_class = self.model.predict(X_scaled)[0]
        
        # Décoder la prédiction
        predicted_result = self.label_encoder.inverse_transform([prediction_class])[0]
        confidence = max(prediction_proba)
        
        return predicted_result, confidence
    
    def get_feature_importance(self):
        """Retourne l'importance des features"""
        if not self.is_trained:
            return {}
        
        importance = self.model.feature_importances_
        feature_importance = dict(zip(self.feature_names, importance))
        
        # Trier par importance
        return dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    
    def save_model(self, filepath='sports_model.pkl'):
        """Sauvegarde le modèle"""
        if self.is_trained:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'label_encoder': self.label_encoder,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, filepath)
            print(f"Modèle sauvegardé dans {filepath}")
    
    def load_model(self, filepath='sports_model.pkl'):
        """Charge un modèle sauvegardé"""
        if os.path.exists(filepath):
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.label_encoder = model_data['label_encoder']
            self.feature_names = model_data['feature_names']
            self.is_trained = model_data['is_trained']
            print(f"Modèle chargé depuis {filepath}")
            return True
        return False

# Instance globale du prédicteur
predictor = SportsPredictor()

def train_predictor_with_data(matches_data):
    """Entraîne le prédicteur avec des données"""
    return predictor.train_model(matches_data)

def get_ml_prediction(match_data):
    """Obtient une prédiction ML pour un match"""
    return predictor.predict(match_data)

def save_predictor():
    """Sauvegarde le prédicteur"""
    predictor.save_model()

def load_predictor():
    """Charge le prédicteur"""
    return predictor.load_model()
