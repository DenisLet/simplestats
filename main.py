from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, or_, desc, and_, func
from sqlalchemy.orm import sessionmaker
from models import Base, SoccerMain, Bet365Odds, XbetOdds, SoccerHalf1Stats, SoccerHalf2Stats, SoccerTimeLine, HockeyMain, XbetOddsHoc, HandballMain, XbetOddsHb, BasketballMain, XbetOddsBb, Bet365OddsBb
from sqlalchemy.orm import joinedload, relationship
from datetime import datetime
from sqlalchemy import exists
import sqlite3
import requests
from datetime import datetime
import time
import threading
from fake_useragent import UserAgent
import random
from datetime import timedelta

app = Flask(__name__)
DATABASE_URL = "postgresql+psycopg2://admin:123456er@127.0.0.1:5432/statix"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

@app.route("/soccer", methods=["GET", "POST"])
def soccer():
    selected_bookmaker = "Bet365"
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
    autocomplete = False

    if request.method == "POST":

        selected_bookmaker = request.form.get("bookmaker")
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")

        from_date = request.form.get("from_date", "2013-01-01")
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        mid_total = request.form.get("mid_total")
        autocomplete = 'autocomplete-toggle' in request.form


        team1_score = request.form.get('team1_score', '')
        opponent_score = request.form.get('opponent_score', '')
        team2_score = request.form.get('team2_score', '')
        opponent2_score = request.form.get('opponent2_score', '')

        def validate_int(value):
            if value == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None



        if team1 and not isinstance(team1, str):
            errors.append("Команда 1 должна быть строкой.")
        if team2 and not isinstance(team2, str):
            errors.append("Команда 2 должна быть строкой.")


        def validate_float(value):
            if value == "":
                return 0
            try:
                return float(value)
            except ValueError:
                return 0


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


        if None in [win_home_open, win_home_open_plus, win_home_open_minus, win_home_close, win_home_close_plus,
                    win_home_close_minus, to25_open, to25_open_plus, to25_open_minus, to25_close, to25_close_plus,
                    to25_close_minus]:
            errors.append("Values must be INTEGER or FLOAT")





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
        print("Полученные данные:", data)
        if selected_bookmaker == 'Bet365':
            book_source = Bet365Odds
            sub_source = SoccerMain.bet365_odds
        if selected_bookmaker == '1XBet':
            book_source = XbetOdds
            sub_source = SoccerMain.xbet_odds

        try:
            team1_score = int(team1_score) if team1_score else None
            opponent_score = int(opponent_score) if opponent_score else None
            team2_score = int(team2_score) if team2_score else None
            opponent2_score = int(opponent2_score) if opponent2_score else None
        except ValueError:
            team1_score = opponent_score = team2_score = opponent2_score = None

        print(team1_score, opponent_score, team2_score, opponent2_score)

        query = session.query(SoccerMain).join(
            book_source, SoccerMain.match_id == book_source.match_id
        ).options(joinedload(sub_source))

        query = query.filter(SoccerMain.match_date >= from_date, SoccerMain.match_date <= datetime.now())

        if not team1 and not team2:
            errors.append("Please select at least one team for filtering!")
            return render_template(
                "soccer.html",
                selected_bookmaker=selected_bookmaker,
                team1=team1,
                team2=team2,
                errors=errors,
                form_data=data,
                autocomplete=autocomplete
            )


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


        if to25_open != 0:
            query = query.filter(
                book_source.odds_2_5_open >= total25MINo,
                book_source.odds_2_5_open <= total25MAXo
            )


        if to25_close != 0:
            query = query.filter(
                book_source.odds_2_5_close >= total25MINc,
                book_source.odds_2_5_close <= total25MAXc
            )


        if win_home_open != 0:
            query = query.filter(
                or_(

                    and_(
                        SoccerMain.team_home == team1,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    ),

                    and_(
                        SoccerMain.team_away == team2,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    )
                )
            )

        if win_home_close != 0:
            query = query.filter(
                or_(

                    and_(
                        SoccerMain.team_home == team1,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    ),

                    and_(
                        SoccerMain.team_away == team2,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    )
                )
            )

        query = query.order_by(SoccerMain.league_name, desc(SoccerMain.match_date))
        matches = query.all()

        match_ids = [match.match_id for match in matches]
        half1_stats = session.query(SoccerHalf1Stats).filter(SoccerHalf1Stats.match_id.in_(match_ids)).all()
        half2_stats = session.query(SoccerHalf2Stats).filter(SoccerHalf2Stats.match_id.in_(match_ids)).all()


        half1_dict = {stat.match_id: stat for stat in half1_stats}
        half2_dict = {stat.match_id: stat for stat in half2_stats}

        timeline_stats = session.query(SoccerTimeLine).filter(SoccerTimeLine.match_id.in_(match_ids)).all()


        timeline_dict = {stat.match_id: stat for stat in timeline_stats}


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

            match.home_corners = home_corners
            match.away_corners = away_corners
            match.home_yellow = home_yellow
            match.away_yellow = away_yellow
            match.home_goals_h1 = home_goals_h1
            match.away_goals_h1 = away_goals_h1


        def filter_team_matches(team, score, opponent_score):
            all_team_matches = [match for match in matches if match.team_home == team or match.team_away == team]
            all_team_matches_sorted = sorted(all_team_matches, key=lambda m: m.match_date)

            if score is not None and opponent_score is not None:
                old_matches = [
                    m for m in all_team_matches_sorted
                    if (
                            (m.team_home == team and m.home_score_ft == score and m.away_score_ft == opponent_score) or
                            (m.team_away == team and m.away_score_ft == score and m.home_score_ft == opponent_score)
                    )
                ]

                next_matches = []
                for old_match in old_matches:
                    future_matches_same_league = [
                        x for x in all_team_matches_sorted
                        if x.match_date > old_match.match_date and x.league_name == old_match.league_name
                    ]
                    if future_matches_same_league:
                        next_matches.append(future_matches_same_league[0])

                return next_matches
            else:
                return all_team_matches_sorted

        if team1:
            if team1_score is not None and opponent_score is not None:
                matches_team1 = filter_team_matches(team1, team1_score, opponent_score)
            else:
                matches_team1 = [match for match in matches if match.team_home == team1 or match.team_away == team1]
            goasl_main1 = calculate_goals_statistics(matches_team1, team1, selected_bookmaker)
            corners_main1 = calculate_corners_statistics(matches_team1, team1)
            yc_main1 = calculate_yellow_cards_statistics(matches_team1, team1)

        if team2:
            if team2_score is not None and opponent2_score is not None:
                matches_team2 = filter_team_matches(team2, team2_score, opponent2_score)
            else:
                matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]
            goasl_main2 = calculate_goals_statistics(matches_team2, team2, selected_bookmaker)
            corners_main2 = calculate_corners_statistics(matches_team2, team2)
            yc_main2 = calculate_yellow_cards_statistics(matches_team2, team2)
        # if team1:
        #     matches_team1 = [match for match in matches if match.team_home == team1 or match.team_away == team1]
        #     goasl_main1 = calculate_goals_statistics(matches_team1, selected_bookmaker)
        #     corners_main1 = calculate_corners_statistics(matches_team1)
        #     yc_main1 = calculate_yellow_cards_statistics(matches_team1)
        # if team2:
        #     matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]
        #     goasl_main2 = calculate_goals_statistics(matches_team2, selected_bookmaker)
        #     corners_main2 = calculate_corners_statistics(matches_team2)
        #     yc_main2 = calculate_yellow_cards_statistics(matches_team2)

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
        yc_main2=yc_main2,
        autocomplete=autocomplete
    )

def calculate_goals_statistics(matches, team, selected_bookmaker):
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
        "total_bets_count": 0,
        "win_with_handicap_1_5": 0,
        "win_with_handicap_0_5": 0,
        "win_with_handicap__0_5": 0,
        "win_with_handicap__1_5": 0,
        "win_with_handicap_2_5": 0,
        "win_with_handicap__2_5": 0,
    })

    for match in matches:
        league_name = match.league_name
        total_goals = match.home_score_ft + match.away_score_ft
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft

        stats = league_stats[league_name]


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


        if home_goals > 0 and away_goals > 0:
            stats["both_teams_scored"] += 1


        if selected_bookmaker == "Bet365":
            odds_source = getattr(match, 'bet365_odds', None)
        elif selected_bookmaker == "1XBet":
            odds_source = getattr(match, 'xbet_odds', None)
        else:
            odds_source = None


        if odds_source and hasattr(odds_source, "odds_2_5_close") and odds_source.odds_2_5_close:
            odds_2_5_close = odds_source.odds_2_5_close
            stats["total_bets_count"] += 1
            if total_goals > 2.5:
                stats["roi_total_2_5"] += odds_2_5_close - 1
            else:
                stats["roi_total_2_5"] -= 1



        if match.team_home == team:
            current_hc = home_goals - away_goals
            odds_home = odds_source.win_home_close

        elif match.team_away == team:
            current_hc = away_goals - home_goals
            odds_home = odds_source.win_away_close

        else:
            continue

        if current_hc > -2.5:
            stats["win_with_handicap__2_5"] += 1
        if current_hc > -1.5:
            stats["win_with_handicap__1_5"] += 1
        if current_hc > -0.5:
            stats["win_with_handicap__0_5"] += 1
        if current_hc > 0.5:
            stats["win_with_handicap_0_5"] += 1
        if current_hc > 1.5:
            stats["win_with_handicap_1_5"] += 1
        if current_hc >2.5:
            stats["win_with_handicap_2_5"] += 1



    for stats in league_stats.values():
        if stats["total_bets_count"] > 0:
            stats["roi_total_2_5"] = round(stats["roi_total_2_5"] / stats["total_bets_count"] * 100, 2)
        else:
            stats["roi_total_2_5"] = None

    return dict(league_stats)


def calculate_corners_statistics(matches, team):
    """
    Подсчитывает статистику по угловым ударам для матчей, разделяя их по лигам.
    Игры, где угловые удары не были записаны или обе команды подали по 0 угловых, пропускаются.
    Также подсчитывает количество случаев, когда первая команда выиграла по угловым с форой.

    :param matches: Список объектов матчей
    :return: Словарь с результатами подсчета по каждой лиге
    """
    from collections import defaultdict


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
        "corners_win_with_handicap__1_5": 0,
        "corners_win_with_handicap__2_5": 0,
        "corners_win_with_handicap__3_5": 0,
        "corners_win_with_handicap__4_5": 0,
        "total_matches": 0
    })

    for match in matches:
        league_name = match.league_name
        home_corners = match.home_corners
        away_corners = match.away_corners

        total_corners = home_corners + away_corners


        if total_corners == 0 or home_corners is None or away_corners is None:
            continue

        stats = league_corners_stats[league_name]


        stats["total_matches"] += 1

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


        corners_diff = None


        if match.team_home == team:
            corners_diff = home_corners - away_corners
        elif match.team_away == team:
            corners_diff = away_corners - home_corners
        else:
            continue

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


        if corners_diff > -1.5:
            stats["corners_win_with_handicap__1_5"] += 1
        if corners_diff > -2.5:
            stats["corners_win_with_handicap__2_5"] += 1
        if corners_diff > -3.5:
            stats["corners_win_with_handicap__3_5"] += 1
        if corners_diff > -4.5:
            stats["corners_win_with_handicap__4_5"] += 1

    return dict(league_corners_stats)


def calculate_yellow_cards_statistics(matches, team):
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
        "yellow_cards_win_with_handicap_minus__1_5": 0,
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


        if total_corners == 0 or home_corners is None or away_corners is None:
            continue
        stats = league_yellow_cards_stats[league_name]


        stats["total_matches"] += 1


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


        yellow_cards_diff = None


        if match.team_home == team:
            yellow_cards_diff = home_yellow - away_yellow # Фора для домашней команды
        elif match.team_away == team:
            yellow_cards_diff = away_yellow - home_yellow  # Фора для выездной команды
        else:
            continue

        if yellow_cards_diff > 1.5:
            stats["yellow_cards_win_with_handicap_minus_1_5"] += 1
        if yellow_cards_diff > 0.5:
            stats["yellow_cards_win_with_handicap_minus_0_5"] += 1
        if yellow_cards_diff > -0.5:
            stats["yellow_cards_win_with_handicap_minus__0_5"] += 1
        if yellow_cards_diff > -1.5:
            stats["yellow_cards_win_with_handicap_minus__1_5"] += 1

    return dict(league_yellow_cards_stats)

@app.route("/search_teams", methods=["GET"])
def search_teams():
    query = request.args.get("q", "").lower()
    if not query or len(query) < 3:
        return {"teams": []}

    teams = session.query(SoccerMain.team_home).distinct().all()
    filtered_teams = [team[0] for team in teams if team[0].lower().startswith(query)]

    return {"teams": filtered_teams}



@app.route("/hockey", methods=["GET", "POST"])
def hockey():
    selected_bookmaker = "1XBet"
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
    autocomplete = False
    hc_team1 = None
    hc_team2 = None
    book_source = XbetOddsHoc
    sub_source = HockeyMain.xbet_odds_hoc
    if request.method == "POST":

        selected_bookmaker = request.form.get("bookmaker")
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")

        from_date = request.form.get("from_date", "2013-01-01")
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        autocomplete = 'autocomplete-toggle' in request.form


        team1_score = request.form.get('team1_score', '')
        opponent_score = request.form.get('opponent_score', '')
        team2_score = request.form.get('team2_score', '')
        opponent2_score = request.form.get('opponent2_score', '')

        def validate_int(value):
            if value == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None



        if team1 and not isinstance(team1, str):
            errors.append("Команда 1 должна быть строкой.")
        if team2 and not isinstance(team2, str):
            errors.append("Команда 2 должна быть строкой.")


        def validate_float(value):
            if value == "":
                return 0
            try:
                return float(value)
            except ValueError:
                return 0

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


        if None in [win_home_open, win_home_open_plus, win_home_open_minus, win_home_close, win_home_close_plus,
                    win_home_close_minus, to25_open, to25_open_plus, to25_open_minus, to25_close, to25_close_plus,
                    to25_close_minus]:
            errors.append("Values must be INTEGER or FLOAT")





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
        print("Полученные данные:", data)
        if selected_bookmaker == '1XBet':
            book_source = XbetOddsHoc
            sub_source = HockeyMain.xbet_odds_hoc

        try:
            team1_score = int(team1_score) if team1_score else None
            opponent_score = int(opponent_score) if opponent_score else None
            team2_score = int(team2_score) if team2_score else None
            opponent2_score = int(opponent2_score) if opponent2_score else None
        except ValueError:
            team1_score = opponent_score = team2_score = opponent2_score = None

        print(team1_score, opponent_score, team2_score, opponent2_score)


        query = session.query(HockeyMain).join(
            book_source, HockeyMain.match_id == book_source.match_id
        ).options(joinedload(sub_source))

        query = query.filter(HockeyMain.match_date >= from_date, HockeyMain.match_date <= datetime.now())

        if not team1 and not team2:
            errors.append("Please select at least one team for filtering!")
            return render_template(
                "hockey.html",
                selected_bookmaker=selected_bookmaker,
                team1=team1,
                team2=team2,
                errors=errors,
                form_data=data,
                autocomplete=autocomplete
            )



        if team1 and team2:
            query = query.filter(
                or_(
                    (HockeyMain.team_home == team1) | (HockeyMain.team_away == team1),
                    (HockeyMain.team_home == team2) | (HockeyMain.team_away == team2)
                )
            )
        elif team1:
            query = query.filter(
                or_(HockeyMain.team_home == team1, HockeyMain.team_away == team1)
            )
        elif team2:
            query = query.filter(
                or_(HockeyMain.team_home == team2, HockeyMain.team_away == team2)
            )


        if to25_open != 0:
            query = query.filter(
                book_source.odds_5_5_open >= total25MINo,
                book_source.odds_5_5_open <= total25MAXo
            )


        if to25_close != 0:
            query = query.filter(
                book_source.odds_5_5_close >= total25MINc,
                book_source.odds_5_5_close <= total25MAXc
            )


        if win_home_open != 0:
            query = query.filter(
                or_(

                    and_(
                        HockeyMain.team_home == team1,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    ),

                    and_(
                        HockeyMain.team_away == team2,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    )
                )
            )

        if win_home_close != 0:
            query = query.filter(
                or_(

                    and_(
                        HockeyMain.team_home == team1,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    ),

                    and_(
                        HockeyMain.team_away == team2,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    )
                )
            )

        query = query.order_by(HockeyMain.league_name, desc(HockeyMain.match_date))
        matches = query.all()

        match_ids = [match.match_id for match in matches]

        def filter_team_matches(team, score, opponent_score):
            all_team_matches = [match for match in matches if match.team_home == team or match.team_away == team]
            all_team_matches_sorted = sorted(all_team_matches, key=lambda m: m.match_date)

            if score is not None and opponent_score is not None:
                old_matches = [
                    m for m in all_team_matches_sorted
                    if (
                            (m.team_home == team and m.home_score_ft == score and m.away_score_ft == opponent_score) or
                            (m.team_away == team and m.away_score_ft == score and m.home_score_ft == opponent_score)
                    )
                ]

                next_matches = []
                for old_match in old_matches:
                    future_matches_same_league = [
                        x for x in all_team_matches_sorted
                        if x.match_date > old_match.match_date and x.league_name == old_match.league_name
                    ]
                    if future_matches_same_league:
                        next_matches.append(future_matches_same_league[0])

                return next_matches
            else:
                return all_team_matches_sorted

        if team1:
            if team1_score is not None and opponent_score is not None:
                matches_team1 = filter_team_matches(team1, team1_score, opponent_score)
            else:
                matches_team1 = [match for match in matches if match.team_home == team1 or match.team_away == team1]
            goasl_main1 = calculate_goals_statistics_hoc(matches_team1, selected_bookmaker)
            hc_team1 = calculate_handicap_statistics_hoc(matches_team1, team1, selected_bookmaker)


        if team2:
            if team2_score is not None and opponent2_score is not None:
                matches_team2 = filter_team_matches(team2, team2_score, opponent2_score)
            else:
                matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]
            goasl_main2 = calculate_goals_statistics_hoc(matches_team2, selected_bookmaker)
            hc_team2 = calculate_handicap_statistics_hoc(matches_team2, team2, selected_bookmaker)


    return render_template(
        "hockey.html",
        selected_bookmaker=selected_bookmaker,
        team1=team1,
        team2=team2,
        errors=errors,
        matches_team1=matches_team1,
        matches_team2=matches_team2,
        form_data = data,
        goasl_main1=goasl_main1,
        goasl_main2=goasl_main2,
        hc_team1=hc_team1,
        hc_team2=hc_team2,
        autocomplete=autocomplete
    )

@app.route("/search_hockey_teams", methods=["GET"])
def search_hockey_teams():
    query = request.args.get("q", "").lower()
    if not query or len(query) < 3:
        return {"teams": []}


    teams = session.query(HockeyMain.team_home).distinct().all()
    filtered_teams = [team[0] for team in teams if team[0].lower().startswith(query)]

    return {"teams": filtered_teams}


def calculate_goals_statistics_hoc(matches, selected_bookmaker):
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
        "over_4_5": 0,
        "over_5_5": 0,
        "over_6_5": 0,
        "over_7_5": 0,
        "over_8_5": 0,
        "over_9_5": 0,
        "over_10_5": 0,
        "roi_total_5_5": 0.0,
        "total_bets_count": 0,
    })

    for match in matches:
        league_name = match.league_name
        total_goals = match.home_score_ft + match.away_score_ft
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft

        stats = league_stats[league_name]


        stats["total_matches"] += 1


        if total_goals > 0.5:
            stats["over_0_5"] += 1
        if total_goals > 1.5:
            stats["over_1_5"] += 1
        if total_goals > 2.5:
            stats["over_2_5"] += 1
        if total_goals > 3.5:
            stats["over_3_5"] += 1
        if total_goals > 4.5:
            stats["over_4_5"] += 1
        if total_goals > 5.5:
            stats["over_5_5"] += 1
        if total_goals > 6.5:
            stats["over_6_5"] += 1
        if total_goals > 7.5:
            stats["over_7_5"] += 1
        if total_goals > 8.5:
            stats["over_8_5"] += 1
        if total_goals > 9.5:
            stats["over_9_5"] += 1
        if total_goals > 10.5:
            stats["over_10_5"] += 1

        if selected_bookmaker == "1XBet":
            odds_source = getattr(match, 'xbet_odds_hoc', None)
        else:
            odds_source = None

        # ROI для total > 2.5 с учетом коэффициента закрытия
        if odds_source and hasattr(odds_source, "odds_5_5_close") and odds_source.odds_5_5_close:
            odds_5_5_close = odds_source.odds_5_5_close
            stats["total_bets_count"] += 1
            if total_goals > 5.5:
                stats["roi_total_5_5"] += odds_5_5_close - 1  # Выигрыш минус ставка
            else:
                stats["roi_total_5_5"] -= 1



    for stats in league_stats.values():
        if stats["total_bets_count"] > 0:
            stats["roi_total_5_5"] = round(stats["roi_total_5_5"] / stats["total_bets_count"] * 100, 2)
        else:
            stats["roi_total_5_5"] = None

    return dict(league_stats)

def calculate_handicap_statistics_hoc(matches, team, selected_bookmaker):
    """
    Рассчитывает полную статистику матчей по лигам для фор от -5.5 до +5.5 с учетом коэффициента из i.xbet_odds.

    :param matches: Список объектов матчей
    :param selected_bookmaker: Выбранный букмекер
    :return: Словарь со всей статистикой по лигам
    """
    from collections import defaultdict


    league_stats = defaultdict(lambda: {
        "total_matches": 0,
        "handicap__0_5": 0,
        "handicap__1_5": 0,
        "handicap__2_5": 0,
        "handicap__3_5": 0,
        "handicap__4_5": 0,
        "handicap__5_5": 0,
        "handicap_0_5": 0,
        "handicap_1_5": 0,
        "handicap_2_5": 0,
        "handicap_3_5": 0,
        "handicap_4_5": 0,
        "handicap_5_5": 0,
        "roi_win": 0.0,
        "total_bets_count": 0,
    })



    for match in matches:
        league_name = match.league_name
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft
        stats = league_stats[league_name]
        stats["total_matches"] += 1

        if selected_bookmaker == "1XBet":
            odds_source = getattr(match, 'xbet_odds_hoc', None)
        else:
            odds_source = None



        if match.team_home == team:
            current_hc = home_goals - away_goals
            odds_home = odds_source.win_home_close

        elif match.team_away == team:
            current_hc = away_goals - home_goals
            odds_home = odds_source.win_away_close

        else:
            continue


        if current_hc > -5.5:
            stats["handicap_5_5"] += 1
        if current_hc > -4.5:
            stats["handicap_4_5"] += 1
        if current_hc > -3.5:
            stats["handicap_3_5"] += 1
        if current_hc > -2.5:
            stats["handicap_2_5"] += 1
        if current_hc > -1.5:
            stats["handicap_1_5"] += 1
        if current_hc > -0.5:
            stats["handicap_0_5"] += 1
        if current_hc > 0.5:
            stats["handicap__0_5"] += 1
        if current_hc > 1.5:
            stats["handicap__1_5"] += 1
        if current_hc >2.5:
            stats["handicap__2_5"] += 1
        if current_hc > 3.5:
            stats["handicap__3_5"] += 1
        if current_hc > 4.5:
            stats["handicap__4_5"] += 1
        if current_hc > 5.5:
            stats["handicap__5_5"] += 1


        if odds_home is not None:
            stats["total_bets_count"] += 1
            if current_hc > 0:
                stats["roi_win"] += odds_home - 1
            else:
                stats["roi_win"] -= 1


    for stats in league_stats.values():
        if stats["total_bets_count"] > 0:
            stats["roi_win"] = round(stats["roi_win"] / stats["total_bets_count"] * 100, 2)
        else:
            stats["roi_win"] = None  # Если ставок не было, ROI = None

    return dict(league_stats)


@app.route("/handball", methods=["GET", "POST"])
def handball():
    selected_bookmaker = "1XBet"
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
    autocomplete = False
    hc_team1 = None
    hc_team2 = None
    book_source = XbetOddsHb
    sub_source = HandballMain.xbet_odds_hb
    mid_total = 60
    mid_total_plus = 3
    mid_total_minus = 3
    hc_base = 0
    hc_vise = 0
    if request.method == "POST":

        selected_bookmaker = request.form.get("bookmaker")
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")

        from_date = request.form.get("from_date", "2013-01-01")
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        autocomplete = 'autocomplete-toggle' in request.form


        team1_score = request.form.get('team1_score', '')
        opponent_score = request.form.get('opponent_score', '')
        team2_score = request.form.get('team2_score', '')
        opponent2_score = request.form.get('opponent2_score', '')
        mid_total = request.form.get('mid_total', '')


        def validate_int(value):
            if value == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None



        if team1 and not isinstance(team1, str):
            errors.append("Must be string.")
        if team2 and not isinstance(team2, str):
            errors.append("Must be string.")


        def validate_float(value):
            if value == "":
                return 0
            try:
                return float(value)
            except ValueError:
                return 0

        # Проверка ставок на числа
        win_home_open = validate_float(request.form.get("win_home_open"))
        win_home_open_plus = validate_float(request.form.get("win_home_open_plus"))
        win_home_open_minus = validate_float(request.form.get("win_home_open_minus"))
        win_home_close = validate_float(request.form.get("win_home_close"))
        win_home_close_plus = validate_float(request.form.get("win_home_close_plus"))
        win_home_close_minus = validate_float(request.form.get("win_home_close_minus"))
        mid_total = validate_float(request.form.get("mid_total"))
        mid_total_plus = validate_float(request.form.get("mid_total_plus"))
        mid_total_minus = validate_float(request.form.get("mid_total_minus"))
        to25_open = validate_float(request.form.get("to25_open"))
        to25_open_plus = validate_float(request.form.get("to25_open_plus"))
        to25_open_minus = validate_float(request.form.get("to25_open_minus"))
        to25_close = validate_float(request.form.get("to25_close"))
        to25_close_plus = validate_float(request.form.get("to25_close_plus"))
        to25_close_minus = validate_float(request.form.get("to25_close_minus"))

        print(mid_total, 'kkkkkkkkkkkkkkkkkk')
        print(mid_total == '')
        if mid_total  == 0:
            mid_total = 60
            mid_total_plus = 60
            mid_total_minus = 60
        print(mid_total)


        total25MAXo = to25_open + to25_open_plus
        total25MINo = to25_open - to25_open_minus
        total25MAXc = to25_close + to25_close_plus
        total25MINc = to25_close - to25_close_minus
        win1OpenMAX = win_home_open + win_home_open_plus
        win1OpenMIN = win_home_open - win_home_open_minus
        win1CloseMAX = win_home_close + win_home_close_plus
        win1CloseMIN = win_home_close - win_home_close_minus
        totalValuePlus = mid_total + mid_total_plus
        totalValueMinus = mid_total - mid_total_minus

        print(totalValuePlus, totalValueMinus)

        if None in [win_home_open, win_home_open_plus, win_home_open_minus, win_home_close, win_home_close_plus,
                    win_home_close_minus, to25_open, to25_open_plus, to25_open_minus, to25_close, to25_close_plus,
                    to25_close_minus]:
            errors.append("Values must be INTEGER or FLOAT")


        data = {
            "team1": team1,
            "team2": team2,
            "win_home_open": win_home_open,
            "win_home_open_plus": win_home_open_plus,
            "win_home_open_minus": win_home_open_minus,
            "win_home_close": win_home_close,
            "win_home_close_plus": win_home_close_plus,
            "win_home_close_minus": win_home_close_minus,
            "mid_total": mid_total,
            "mid_total_plus": mid_total_plus,
            "mid_total_minus": mid_total_minus,
            "to25_open": to25_open,
            "to25_open_plus": to25_open_plus,
            "to25_open_minus": to25_open_minus,
            "to25_close": to25_close,
            "to25_close_plus": to25_close_plus,
            "to25_close_minus": to25_close_minus,
            "bookmaker": selected_bookmaker,
            "from_date": from_date
        }
        print("Полученные данные:", data)
        if selected_bookmaker == '1XBet':
            book_source = XbetOddsHb
            sub_source = HandballMain.xbet_odds_hb

        try:
            team1_score = int(team1_score) if team1_score else None
            opponent_score = int(opponent_score) if opponent_score else None
            team2_score = int(team2_score) if team2_score else None
            opponent2_score = int(opponent2_score) if opponent2_score else None
        except ValueError:
            team1_score = opponent_score = team2_score = opponent2_score = None

        print(team1_score, opponent_score, team2_score, opponent2_score)

        # Базовый запрос
        query = session.query(HandballMain).join(
            book_source, HandballMain.match_id == book_source.match_id
        ).options(joinedload(sub_source))

        query = query.filter(HandballMain.match_date >= from_date, HandballMain.match_date <= datetime.now())

        if not team1 and not team2:
            errors.append("Please select at least one team for filtering!")
            return render_template(
                "handball.html",
                selected_bookmaker=selected_bookmaker,
                team1=team1,
                team2=team2,
                errors=errors,
                form_data=data,
                autocomplete=autocomplete
            )


        # Фильтр по командам
        if team1 and team2:
            query = query.filter(
                or_(
                    (HandballMain.team_home == team1) | (HandballMain.team_away == team1),
                    (HandballMain.team_home == team2) | (HandballMain.team_away == team2)
                )
            )
        elif team1:
            query = query.filter(
                or_(HandballMain.team_home == team1, HandballMain.team_away == team1)
            )
        elif team2:
            query = query.filter(
                or_(HandballMain.team_home == team2, HandballMain.team_away == team2)
            )

        # Фильтр по odds_2_5_open
        if to25_open != 0:
            query = query.filter(
                book_source.odds_5_5_open >= total25MINo,
                book_source.odds_5_5_open <= total25MAXo
            )

        # Фильтр по odds_2_5_close
        if to25_close != 0:
            query = query.filter(
                book_source.odds_5_5_close >= total25MINc,
                book_source.odds_5_5_close <= total25MAXc
            )

        # Фильтр по win1_open
        if win_home_open != 0:
            query = query.filter(
                or_(
                    # Для первой команды как хозяина
                    and_(
                        HandballMain.team_home == team1,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    ),
                    # Для второй команды как гостя
                    and_(
                        HandballMain.team_away == team2,
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
                        HandballMain.team_home == team1,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    ),
                    # Для второй команды как гостя
                    and_(
                        HandballMain.team_away == team2,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    )
                )
            )

        if mid_total !=0:
            query = query.filter(
                book_source.total_value >= totalValueMinus,
                book_source.total_value <= totalValuePlus
            )

        query = query.order_by(HandballMain.league_name, desc(HandballMain.match_date))
        matches = query.all()

        match_ids = [match.match_id for match in matches]
        # Логика работы с командами
        def filter_team_matches(team, score, opponent_score):
            all_team_matches = [match for match in matches if match.team_home == team or match.team_away == team]
            all_team_matches_sorted = sorted(all_team_matches, key=lambda m: m.match_date)

            if score is not None and opponent_score is not None:
                old_matches = [
                    m for m in all_team_matches_sorted
                    if (
                            (m.team_home == team and m.home_score_ft == score and m.away_score_ft == opponent_score) or
                            (m.team_away == team and m.away_score_ft == score and m.home_score_ft == opponent_score)
                    )
                ]

                next_matches = []
                for old_match in old_matches:
                    future_matches_same_league = [
                        x for x in all_team_matches_sorted
                        if x.match_date > old_match.match_date and x.league_name == old_match.league_name
                    ]
                    if future_matches_same_league:
                        next_matches.append(future_matches_same_league[0])

                return next_matches
            else:
                return all_team_matches_sorted

        if team1:
            if team1_score is not None and opponent_score is not None:
                matches_team1 = filter_team_matches(team1, team1_score, opponent_score)
            else:
                matches_team1 = [match for match in matches if match.team_home == team1 or match.team_away == team1]
            goasl_main1 = calculate_goals_statistics_hb(matches_team1,mid_total, selected_bookmaker)
            hc_team1 = calculate_handicap_statistics_hb(matches_team1, team1, selected_bookmaker)


        if team2:
            if team2_score is not None and opponent2_score is not None:
                matches_team2 = filter_team_matches(team2, team2_score, opponent2_score)
            else:
                matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]
            goasl_main2 = calculate_goals_statistics_hb(matches_team2,mid_total, selected_bookmaker)
            hc_team2 = calculate_handicap_statistics_hb(matches_team2, team2, selected_bookmaker)

        print(mid_total, 'again')


    return render_template(
        "handball.html",
        selected_bookmaker=selected_bookmaker,
        team1=team1,
        team2=team2,
        errors=errors,
        matches_team1=matches_team1,
        matches_team2=matches_team2,
        form_data = data,
        goasl_main1=goasl_main1,
        goasl_main2=goasl_main2,
        hc_team1=hc_team1,
        hc_team2=hc_team2,
        mid_total= int(mid_total),
        hc_base=hc_base,
        hc_vise=hc_vise,
        autocomplete=autocomplete
    )

@app.route("/search_handball_teams", methods=["GET"])
def search_handball_teams():
    query = request.args.get("q", "").lower()
    if not query or len(query) < 3:
        return {"teams": []}

    teams = session.query(HandballMain.team_home).distinct().all()  # Замените на ваш источник данных
    filtered_teams = [team[0] for team in teams if team[0].lower().startswith(query)]

    return {"teams": filtered_teams}


def calculate_handicap_statistics_hb(matches, team, selected_bookmaker):
    """
    Рассчитывает полную статистику матчей по лигам для фор от -5.5 до +5.5 с учетом коэффициента из i.xbet_odds.

    :param matches: Список объектов матчей
    :param selected_bookmaker: Выбранный букмекер
    :return: Словарь со всей статистикой по лигам
    """
    from collections import defaultdict

    # Инициализируем статистику
    league_stats = defaultdict(lambda: {
        "total_matches": 0,
        "handicap__0_5": 0,
        "handicap__1_5": 0,
        "handicap__2_5": 0,
        "handicap__3_5": 0,
        "handicap__4_5": 0,
        "handicap__5_5": 0,
        "handicap__6_5": 0,
        "handicap__7_5": 0,
        "handicap__8_5": 0,
        "handicap__9_5": 0,
        "handicap__10_5": 0,
        "handicap__11_5": 0,
        "handicap__12_5": 0,
        "handicap__13_5": 0,
        "handicap__14_5": 0,
        "handicap__15_5": 0,
        "handicap__16_5": 0,
        "handicap_0_5": 0,
        "handicap_1_5": 0,
        "handicap_2_5": 0,
        
        "handicap_3_5": 0,
        "handicap_4_5": 0,
        "handicap_5_5": 0,
        "handicap_6_5": 0,
        "handicap_7_5": 0,
        "handicap_8_5": 0,
        "handicap_9_5": 0,
        "handicap_10_5": 0,
        "handicap_11_5": 0,
        "handicap_12_5": 0,
        "handicap_13_5": 0,
        "handicap_14_5": 0,
        "handicap_15_5": 0,
        "handicap_16_5": 0,
        "total_bets_count": 0,  # Количество матчей с коэффициентом закрытия
    })



    for match in matches:
        league_name = match.league_name
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft
        stats = league_stats[league_name]
        stats["total_matches"] += 1

        if selected_bookmaker == "1XBet":
            odds_source = getattr(match, 'xbet_odds_hoc', None)
        else:
            odds_source = None



        if match.team_home == team:
            current_hc = home_goals - away_goals

        elif match.team_away == team:
            current_hc = away_goals - home_goals

        else:
            continue

        if current_hc > -16.5:
            stats["handicap_16_5"] += 1
        if current_hc > -15.5:
            stats["handicap_15_5"] += 1
        if current_hc > -14.5:
            stats["handicap_14_5"] += 1
        if current_hc > -13.5:
            stats["handicap_13_5"] += 1
        if current_hc > -12.5:
            stats["handicap_12_5"] += 1
        if current_hc > -11.5:
            stats["handicap_11_5"] += 1
        if current_hc > -10.5:
            stats["handicap_10_5"] += 1
        if current_hc > -9.5:
            stats["handicap_9_5"] += 1
        if current_hc > -8.5:
            stats["handicap_8_5"] += 1
        if current_hc > -7.5:
            stats["handicap_7_5"] += 1
        if current_hc > -6.5:
            stats["handicap_6_5"] += 1
        if current_hc > -5.5:
            stats["handicap_5_5"] += 1
        if current_hc > -4.5:
            stats["handicap_4_5"] += 1
        if current_hc > -3.5:
            stats["handicap_3_5"] += 1
        if current_hc > -2.5:
            stats["handicap_2_5"] += 1
        if current_hc > -1.5:
            stats["handicap_1_5"] += 1
        if current_hc > -0.5:
            stats["handicap_0_5"] += 1
        if current_hc > 0.5:
            stats["handicap__0_5"] += 1
        if current_hc > 1.5:
            stats["handicap__1_5"] += 1
        if current_hc >2.5:
            stats["handicap__2_5"] += 1
        if current_hc > 3.5:
            stats["handicap__3_5"] += 1
        if current_hc > 4.5:
            stats["handicap__4_5"] += 1
        if current_hc > 5.5:
            stats["handicap__5_5"] += 1
        if current_hc > 6.5:
            stats["handicap__6_5"] += 1
        if current_hc > 7.5:
            stats["handicap__7_5"] += 1
        if current_hc >8.5:
            stats["handicap__8_5"] += 1
        if current_hc > 9.5:
            stats["handicap__9_5"] += 1
        if current_hc > 10.5:
            stats["handicap__10_5"] += 1
        if current_hc > 11.5:
            stats["handicap__11_5"] += 1
        if current_hc > 12.5:
            stats["handicap__12_5"] += 1
        if current_hc >13.5:
            stats["handicap__13_5"] += 1
        if current_hc > 14.5:
            stats["handicap__14_5"] += 1
        if current_hc > 15.5:
            stats["handicap__15_5"] += 1
        if current_hc > 16.5:
            stats["handicap__16_5"] += 1


    return dict(league_stats)

def calculate_goals_statistics_hb(matches, mid_total, selected_bookmaker):
    """
    Рассчитывает полную статистику матчей по лигам, включая ROI для total > 2.5 с учетом коэффициента из i.xbet_odds.odds_2_5_close.

    :param matches: Список объектов матчей
    :param selected_bookmaker: Выбранный букмекер
    :return: Словарь со всей статистикой по лигам
    """
    from collections import defaultdict

    league_stats = defaultdict(lambda: {
        "total_matches": 0,
        "over_0_0": 0,
        "over_0_5": 0,
        "over_1_5": 0,
        "over_2_5": 0,
        "over_3_5": 0,
        "over_4_5": 0,
        "over_5_5": 0,
        "over_6_5": 0,
        "over_7_5": 0,
        "over_8_5": 0,
        "over_9_5": 0,
        "over_10_5": 0,
        "over_11_5": 0,
        "min_ft": float('inf'),
        "max_ft": float('-inf'),
        "total_bets_count": 0,
    })

    for match in matches:
        league_name = match.league_name
        total_goals = match.home_score_ft + match.away_score_ft
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft

        stats = league_stats[league_name]

        stats["total_matches"] += 1

        # Подсчет голов
        if total_goals > mid_total - 6:
            stats["over_0_0"] += 1
        if total_goals > mid_total - 5:
            stats["over_0_5"] += 1
        if total_goals > mid_total - 4:
            stats["over_1_5"] += 1
        if total_goals > mid_total - 3:
            stats["over_2_5"] += 1
        if total_goals > mid_total - 2:
            stats["over_3_5"] += 1
        if total_goals > mid_total - 1:
            stats["over_4_5"] += 1
        if total_goals > mid_total:
            stats["over_5_5"] += 1
        if total_goals > mid_total + 1:
            stats["over_6_5"] += 1
        if total_goals > mid_total + 2:
            stats["over_7_5"] += 1
        if total_goals > mid_total + 3:
            stats["over_8_5"] += 1
        if total_goals > mid_total + 4:
            stats["over_9_5"] += 1
        if total_goals > mid_total + 5:
            stats["over_10_5"] += 1
        if total_goals > mid_total + 6:
            stats["over_11_5"] += 1


        stats["min_ft"] = min(stats["min_ft"], total_goals)
        stats["max_ft"] = max(stats["max_ft"], total_goals)


        if selected_bookmaker == "1XBet":
            odds_source = getattr(match, 'xbet_odds_hoc', None)
            if odds_source:
                stats["total_bets_count"] += 1
        else:
            odds_source = None


    return dict(league_stats)

###################################################BASKETBALL##########################################################

@app.route("/basketball", methods=["GET", "POST"])
def basketball():
    selected_bookmaker = "1XBet"  # Значение по умолчанию
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
    autocomplete = False
    hc_team1 = None
    hc_team2 = None
    book_source = XbetOddsHb
    sub_source = None
    mid_total = 160
    mid_total_plus = 4
    mid_total_minus = 4
    hc_base = 0
    hc_vise = 0
    if request.method == "POST":

        selected_bookmaker = request.form.get("bookmaker")
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")

        from_date = request.form.get("from_date", "2013-01-01")
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        autocomplete = 'autocomplete-toggle' in request.form

        team1_score = request.form.get('team1_score', '')
        opponent_score = request.form.get('opponent_score', '')
        team2_score = request.form.get('team2_score', '')
        opponent2_score = request.form.get('opponent2_score', '')
        mid_total = request.form.get('mid_total', '')



        def validate_int(value):
            if value == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None


        if team1 and not isinstance(team1, str):
            errors.append("Must be string.")
        if team2 and not isinstance(team2, str):
            errors.append("Must be string.")


        def validate_float(value):
            if value == "":
                return 0
            try:
                return float(value)
            except ValueError:
                return 0

        win_home_open = validate_float(request.form.get("win_home_open"))
        win_home_open_plus = validate_float(request.form.get("win_home_open_plus"))
        win_home_open_minus = validate_float(request.form.get("win_home_open_minus"))
        win_home_close = validate_float(request.form.get("win_home_close"))
        win_home_close_plus = validate_float(request.form.get("win_home_close_plus"))
        win_home_close_minus = validate_float(request.form.get("win_home_close_minus"))
        mid_total = validate_float(request.form.get("mid_total"))
        mid_total_plus = validate_float(request.form.get("mid_total_plus"))
        mid_total_minus = validate_float(request.form.get("mid_total_minus"))
        to25_open = validate_float(request.form.get("to25_open"))
        to25_open_plus = validate_float(request.form.get("to25_open_plus"))
        to25_open_minus = validate_float(request.form.get("to25_open_minus"))
        to25_close = validate_float(request.form.get("to25_close"))
        to25_close_plus = validate_float(request.form.get("to25_close_plus"))
        to25_close_minus = validate_float(request.form.get("to25_close_minus"))

        print(mid_total, 'kkkkkkkkkkkkkkkkkk')
        print(mid_total == '')
        if mid_total == 0:
            mid_total = 160
            mid_total_minus = 160
            mid_total_plus = 160
        print(mid_total)

        total25MAXo = to25_open + to25_open_plus
        total25MINo = to25_open - to25_open_minus
        total25MAXc = to25_close + to25_close_plus
        total25MINc = to25_close - to25_close_minus
        win1OpenMAX = win_home_open + win_home_open_plus
        win1OpenMIN = win_home_open - win_home_open_minus
        win1CloseMAX = win_home_close + win_home_close_plus
        win1CloseMIN = win_home_close - win_home_close_minus
        totalValuePlus = mid_total + mid_total_plus
        totalValueMinus = mid_total - mid_total_minus

        print(totalValuePlus, totalValueMinus)
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
            "mid_total": mid_total,
            "mid_total_plus": mid_total_plus,
            "mid_total_minus": mid_total_minus,
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
            book_source = Bet365OddsBb
            sub_source = BasketballMain.bet365_odds_bb
        if selected_bookmaker == '1XBet':
            book_source = XbetOddsBb
            sub_source = BasketballMain.xbet_odds_bb

        try:
            team1_score = int(team1_score) if team1_score else None
            opponent_score = int(opponent_score) if opponent_score else None
            team2_score = int(team2_score) if team2_score else None
            opponent2_score = int(opponent2_score) if opponent2_score else None
        except ValueError:
            team1_score = opponent_score = team2_score = opponent2_score = None

        print(team1_score, opponent_score, team2_score, opponent2_score)

        # Базовый запрос
        query = session.query(BasketballMain).join(
            book_source, BasketballMain.match_id == book_source.match_id
        ).options(joinedload(sub_source))

        query = query.filter(BasketballMain.match_date >= from_date,BasketballMain.match_date <= datetime.now())

        if not team1 and not team2:
            errors.append("Please select at least one team for filtering!")
            return render_template(
                "basketball.html",
                selected_bookmaker=selected_bookmaker,
                team1=team1,
                team2=team2,
                errors=errors,
                form_data=data,
                autocomplete=autocomplete
            )

        # Фильтр по командам
        if team1 and team2:
            query = query.filter(
                or_(
                    (BasketballMain.team_home == team1) | (BasketballMain.team_away == team1),
                    (BasketballMain.team_home == team2) | (BasketballMain.team_away == team2)
                )
            )
        elif team1:
            query = query.filter(
                or_(BasketballMain.team_home == team1, BasketballMain.team_away == team1)
            )
        elif team2:
            query = query.filter(
                or_(BasketballMain.team_home == team2, BasketballMain.team_away == team2)
            )

        # Фильтр по odds_2_5_open
        if to25_open != 0:
            query = query.filter(
                book_source.odds_5_5_open >= total25MINo,
                book_source.odds_5_5_open <= total25MAXo
            )

        # Фильтр по odds_2_5_close
        if to25_close != 0:
            query = query.filter(
                book_source.odds_5_5_close >= total25MINc,
                book_source.odds_5_5_close <= total25MAXc
            )

        # Фильтр по win1_open
        if win_home_open != 0:
            query = query.filter(
                or_(
                    # Для первой команды как хозяина
                    and_(
                        BasketballMain.team_home == team1,
                        book_source.win_home_open >= win1OpenMIN,
                        book_source.win_home_open <= win1OpenMAX,
                    ),
                    # Для второй команды как гостя
                    and_(
                        BasketballMain.team_away == team2,
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
                        BasketballMain.team_home == team1,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    ),
                    # Для второй команды как гостя
                    and_(
                        BasketballMain.team_away == team2,
                        book_source.win_home_close >= win1CloseMIN,
                        book_source.win_home_close <= win1CloseMAX,
                    )
                )
            )

        if mid_total != 0:
            query = query.filter(
                book_source.total_value >= totalValueMinus,
                book_source.total_value <= totalValuePlus
            )

        query = query.order_by(BasketballMain.league_name, desc(BasketballMain.match_date))
        matches = query.all()

        match_ids = [match.match_id for match in matches]

        def filter_team_matches(team, score, opponent_score):
            all_team_matches = [match for match in matches if match.team_home == team or match.team_away == team]
            all_team_matches_sorted = sorted(all_team_matches, key=lambda m: m.match_date)

            if score is not None and opponent_score is not None:
                old_matches = [
                    m for m in all_team_matches_sorted
                    if (
                            (m.team_home == team and m.home_score_ft == score and m.away_score_ft == opponent_score) or
                            (m.team_away == team and m.away_score_ft == score and m.home_score_ft == opponent_score)
                    )
                ]

                next_matches = []
                for old_match in old_matches:
                    future_matches_same_league = [
                        x for x in all_team_matches_sorted
                        if x.match_date > old_match.match_date and x.league_name == old_match.league_name
                    ]
                    if future_matches_same_league:
                        next_matches.append(future_matches_same_league[0])

                return next_matches
            else:
                return all_team_matches_sorted

        if team1:
            if team1_score is not None and opponent_score is not None:
                matches_team1 = filter_team_matches(team1, team1_score, opponent_score)
            else:
                matches_team1 = [match for match in matches if match.team_home == team1 or match.team_away == team1]
            goasl_main1 = calculate_goals_statistics_bb(matches_team1, mid_total, selected_bookmaker)
            hc_team1 = calculate_handicap_statistics_bb(matches_team1, team1, selected_bookmaker)

        if team2:
            if team2_score is not None and opponent2_score is not None:
                matches_team2 = filter_team_matches(team2, team2_score, opponent2_score)
            else:
                matches_team2 = [match for match in matches if match.team_home == team2 or match.team_away == team2]
            goasl_main2 = calculate_goals_statistics_bb(matches_team2, mid_total, selected_bookmaker)
            hc_team2 = calculate_handicap_statistics_bb(matches_team2, team2, selected_bookmaker)

        print(mid_total, 'again')

    return render_template(
        "basketball.html",
        selected_bookmaker=selected_bookmaker,
        team1=team1,
        team2=team2,
        errors=errors,
        matches_team1=matches_team1,
        matches_team2=matches_team2,
        form_data=data,
        goasl_main1=goasl_main1,
        goasl_main2=goasl_main2,
        hc_team1=hc_team1,
        hc_team2=hc_team2,
        mid_total=int(mid_total),
        hc_base=hc_base,
        hc_vise=hc_vise,
        autocomplete=autocomplete
    )


@app.route("/search_basketball_teams", methods=["GET"])
def search_basketball_teams():
    query = request.args.get("q", "").lower()
    if not query or len(query) < 3:
        return {"teams": []}  # Пустой список, если запрос короткий

    # Пример: фильтрация списка хоккейных команд из базы данных
    teams = session.query(BasketballMain.team_home).distinct().all()  # Замените на ваш источник данных
    filtered_teams = [team[0] for team in teams if team[0].lower().startswith(query)]

    return {"teams": filtered_teams}


def calculate_handicap_statistics_bb(matches, team, selected_bookmaker):
    """
    Рассчитывает полную статистику матчей по лигам для фор от -5.5 до +5.5 с учетом коэффициента из i.xbet_odds.

    :param matches: Список объектов матчей
    :param selected_bookmaker: Выбранный букмекер
    :return: Словарь со всей статистикой по лигам
    """
    from collections import defaultdict

    # Инициализируем статистику
    league_stats = defaultdict(lambda: {
        "total_matches": 0,
        "handicap__0_5": 0,
        "handicap__1_5": 0,
        "handicap__2_5": 0,
        "handicap__3_5": 0,
        "handicap__4_5": 0,
        "handicap__5_5": 0,
        "handicap__6_5": 0,
        "handicap__7_5": 0,
        "handicap__8_5": 0,
        "handicap__9_5": 0,
        "handicap__10_5": 0,
        "handicap__11_5": 0,
        "handicap__12_5": 0,
        "handicap__13_5": 0,
        "handicap__14_5": 0,
        "handicap__15_5": 0,
        "handicap__16_5": 0,
        "handicap_0_5": 0,
        "handicap_1_5": 0,
        "handicap_2_5": 0,

        "handicap_3_5": 0,
        "handicap_4_5": 0,
        "handicap_5_5": 0,
        "handicap_6_5": 0,
        "handicap_7_5": 0,
        "handicap_8_5": 0,
        "handicap_9_5": 0,
        "handicap_10_5": 0,
        "handicap_11_5": 0,
        "handicap_12_5": 0,
        "handicap_13_5": 0,
        "handicap_14_5": 0,
        "handicap_15_5": 0,
        "handicap_16_5": 0,
        "total_bets_count": 0,  # Количество матчей с коэффициентом закрытия
    })

    for match in matches:
        league_name = match.league_name
        home_goals = match.home_score_ft
        away_goals = match.away_score_ft
        stats = league_stats[league_name]
        stats["total_matches"] += 1

        # Определяем фора для выбранной команды
        if match.team_home == team:
            current_hc = home_goals - away_goals  # Фора для домашней команды

        elif match.team_away == team:
            current_hc = away_goals - home_goals  # Фора для выездной команды

        else:
            continue

        # Подсчитываем форы от -5.5 до +5.5 для различных диапазонов форы
        if current_hc > -16.5:
            stats["handicap_16_5"] += 1
        if current_hc > -15.5:
            stats["handicap_15_5"] += 1
        if current_hc > -14.5:
            stats["handicap_14_5"] += 1
        if current_hc > -13.5:
            stats["handicap_13_5"] += 1
        if current_hc > -12.5:
            stats["handicap_12_5"] += 1
        if current_hc > -11.5:
            stats["handicap_11_5"] += 1
        if current_hc > -10.5:
            stats["handicap_10_5"] += 1
        if current_hc > -9.5:
            stats["handicap_9_5"] += 1
        if current_hc > -8.5:
            stats["handicap_8_5"] += 1
        if current_hc > -7.5:
            stats["handicap_7_5"] += 1
        if current_hc > -6.5:
            stats["handicap_6_5"] += 1
        if current_hc > -5.5:
            stats["handicap_5_5"] += 1
        if current_hc > -4.5:
            stats["handicap_4_5"] += 1
        if current_hc > -3.5:
            stats["handicap_3_5"] += 1
        if current_hc > -2.5:
            stats["handicap_2_5"] += 1
        if current_hc > -1.5:
            stats["handicap_1_5"] += 1
        if current_hc > -0.5:
            stats["handicap_0_5"] += 1
        if current_hc > 0.5:
            stats["handicap__0_5"] += 1
        if current_hc > 1.5:
            stats["handicap__1_5"] += 1
        if current_hc > 2.5:
            stats["handicap__2_5"] += 1
        if current_hc > 3.5:
            stats["handicap__3_5"] += 1
        if current_hc > 4.5:
            stats["handicap__4_5"] += 1
        if current_hc > 5.5:
            stats["handicap__5_5"] += 1
        if current_hc > 6.5:
            stats["handicap__6_5"] += 1
        if current_hc > 7.5:
            stats["handicap__7_5"] += 1
        if current_hc > 8.5:
            stats["handicap__8_5"] += 1
        if current_hc > 9.5:
            stats["handicap__9_5"] += 1
        if current_hc > 10.5:
            stats["handicap__10_5"] += 1
        if current_hc > 11.5:
            stats["handicap__11_5"] += 1
        if current_hc > 12.5:
            stats["handicap__12_5"] += 1
        if current_hc > 13.5:
            stats["handicap__13_5"] += 1
        if current_hc > 14.5:
            stats["handicap__14_5"] += 1
        if current_hc > 15.5:
            stats["handicap__15_5"] += 1
        if current_hc > 16.5:
            stats["handicap__16_5"] += 1

    return dict(league_stats)


def calculate_goals_statistics_bb(matches, mid_total, selected_bookmaker):
    """
    Рассчитывает полную статистику матчей по лигам, включая ROI для total > 2.5 с учетом коэффициента из i.xbet_odds.odds_2_5_close.

    :param matches: Список объектов матчей
    :param selected_bookmaker: Выбранный букмекер
    :return: Словарь со всей статистикой по лигам
    """
    from collections import defaultdict

    league_stats = defaultdict(lambda: {
        "total_matches": 0,
        "over_0_0": 0,
        "over_0_5": 0,
        "over_1_5": 0,
        "over_2_5": 0,
        "over_3_5": 0,
        "over_4_5": 0,
        "over_5_5": 0,
        "over_6_5": 0,
        "over_7_5": 0,
        "over_8_5": 0,
        "over_9_5": 0,
        "over_10_5": 0,
        "over_11_5": 0,
        "min_ft": float('inf'),  # Изначально задаем минимальный счет как бесконечность
        "max_ft": float('-inf'),  # Изначально задаем максимальный счет как минус бесконечность
        "total_bets_count": 0,  # Количество матчей с коэффициентом закрытия
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
        if total_goals > mid_total - 6:
            stats["over_0_0"] += 1
        if total_goals > mid_total - 5:
            stats["over_0_5"] += 1
        if total_goals > mid_total - 4:
            stats["over_1_5"] += 1
        if total_goals > mid_total - 3:
            stats["over_2_5"] += 1
        if total_goals > mid_total - 2:
            stats["over_3_5"] += 1
        if total_goals > mid_total - 1:
            stats["over_4_5"] += 1
        if total_goals > mid_total:
            stats["over_5_5"] += 1
        if total_goals > mid_total + 1:
            stats["over_6_5"] += 1
        if total_goals > mid_total + 2:
            stats["over_7_5"] += 1
        if total_goals > mid_total + 3:
            stats["over_8_5"] += 1
        if total_goals > mid_total + 4:
            stats["over_9_5"] += 1
        if total_goals > mid_total + 5:
            stats["over_10_5"] += 1
        if total_goals > mid_total + 6:
            stats["over_11_5"] += 1


        stats["min_ft"] = min(stats["min_ft"], total_goals)
        stats["max_ft"] = max(stats["max_ft"], total_goals)

    return dict(league_stats)


@app.route("/", methods=["GET"])
@app.route("/info", methods=["GET"])
def info():
    return render_template('info.html')


ua = UserAgent()
session_r = requests.Session()
session_r.headers.update({'User-Agent': ua.random})

def connect_db():
    return sqlite3.connect('matches.db')

def safe_request(url):
    try:
        session_r.headers.update({'User-Agent': ua.random})
        response = session_r.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None


def create_tables():
    """Создает таблицы для хранения матчей"""
    conn = connect_db()
    cursor = conn.cursor()


    cursor.execute('DROP TABLE IF EXISTS first_scan_matches')
    cursor.execute('DROP TABLE IF EXISTS new_matches')
    cursor.execute('DROP TABLE IF EXISTS first_scan_basketball_matches')
    cursor.execute('DROP TABLE IF EXISTS new_basketball_matches')


    cursor.execute('''
    CREATE TABLE first_scan_matches (
        id INTEGER PRIMARY KEY,
        league TEXT,
        start_time TEXT,
        home_team TEXT,
        away_team TEXT,
        found_at TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE new_matches (
        id INTEGER PRIMARY KEY,
        league TEXT,
        start_time TEXT,
        home_team TEXT,
        away_team TEXT,
        found_at TEXT
    )
    ''')


    cursor.execute('''
    CREATE TABLE first_scan_basketball_matches (
        id INTEGER PRIMARY KEY,
        league TEXT,
        start_time TEXT,
        home_team TEXT,
        away_team TEXT,
        found_at TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE new_basketball_matches (
        id INTEGER PRIMARY KEY,
        league TEXT,
        start_time TEXT,
        home_team TEXT,
        away_team TEXT,
        found_at TEXT
    )
    ''')

    conn.commit()
    conn.close()


def save_match_to_first_scan(league, start_time, home_team, away_team, found_at, is_basketball=False):
    """Сохраняет матч в таблицу first_scan_matches или first_scan_basketball_matches"""
    conn = connect_db()
    cursor = conn.cursor()
    table = 'first_scan_basketball_matches' if is_basketball else 'first_scan_matches'
    cursor.execute(f'''
    INSERT INTO {table} (league, start_time, home_team, away_team, found_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (league, start_time, home_team, away_team, found_at))
    conn.commit()
    conn.close()


def save_match_to_new_matches(league, start_time, home_team, away_team, found_at, is_basketball=False):
    """Сохраняет матч в таблицу new_matches или new_basketball_matches"""
    conn = connect_db()
    cursor = conn.cursor()
    table = 'new_basketball_matches' if is_basketball else 'new_matches'
    cursor.execute(f'''
    INSERT INTO {table} (league, start_time, home_team, away_team, found_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (league, start_time, home_team, away_team, found_at))
    conn.commit()
    conn.close()


def match_exists_in_any_scan(home_team, away_team, start_time, is_basketball=False):
    """Проверяет, существует ли матч в таблицах first_scan_matches или new_matches"""
    conn = connect_db()
    cursor = conn.cursor()
    table = 'first_scan_basketball_matches' if is_basketball else 'first_scan_matches'


    cursor.execute(f'''
    SELECT * FROM {table}
    WHERE home_team = ? AND away_team = ? AND start_time = ?
    ''', (home_team, away_team, start_time))
    result = cursor.fetchone()

    if result is None:
        table = 'new_basketball_matches' if is_basketball else 'new_matches'
        cursor.execute(f'''
        SELECT * FROM {table}
        WHERE home_team = ? AND away_team = ? AND start_time = ?
        ''', (home_team, away_team, start_time))
        result = cursor.fetchone()

    conn.close()
    return result is not None


def fetch_and_process_matches(url, is_first_run=False, is_basketball=False):
    """Запрашивает матчи и отправляет их в нужные таблицы"""
    data = safe_request(url)
    if not data:
        return
    print(f"New request {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    n_data = data.get("n", [])
    skiped_29andSoccer = n_data[0][2]

    for item in skiped_29andSoccer:
            league = item[1]
            matches = item[2]

            for match in matches:
                if match:
                    home_team = match[1]
                    away_team = match[2]
                    start_timestamp = match[4]
                    start_time = datetime.utcfromtimestamp(start_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    found_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


                    if is_first_run:
                        save_match_to_first_scan(league, start_time, home_team, away_team, found_at, is_basketball)

                    else:

                        if not match_exists_in_any_scan(home_team, away_team, start_time, is_basketball):
                            save_match_to_new_matches(league, start_time, home_team, away_team, found_at, is_basketball)
                            print(
                                f"New match: {home_team} - {away_team}, League: {league}, Time: {start_time}, Found at: {found_at}")
    print(f"First scan table was fulfilled at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def periodic_check(url, is_basketball=False):
    fetch_and_process_matches(url, is_first_run=True, is_basketball=is_basketball)
    while True:
        fetch_and_process_matches(url, is_first_run=False, is_basketball=is_basketball)
        sleep_time = random.randint(420, 720)
        print(f"Следующий запрос через {sleep_time // 60} минут.")
        time.sleep(sleep_time)


def get_matches_within_last_day(cursor, is_basketball=False):
    """Функция для получения матчей, обнаруженных за последние 24 часа"""

    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)


    one_day_ago_str = one_day_ago.strftime('%Y-%m-%d %H:%M:%S')


    table = 'new_basketball_matches' if is_basketball else 'new_matches'
    cursor.execute(f'''
    SELECT league, home_team, away_team, start_time, found_at 
    FROM {table}
    WHERE found_at >= ?
    ORDER BY found_at DESC
    ''', (one_day_ago_str,))
    return cursor.fetchall()

@app.route('/opened_line')
def show_matches():
    """Отображает страницу с новыми матчами для футбола и баскетбола"""
    conn = connect_db()
    cursor = conn.cursor()


    football_matches = get_matches_within_last_day(cursor)


    basketball_matches = get_matches_within_last_day(cursor, is_basketball=True)

    conn.close()

    return render_template('opened_line.html', football_matches=football_matches, basketball_matches=basketball_matches)


@app.route('/api/new_matches', methods=['GET'])
def get_new_matches():
    """Отправляет новые матчи через обычный HTTP запрос"""
    conn = connect_db()
    cursor = conn.cursor()


    football_matches = get_matches_within_last_day(cursor)


    basketball_matches = get_matches_within_last_day(cursor, is_basketball=True)

    conn.close()

    return jsonify({
        'football_matches': football_matches,
        'basketball_matches': basketball_matches
    })


if __name__ == "__main__":
    create_tables()


    url_football = "https://www.pin880.com/sports-service/sv/compact/events?btg=1&c=&cl=3&d=&ec=&ev=&g=&hle=true&ic=false&inl=false&l=3&lang=&lg=&lv=&me=0&mk=0&more=false&o=1&ot=1&pa=0&pimo=0%2C1%2C8%2C39%2C2%2C3%2C6%2C7%2C4%2C5&pn=-1&pv=1&sp=29&tm=0&v=0&locale=en_US&_=1739107865269&withCredentials=true"


    football_thread = threading.Thread(target=periodic_check, args=(url_football, False))
    football_thread.daemon = True
    football_thread.start()


    url_basketball = "https://www.pin880.com/sports-service/sv/compact/events?btg=1&c=&cl=3&d=&ec=&ev=&g=&hle=true&ic=false&inl=false&l=3&lang=&lg=&lv=&me=0&mk=0&more=false&o=1&ot=1&pa=0&pimo=0%2C1%2C2&pn=-1&pv=1&sp=4&tm=0&v=0&locale=en_US&_=1739192491263&withCredentials=true"


    basketball_thread = threading.Thread(target=periodic_check, args=(url_basketball, True))
    basketball_thread.daemon = True
    basketball_thread.start()


    app.run(debug=True,port=80)