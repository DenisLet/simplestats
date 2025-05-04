#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""series_yellow_fixed.py — корректный streak‑анализ по итоговым жёлтым карточкам (full‑time).

Исправления:
• Даты приводятся к datetime и сортируются перед анализом.
• Идентификатор серии (`sid`) считается через `groupby.transform`, поэтому индексы не расходятся.
• Все булевы флаги приводятся к `bool` через `astype(bool)`.
• SQL использует `COALESCE` для исключения NULL.
• Публичные функции и подписи полностью совместимы с исходником (`yc_streak_table_html`, `td_green`).
"""

from __future__ import annotations
from typing import List, Callable, Tuple, Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from flask import url_for
from markupsafe import Markup

TABLE_HEADERS: List[str] = [
    "team","league","W","L","W/D","D/L",
    "YC>1.5","YC>2.5","YC>3.5","YC>4.5",
    "YC<1.5","YC<2.5","YC<3.5","YC<4.5",
]

class YellowAnalyzer:
    FLAG_NAMES: Dict[str,str] = {
        "is_win":"W","is_loss":"L","is_not_loss":"W/D","is_not_win":"D/L",
        "yc_lt1_5":"YC<1.5","yc_lt2_5":"YC<2.5","yc_lt3_5":"YC<3.5","yc_lt4_5":"YC<4.5",
        "yc_gt1_5":"YC>1.5","yc_gt2_5":"YC>2.5","yc_gt3_5":"YC>3.5","yc_gt4_5":"YC>4.5",
    }
    FLAG_COLS = list(FLAG_NAMES)

    def __init__(self, db_uri:str):
        self.engine = create_engine(db_uri)

    # ---------- SQL ----------
    def _load(self, teams:List[str]) -> pd.DataFrame:
        ph=','.join(f":{i}" for i,_ in enumerate(teams))
        sql=f"""
        SELECT m.match_id, m.match_date, m.league_name, m.team_home, m.team_away,
               COALESCE(h1.home_yellow,0)+COALESCE(h2.home_yellow,0) AS home_yellow,
               COALESCE(h1.away_yellow,0)+COALESCE(h2.away_yellow,0) AS away_yellow
        FROM soccer_main m
        JOIN soccer_half1_stats h1 USING(match_id)
        JOIN soccer_half2_stats h2 USING(match_id)
        WHERE m.team_home IN ({ph}) OR m.team_away IN ({ph})
        ORDER BY m.match_date;
        """
        return pd.read_sql(text(sql), self.engine, params={str(i):t for i,t in enumerate(teams)})

    # ---------- flags ----------
    @staticmethod
    def _flags(df:pd.DataFrame, team:str) -> pd.DataFrame:
        h = df.team_home.eq(team)
        yc_team = df.home_yellow.where(h, df.away_yellow)
        yc_opp  = df.away_yellow.where(h, df.home_yellow)
        total   = (df.home_yellow + df.away_yellow).astype(int)
        c = df.copy()
        c["is_win"]      = yc_team.gt(yc_opp)
        c["is_loss"]     = yc_team.lt(yc_opp)
        c["is_not_loss"] = yc_team.ge(yc_opp)
        c["is_not_win"]  = yc_team.le(yc_opp)
        # totals
        c["yc_lt1_5"] = total.le(1); c["yc_gt1_5"] = total.ge(2)
        c["yc_lt2_5"] = total.le(2); c["yc_gt2_5"] = total.ge(3)
        c["yc_lt3_5"] = total.le(3); c["yc_gt3_5"] = total.ge(4)
        c["yc_lt4_5"] = total.le(4); c["yc_gt4_5"] = total.ge(5)
        return c.astype({col:bool for col in YellowAnalyzer.FLAG_COLS})

    # ---------- helpers ----------
    @staticmethod
    def _cur_len(s:pd.Series) -> int:
        n=0
        for v in s:
            if v: n+=1
            else: break
        return n

    @staticmethod
    def _hist(df:pd.DataFrame, flag:str) -> pd.DataFrame:
        d = df.sort_values('match_date').copy()
        d['sid'] = d.groupby('league_name')[flag].transform(lambda x:(x!=x.shift()).cumsum())
        return (
            d[d[flag]]
            .groupby(['league_name','sid'],as_index=False)
            .agg(start=('match_date','first'), end=('match_date','last'), length=('match_id','size'))
        )

    # ---------- main ----------
    def build(self, teams:List[str]) -> Tuple[pd.DataFrame,dict]:
        matches=self._load(teams)
        rows=[]; meta={}
        for team in teams:
            df_team = matches[(matches.team_home==team)|(matches.team_away==team)].copy()
            if df_team.empty: continue
            df_team['match_date']=pd.to_datetime(df_team['match_date']); df_team.sort_values('match_date',inplace=True)
            df_flags=self._flags(df_team,team); desc=df_flags.sort_values('match_date',ascending=False)
            meta[team]={}
            for flag in self.FLAG_COLS:
                cur={lg:self._cur_len(g[flag]) for lg,g in desc.groupby('league_name')}
                hist=self._hist(df_flags,flag)
                dist,longest,mx={}, {}, {}
                for lg,grp in hist.groupby('league_name'):
                    dist[lg]=grp.length.value_counts().sort_index().to_dict()
                    mx_len=int(grp.length.max()) if not grp.empty else 0
                    mx[lg]=mx_len
                    longest[lg]=grp[grp.length==mx_len][['start','end','length']].to_dict('records') if mx_len else []
                meta[team][flag]={'current':cur,'max':mx,'distribution':dist,'longest':longest}
            for lg in meta[team]['is_win']['current']:
                row={'team':team,'league':lg};
                for f,short in self.FLAG_NAMES.items(): row[short]=meta[team][f]['current'].get(lg,0)
                rows.append(row)
        df_out=pd.DataFrame(rows).set_index(['team','league']).sort_index() if rows else pd.DataFrame([])
        return df_out, meta

# ---------- HTML helper ----------

def yc_streak_table_html(teams:List[str], db_uri:str, td_renderer:Callable[[int,int],str], link_endpoint:Optional[str]=None) -> Tuple[Markup,dict]:
    df,meta=YellowAnalyzer(db_uri).build(teams)
    if df.empty: return Markup(""),meta
    rows=[]
    for (tm,lg),r in df.iterrows():
        first=f'<td><a href="{url_for(link_endpoint,team=tm,league=lg)}">{tm}</a></td>' if link_endpoint else f'<td>{tm}</td>'
        cells=[first,f'<td>{lg}</td>']
        for flag,short in YellowAnalyzer.FLAG_NAMES.items():
            cur=int(r[short]); mx=meta[tm][flag]['max'].get(lg,0); cells.append(td_renderer(cur,mx))
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    header=''.join(f'<th>{h}</th>' for h in TABLE_HEADERS)
    table='<table class="table table-bordered table-sm mb-4"><thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
    return Markup(table), meta

# ---------- td renderer ----------

def td_green(cur:int,mx:int)->str:
    if mx==0: return f'<td>{cur}</td>'
    alpha=0.05+0.95*min(cur/mx,1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'
