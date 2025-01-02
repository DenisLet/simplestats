from flask import Flask, render_template, request
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, or_, desc, and_, func
from sqlalchemy.orm import sessionmaker
from models import Base, SoccerMain, Bet365Odds, XbetOdds, SoccerHalf1Stats, SoccerHalf2Stats, SoccerTimeLine
from sqlalchemy.orm import joinedload, relationship

app = Flask(__name__)
DATABASE_URL = "postgresql+psycopg2://admin:123456er@localhost:5432/statix"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def get_all_matches_by_team(team):
    query = session.query(SoccerMain).filter(
        (SoccerMain.team_home == team) or (SoccerMain.team_away == team)
    )
    return query.all()

@app.route("/soccer", methods=["GET", "POST"])
def soccer():
    selected_bookmaker = "Bet365"  # Значение по умолчанию
    team1 = ""
    team2 = ""
    last_matches = None  # Переменная для хранения данных о последних матчах
    errors = []
    matches_team1 = None
    matches_team2 = None
    if request.method == "POST":
        # Получение данных из формы
        selected_bookmaker = request.form.get("bookmaker")
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")

        # Проверка поля "Last Matches" на число
        def validate_int(value):
            if value == "":  # Пустое значение считается валидным
                return None
            try:
                return int(value)
            except ValueError:
                return None  # Если не удается преобразовать в число, возвращаем None

        # Получение и валидация "Last Matches"
        try:
            last_matches = validate_int(request.form.get("last_matches"))
        except:
            last_matches = None

        # Проверка полей для команд (они должны быть строками, или быть пустыми)
        if team1 and not isinstance(team1, str):
            errors.append("Команда 1 должна быть строкой.")
        if team2 and not isinstance(team2, str):
            errors.append("Команда 2 должна быть строкой.")

        # Проверка числовых полей на ставки
        def validate_float(value):
            if value == "":  # Пустые строки разрешены
                return 0  # Пустая строка считается валидной
            try:
                return float(value)
            except ValueError:
                return 0  # Если не удается преобразовать в число, возвращаем None

        # Проверка ставок на числа
        win_home_open = validate_float(request.form.get("win_home_open"))
        win_home_open_plus = validate_float(request.form.get("win_home_open_plus"))
        win_home_open_minus = validate_float(request.form.get("win_home_open_minus"))
        win_home_close = validate_float(request.form.get("win_home_close"))
        win_home_close_plus = validate_float(request.form.get("win_home_close_plus"))
        win_home_close_minus = validate_float(request.form.get("win_home_close_minus"))
        to25_open = validate_float(request.form.get("to25_open"))
        to25_open_plus = validate_float(request.form.get("to25_open_plus"))
        to25_open_minus = validate_float(request.form.get("to25_open_minus"))
        to25_close = validate_float(request.form.get("to25_close"))
        to25_close_plus = validate_float(request.form.get("to25_close_plus"))
        to25_close_minus = validate_float(request.form.get("to25_close_minus"))



        total25MAXo = to25_open + to25_open_plus
        total25MINo = to25_open - to25_open_minus
        total25MAXc = to25_close + to25_close_plus
        total25MINc = to25_close - to25_close_minus
        win1OpenMAX = win_home_open + win_home_open_plus
        win1OpenMIN = win_home_open - win_home_open_minus
        win1CloseMAX = win_home_close + win_home_close_plus
        win1CloseMIN = win_home_close - win_home_close_minus

        # Проверка на ошибки
        if None in [win_home_open, win_home_open_plus, win_home_open_minus, win_home_close, win_home_close_plus,
                    win_home_close_minus, to25_open, to25_open_plus, to25_open_minus, to25_close, to25_close_plus,
                    to25_close_minus]:
            errors.append("Values must be INTEGER or FLOAT")
        if last_matches is None:
            errors.append("Last Matches must be INTEGER")

        # Если есть ошибки, передаем их в шаблон
        if errors:
            return render_template("soccer.html", selected_bookmaker=selected_bookmaker, team1=team1, team2=team2,
                                   last_matches=last_matches, errors=errors)

        # Данные, если ошибок нет
        data = {
            "team1": team1,
            "team2": team2,
            "win_home_open": win_home_open,
            "win_home_open_plus": win_home_open_plus,
            "win_home_open_minus": win_home_open_minus,
            "win_home_close": win_home_close,
            "win_home_close_plus": win_home_close_plus,
            "win_home_close_minus": win_home_close_minus,
            "to25_open": to25_open,
            "to25_open_plus": to25_open_plus,
            "to25_open_minus": to25_open_minus,
            "to25_close": to25_close,
            "to25_close_plus": to25_close_plus,
            "to25_close_minus": to25_close_minus,
            "bookmaker": selected_bookmaker,
            "last_matches": last_matches
        }
        print("Полученные данные:", data)  # Вывод данных в терминал
        if selected_bookmaker == 'Bet365':
            book_source = Bet365Odds
            sub_source = SoccerMain.bet365_odds
        if selected_bookmaker == '1XBet':
            book_source = XbetOdds
            sub_source = SoccerMain.xbet_odds

        # Базовый запрос
        query = session.query(SoccerMain).join(
            book_source, SoccerMain.match_id == book_source.match_id
        ).options(joinedload(sub_source))

        # Фильтр по командам
        if team1 and team2:
            query = query.filter(
                or_(
                    (SoccerMain.team_home == team1) | (SoccerMain.team_away == team1),
                    (SoccerMain.team_home == team2) | (SoccerMain.team_away == team2)
                )
            )
        elif team1:
            query = query.filter(
                or_(SoccerMain.team_home == team1, SoccerMain.team_away == team1)
            )
        elif team2:
            query = query.filter(
                or_(SoccerMain.team_home == team2, SoccerMain.team_away == team2)
            )

        # Фильтр по odds_2_5_open
        if to25_open != 0:
            query = query.filter(
                book_source.odds_2_5_open >= total25MINo,
                book_source.odds_2_5_open <= total25MAXo
            )

        # Фильтр по odds_2_5_close
        if to25_close != 0:
            query = query.filter(
                book_source.odds_2_5_close >= total25MINc,
                book_source.odds_2_5_close <= total25MAXc
            )

        # Фильтр по win1_open
        if win_home_open != 0:
            query = query.filter(
                or_(
                    # Для первой команды как хозяина
                    and_(
                        SoccerMain.team_home == team1,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    ),
                    # Для второй команды как гостя
                    and_(
                        SoccerMain.team_away == team2,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    )
                )
            )
        # Фильтр по win1_close
        if win_home_close != 0:
            query = query.filter(
                or_(
                    # Для первой команды как хозяина
                    and_(
                        SoccerMain.team_home == team1,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    ),
                    # Для второй команды как гостя
                    and_(
                        SoccerMain.team_away == team2,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    )
                )
            )

        # Сортировка по лиге и дате
        query = query.order_by(SoccerMain.league_name, desc(SoccerMain.match_date))
        matches = query.all()

        match_ids = [match.match_id for match in matches]
        half1_stats = session.query(SoccerHalf1Stats).filter(SoccerHalf1Stats.match_id.in_(match_ids)).all()
        half2_stats = session.query(SoccerHalf2Stats).filter(SoccerHalf2Stats.match_id.in_(match_ids)).all()

        # Преобразование в словарь для быстрого доступа
        half1_dict = {stat.match_id: stat for stat in half1_stats}
        half2_dict = {stat.match_id: stat for stat in half2_stats}

        timeline_stats = session.query(SoccerTimeLine).filter(SoccerTimeLine.match_id.in_(match_ids)).all()

        # Преобразование в словарь для быстрого доступа
        timeline_dict = {stat.match_id: stat for stat in timeline_stats}

        # Добавление угловых в результаты матчей
        for match in matches:
            match_id = match.match_id
            half1 = half1_dict.get(match_id)
            half2 = half2_dict.get(match_id)
            timeline = timeline_dict.get(match_id)

            home_goals_h1 = len(timeline.home_goals_h1) if timeline and timeline.home_goals_h1 else 0
            away_goals_h1 = len(timeline.away_goals_h1) if timeline and timeline.away_goals_h1 else 0

            home_corners = (half1.home_corners if half1 and half1.home_corners is not None else 0) + \
                           (half2.home_corners if half2 and half2.home_corners is not None else 0)

            away_corners = (half1.away_corners if half1 and half1.away_corners is not None else 0) + \
                           (half2.away_corners if half2 and half2.away_corners is not None else 0)

            home_yellow = (half1.home_yellow if half1 and half1.home_yellow is not None else 0) + \
                          (half2.home_yellow if half2 and half2.home_yellow is not None else 0)

            away_yellow = (half1.away_yellow if half1 and half1.away_yellow is not None else 0) + \
                          (half2.away_yellow if half2 and half2.away_yellow is not None else 0)
            # Добавление информации в список матчей для команд
            match.home_corners = home_corners
            match.away_corners = away_corners
            match.home_yellow = home_yellow
            match.away_yellow = away_yellow
            match.home_goals_h1 = home_goals_h1
            match.away_goals_h1 = away_goals_h1

        # Разделение по командам
        if team1:
            matches_team1 = [match for match in matches if match.team_home == team1 or match.team_away == team1]
        if team2:
            matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]

        print([i.home_yellow for i in matches_team1])
        print(len([i.match_id for i in matches_team1]))
    return render_template(
        "soccer.html",
        selected_bookmaker=selected_bookmaker,
        team1=team1,
        team2=team2,
        last_matches=last_matches,
        errors=errors,
        matches_team1=matches_team1,
        matches_team2=matches_team2,
        form_data = data
    )




@app.route("/search_teams", methods=["GET"])
def search_teams():
    query = request.args.get("q", "").lower()
    if not query or len(query) < 3:
        return {"teams": []}  # Пустой список, если запрос короткий

    # Пример: фильтрация списка команд из базы данных
    teams = session.query(SoccerMain.team_home).distinct().all()  # Замените на ваш источник данных
    filtered_teams = [team[0] for team in teams if team[0].lower().startswith(query)]

    return {"teams": filtered_teams}

if __name__ == "__main__":
    app.run(debug=True, port=5001)