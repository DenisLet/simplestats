import psycopg2

# Параметры подключения к базе данных
conn_params = {
    'dbname': 'statix',
    'user': 'admin',
    'password': '123456er',
    'host': 'localhost',
    'port': '5432'
}

# Создаем соединение с базой данных
conn = psycopg2.connect(**conn_params)
cursor = conn.cursor()

# Запрос
query = """
WITH losing_matches AS (
    SELECT match_id, match_date, start_time
    FROM soccer_main
    WHERE (team_home = 'Arsenal' AND home_score_ft = 0 AND away_score_ft = 3)
    OR (team_away = 'Arsenal' AND home_score_ft = 3 AND away_score_ft = 0)
)
SELECT sm.*
FROM soccer_main sm
JOIN losing_matches lm
    ON (sm.match_date > lm.match_date
        OR (sm.match_date = lm.match_date AND sm.start_time > lm.start_time))
WHERE (sm.team_home = 'Arsenal' OR sm.team_away = 'Arsenal')
    AND NOT EXISTS (
        SELECT 1
        FROM soccer_main sm2
        WHERE (sm2.team_home = 'Arsenal' OR sm2.team_away = 'Arsenal')
            AND (sm2.match_date > lm.match_date
                 OR (sm2.match_date = lm.match_date AND sm2.start_time > lm.start_time))
            AND (sm2.match_date < sm.match_date
                 OR (sm2.match_date = sm.match_date AND sm2.start_time < sm.start_time))
    )
ORDER BY lm.match_date, lm.start_time, sm.match_date, sm.start_time;
"""

# Выполнение запроса
cursor.execute(query)

# Получаем результаты
results = cursor.fetchall()

# Выводим результаты
for row in results:
    print(row)

# Закрываем соединение
cursor.close()
conn.close()
