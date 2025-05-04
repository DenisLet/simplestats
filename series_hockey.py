#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""series_hockey_fixed.py — корректный расчёт серий по хоккею + HTML‑вывод"""
from __future__ import annotations
from typing import List, Callable, Tuple, Dict
import html
import pandas as pd
from sqlalchemy import create_engine
from flask import url_for
from markupsafe import Markup

TABLE_HEADERS: List[str] = [
    'team','league','W','L','W/D','D/L',
    'GF=0','GF<0.5','GF<1.5','GF>1.5','GF<2.5','GF>2.5',
    'GA=0','GA<0.5','GA<1.5','GA>1.5','GA<2.5','GA>2.5',
    'T=0','T<0.5','T<1.5','T>1.5','T<2.5','T>2.5',
    'T<3.5','T>3.5','T<4.5','T>4.5','T<5.5','T>5.5']

class StreakAnalyzerHOC:
    FLAG_NAMES: Dict[str,str] = {
        'is_win':'W','is_loss':'L','is_not_loss':'W/D','is_not_win':'D/L',
        'gf_eq0':'GF=0','gf_gt0_5':'GF>0.5','gf_gt1_5':'GF>1.5','gf_lt1_5':'GF<1.5','gf_gt2_5':'GF>2.5','gf_lt2_5':'GF<2.5',
        'ga_eq0':'GA=0','ga_gt0_5':'GA>0.5','ga_gt1_5':'GA>1.5','ga_lt1_5':'GA<1.5','ga_gt2_5':'GA>2.5','ga_lt2_5':'GA<2.5',
        'tot_eq0':'T=0','tot_gt0_5':'T>0.5','tot_gt1_5':'T>1.5','tot_lt1_5':'T<1.5','tot_gt2_5':'T>2.5','tot_lt2_5':'T<2.5',
        'tot_gt3_5':'T>3.5','tot_lt3_5':'T<3.5','tot_gt4_5':'T>4.5','tot_lt4_5':'T<4.5','tot_gt5_5':'T>5.5','tot_lt5_5':'T<5.5'}
    FLAG_COLS = list(FLAG_NAMES)
    def __init__(self, db_uri:str):
        self.engine = create_engine(db_uri)
    def _load(self, teams:List[str]) -> pd.DataFrame:
        ph=','.join(f"%({i})s" for i,_ in enumerate(teams))
        sql=f"SELECT match_id,match_date,league_name,team_home,team_away,home_score_ft,away_score_ft FROM hockey_main WHERE team_home IN ({ph}) OR team_away IN ({ph}) ORDER BY match_date;"
        return pd.read_sql(sql,self.engine,params={str(i):t for i,t in enumerate(teams)})
    @staticmethod
    def _flags(df:pd.DataFrame, team:str)->pd.DataFrame:
        h=df.team_home.eq(team)
        win=(h & (df.home_score_ft>df.away_score_ft))|(~h & (df.away_score_ft>df.home_score_ft))
        loss=(h & (df.home_score_ft<df.away_score_ft))|(~h & (df.away_score_ft<df.home_score_ft))
        gf=df.home_score_ft.where(h,df.away_score_ft); ga=df.away_score_ft.where(h,df.home_score_ft); tot=df.home_score_ft+df.away_score_ft
        c=df.copy(); c['is_win']=win.astype(bool); c['is_loss']=loss.astype(bool); c['is_not_loss']=~loss; c['is_not_win']=~win
        setf=c.__setitem__; setf('gf_eq0',gf.eq(0)); setf('gf_gt0_5',gf.ge(1)); setf('gf_gt1_5',gf.ge(2)); setf('gf_lt1_5',gf.le(1)); setf('gf_gt2_5',gf.ge(3)); setf('gf_lt2_5',gf.le(2))
        setf('ga_eq0',ga.eq(0)); setf('ga_gt0_5',ga.ge(1)); setf('ga_gt1_5',ga.ge(2)); setf('ga_lt1_5',ga.le(1)); setf('ga_gt2_5',ga.ge(3)); setf('ga_lt2_5',ga.le(2))
        setf('tot_eq0',tot.eq(0)); setf('tot_gt0_5',tot.ge(1)); setf('tot_gt1_5',tot.ge(2)); setf('tot_lt1_5',tot.le(1)); setf('tot_gt2_5',tot.ge(3)); setf('tot_lt2_5',tot.le(2)); setf('tot_gt3_5',tot.ge(4)); setf('tot_lt3_5',tot.le(3)); setf('tot_gt4_5',tot.ge(5)); setf('tot_lt4_5',tot.le(4)); setf('tot_gt5_5',tot.ge(6)); setf('tot_lt5_5',tot.le(5))
        return c
    @staticmethod
    def _cur_len(s:pd.Series)->int:
        n=0
        for v in s:
            if v: n+=1
            else: break
        return n
    @staticmethod
    def _hist(df:pd.DataFrame, flag:str)->pd.DataFrame:
        d=df.sort_values('match_date').copy(); d['sid']=d.groupby('league_name')[flag].transform(lambda x:(x!=x.shift()).cumsum())
        return d[d[flag]].groupby(['league_name','sid'],as_index=False).agg(start=('match_date','first'),end=('match_date','last'),length=('match_id','size'))
    def build(self, teams:List[str])->Tuple[pd.DataFrame,dict]:
        matches=self._load(teams); rows=[]; meta={}
        for team in teams:
            df_team=matches[(matches.team_home==team)|(matches.team_away==team)].copy()
            if df_team.empty: continue
            df_team['match_date']=pd.to_datetime(df_team['match_date']); df_team.sort_values('match_date',inplace=True)
            df_flags=self._flags(df_team,team); desc=df_flags.sort_values('match_date',ascending=False); meta[team]={}
            for flag in self.FLAG_COLS:
                cur={lg:self._cur_len(g[flag]) for lg,g in desc.groupby('league_name')}
                hist=self._hist(df_flags,flag); dist={}; longest={}; mx={}
                for lg,grp in hist.groupby('league_name'):
                    dist[lg]=grp.length.value_counts().sort_index().to_dict(); mlen=int(grp.length.max()) if not grp.empty else 0; mx[lg]=mlen; longest[lg]=grp[grp.length==mlen][['start','end','length']].to_dict('records') if mlen else []
                meta[team][flag]={'current':cur,'max':mx,'distribution':dist,'longest':longest}
            for lg in meta[team]['is_win']['current']:
                row={'team':team,'league':lg};
                for f,short in self.FLAG_NAMES.items(): row[short]=meta[team][f]['current'].get(lg,0)
                rows.append(row)
        df_out=pd.DataFrame(rows).set_index(['team','league']).sort_index() if rows else pd.DataFrame([])
        return df_out, meta

def streak_table_html(teams:List[str], db_uri:str, td_renderer:Callable[[int,int],str], link_endpoint:str|None=None)->Tuple[str,dict]:
    df,meta=StreakAnalyzerHOC(db_uri).build(teams)
    if df.empty: return "",meta
    rows=[]
    for (tm,lg),r in df.iterrows():
        first=f'<td><a href="{url_for(link_endpoint,team=tm,league=lg)}">{html.escape(tm)}</a></td>' if link_endpoint else f'<td>{html.escape(tm)}</td>'
        cells=[first,f'<td>{html.escape(lg)}</td>']
        for flag,short in StreakAnalyzerHOC.FLAG_NAMES.items():
            cur=int(r[short]); mx=meta[tm][flag]['max'].get(lg,0); cells.append(td_renderer(cur,mx))
        rows.append('<tr>'+''.join(cells)+'</tr>')
    header=''.join(f'<th>{h}</th>' for h in TABLE_HEADERS)
    table='<table class="table table-bordered table-sm mb-4"><thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
    return Markup(table), meta

def td_green(cur:int,mx:int)->str:
    if mx==0: return f'<td>{cur}</td>'
    alpha=0.05+0.95*min(cur/mx,1) if cur else 0
    return f'<td style="background:rgba(0,200,0,{alpha:.2f});">{cur}</td>'
