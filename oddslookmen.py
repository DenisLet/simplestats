import requests

url = 'https://guest.api.arcadia.pinnacle.com/0.1/sports/29/leagues?all=false&brandId=0'
response = requests.get(url)
data = response.json()

# Список для хранения всех matchupId
all_matchup_ids = []

# Проходим по всем лигам
for league in data:
    if 'matchups' in league:  # Проверяем, есть ли ключ 'matchups' (или замените на правильный)
        matchups = league['matchups']  # Получаем список матчей
        for matchup in matchups:
            all_matchup_ids.append(matchup['matchupId'])  # Добавляем все matchupId

# Общее количество matchupId
total_matchup_ids = len(all_matchup_ids)

print(f'Общее количество matchupId: {total_matchup_ids}')
