from sqlalchemy import (
    Column, Integer, String, Date, Time, Float, ForeignKey, ARRAY
)
from sqlalchemy.orm import joinedload, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Модель таблицы soccer_main
class SoccerMain(Base):
    __tablename__ = 'soccer_main'

    match_id = Column(Integer, primary_key=True)
    league_id = Column(Integer)
    match_date = Column(Date)
    start_time = Column(Time)
    team_home = Column(String)
    team_away = Column(String)
    league_name = Column(String)
    stage = Column(String)
    home_score_ft = Column(Integer)
    away_score_ft = Column(Integer)
    total_ft = Column(Integer)
    final = Column(String)
    bet365_odds = relationship('Bet365Odds', back_populates='soccer_main', uselist=False)
    xbet_odds = relationship('XbetOdds', back_populates='soccer_main', uselist=False)


# Модель таблицы bet365_odds
class Bet365Odds(Base):
    __tablename__ = 'bet365_odds'

    match_id = Column(Integer, ForeignKey('soccer_main.match_id'), primary_key=True)
    win_home_open = Column(Float)
    win_home_close = Column(Float)
    draw_open = Column(Float)
    draw_close = Column(Float)
    win_away_open = Column(Float)
    win_away_close = Column(Float)
    odds_2_5_open = Column(Float)
    odds_2_5_close = Column(Float)
    soccer_main = relationship('SoccerMain', back_populates='bet365_odds')


# Модель таблицы xbet_odds
class XbetOdds(Base):
    __tablename__ = 'xbet_odds'

    match_id = Column(Integer, ForeignKey('soccer_main.match_id'), primary_key=True)
    win_home_open = Column(Float)
    win_home_close = Column(Float)
    draw_open = Column(Float)
    draw_close = Column(Float)
    win_away_open = Column(Float)
    win_away_close = Column(Float)
    odds_2_5_open = Column(Float)
    odds_2_5_close = Column(Float)
    soccer_main = relationship('SoccerMain', back_populates='xbet_odds')


# Модель таблицы soccer_half1_stats
class SoccerHalf1Stats(Base):
    __tablename__ = 'soccer_half1_stats'

    match_id = Column(Integer, primary_key=True)
    home_corners = Column(Integer)
    away_corners = Column(Integer)
    home_yellow = Column(Integer)
    away_yellow = Column(Integer)
    # другие поля...


# Модель таблицы soccer_half2_stats
class SoccerHalf2Stats(Base):
    __tablename__ = 'soccer_half2_stats'

    match_id = Column(Integer, primary_key=True)
    home_corners = Column(Integer)
    away_corners = Column(Integer)
    home_yellow = Column(Integer)
    away_yellow = Column(Integer)
    # другие поля...


class SoccerTimeLine(Base):
    __tablename__ = 'soccer_timeline'

    match_id = Column(Integer, primary_key=True)
    home_goals_h1 = Column(ARRAY(Integer))
    away_goals_h1 = Column(ARRAY(Integer))


class HockeyMain(Base):
    __tablename__ = 'hockey_main'

    match_id = Column(Integer, primary_key=True)
    league_id = Column(Integer)
    match_date = Column(Date)
    start_time = Column(Time)
    team_home = Column(String)
    team_away = Column(String)
    league_name = Column(String)
    stage = Column(String)
    home_score_ft = Column(Integer)
    away_score_ft = Column(Integer)
    home_1p = Column(Integer)
    away_1p = Column(Integer)
    home_2p = Column(Integer)
    away_2p = Column(Integer)
    home_3p = Column(Integer)
    away_3p = Column(Integer)
    total_ft = Column(Integer)
    final = Column(String)
    xbet_odds_hoc = relationship('XbetOddsHoc', back_populates='hockey_main', uselist=False)

class XbetOddsHoc(Base):
    __tablename__ = 'xbet_odds_hoc'

    match_id = Column(Integer, ForeignKey('hockey_main.match_id'), primary_key=True)
    win_home_open = Column(Float)
    win_home_close = Column(Float)
    draw_open = Column(Float)
    draw_close = Column(Float)
    win_away_open = Column(Float)
    win_away_close = Column(Float)
    odds_5_5_open = Column(Float)
    odds_5_5_close = Column(Float)
    hockey_main = relationship('HockeyMain', back_populates='xbet_odds_hoc')