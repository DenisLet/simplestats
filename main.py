from flask import Flask, render_template, request
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, or_, desc, and_, func
from sqlalchemy.orm import sessionmaker
from models import Base, SoccerMain, Bet365Odds, XbetOdds, SoccerHalf1Stats, SoccerHalf2Stats, SoccerTimeLine
from sqlalchemy.orm import joinedload, relationship
from datetime import datetime


app = Flask(__name__)
DATABASE_URL = "postgresql+psycopg2://admin:123456er@localhost:5432/statix"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

@app.route("/", methods=["GET", "POST"])
@app.route("/soccer", methods=["GET", "POST"])
def soccer():
    selected_bookmaker = "Bet365"  # Значение по умолчанию
    team1 = ""
    team2 = ""
    errors = []
    matches_team1 = None
    matches_team2 = None
    data = {}
    corners_main1 = None
    goasl_main1 = None
    yc_main1 = None
    corners_main2 = None
    goasl_main2 = None
    yc_main2 = None
    form_data = {}
    if request.method == "POST":
        # Получение данных из формы
        selected_bookmaker = request.form.get("bookmaker")
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")
        # Получение даты из формы или установка дефолтной даты
        from_date = request.form.get("from_date", "2013-01-01")
        from_date = datetime.strptime(from_date, "%Y-%m-%d")

        # Проверка поля "Last Matches" на число
        def validate_int(value):
            if value == "":  # Пустое значение считается валидным
                return None
            try:
                return int(value)
            except ValueError:
                return None  # Если не удается преобразовать в число, возвращаем None


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
            "from_date": from_date
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

        query = query.filter(SoccerMain.match_date >= from_date, SoccerMain.match_date <= datetime.now())

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
            goasl_main1 = calculate_goals_statistics(matches_team1, selected_bookmaker)
            corners_main1 = calculate_corners_statistics(matches_team1)
            yc_main1 = calculate_yellow_cards_statistics(matches_team1)
        if team2:
            matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]
            goasl_main2 = calculate_goals_statistics(matches_team2, selected_bookmaker)
            corners_main2 = calculate_corners_statistics(matches_team2)
            yc_main2 = calculate_yellow_cards_statistics(matches_team2)


    return render_template(
        "soccer.html",
        selected_bookmaker=selected_bookmaker,
        team1=team1,
        team2=team2,
        errors=errors,
        matches_team1=matches_team1,
        matches_team2=matches_team2,
        form_data = data,
        corners_main1=corners_main1,
        goasl_main1=goasl_main1,
        yc_main1=yc_main1,
        corners_main2=corners_main2,
        goasl_main2=goasl_main2,
        yc_main2=yc_main2
    )

def calculate_goals_statistics(matches, selected_bookmaker):
    """
    Рассчитывает полную статистику матчей по лигам, включая ROI для total > 2.5 с учетом коэффициента из i.xbet_odds.odds_2_5_close.

    :param matches: Список объектов матчей
    :param selected_bookmaker: Выбранный букмекер
    :return: Словарь со всей статистикой по лигам
    """
    from collections import defaultdict

    league_stats = defaultdict(lambda: {
        "total_matches": 0,
        "over_0_5": 0,
        "over_1_5": 0,
        "over_2_5": 0,
        "over_3_5": 0,
        "both_teams_scored": 0,
        "roi_total_2_5": 0.0,
        "total_bets_count": 0,  # Количество матчей с коэффициентом закрытия
        "win_with_handicap_1_5": 0,
        "win_with_handicap_0_5": 0,
        "win_with_handicap__0_5": 0,
        "win_with_handicap__1_5": 0,
    })

    for match in matches:
        league_name = match.league_name
        total_goals = match.home_score_ft + match.away_score_ft
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft

        stats = league_stats[league_name]

        # Обновляем общий счетчик матчей
        stats["total_matches"] += 1

        # Подсчет голов
        if total_goals > 0.5:
            stats["over_0_5"] += 1
        if total_goals > 1.5:
            stats["over_1_5"] += 1
        if total_goals > 2.5:
            stats["over_2_5"] += 1
        if total_goals > 3.5:
            stats["over_3_5"] += 1

        # Проверка на обе забившие команды
        if home_goals > 0 and away_goals > 0:
            stats["both_teams_scored"] += 1

        # Определяем используемого букмекера
        if selected_bookmaker == "Bet365":
            odds_source = getattr(match, 'bet365_odds', None)
        elif selected_bookmaker == "1XBet":
            odds_source = getattr(match, 'xbet_odds', None)
        else:
            odds_source = None

        # ROI для total > 2.5 с учетом коэффициента закрытия
        if odds_source and hasattr(odds_source, "odds_2_5_close") and odds_source.odds_2_5_close:
            odds_2_5_close = odds_source.odds_2_5_close
            stats["total_bets_count"] += 1
            if total_goals > 2.5:
                stats["roi_total_2_5"] += odds_2_5_close - 1  # Выигрыш минус ставка
            else:
                stats["roi_total_2_5"] -= 1  # Проигрыш (ставка -1)

        # Подсчет фор
        if home_goals - away_goals > 1.5:
            stats["win_with_handicap_1_5"] += 1
        if home_goals - away_goals > 0.5:
            stats["win_with_handicap_0_5"] += 1
        if home_goals - away_goals > -0.5:
            stats["win_with_handicap__0_5"] += 1
        if home_goals - away_goals > -1.5:
            stats["win_with_handicap__1_5"] += 1

    # Финальный расчет ROI
    for stats in league_stats.values():
        if stats["total_bets_count"] > 0:
            stats["roi_total_2_5"] = round(stats["roi_total_2_5"] / stats["total_bets_count"] * 100, 2)
        else:
            stats["roi_total_2_5"] = None  # Если ставок не было, ROI = None

    return dict(league_stats)


def calculate_corners_statistics(matches):
    """
    Подсчитывает статистику по угловым ударам для матчей, разделяя их по лигам.
    Игры, где угловые удары не были записаны или обе команды подали по 0 угловых, пропускаются.
    Также подсчитывает количество случаев, когда первая команда выиграла по угловым с форой.

    :param matches: Список объектов матчей
    :return: Словарь с результатами подсчета по каждой лиге
    """
    from collections import defaultdict

    # Словарь для хранения статистики по угловым ударам по лигам
    league_corners_stats = defaultdict(lambda: {
        "corners_over_5_5": 0,
        "corners_over_6_5": 0,
        "corners_over_7_5": 0,
        "corners_over_8_5": 0,
        "corners_over_9_5": 0,
        "corners_over_10_5": 0,
        "corners_over_11_5": 0,
        "corners_win_with_handicap_4_5": 0,
        "corners_win_with_handicap_3_5": 0,
        "corners_win_with_handicap_2_5": 0,
        "corners_win_with_handicap_1_5": 0,
        "corners_win_with_handicap_0_5": 0,
        "corners_win_with_handicap__0_5": 0,
        "total_matches": 0
    })

    for match in matches:
        league_name = match.league_name
        home_corners = match.home_corners
        away_corners = match.away_corners

        total_corners = home_corners + away_corners

        # Пропускаем матчи без угловых или с нулевыми угловыми у обеих команд
        if total_corners == 0 or home_corners is None or away_corners is None:
            continue

        stats = league_corners_stats[league_name]

        # Обновляем общий счетчик матчей
        stats["total_matches"] += 1

        # Подсчет угловых для over_x.5
        if total_corners > 5.5:
            stats["corners_over_5_5"] += 1
        if total_corners > 6.5:
            stats["corners_over_6_5"] += 1
        if total_corners > 7.5:
            stats["corners_over_7_5"] += 1
        if total_corners > 8.5:
            stats["corners_over_8_5"] += 1
        if total_corners > 9.5:
            stats["corners_over_9_5"] += 1
        if total_corners > 10.5:
            stats["corners_over_10_5"] += 1
        if total_corners > 11.5:
            stats["corners_over_11_5"] += 1

        # Подсчет случаев, когда первая команда выиграла по угловым с форой
        corners_diff = home_corners - away_corners

        if corners_diff > 4.5:
            stats["corners_win_with_handicap_4_5"] += 1
        if corners_diff > 3.5:
            stats["corners_win_with_handicap_3_5"] += 1
        if corners_diff > 2.5:
            stats["corners_win_with_handicap_2_5"] += 1
        if corners_diff > 1.5:
            stats["corners_win_with_handicap_1_5"] += 1
        if corners_diff > 0.5:
            stats["corners_win_with_handicap_0_5"] += 1
        if corners_diff > -0.5:
            stats["corners_win_with_handicap__0_5"] += 1

    return dict(league_corners_stats)

def calculate_yellow_cards_statistics(matches):
    """
    Подсчитывает статистику по желтым карточкам для матчей, разделяя их по лигам.
    Игры, где не было желтых карточек, пропускаются.
    Также подсчитывает количество случаев, когда первая команда выиграла по желтым карточкам с форой.

    :param matches: Список объектов матчей
    :return: Словарь с результатами подсчета по каждой лиге
    """
    from collections import defaultdict

    # Словарь для хранения статистики по желтым карточкам по лигам
    league_yellow_cards_stats = defaultdict(lambda: {
        "yellow_cards_over_1_5": 0,
        "yellow_cards_over_2_5": 0,
        "yellow_cards_over_3_5": 0,
        "yellow_cards_over_4_5": 0,
        "yellow_cards_over_5_5": 0,
        "yellow_cards_win_with_handicap_minus_1_5": 0,
        "yellow_cards_win_with_handicap_minus_0_5": 0,
        "yellow_cards_win_with_handicap_minus__0_5": 0,
        "total_matches": 0
    })

    for match in matches:
        league_name = match.league_name
        home_yellow = match.home_yellow
        away_yellow = match.away_yellow

        total_yellow_cards = home_yellow + away_yellow

        home_corners = match.home_corners
        away_corners = match.away_corners

        total_corners = home_corners + away_corners

        # Пропускаем матчи без угловых или с нулевыми угловыми у обеих команд
        if total_corners == 0 or home_corners is None or away_corners is None:
            continue
        stats = league_yellow_cards_stats[league_name]

        # Обновляем общий счетчик матчей
        stats["total_matches"] += 1

        # Подсчет желтых карточек для over_x.5
        if total_yellow_cards > 1.5:
            stats["yellow_cards_over_1_5"] += 1
        if total_yellow_cards > 2.5:
            stats["yellow_cards_over_2_5"] += 1
        if total_yellow_cards > 3.5:
            stats["yellow_cards_over_3_5"] += 1
        if total_yellow_cards > 4.5:
            stats["yellow_cards_over_4_5"] += 1
        if total_yellow_cards > 5.5:
            stats["yellow_cards_over_5_5"] += 1

        # Подсчет случаев, когда первая команда выиграла по желтым карточкам с форой
        yellow_cards_diff = home_yellow - away_yellow

        if yellow_cards_diff > 1.5:
            stats["yellow_cards_win_with_handicap_minus_1_5"] += 1
        if yellow_cards_diff > 0.5:
            stats["yellow_cards_win_with_handicap_minus_0_5"] += 1
        if yellow_cards_diff > -0.5:
            stats["yellow_cards_win_with_handicap_minus__0_5"] += 1

    return dict(league_yellow_cards_stats)

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