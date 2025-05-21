#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
series_handball_fixed.py — корректный streak-анализ гандбольных матчей
Полная копия функционала series_basketball_fixed.py, адаптированного под таблицу hb_main:
включает динамические TOTAL (X-3 / X / X+3) и хендикапы ±5 / ±10.
FIX 2025-05-20: добавлены колонки TOTAL точно как в баскете.
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Callable, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from flask import url_for
from markupsafe import Markup

# ──────────────────────────────────────────────────────────────────────
# 0. Заголовки таблицы
# ──────────────────────────────────────────────────────────────────────
BASE_HEADERS: List[str] = ["team", "league", "W", "L", "W/D", "D/L"]
HANDICAP_THRESHOLDS: List[int] = [5, 10]

def build_table_headers(tot_threshold: Optional[float] = None) -> List[str]:
    """
    Формирует список заголовков:
      • базовые: team, league, W, L, W/D, D/L
      • динамические TOTAL: X-3 / X / X+3 (только если передан tot_threshold)
      • хендикапы ±5 и ±10
    """
    headers = BASE_HEADERS.copy()
    if tot_threshold is not None:
        base = int(round(tot_threshold))
        for t in sorted({base - 3, base, base + 3}):
            headers += [f"T≤{t}", f"T>{t}"]
    for d in HANDICAP_THRESHOLDS:
        headers += [f"W>{d}", f"W≤{d}", f"L>{d}", f"L≤{d}"]
    return headers

# ──────────────────────────────────────────────────────────────────────
# 1. Анализатор серий
# ──────────────────────────────────────────────────────────────────────
class StreakAnalyzerHB:
    """Считает streak-и по гандболу: W/L, W/D, D/L, TOTAL и хендикапы."""
    def __init__(self, db_uri: str, tot_threshold: Optional[float] = None):
        self.engine = create_engine(db_uri)
        self.tot_threshold = tot_threshold
        # короткие имена для вывода: всё после team, league
        self.flag_shorts = build_table_headers(tot_threshold)[2:]
        # map long flag key → short header
        self.FLAG_NAMES = dict(zip(self._flag_keys(), self.flag_shorts))

    def _load(self, teams: List[str]) -> pd.DataFrame:
        """Загружает из hb_main матчи для указанных команд."""
        if not teams:
            return pd.DataFrame()
        ph = ", ".join(f":{i}" for i in range(len(teams)))
        sql = f"""
            SELECT match_id, match_date, league_name,
                   team_home, team_away,
                   COALESCE(home_score_ft,0) AS home_score_ft,
                   COALESCE(away_score_ft,0) AS away_score_ft
            FROM hb_main
            WHERE team_home IN ({ph}) OR team_away IN ({ph})
            ORDER BY match_date
        """
        return pd.read_sql(
            text(sql),
            self.engine,
            params={str(i): team for i, team in enumerate(teams)}
        )

    def _flag_keys(self) -> List[str]:
        """Длинные имена флагов в порядке, соответствующем flag_shorts."""
        keys = ["is_win", "is_loss", "is_not_loss", "is_not_win"]
        # динамические TOTAL
        if self.tot_threshold is not None:
            base = int(round(self.tot_threshold))
            for t in sorted({base - 3, base, base + 3}):
                keys += [f"tot_le_{t}", f"tot_gt_{t}"]
        # хендикапы
        for d in HANDICAP_THRESHOLDS:
            keys += [f"win_gt{d}", f"win_le{d}", f"loss_gt{d}", f"loss_le{d}"]
        return keys

    def _flags(self, df: pd.DataFrame, team: str) -> pd.DataFrame:
        """
        Добавляет во входной DataFrame булевы столбцы-флаги:
        is_win, is_loss, is_not_loss, is_not_win,
        tot_le_N, tot_gt_N (если tot_threshold),
        win_gtD, win_leD, loss_gtD, loss_leD для каждого D в HANDICAP_THRESHOLDS.
        """
        # признак домашнее?
        h = df.team_home.eq(team)
        # победа/поражение
        win  = (h & (df.home_score_ft > df.away_score_ft)) | (~h & (df.away_score_ft > df.home_score_ft))
        loss = (h & (df.home_score_ft < df.away_score_ft)) | (~h & (df.away_score_ft < df.home_score_ft))
        # разница очков в пользу team
        margin = (df.home_score_ft - df.away_score_ft).where(h,
                  df.away_score_ft - df.home_score_ft)
        # общий total
        tot = df.home_score_ft + df.away_score_ft

        c = df.copy()
        # базовые
        c["is_win"]      = win
        c["is_loss"]     = loss
        c["is_not_loss"] = ~loss
        c["is_not_win"]  = ~win

        # динамические TOTAL
        if self.tot_threshold is not None:
            base = int(round(self.tot_threshold))
            for t in sorted({base - 3, base, base + 3}):
                c[f"tot_le_{t}"] = tot.le(t)
                c[f"tot_gt_{t}"] = tot.gt(t)

        # хендикапы
        for d in HANDICAP_THRESHOLDS:
            c[f"win_gt{d}"]  = win  & margin.gt(d)
            c[f"win_le{d}"]  = win  & margin.le(d)
            c[f"loss_gt{d}"] = loss & margin.lt(-d)
            c[f"loss_le{d}"] = loss & margin.ge(-d)

        # привести все флаги к bool
        return c.astype({col: bool for col in self._flag_keys()})

    @staticmethod
    def _cur_len(series: pd.Series) -> int:
        """Длина текущей серии True от начала Series."""
        count = 0
        for val in series:
            if val:
                count += 1
            else:
                break
        return count

    @staticmethod
    def _hist(df: pd.DataFrame, flag: str) -> pd.DataFrame:
        """
        Собирает историю серий True по флагу:
        выдаёт таблицу league_name, sid, start, end, length
        """
        d = df.sort_values("match_date").copy()
        d["sid"] = d.groupby("league_name")[flag].transform(
            lambda x: (x != x.shift()).cumsum()
        )
        return (
            d[d[flag]]
             .groupby(["league_name", "sid"], as_index=False)
             .agg(
                 start  = ("match_date", "first"),
                 end    = ("match_date", "last"),
                 length = ("match_id", "size")
             )
        )

    def build(self, teams: List[str]) -> Tuple[pd.DataFrame, dict]:
        """
        Собирает итоговый DataFrame (index=['team','league']) и метаданные meta:
        текущие и максимальные серии, распределение и детали longest.
        """
        matches = self._load(teams)
        rows: List[Dict[str,int]] = []
        meta: Dict[str,dict]  = {}

        for team in teams:
            df_t = matches[
                (matches.team_home == team) |
                (matches.team_away == team)
            ].copy()
            if df_t.empty:
                continue
            df_t["match_date"] = pd.to_datetime(df_t["match_date"], errors="coerce")
            df_t.sort_values("match_date", inplace=True)

            df_flags = self._flags(df_t, team)
            desc     = df_flags.sort_values("match_date", ascending=False)
            meta[team] = {}

            # проходим по каждому флагу
            for flag in self._flag_keys():
                cur = {lg: self._cur_len(g[flag]) for lg,g in desc.groupby("league_name")}
                hist = self._hist(df_flags, flag)

                dist, longest, mx = {}, {}, {}
                for lg, grp in hist.groupby("league_name"):
                    dist[lg]    = grp.length.value_counts().sort_index().to_dict()
                    max_len     = int(grp.length.max()) if not grp.empty else 0
                    mx[lg]      = max_len
                    longest[lg] = (
                        grp[grp.length == max_len][["start","end","length"]]
                           .to_dict("records")
                        if max_len else []
                    )
                meta[team][flag] = {
                    "current": cur,
                    "max":     mx,
                    "distribution": dist,
                    "longest":      longest
                }

            # строим строки для итогового DataFrame
            for lg in meta[team]["is_win"]["current"]:
                row = {"team": team, "league": lg}
                for flag, short in self.FLAG_NAMES.items():
                    row[short] = meta[team][flag]["current"].get(lg, 0)
                rows.append(row)

        df_out = (
            pd.DataFrame(rows)
              .set_index(["team","league"])
              .sort_index()
            if rows else pd.DataFrame()
        )
        return df_out, meta

# ──────────────────────────────────────────────────────────────────────
# 2. Генератор HTML-таблицы
# ──────────────────────────────────────────────────────────────────────
def streak_table_html_hb(
    teams: List[str],
    db_uri: str,
    td_renderer: Callable[[int,int], str],
    link_endpoint: Optional[str]    = None,
    tot_threshold: Optional[float]  = None,
) -> Tuple[str, dict]:
    """
    Возвращает HTML-код таблицы и meta, аналогично basketball, но для гандбола.
    Передайте tot_threshold, чтобы появились колонки TOTAL.
    """
    analyzer = StreakAnalyzerHB(db_uri, tot_threshold)
    df, meta = analyzer.build(teams)
    if df.empty:
        return "", meta

    headers = build_table_headers(analyzer.tot_threshold)
    head_html = "".join(f"<th>{h}</th>" for h in headers)

    rows_html: List[str] = []
    for (tm, lg), row in df.iterrows():
        params = {"team": tm, "league": lg}
        if analyzer.tot_threshold is not None:
            params["tt"] = analyzer.tot_threshold
        first_td = (
            f'<td><a href="{url_for(link_endpoint, **params)}">{tm}</a></td>'
            if link_endpoint else f"<td>{tm}</td>"
        )
        cells = [first_td, f"<td>{lg}</td>"]
        for short in analyzer.flag_shorts:
            flag = next(k for k,v in analyzer.FLAG_NAMES.items() if v == short)
            cur = int(row[short])
            mx  = meta[tm][flag]["max"].get(lg, 0)
            cells.append(td_renderer(cur, mx))
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    table_html = (
        '<table class="table table-bordered table-sm mb-4">'
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
    )
    return Markup(table_html), meta

# ──────────────────────────────────────────────────────────────────────
# 3. Пример функции для рендеринга ячеек
# ──────────────────────────────────────────────────────────────────────
def td_green(cur: int, mx: int) -> str:
    """
    Красит фон зелёным по линейной шкале от 0 до mx.
    """
    if mx == 0:
        return f"<td>{cur}</td>"
    alpha = 0.05 + 0.95 * min(cur/mx, 1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'
