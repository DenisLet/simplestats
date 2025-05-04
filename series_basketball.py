#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""series_basketball_fixed.py — корректный streak‑анализ баскетбольных матчей

Исправлено • добавлено:
• Даты сортируются, sid считается через groupby.transform → длины/периоды серий корректны.
• Все булевы колонки явно приведены к bool.
• SQL использует COALESCE для счёта (на случай NULL).
• Поддержка динамического тотала: X‑3, X, X+3.
• Публичный API совместим со старым (`streak_table_html_bb`, `td_green`).
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Callable, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from flask import url_for
from markupsafe import Markup

BASE_HEADERS: List[str] = ["team", "league", "W", "L", "W/D", "D/L"]
HANDICAP_THRESHOLDS = [5, 10]

# ═══════════════════════════════════════
# 1. Анализатор
# ═══════════════════════════════════════
class StreakAnalyzerBB:
    def __init__(self, db_uri: str, tot_threshold: Optional[float] = None):
        self.engine = create_engine(db_uri)
        self.tot_threshold = tot_threshold
        self.FLAG_NAMES: Dict[str, str] = {
            "is_win": "W", "is_loss": "L",
            "is_not_loss": "W/D", "is_not_win": "D/L",
        }
        # dynamic totals
        self.tot_thresholds: List[int] = []
        if tot_threshold is not None:
            base = int(round(tot_threshold))
            self.tot_thresholds = sorted({base - 3, base, base + 3})
            for t in self.tot_thresholds:
                self.FLAG_NAMES[f"tot_le_{t}"] = f"T≤{t}"
                self.FLAG_NAMES[f"tot_gt_{t}"] = f"T>{t}"
        # handicap
        for d in HANDICAP_THRESHOLDS:
            self.FLAG_NAMES |= {
                f"win_gt{d}": f"W>{d}", f"win_le{d}": f"W≤{d}",
                f"loss_gt{d}": f"L>{d}", f"loss_le{d}": f"L≤{d}",
            }

    # ---------- SQL ----------
    def _load(self, teams: List[str]) -> pd.DataFrame:
        if not teams:
            return pd.DataFrame()
        ph = ",".join(f":{i}" for i, _ in enumerate(teams))
        sql = f"""
            SELECT match_id, match_date, league_name,
                   team_home, team_away,
                   COALESCE(home_score_ft,0) AS home_score_ft,
                   COALESCE(away_score_ft,0) AS away_score_ft
            FROM bb_main
            WHERE team_home IN ({ph}) OR team_away IN ({ph})
            ORDER BY match_date;
        """
        return pd.read_sql(text(sql), self.engine, params={str(i): t for i, t in enumerate(teams)})

    # ---------- flags ----------
    def _flags(self, df: pd.DataFrame, team: str) -> pd.DataFrame:
        h = df.team_home.eq(team)
        win = (h & (df.home_score_ft > df.away_score_ft)) | (~h & (df.away_score_ft > df.home_score_ft))
        loss = (h & (df.home_score_ft < df.away_score_ft)) | (~h & (df.away_score_ft < df.home_score_ft))
        margin = (df.home_score_ft - df.away_score_ft).where(h, df.away_score_ft - df.home_score_ft)
        tot = df.home_score_ft + df.away_score_ft
        c = df.copy()
        c["is_win"] = win; c["is_loss"] = loss
        c["is_not_loss"] = ~loss; c["is_not_win"] = ~win
        # totals
        for t in self.tot_thresholds:
            c[f"tot_le_{t}"] = tot.le(t)
            c[f"tot_gt_{t}"] = tot.gt(t)
        # handicap
        for d in HANDICAP_THRESHOLDS:
            c[f"win_gt{d}"] = win & margin.ge(d)
            c[f"win_le{d}"] = win & margin.lt(d)
            c[f"loss_gt{d}"] = loss & margin.le(-d)
            c[f"loss_le{d}"] = loss & margin.gt(-d)
        return c.astype({col: bool for col in self.FLAG_NAMES})

    # ---------- helpers ----------
    @staticmethod
    def _cur_len(s: pd.Series) -> int:
        n = 0
        for v in s:
            if v: n += 1
            else: break
        return n

    @staticmethod
    def _hist(df: pd.DataFrame, flag: str) -> pd.DataFrame:
        d = df.sort_values("match_date").copy()
        d["sid"] = d.groupby("league_name")[flag].transform(lambda x: (x != x.shift()).cumsum())
        return (
            d[d[flag]]
            .groupby(["league_name", "sid"], as_index=False)
            .agg(start=("match_date", "first"), end=("match_date", "last"), length=("match_id", "size"))
        )

    # ---------- build ----------
    def build(self, teams: List[str]) -> Tuple[pd.DataFrame, dict]:
        matches = self._load(teams)
        rows = []; meta: Dict[str, dict] = {}
        for team in teams:
            df_team = matches[(matches.team_home == team) | (matches.team_away == team)].copy()
            if df_team.empty:
                continue
            df_team["match_date"] = pd.to_datetime(df_team["match_date"]); df_team.sort_values("match_date", inplace=True)
            df_flags = self._flags(df_team, team)
            desc = df_flags.sort_values("match_date", ascending=False)
            meta[team] = {}
            for flag in self.FLAG_NAMES:
                cur = {lg: self._cur_len(g[flag]) for lg, g in desc.groupby("league_name")}
                hist = self._hist(df_flags, flag)
                dist, longest, mx = {}, {}, {}
                for lg, grp in hist.groupby("league_name"):
                    dist[lg] = grp.length.value_counts().sort_index().to_dict()
                    mx_len = int(grp.length.max()) if not grp.empty else 0
                    mx[lg] = mx_len
                    longest[lg] = grp[grp.length == mx_len][["start", "end", "length"]].to_dict("records") if mx_len else []
                meta[team][flag] = {"current": cur, "max": mx, "distribution": dist, "longest": longest}
            for lg in meta[team]["is_win"]["current"]:
                row = {"team": team, "league": lg}
                for f, short in self.FLAG_NAMES.items():
                    row[short] = meta[team][f]["current"].get(lg, 0)
                rows.append(row)
        df_out = pd.DataFrame(rows).set_index(["team", "league"]).sort_index() if rows else pd.DataFrame([])
        return df_out, meta

# ═══════════════════════════════════════
# 2. HTML‑таблица
# ═══════════════════════════════════════

def streak_table_html_bb(teams: List[str], db_uri: str, td_renderer: Callable[[int, int], str], link_endpoint: Optional[str] = None, tot_threshold: Optional[float] = None) -> Tuple[str, dict]:
    analyzer = StreakAnalyzerBB(db_uri, tot_threshold)
    df, meta = analyzer.build(teams)
    if df.empty:
        return "", meta
    headers = BASE_HEADERS + list(analyzer.FLAG_NAMES.values())[4:]
    rows = []
    for (tm, lg), r in df.iterrows():
        href_params = dict(team=tm, league=lg, tt=analyzer.tot_threshold) if analyzer.tot_threshold is not None else dict(team=tm, league=lg)
        first_td = f'<td><a href="{url_for(link_endpoint, **href_params)}">{tm}</a></td>' if link_endpoint else f"<td>{tm}</td>"
        cells = [first_td, f"<td>{lg}</td>"]
        for flag, short in analyzer.FLAG_NAMES.items():
            cur = int(r[short]); mx = meta[tm][flag]["max"].get(lg, 0)
            cells.append(td_renderer(cur, mx))
        rows.append("<tr>" + "".join(cells) + "</tr>")
    head = "".join(f"<th>{h}</th>" for h in headers)
    table = '<table class="table table-bordered table-sm mb-4"><thead><tr>'+head+'</tr></thead><tbody>'+"".join(rows)+'</tbody></table>'
    return Markup(table), meta

# ═══════════════════════════════════════
# 3. td renderer
# ═══════════════════════════════════════

def td_green(cur: int, mx: int) -> str:
    if mx == 0:
        return f"<td>{cur}</td>"
    alpha = 0.05 + 0.95 * min(cur / mx, 1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'
