"""
🤖 GESTIONNAIRE DE MODÈLES IA ORACXPRED
========================================
Gestion des modèles IA (.pkl) séparés des données utilisateurs
"""

import os
import pickle
import json
from datetime import datetime
from flask import current_app


MODELS_DIR = 'ai_models'
MODELS_METADATA_FILE = 'models_metadata.json'


def ensure_models_directory():
    """Crée le répertoire des modèles s'il n'existe pas"""
    models_path = os.path.join(current_app.root_path, MODELS_DIR)
    os.makedirs(models_path, exist_ok=True)
    return models_path


def save_model(model, model_name, version=None, metadata=None):
    """
    Sauvegarde un modèle IA dans un fichier .pkl
    
    Args:
        model: Le modèle à sauvegarder (objet Python sérialisable)
        model_name: Nom du modèle (ex: 'prediction_1x2', 'prediction_alternatifs')
        version: Version du modèle (optionnel, auto-généré si None)
        metadata: Métadonnées supplémentaires (dict)
    
    Returns:
        Chemin du fichier sauvegardé
    """
    models_path = ensure_models_directory()
    
    # Générer un nom de version si non fourni
    if version is None:
        version = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    filename = f"{model_name}_v{version}.pkl"
    filepath = os.path.join(models_path, filename)
    
    # Sauvegarder le modèle
    with open(filepath, 'wb') as f:
        pickle.dump(model, f)
    
    # Mettre à jour les métadonnées
    update_model_metadata(model_name, version, filepath, metadata)
    
    print(f"✅ Modèle sauvegardé: {filepath}")
    return filepath


def load_model(model_name, version=None):
    """
    Charge un modèle IA depuis un fichier .pkl
    
    Args:
        model_name: Nom du modèle
        version: Version spécifique (optionnel, charge la dernière si None)
    
    Returns:
        Le modèle chargé ou None si non trouvé
    """
    models_path = ensure_models_directory()
    metadata_file = os.path.join(models_path, MODELS_METADATA_FILE)
    
    # Charger les métadonnées
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        return None
    
    # Trouver le modèle
    if model_name not in metadata:
        return None
    
    model_versions = metadata[model_name]
    
    if version:
        # Charger une version spécifique
        if version in model_versions:
            filepath = model_versions[version]['filepath']
        else:
            return None
    else:
        # Charger la dernière version
        if not model_versions:
            return None
        latest_version = max(model_versions.keys())
        filepath = model_versions[latest_version]['filepath']
    
    # Charger le modèle
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            model = pickle.load(f)
        return model
    
    return None


def update_model_metadata(model_name, version, filepath, metadata=None):
    """Met à jour les métadonnées d'un modèle"""
    models_path = ensure_models_directory()
    metadata_file = os.path.join(models_path, MODELS_METADATA_FILE)
    
    # Charger les métadonnées existantes
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            all_metadata = json.load(f)
    else:
        all_metadata = {}
    
    # Mettre à jour
    if model_name not in all_metadata:
        all_metadata[model_name] = {}
    
    all_metadata[model_name][version] = {
        'filepath': filepath,
        'created_at': datetime.now().isoformat(),
        'metadata': metadata or {}
    }
    
    # Sauvegarder
    with open(metadata_file, 'w') as f:
        json.dump(all_metadata, f, indent=2)


def list_models():
    """Liste tous les modèles disponibles"""
    models_path = ensure_models_directory()
    metadata_file = os.path.join(models_path, MODELS_METADATA_FILE)
    
    if not os.path.exists(metadata_file):
        return {}
    
    with open(metadata_file, 'r') as f:
        return json.load(f)


def get_latest_model_version(model_name):
    """Récupère la dernière version d'un modèle"""
    models = list_models()
    if model_name not in models:
        return None
    
    versions = models[model_name]
    if not versions:
        return None
    
    return max(versions.keys())


def delete_model(model_name, version=None):
    """Supprime un modèle"""
    models_path = ensure_models_directory()
    metadata_file = os.path.join(models_path, MODELS_METADATA_FILE)
    
    if not os.path.exists(metadata_file):
        return False
    
    with open(metadata_file, 'r') as f:
        all_metadata = json.load(f)
    
    if model_name not in all_metadata:
        return False
    
    if version:
        # Supprimer une version spécifique
        if version in all_metadata[model_name]:
            filepath = all_metadata[model_name][version]['filepath']
            if os.path.exists(filepath):
                os.remove(filepath)
            del all_metadata[model_name][version]
        else:
            return False
    else:
        # Supprimer toutes les versions
        for v, data in all_metadata[model_name].items():
            filepath = data['filepath']
            if os.path.exists(filepath):
                os.remove(filepath)
        del all_metadata[model_name]
    
    # Sauvegarder les métadonnées mises à jour
    with open(metadata_file, 'w') as f:
        json.dump(all_metadata, f, indent=2)
    
    return True
