#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
series_soccer_fixed.py — корректный расчёт игровых серий + генерация HTML‑таблицы

Исправления по сравнению с предыдущей версией:
• Корректно вычисляются ID серий (sid) — используется transform, а не apply + values, что гарантирует
  совпадение индексов и отсутствие рассинхронизации.
• Перед расчётом серий DataFrame внутри _hist сортируется по match_date, поэтому минимальная и
  максимальная даты streak‑а действительно отражают фактический диапазон.
• В _hist агрегаты start / end берутся через first / last вместо min / max (они эквивалентны после
  сортировки, но first/last чуть нагляднее).
• Добавлена явная типизация булевых столбцов в _flags, чтобы избежать неожиданного поведения при
  побитовых операциях.
• В build() текущие streak‑и считаются так же, как и раньше, но весь расчёт делается над копией
  DataFrame, где даты уже приведены к типу datetime и отсортированы.
• Все публичные функции сохранены (streak_table_html_soc, td_green), так что модуль можно просто
  заменить на старый.
"""

from __future__ import annotations

from typing import List, Callable, Tuple, Dict
import html

import pandas as pd
from markupsafe import Markup
from sqlalchemy import create_engine
from flask import url_for

# ------------------------------------------------------------------
# Фиксированный порядок заголовков для HTML‑таблицы
# ------------------------------------------------------------------
TABLE_HEADERS: List[str] = [
    "team", "league",
    "W", "L", "W/D", "D/L",
    "GF=0", "GF<0.5", "GF<1.5", "GF>1.5", "GF<2.5", "GF>2.5",
    "GA=0", "GA<0.5", "GA<1.5", "GA>1.5", "GA<2.5", "GA>2.5",
    "T=0", "T<0.5", "T<1.5", "T>1.5", "T<2.5", "T>2.5", "T<3.5", "T>3.5",
]


# ═══════════════════════════════════════
# 1. Анализатор
# ═══════════════════════════════════════
class StreakAnalyzer:
    FLAG_NAMES: Dict[str, str] = {
        "is_win": "W",
        "is_loss": "L",
        "is_not_loss": "W/D",
        "is_not_win": "D/L",
        # ——————————————————— GF ———————————————————
        "gf_eq0": "GF=0",
        "gf_gt0_5": "GF>0.5",
        "gf_gt1_5": "GF>1.5",
        "gf_lt1_5": "GF<1.5",
        "gf_gt2_5": "GF>2.5",
        "gf_lt2_5": "GF<2.5",
        # ——————————————————— GA ———————————————————
        "ga_eq0": "GA=0",
        "ga_gt0_5": "GA>0.5",
        "ga_gt1_5": "GA>1.5",
        "ga_lt1_5": "GA<1.5",
        "ga_gt2_5": "GA>2.5",
        "ga_lt2_5": "GA<2.5",
        # ——————————————————— TOT ——————————————————
        "tot_eq0": "T=0",
        "tot_gt0_5": "T>0.5",
        "tot_gt1_5": "T>1.5",
        "tot_lt1_5": "T<1.5",
        "tot_gt2_5": "T>2.5",
        "tot_lt2_5": "T<2.5",
        "tot_gt3_5": "T>3.5",
        "tot_lt3_5": "T<3.5",
    }
    FLAG_COLS = list(FLAG_NAMES)

    def __init__(self, db_uri: str):
        self.engine = create_engine(db_uri)

    # ---------- SQL ----------
    def _load(self, teams: List[str]) -> pd.DataFrame:
        placeholders = ",".join(f"%({i})s" for i, _ in enumerate(teams))
        sql = f"""
        SELECT match_id, match_date, league_name,
               team_home, team_away, home_score_ft, away_score_ft
        FROM soccer_main
        WHERE team_home IN ({placeholders}) OR team_away IN ({placeholders})
        ORDER BY match_date;
        """
        return pd.read_sql(sql, self.engine,
                           params={str(i): t for i, t in enumerate(teams)})

    # ---------- флаги ----------
    @staticmethod
    def _flags(df: pd.DataFrame, team: str) -> pd.DataFrame:
        """Возвращает DataFrame c булевыми столбцами‑флагами."""
        h = df.team_home.eq(team)
        win = (h & (df.home_score_ft > df.away_score_ft)) | (~h & (df.away_score_ft > df.home_score_ft))
        loss = (h & (df.home_score_ft < df.away_score_ft)) | (~h & (df.away_score_ft < df.home_score_ft))

        gf = df.home_score_ft.where(h, df.away_score_ft)
        ga = df.away_score_ft.where(h, df.home_score_ft)
        tot = df.home_score_ft + df.away_score_ft

        c = df.copy()
        # W / L
        c["is_win"] = win.astype(bool)
        c["is_loss"] = loss.astype(bool)
        c["is_not_loss"] = (~loss).astype(bool)
        c["is_not_win"] = (~win).astype(bool)
        # GF
        c["gf_eq0"] = gf.eq(0)
        c["gf_gt0_5"] = gf.ge(1)
        c["gf_gt1_5"] = gf.ge(2)
        c["gf_lt1_5"] = gf.le(1)
        c["gf_gt2_5"] = gf.ge(3)
        c["gf_lt2_5"] = gf.le(2)
        # GA
        c["ga_eq0"] = ga.eq(0)
        c["ga_gt0_5"] = ga.ge(1)
        c["ga_gt1_5"] = ga.ge(2)
        c["ga_lt1_5"] = ga.le(1)
        c["ga_gt2_5"] = ga.ge(3)
        c["ga_lt2_5"] = ga.le(2)
        # TOT
        c["tot_eq0"] = tot.eq(0)
        c["tot_gt0_5"] = tot.ge(1)
        c["tot_gt1_5"] = tot.ge(2)
        c["tot_lt1_5"] = tot.le(1)
        c["tot_gt2_5"] = tot.ge(3)
        c["tot_lt2_5"] = tot.le(2)
        c["tot_gt3_5"] = tot.ge(4)
        c["tot_lt3_5"] = tot.le(3)
        return c

    # ---------- helpers ----------
    @staticmethod
    def _cur_len(s: pd.Series) -> int:
        """Длина текущей (самой свежей) серии True‑значений."""
        cnt = 0
        for v in s:
            if v:
                cnt += 1
            else:
                break
        return cnt

    @staticmethod
    def _hist(df: pd.DataFrame, flag: str) -> pd.DataFrame:
        """Возвращает DataFrame с параметрами всех серий `flag`."""
        d = df.sort_values("match_date").copy()
        # transform гарантирует выравнивание индекса
        d["sid"] = d.groupby("league_name")[flag].transform(lambda x: (x != x.shift()).cumsum())

        return (
            d[d[flag]]
            .groupby(["league_name", "sid"], as_index=False)
            .agg(
                start=("match_date", "first"),
                end=("match_date", "last"),
                length=("match_id", "size"),
            )
        )

    # ---------- основной расчёт ----------
    def build(self, teams: List[str]) -> Tuple[pd.DataFrame, dict]:
        matches = self._load(teams)
        rows, meta = [], {}

        for team in teams:
            df_team = matches[(matches.team_home == team) | (matches.team_away == team)].copy()
            if df_team.empty:
                continue

            # гарантируем datetime и сортировку
            df_team["match_date"] = pd.to_datetime(df_team["match_date"], errors="coerce")
            df_team.sort_values("match_date", inplace=True)

            df_flags = self._flags(df_team, team)
            desc = df_flags.sort_values("match_date", ascending=False)
            meta[team] = {}

            for flag in self.FLAG_COLS:
                # текущая серия
                cur = {lg: self._cur_len(g[flag]) for lg, g in desc.groupby("league_name")}
                # все серии
                hist = self._hist(df_flags, flag)

                dist, longest, mx = {}, {}, {}
                for lg, grp in hist.groupby("league_name"):
                    dist[lg] = grp.length.value_counts().sort_index().to_dict()
                    mx_len = int(grp.length.max())
                    mx[lg] = mx_len
                    longest[lg] = grp[grp.length == mx_len][["start", "end", "length"]].to_dict("records")

                meta[team][flag] = dict(current=cur, max=mx, distribution=dist, longest=longest)

            # строки будущей HTML‑таблицы
            for lg in meta[team]["is_win"]["current"]:
                row = {"team": team, "league": lg}
                for f, short in self.FLAG_NAMES.items():
                    row[short] = meta[team][f]["current"].get(lg, 0)
                rows.append(row)

        # --- безопасное формирование DataFrame ---
        if rows:
            df_out = pd.DataFrame(rows).set_index(["team", "league"]).sort_index()
        else:
            df_out = pd.DataFrame([])  # пустой без столбцов

        return df_out, meta


# ═══════════════════════════════════════
# 2. Генератор HTML‑таблицы
# ═══════════════════════════════════════

def streak_table_html_soc(
    teams: List[str],
    db_uri: str,
    td_renderer: Callable[[int, int], str],
    link_endpoint: str | None = None,
) -> Tuple[str, dict]:

    df, meta = StreakAnalyzer(db_uri).build(teams)

    # в БД нет матчей – просто вернуть «пусто»
    if df.empty:
        return "", meta

    # ----------------- строки таблицы -----------------
    rows_html: List[str] = []
    for (tm, lg), r in df.iterrows():
        first_td = (
            f'<td><a href="{url_for(link_endpoint, team=tm, league=lg)}">{html.escape(tm)}</a></td>'
            if link_endpoint
            else f"<td>{html.escape(tm)}</td>"
        )
        cells = [first_td, f"<td>{html.escape(lg)}</td>"]

        for flag, short in StreakAnalyzer.FLAG_NAMES.items():
            cur = int(r[short])
            mx = meta[tm][flag]["max"].get(lg, 0)
            cells.append(td_renderer(cur, mx))

        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    # ----------------- шапка ------------------
    header = "".join(f"<th>{h}</th>" for h in TABLE_HEADERS)

    table_html = (
        '<table class="table table-bordered table-sm mb-4">'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table>"
    )

    return Markup(table_html), meta


# ═══════════════════════════════════════
# 3. Пример td‑рендера
# ═══════════════════════════════════════

def td_green(cur: int, mx: int) -> str:
    """Окрашивает фон ячейки в зависимости от отношения cur / mx."""
    if mx == 0:
        return f"<td>{cur}</td>"
    alpha = 0.05 + 0.95 * min(cur / mx, 1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'
