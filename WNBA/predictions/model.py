"""
Bayesian conjugate linear-regression model for WNBA point spreads.

Model
-----
    y = X beta + eps,    eps ~ Normal(0, sigma^2)
where y = HomeScore - AwayScore (positive favours the home team).

Conjugate Normal-Inverse-Gamma prior/posterior:
    beta | sigma^2 ~ Normal(m, sigma^2 * Lambda^{-1})
    sigma^2        ~ InverseGamma(a, b)

We store the posterior as (Lambda, eta, a, b) where:
    Lambda = precision matrix (= V^{-1})
    eta    = Lambda @ m   (precision-weighted mean; m = Lambda^{-1} eta)

Sequential ("online") update — the current posterior becomes the prior for the
next batch of games, so the model literally improves game over game:
    Lambda' = Lambda + X^T X
    eta'    = eta    + X^T y
    a'      = a + n/2
    b'      = b + 0.5 * ( y^T y + m^T Lambda m - m'^T Lambda' m' )

Posterior predictive for a new game x* is Student-t:
    dof   nu = 2a
    loc   mu = x*^T m                       (predicted home-minus-away spread)
    scale s  = sqrt( (b/a) * (1 + x*^T Lambda^{-1} x*) )
    P(home win) = P(y* > 0) = StudentT_nu( mu / s )

Between seasons we apply a forgetting/discount factor that re-inflates
predictive uncertainty so recent data carries more weight (roster turnover,
expansion teams) without discarding what was learned. Point estimates are
preserved; only the confidence (effective sample size) shrinks.

Features are standardized (except the intercept) using statistics frozen from
the burn-in period, so a single prior scale is sensible for every coefficient.
"""

import json
import numpy as np
from scipy import stats

from features import FEATURE_COLS, N_FEATURES


class BayesianSpreadModel:
    def __init__(self,
                 prior_coef_sd=6.0,        # prior sd of each (standardized) slope, in points
                 prior_intercept_sd=12.0,  # weak prior on the home-court constant
                 prior_sigma=12.0,         # prior residual sd of a game spread (points)
                 prior_sigma_strength=3.0):
        self.n_features = N_FEATURES
        self.feature_cols = list(FEATURE_COLS)

        # --- standardization (frozen after .fit_scaler) -------------------
        self.feat_mean = np.zeros(self.n_features)
        self.feat_std = np.ones(self.n_features)
        self._scaler_fit = False

        # --- prior on beta (in standardized space) ------------------------
        v0 = np.full(self.n_features, prior_coef_sd ** 2)
        v0[self.feature_cols.index("intercept")] = prior_intercept_sd ** 2
        self.Lambda = np.diag(1.0 / v0)                     # precision
        self.eta = self.Lambda @ np.zeros(self.n_features)  # -> m0 = 0

        # --- prior on sigma^2 (InverseGamma) ------------------------------
        self.a = float(prior_sigma_strength)
        self.b = float(prior_sigma ** 2 * (prior_sigma_strength - 1.0))

        self.n_obs = 0  # games assimilated (bookkeeping)

    # ------------------------------------------------------------------ #
    # Standardization
    # ------------------------------------------------------------------ #
    def fit_scaler(self, X):
        """Freeze standardization stats from burn-in data. Intercept untouched."""
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std < 1e-8] = 1.0
        i = self.feature_cols.index("intercept")
        mean[i] = 0.0
        std[i] = 1.0
        self.feat_mean = mean
        self.feat_std = std
        self._scaler_fit = True

    def _transform(self, X):
        X = np.atleast_2d(np.asarray(X, dtype=float))
        return (X - self.feat_mean) / self.feat_std

    # ------------------------------------------------------------------ #
    # Derived quantities
    # ------------------------------------------------------------------ #
    @property
    def mean_beta(self):
        return np.linalg.solve(self.Lambda, self.eta)

    @property
    def sigma2_hat(self):
        return self.b / max(self.a - 1.0, 1e-6)

    # ------------------------------------------------------------------ #
    # Sequential update
    # ------------------------------------------------------------------ #
    def update(self, X, y):
        """Assimilate a batch of completed games (current posterior -> prior)."""
        Xs = self._transform(X)
        y = np.asarray(y, dtype=float).ravel()
        n = len(y)
        if n == 0:
            return

        m_old = self.mean_beta
        Lambda_new = self.Lambda + Xs.T @ Xs
        eta_new = self.eta + Xs.T @ y
        m_new = np.linalg.solve(Lambda_new, eta_new)

        a_new = self.a + n / 2.0
        b_new = self.b + 0.5 * (
            float(y @ y)
            + float(m_old @ (self.Lambda @ m_old))
            - float(m_new @ (Lambda_new @ m_new))
        )

        self.Lambda = Lambda_new
        self.eta = eta_new
        self.a = a_new
        self.b = max(b_new, 1e-6)
        self.n_obs += n

    # ------------------------------------------------------------------ #
    # Forgetting / re-inflation
    # ------------------------------------------------------------------ #
    def discount(self, factor):
        """Shrink confidence by `factor` in (0,1]. Point estimates (m, sigma^2)
        are preserved; predictive uncertainty widens so new data matters more.
        Applied at season boundaries."""
        f = float(factor)
        if not (0 < f <= 1):
            return
        s2 = self.sigma2_hat               # capture residual variance BEFORE
        self.Lambda = self.Lambda * f
        self.eta = self.eta * f
        self.a = max(self.a * f, 1.0 + 1e-6)
        self.b = s2 * (self.a - 1.0)       # preserve sigma^2; only shrink confidence

    # ------------------------------------------------------------------ #
    # Prediction (posterior predictive Student-t)
    # ------------------------------------------------------------------ #
    def predict(self, X):
        """Return dict of arrays: pred_spread, win_prob_home, pp_scale, dof."""
        Xs = self._transform(X)
        m = self.mean_beta
        nu = 2.0 * self.a
        s2_coef = self.b / self.a

        mu = Xs @ m
        Linv_Xt = np.linalg.solve(self.Lambda, Xs.T)        # (p, n)
        quad = np.einsum("ij,ji->i", Xs, Linv_Xt)           # (n,)
        scale = np.sqrt(s2_coef * (1.0 + quad))
        scale = np.clip(scale, 1e-6, None)

        win_prob = stats.t.cdf(mu / scale, df=nu)
        return {
            "pred_spread": mu,
            "win_prob_home": win_prob,
            "pp_scale": scale,
            "dof": np.full_like(mu, nu),
        }

    def predict_one(self, x):
        out = self.predict(np.atleast_2d(x))
        return {k: float(v[0]) for k, v in out.items()}

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self):
        return {
            "feature_cols": self.feature_cols,
            "feat_mean": self.feat_mean.tolist(),
            "feat_std": self.feat_std.tolist(),
            "scaler_fit": self._scaler_fit,
            "Lambda": self.Lambda.tolist(),
            "eta": self.eta.tolist(),
            "a": self.a,
            "b": self.b,
            "n_obs": self.n_obs,
        }

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, d):
        m = cls()
        m.feature_cols = d["feature_cols"]
        m.n_features = len(m.feature_cols)
        m.feat_mean = np.array(d["feat_mean"], dtype=float)
        m.feat_std = np.array(d["feat_std"], dtype=float)
        m._scaler_fit = d.get("scaler_fit", True)
        m.Lambda = np.array(d["Lambda"], dtype=float)
        m.eta = np.array(d["eta"], dtype=float)
        m.a = float(d["a"])
        m.b = float(d["b"])
        m.n_obs = int(d.get("n_obs", 0))
        return m

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_dict(json.load(f))

    # ------------------------------------------------------------------ #
    def coefficients(self):
        """Human-readable posterior mean coefficients (standardized space)."""
        return dict(zip(self.feature_cols, self.mean_beta.tolist()))
