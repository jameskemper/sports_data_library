"""Compare feature sets with identical walk-forward logic (research only)."""
import numpy as np, pandas as pd
from scipy import stats
import config as C, features as F, adj_ratings as AR


def feats(variant, season, date, home, away):
    h = F.team_rating(season, date, home); a = F.team_rating(season, date, away)
    rest_h = F._rest_days(date, h["last_date"]); rest_a = F._rest_days(date, a["last_date"])
    rest = float(np.clip(rest_h - rest_a, -F.REST_CAP, F.REST_CAP))
    base = [1.0, h["net"]-a["net"], h["pf"]-a["pf"], a["pa"]-h["pa"],
            h["winpct"]-a["winpct"], h["form"]-a["form"], rest]
    if variant == "base":
        return base
    R = AR.ratings_asof(season, pd.Timestamp(date).strftime("%Y-%m-%d"))
    rh, ra = R.get(home, {}), R.get(away, {})
    adj_net = rh.get("net",0.0)-ra.get("net",0.0)
    adj_eff = rh.get("eff_net",0.0)-ra.get("eff_net",0.0)
    if variant == "base+net":
        return base + [adj_net]
    if variant == "base+net+eff":
        return base + [adj_net, adj_eff]
    if variant == "lean":   # replace raw margin features with adjusted ones
        return [1.0, adj_net, adj_eff, h["winpct"]-a["winpct"], h["form"]-a["form"], rest]
    raise ValueError(variant)


def build(variant, seasons):
    X, y, meta = [], [], []
    for s in seasons:
        df = F._load_results(s)
        for _, gm in df.iterrows():
            X.append(feats(variant, s, gm["Date"], gm["HomeTeam"], gm["AwayTeam"]))
            sp = float(gm["HomeScore"]-gm["AwayScore"])
            y.append(sp); meta.append({"season": s, "date": gm["Date"].strftime("%Y-%m-%d"),
                                       "home_win": int(sp>0)})
    return np.array(X), np.array(y), pd.DataFrame(meta)


class BR:  # minimal conjugate Bayesian linear regression (same math as model.py)
    def __init__(self, p, coef_sd=6.0, int_sd=12.0, sigma=12.0, a=3.0):
        v=np.full(p, coef_sd**2); v[0]=int_sd**2
        self.L=np.diag(1/v); self.eta=np.zeros(p); self.a=a; self.b=sigma**2*(a-1)
        self.mean=np.zeros(p); self.std=np.ones(p); self.fit=False
    def scale(self,X):
        m=X.mean(0); s=X.std(0); s[s<1e-8]=1; m[0]=0; s[0]=1; self.mean=m; self.std=s; self.fit=True
    def _t(self,X): return (np.atleast_2d(X)-self.mean)/self.std
    @property
    def m(self): return np.linalg.solve(self.L,self.eta)
    def update(self,X,y):
        Xs=self._t(X); y=np.asarray(y,float); n=len(y)
        if n==0: return
        mo=self.m; Ln=self.L+Xs.T@Xs; en=self.eta+Xs.T@y; mn=np.linalg.solve(Ln,en)
        self.a+=n/2; self.b=max(self.b+0.5*(y@y+mo@(self.L@mo)-mn@(Ln@mn)),1e-6); self.L=Ln; self.eta=en
    def discount(self,f):
        s2=self.b/max(self.a-1,1e-6); self.L*=f; self.eta*=f; self.a=max(self.a*f,1.0001); self.b=s2*(self.a-1)
    def predict(self,X):
        Xs=self._t(X); mu=Xs@self.m; nu=2*self.a
        quad=np.einsum("ij,ji->i",Xs,np.linalg.solve(self.L,Xs.T))
        sc=np.clip(np.sqrt(self.b/self.a*(1+quad)),1e-6,None)
        return mu, stats.t.cdf(mu/sc,df=nu)


def walk(variant):
    F.clear_caches(); AR.clear_caches()
    Xb,yb,_=build(variant, C.BURN_IN_SEASONS)
    m=BR(Xb.shape[1]); m.scale(Xb); m.update(Xb,yb)
    P,Y=[],[]
    for s in C.EVAL_SEASONS:
        Xs,ys,ms=build(variant,[s]); ms=ms.reset_index(drop=True); m.discount(C.SEASON_DISCOUNT)
        for d,idx in ms.groupby("date").groups.items():
            idx=list(idx); mu,wp=m.predict(Xs[idx])
            P+=list(wp); Y+=list(ms.loc[idx,"home_win"]); m.update(Xs[idx],ys[idx])
    P=np.array(P); Y=np.array(Y)
    acc=((P>=0.5).astype(int)==Y).mean(); brier=np.mean((P-Y)**2)
    return acc, brier, len(Y)


for v in ["base","base+net","base+net+eff","lean"]:
    acc,br,n=walk(v)
    print(f"{v:14} acc {acc:.4f}  brier {br:.4f}  (n={n})")
