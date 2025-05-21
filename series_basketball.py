#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
series_basketball_fixed.py — streak-анализ баскетбольных матчей
FIX 2025-05-20 (исправлено смещение шорт-меток)
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Callable, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from flask import url_for
from markupsafe import Markup   # Markup теперь берём отсюда

# ──────────────────────────────────────────────────────────────────────
# 0.  Заголовки
# ──────────────────────────────────────────────────────────────────────
BASE_HEADERS: List[str] = ["team", "league", "W", "L", "W/D", "D/L"]
HANDICAP_THRESHOLDS: List[int] = [5, 10]


def build_table_headers(tot_threshold: Optional[float] = None) -> List[str]:
    headers = BASE_HEADERS.copy()
    if tot_threshold is not None:
        base = int(round(tot_threshold))
        for t in sorted({base - 3, base, base + 3}):
            headers += [f"T≤{t}", f"T>{t}"]
    for d in HANDICAP_THRESHOLDS:
        headers += [f"W>{d}", f"W≤{d}", f"L>{d}", f"L≤{d}"]
    return headers


# ──────────────────────────────────────────────────────────────────────
# 1.  Анализатор
# ──────────────────────────────────────────────────────────────────────
class StreakAnalyzerBB:
    def __init__(self, db_uri: str, tot_threshold: Optional[float] = None):
        self.engine = create_engine(db_uri)
        self.tot_threshold = tot_threshold

        # ‼ здесь была ошибка: нужно отрезать только 'team' и 'league'
        self.flag_shorts: List[str] = build_table_headers(tot_threshold)[2:]
        self.FLAG_NAMES: Dict[str, str] = dict(zip(self._flag_keys(), self.flag_shorts))

    # ---------- SQL ----------
    def _load(self, teams: List[str]) -> pd.DataFrame:
        if not teams:
            return pd.DataFrame()
        ph = ", ".join(f":{i}" for i, _ in enumerate(teams))
        sql = f"""
            SELECT match_id, match_date, league_name,
                   team_home, team_away,
                   COALESCE(home_score_ft,0)  AS home_score_ft,
                   COALESCE(away_score_ft,0)  AS away_score_ft
            FROM   bb_main
            WHERE  team_home IN ({ph}) OR team_away IN ({ph})
            ORDER  BY match_date;
        """
        return pd.read_sql(text(sql), self.engine,
                           params={str(i): t for i, t in enumerate(teams)})

    # ---------- ключи-флаги ----------
    def _flag_keys(self) -> List[str]:
        keys = ["is_win", "is_loss", "is_not_loss", "is_not_win"]
        if self.tot_threshold is not None:
            base = int(round(self.tot_threshold))
            for t in sorted({base - 3, base, base + 3}):
                keys += [f"tot_le_{t}", f"tot_gt_{t}"]
        for d in HANDICAP_THRESHOLDS:
            keys += [f"win_gt{d}", f"win_le{d}", f"loss_gt{d}", f"loss_le{d}"]
        return keys

    # ---------- расчёт флагов ----------
    def _flags(self, df: pd.DataFrame, team: str) -> pd.DataFrame:
        h = df.team_home.eq(team)
        win  = (h & (df.home_score_ft > df.away_score_ft)) | (~h & (df.away_score_ft > df.home_score_ft))
        loss = (h & (df.home_score_ft < df.away_score_ft)) | (~h & (df.away_score_ft < df.home_score_ft))
        margin = (df.home_score_ft - df.away_score_ft).where(h, df.away_score_ft - df.home_score_ft)
        tot = df.home_score_ft + df.away_score_ft

        c = df.copy()
        c["is_win"]      = win
        c["is_loss"]     = loss
        c["is_not_loss"] = ~loss
        c["is_not_win"]  = ~win

        if self.tot_threshold is not None:
            base = int(round(self.tot_threshold))
            for t in sorted({base - 3, base, base + 3}):
                c[f"tot_le_{t}"] = tot.le(t)
                c[f"tot_gt_{t}"] = tot.gt(t)

        for d in HANDICAP_THRESHOLDS:
            c[f"win_gt{d}"]  = win  & margin.gt(d)
            c[f"win_le{d}"]  = win  & margin.le(d)
            c[f"loss_gt{d}"] = loss & margin.lt(-d)
            c[f"loss_le{d}"] = loss & margin.ge(-d)

        return c.astype({col: bool for col in self._flag_keys()})

    # ---------- helpers ----------
    @staticmethod
    def _cur_len(s: pd.Series) -> int:
        cnt = 0
        for v in s:
            if v:
                cnt += 1
            else:
                break
        return cnt

    @staticmethod
    def _hist(df: pd.DataFrame, flag: str) -> pd.DataFrame:
        d = df.sort_values("match_date").copy()
        d["sid"] = d.groupby("league_name")[flag].transform(lambda x: (x != x.shift()).cumsum())
        return (
            d[d[flag]]
            .groupby(["league_name", "sid"], as_index=False)
            .agg(start=("match_date", "first"),
                 end=("match_date", "last"),
                 length=("match_id", "size"))
        )

    # ---------- основной расчёт ----------
    def build(self, teams: List[str]) -> Tuple[pd.DataFrame, dict]:
        matches = self._load(teams)
        rows: List[Dict[str, int]] = []
        meta: Dict[str, dict] = {}

        for team in teams:
            df_team = matches[(matches.team_home == team) | (matches.team_away == team)].copy()
            if df_team.empty:
                continue

            df_team["match_date"] = pd.to_datetime(df_team["match_date"], errors="coerce")
            df_team.sort_values("match_date", inplace=True)
            df_flags = self._flags(df_team, team)
            desc = df_flags.sort_values("match_date", ascending=False)
            meta[team] = {}

            for flag in self._flag_keys():
                cur = {lg: self._cur_len(g[flag]) for lg, g in desc.groupby("league_name")}
                hist = self._hist(df_flags, flag)

                dist, longest, mx = {}, {}, {}
                for lg, grp in hist.groupby("league_name"):
                    dist[lg] = grp.length.value_counts().sort_index().to_dict()
                    mx_len = int(grp.length.max()) if not grp.empty else 0
                    mx[lg] = mx_len
                    longest[lg] = (
                        grp[grp.length == mx_len][["start", "end", "length"]]
                        .to_dict("records") if mx_len else []
                    )
                meta[team][flag] = {
                    "current": cur,
                    "max": mx,
                    "distribution": dist,
                    "longest": longest,
                }

            for lg in meta[team]["is_win"]["current"]:
                row = {"team": team, "league": lg}
                for flag, short in self.FLAG_NAMES.items():
                    row[short] = meta[team][flag]["current"].get(lg, 0)
                rows.append(row)

        df_out = (
            pd.DataFrame(rows).set_index(["team", "league"]).sort_index()
            if rows else pd.DataFrame([])
        )
        return df_out, meta


# ──────────────────────────────────────────────────────────────────────
# 2.  HTML-таблица  (осталась без изменений)
# ──────────────────────────────────────────────────────────────────────
def streak_table_html_bb(
    teams: List[str],
    db_uri: str,
    td_renderer: Callable[[int, int], str],
    link_endpoint: Optional[str] = None,
    tot_threshold: Optional[float] = None,
) -> Tuple[str, dict]:
    analyzer = StreakAnalyzerBB(db_uri, tot_threshold)
    df, meta = analyzer.build(teams)
    if df.empty:
        return "", meta

    headers = build_table_headers(analyzer.tot_threshold)
    head_html = "".join(f"<th>{h}</th>" for h in headers)

    rows_html: List[str] = []
    for (tm, lg), r in df.iterrows():
        href_params = dict(team=tm, league=lg)
        if analyzer.tot_threshold is not None:
            href_params["tt"] = analyzer.tot_threshold
        first_td = (
            f'<td><a href="{url_for(link_endpoint, **href_params)}">{tm}</a></td>'
            if link_endpoint else f"<td>{tm}</td>"
        )
        cells = [first_td, f"<td>{lg}</td>"]

        for short in analyzer.flag_shorts:
            flag = next(k for k, v in analyzer.FLAG_NAMES.items() if v == short)
            cur = int(r[short])
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
# 3.  Рендер ячеек
# ──────────────────────────────────────────────────────────────────────
def td_green(cur: int, mx: int) -> str:
    if mx == 0:
        return f"<td>{cur}</td>"
    alpha = 0.05 + 0.95 * min(cur / mx, 1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'
