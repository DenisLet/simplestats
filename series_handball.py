#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
series_handball.py — расчёт серий W/L/W-D/D-L для гандбола + генерация HTML‑таблицы.

Полный аналог series_basketball.py, но данные берём из таблицы **hb_main**.

Столбцы‑флаги:
  • **W**   — победы команды
  • **L**   — поражения команды
  • **W/D** — не проиграла (Win или Draw)
  • **D/L** — не выиграла  (Draw или Loss)

Фиксированный порядок столбцов задаётся константой `TABLE_HEADERS`.

Пример вызова во Flask‑роуте:

```python
streak_table, meta = streak_table_html_hb([team1, team2], DB_URI, td_green,
                                          link_endpoint="handball_details")
```
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Callable
import pandas as pd
from sqlalchemy import create_engine
from flask import url_for
from markupsafe import Markup

# ------------------------------------------------------------------
# Фиксированный порядок столбцов для HTML‑таблицы
# ------------------------------------------------------------------
TABLE_HEADERS: List[str] = [
    "team", "league",
    "W", "L", "W/D", "D/L",
]


# ═══════════════════════════════════════
# 1. Анализатор серий
# ═══════════════════════════════════════
class StreakAnalyzerHB:
    """Считает серии W / L / W‑D / D‑L для переданных гандбольных команд."""

    # отображение внутренних булевых столбцов → сокращённых названий
    FLAG_NAMES: Dict[str, str] = {
        "is_win": "W",
        "is_loss": "L",
        "is_not_loss": "W/D",
        "is_not_win": "D/L",
    }
    FLAG_COLS = list(FLAG_NAMES)

    # ---------- init ----------
    def __init__(self, db_uri: str):
        self.engine = create_engine(db_uri)

    # ---------- SQL ----------
    def _load(self, teams: List[str]) -> pd.DataFrame:
        """Загружает все матчи для указанных команд из hb_main."""
        if not teams:
            return pd.DataFrame()

        placeholders = ",".join(f"%({i})s" for i, _ in enumerate(teams))
        sql = f"""
            SELECT match_id, match_date, league_name,
                   team_home, team_away, home_score_ft, away_score_ft
            FROM hb_main
            WHERE team_home IN ({placeholders}) OR team_away IN ({placeholders})
            ORDER BY match_date;
        """
        return pd.read_sql(sql, self.engine,
                           params={str(i): t for i, t in enumerate(teams)})

    # ---------- флаги ----------
    @staticmethod
    def _flags(df: pd.DataFrame, team: str) -> pd.DataFrame:
        """Добавляет булевы флаги результатов матча для `team`."""
        is_home = df.team_home.eq(team)

        win = (is_home & (df.home_score_ft > df.away_score_ft)) |\
              (~is_home & (df.away_score_ft > df.home_score_ft))

        loss = (is_home & (df.home_score_ft < df.away_score_ft)) |\
               (~is_home & (df.away_score_ft < df.home_score_ft))

        c = df.copy()
        c["is_win"], c["is_loss"] = win, loss
        c["is_not_loss"], c["is_not_win"] = ~loss, ~win
        return c

    # ---------- helpers ----------
    @staticmethod
    def _cur_len(s: pd.Series) -> int:
        """Возвращает длину текущей (последней) серии подряд идущих True."""
        cnt = 0
        for v in s:
            if v:
                cnt += 1
            else:
                break
        return cnt

    @staticmethod
    def _hist(df: pd.DataFrame, flag: str) -> pd.DataFrame:
        """Полная история всех серий по заданному булеву флагу."""
        d = df.copy()
        # идентификатор серии: меняется, когда значение столбца flag меняется
        d["sid"] = d.groupby("league_name")[flag].apply(lambda x: (x != x.shift()).cumsum()).values
        return (
            d[d[flag]]
            .groupby(["league_name", "sid"], as_index=False)
            .agg(start=("match_date", "min"), end=("match_date", "max"), length=("match_id", "size"))
        )

    # ---------- основной расчёт ----------
    def build(self, teams: List[str]) -> Tuple[pd.DataFrame, dict]:
        """Возвращает (DataFrame, meta) по списку команд."""
        matches = self._load(teams)
        rows: List[dict] = []
        meta: dict = {}

        for team in teams:
            df_team = matches[(matches.team_home == team) | (matches.team_away == team)].copy()
            if df_team.empty:
                continue

            df_team.match_date = pd.to_datetime(df_team.match_date)
            df_flags = self._flags(df_team, team)
            desc = df_flags.sort_values("match_date", ascending=False)
            meta[team] = {}

            # вычисляем данные по каждому флагу
            for flag in self.FLAG_COLS:
                # текущая длина серии для каждой лиги
                cur = {lg: self._cur_len(g[flag]) for lg, g in desc.groupby("league_name")}

                # вся история серий → распределение, максимум и списки самых длинных
                hist = self._hist(df_flags, flag)
                dist, longest, mx = {}, {}, {}
                for lg, grp in hist.groupby("league_name"):
                    dist[lg] = grp.length.value_counts().sort_index().to_dict()
                    mx_len = grp.length.max()
                    mx[lg] = mx_len
                    longest[lg] = grp[grp.length == mx_len][["start", "end", "length"]].to_dict("records")

                meta[team][flag] = dict(current=cur, max=mx,
                                        distribution=dist, longest=longest)

            # формируем строки для итоговой таблицы
            for lg in meta[team]["is_win"]["current"]:
                row = {"team": team, "league": lg}
                for f, short in self.FLAG_NAMES.items():
                    row[short] = meta[team][f]["current"].get(lg, 0)
                rows.append(row)

        # безопасное формирование DataFrame
        if rows:
            df_out = pd.DataFrame(rows).set_index(["team", "league"]).sort_index()
        else:
            df_out = pd.DataFrame()
        return df_out, meta


# ═══════════════════════════════════════
# 2. Генератор HTML‑таблицы
# ═══════════════════════════════════════

def streak_table_html_hb(
    teams: List[str],
    db_uri: str,
    td_renderer: Callable[[int, int], str],
    link_endpoint: str | None = None,
) -> Tuple[str, dict]:
    """Возвращает (html‑таблица, meta‑данные) для переданных команд."""

    df, meta = StreakAnalyzerHB(db_uri).build(teams)

    if df.empty:
        return "", meta

    # ---------- строки таблицы ----------
    rows_html: List[str] = []
    for (tm, lg), r in df.iterrows():
        first_td = (
            f'<td><a href="{url_for(link_endpoint, team=tm, league=lg)}">{tm}</a></td>'
            if link_endpoint else f"<td>{tm}</td>"
        )
        cells = [first_td, f"<td>{lg}</td>"]

        for flag, short in StreakAnalyzerHB.FLAG_NAMES.items():
            cur = r[short]
            mx = meta[tm][flag]["max"].get(lg, 0)
            cells.append(td_renderer(cur, mx))

        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    # ---------- thead ----------
    header = "".join(f"<th>{h}</th>" for h in TABLE_HEADERS)
    table_html = (
        '<table class="table table-bordered table-sm mb-4">'
        f'<thead><tr>{header}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        "</table>"
    )
    return Markup(table_html), meta


# ═══════════════════════════════════════
# 3. Пример td‑рендера
# ═══════════════════════════════════════

def td_green(cur: int, mx: int) -> str:
    """Окрашивает ячейку оттенком зелёного в зависимости от отношения cur / mx."""
    if mx == 0:
        return f"<td>{cur}</td>"
    alpha = 0.05 + 0.95 * min(cur / mx, 1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'


# ═══════════════════════════════════════
# 4. Пример использования во Flask (фрагмент)
# ═══════════════════════════════════════
"""
from flask import Flask, render_template, request, redirect, url_for
from series_handball import streak_table_html_hb, td_green

app = Flask(__name__)
DB_URI = "postgresql://admin:123456er@localhost:5432/statix"
STREAK_HB_CACHE = {}

@app.route("/handball", methods=["GET", "POST"])
def handball():
    team1 = request.form.get("team1", "").strip()
    team2 = request.form.get("team2", "").strip()
    teams = [t for t in (team1, team2) if t]

    table_html, meta = streak_table_html_hb(teams, DB_URI, td_green,
                                            link_endpoint="handball_details")
    STREAK_HB_CACHE.clear(); STREAK_HB_CACHE.update(meta)

    return render_template("handball.html", streak_table=table_html,
                           team1=team1, team2=team2)
"""
