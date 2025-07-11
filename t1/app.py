from flask import Flask, render_template, request, url_for


import math
import requests
from datetime import datetime
import os

app = Flask(__name__)


API_URL = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr&gr=70&mode=4&country=96&getEmpty=true"

def fetch_matches():
    try:
        resp = requests.get(API_URL, timeout=10)
        data = resp.json()
        matches = []
        for item in data.get('Value', []):
            # Support du format personnalisé si présent
            if 'teams' in item and 'logos' in item:
                match = {
                    'id': item.get('id', 0),
                    'equipe1': item.get('teams', [''])[0],
                    'equipe1_logo': item.get('logos', {}).get('team1', ''),
                    'score1': item.get('scores', {}).get('half', {}).get('team1', ''),
                    'score2': item.get('scores', {}).get('half', {}).get('team2', ''),
                    'equipe2': item.get('teams', ['',''])[1] if len(item.get('teams', [])) > 1 else '',
                    'equipe2_logo': item.get('logos', {}).get('team2', ''),
                    'sport': item.get('sport', ''),
                    'ligue': item.get('league', ''),
                    'statut': item.get('status', ''),
                    'date_heure': datetime.fromtimestamp(item.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M') if item.get('timestamp') else '',
                    'cotes': item.get('odds', {}),
                    'handicaps': item.get('handicaps', []),
                    'prediction': '',
                    'details_url': f"/match/{item.get('id', 0)}"
                }
            else:
                match = {
                    'id': item.get('I', 0),
                    'equipe1': item.get('O1', 'Équipe 1'),
                    'equipe1_logo': item.get('O1IMG', ''),
                    'score1': item.get('SC', {}).get('FS', '').split('-')[0] if item.get('SC', {}).get('FS') else '',
                    'score2': item.get('SC', {}).get('FS', '').split('-')[1] if item.get('SC', {}).get('FS') else '',
                    'equipe2': item.get('O2', 'Équipe 2'),
                    'equipe2_logo': item.get('O2IMG', ''),
                    'sport': item.get('SN', 'Football'),
                    'ligue': item.get('L', 'Ligue'),
                    'ligue_en': item.get('LE', ''),
                    'statut': item.get('TN', 'À venir'),
                    'statut_en': item.get('TNS', ''),
                    'date_heure': datetime.fromtimestamp(item.get('S', 0)).strftime('%Y-%m-%d %H:%M') if item.get('S') else '',
                    'temperature': item.get('Weather', {}).get('T', ''),
                    'humidite': item.get('Weather', {}).get('H', ''),
                    'cotes': {
                        '1': next((e.get('C', '') for e in item.get('E', []) if e.get('T') == '1'), ''),
                        '2': next((e.get('C', '') for e in item.get('E', []) if e.get('T') == '2'), ''),
                        'X': next((e.get('C', '') for e in item.get('E', []) if e.get('T') == 'X'), '')
                    },
                    'prediction': '',
                    'details_url': f"/match/{item.get('I', 0)}"
                }
            matches.append(match)
        return matches
    except Exception as e:
        print(f"Erreur API: {e}")
        return []

def get_filters(matches):
    sports = sorted(list(set(m['sport'] for m in matches)))
    ligues = sorted(list(set(m['ligue'] for m in matches)))
    statuts = sorted(list(set(m['statut'] for m in matches)))
    return sports, ligues, statuts

@app.route('/')
def index():
    matches = fetch_matches()
    print(f"Nombre de matchs récupérés: {len(matches)}")
    sports, ligues, statuts = get_filters(matches)
    sport = request.args.get('sport', '')
    ligue = request.args.get('ligue', '')
    statut = request.args.get('statut', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    filtered = matches
    if sport:
        filtered = [m for m in filtered if m['sport'] == sport]
    if ligue:
        filtered = [m for m in filtered if m['ligue'] == ligue]
    if statut:
        filtered = [m for m in filtered if m['statut'] == statut]

    total = len(filtered)
    pages = max(1, math.ceil(total / per_page))
    start = (page - 1) * per_page
    end = start + per_page
    matchs_page = filtered[start:end]

    message = None
    if not matches:
        message = "Aucun match n'a été récupéré depuis l'API. Vérifiez la connexion ou l'API."
    elif not matchs_page:
        message = "Aucun match à afficher avec les filtres sélectionnés."

    return render_template('index.html',
        matchs=matchs_page,
        sports=sports,
        ligues=ligues,
        statuts=statuts,
        selected_sport=sport,
        selected_ligue=ligue,
        selected_statut=statut,
        page=page,
        pages=pages,
        total=total,
        message=message
    )

@app.route('/match/<int:match_id>')
def match_details(match_id):
    matches = fetch_matches()
    match = next((m for m in matches if m['id'] == match_id), None)
    if not match:
        return render_template('404.html'), 404
    return render_template('details.html', match=match)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
