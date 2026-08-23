"""HMM regime detection engine.

A Gaussian HMM used as a VOLATILITY CLASSIFIER — labels are descriptive,
assigned post-fit by mean return; the strategy layer sorts by volatility.
CRITICAL — no look-ahead: inference is forward-algorithm only (filtered
P(state_t | obs_{1:t})); ``model.predict()`` (Viterbi) is never used
because it revises past states using future observations.
"""

from __future__ import annotations

import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from scipy.stats import multivariate_normal

# Re-exported for backward compatibility: regime type definitions live in
# core.regime_types but remain importable from here.
from core.regime_types import (  # noqa: F401
    LABEL_SETS, LABEL_POLICY as _LABEL_POLICY, Regime, RegimeInfo,
    RegimeLabel, RegimeState)

logger = logging.getLogger("regime_trader.hmm")

#: Size multiplier while a regime change is pending confirmation (-25%).
TRANSITION_SIZE_MULT = 0.75
#: Size multiplier while the classifier is flickering (uncertainty mode).
UNCERTAINTY_SIZE_MULT = 0.50


class HMMEngine:
    """Gaussian HMM volatility-regime classifier with filtered inference.

    Key parameters: ``n_candidates`` (state counts scored by BIC),
    ``n_init`` (restarts per candidate), ``min_train_bars``,
    ``stability_bars`` (persistence before a change confirms),
    ``flicker_window``/``flicker_threshold`` (uncertainty mode),
    ``min_confidence`` (floor for confirmation bars), ``retrain_interval``
    (expanding-window cadence), ``return_column`` (labeling sort key).
    """

    def __init__(
        self,
        n_candidates: list[int] | None = None,
        n_init: int = 10,
        covariance_type: str = "full",
        min_train_bars: int = 504,
        stability_bars: int = 3,
        flicker_window: int = 20,
        flicker_threshold: int = 4,
        min_confidence: float = 0.55,
        retrain_interval: int = 63,
        return_column: str = "log_ret_1",
        n_iter: int = 200,
        random_state: int | None = None,
    ) -> None:
        self.n_candidates = list(n_candidates or [3, 4, 5, 6, 7])
        unknown = [k for k in self.n_candidates if k not in LABEL_SETS]
        if unknown:
            raise ValueError(f"no label set for candidate counts {unknown}")
        self.n_init = n_init
        self.covariance_type = covariance_type
        self.min_train_bars = min_train_bars
        self.stability_bars = stability_bars
        self.flicker_window = flicker_window
        self.flicker_threshold = flicker_threshold
        self.min_confidence = min_confidence
        self.retrain_interval = retrain_interval
        self.return_column = return_column
        self.n_iter = n_iter
        self.random_state = random_state

        self.model: GaussianHMM | None = None
        self.state_to_label: dict[int, RegimeLabel] = {}
        self.regime_info: dict[int, RegimeInfo] = {}
        self.feature_columns: list[str] | None = None
        self.metadata: dict[str, Any] = {}
        self._trained_bars: int = 0
        self._last_run: pd.DataFrame | None = None
        self._last_probs: np.ndarray | None = None

    # ------------------------------------------------------------------ fit

    def fit(self, features: pd.DataFrame) -> None:
        """Fit via BIC model selection and label states by mean return.
        For expanding-window retraining, refit when needs_retrain() is True."""
        if not isinstance(features, pd.DataFrame):
            raise TypeError("features must be a DataFrame (column names are "
                            "needed for labeling and validation)")
        if len(features) < self.min_train_bars:
            raise ValueError(
                f"need >= {self.min_train_bars} bars to fit, got {len(features)}"
            )
        if features.isna().any().any():
            raise ValueError("features contain NaNs; drop warm-up rows first")
        if self.return_column not in features.columns:
            raise ValueError(f"return column '{self.return_column}' not in features")

        self.feature_columns = list(features.columns)
        model, candidates = self.select_model(features)
        self.model = model
        self._trained_bars = len(features)

        ret_idx = self.feature_columns.index(self.return_column)
        order = np.argsort(model.means_[:, ret_idx])
        labels = LABEL_SETS[model.n_components]
        self.state_to_label = {int(s): labels[rank] for rank, s in enumerate(order)}

        self.regime_info = {}
        for s in range(model.n_components):
            label = self.state_to_label[s]
            strat, lev, pos, conf = _LABEL_POLICY[label]
            self.regime_info[s] = RegimeInfo(
                regime_id=s,
                regime_name=label.value,
                expected_return=float(model.means_[s, ret_idx]),
                expected_volatility=float(
                    np.sqrt(model.covars_[s][ret_idx, ret_idx])
                ),
                recommended_strategy_type=strat,
                max_leverage_allowed=lev,
                max_position_size_pct=pos,
                min_confidence_to_act=conf,
            )

        chosen = next(c for c in candidates
                      if c["n_components"] == model.n_components)
        self.metadata = {
            "n_regimes": int(model.n_components),
            "bic": chosen["bic"],
            "log_likelihood": chosen["log_likelihood"],
            "converged": chosen["converged"],
            "iterations": chosen["iterations"],
            "training_date": datetime.now(timezone.utc).isoformat(),
            "training_bars": len(features),
            "labels": {s: lbl.value for s, lbl in self.state_to_label.items()},
            "candidates": candidates,
        }
        self._last_run = None
        self._last_probs = None
        logger.info(
            "HMM fitted: n_regimes=%d bic=%.1f logL=%.1f converged=%s iter=%d "
            "labels=%s",
            model.n_components, chosen["bic"], chosen["log_likelihood"],
            chosen["converged"], chosen["iterations"], self.metadata["labels"],
        )

    def select_model(
        self, features: pd.DataFrame
    ) -> tuple[GaussianHMM, list[dict[str, Any]]]:
        """Fit every candidate (``n_init`` restarts each) and pick the lowest
        BIC = -2 * logL + n_params * log(n_samples). All scores logged."""
        X = features.to_numpy(dtype=float)
        n_samples, n_features = X.shape
        rng = np.random.default_rng(self.random_state)
        results: list[dict[str, Any]] = []
        best_model: GaussianHMM | None = None
        best_bic = np.inf

        for k in self.n_candidates:
            best_k: tuple[GaussianHMM, float] | None = None
            for _ in range(self.n_init):
                seed = int(rng.integers(0, 2**31 - 1))
                m = GaussianHMM(
                    n_components=k,
                    covariance_type=self.covariance_type,
                    n_iter=self.n_iter,
                    tol=1e-4,
                    random_state=seed,
                )
                try:
                    m.fit(X)
                    ll = float(m.score(X))
                except Exception as exc:  # degenerate init/covariance
                    logger.debug("candidate n=%d seed=%d failed: %s", k, seed, exc)
                    continue
                if not np.isfinite(ll):
                    continue
                if best_k is None or ll > best_k[1]:
                    best_k = (m, ll)
            if best_k is None:
                logger.warning("HMM candidate n=%d: all %d inits failed; skipped",
                               k, self.n_init)
                continue
            m, ll = best_k
            bic = -2.0 * ll + self._n_params(k, n_features) * np.log(n_samples)
            results.append({
                "n_components": k,
                "log_likelihood": ll,
                "bic": float(bic),
                "converged": bool(m.monitor_.converged),
                "iterations": int(m.monitor_.iter),
            })
            logger.info("HMM candidate n=%d: BIC=%.1f logL=%.1f converged=%s "
                        "iter=%d", k, bic, ll, m.monitor_.converged,
                        m.monitor_.iter)
            if bic < best_bic:
                best_bic, best_model = bic, m

        if best_model is None:
            raise RuntimeError("HMM training failed for every candidate")
        logger.info("HMM selected n_components=%d (lowest BIC=%.1f)",
                    best_model.n_components, best_bic)
        return best_model, results

    def _n_params(self, k: int, d: int) -> int:
        """Free parameters: startprob + transitions + means + covariances."""
        cov = {
            "full": k * d * (d + 1) // 2,
            "diag": k * d,
            "tied": d * (d + 1) // 2,
            "spherical": k,
        }[self.covariance_type]
        return (k - 1) + k * (k - 1) + k * d + cov

    def needs_retrain(self, n_total_bars: int) -> bool:
        """True when the expanding window has grown by ``retrain_interval``."""
        self._require_fitted()
        return n_total_bars - self._trained_bars >= self.retrain_interval

    # ------------------------------------------------- filtered inference

    def filter_probabilities(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Forward algorithm: P(state_t | obs_{1:t}) for every t.

        Log-space pass, normalized per step; uses only past and present
        observations — never Viterbi/smoothing. Returns (T, K) probabilities.
        """
        X = self._prepare(features)
        log_b = self._log_emissions(X)
        log_pi = np.log(np.maximum(self.model.startprob_, 1e-300))
        log_A = np.log(np.maximum(self.model.transmat_, 1e-300))

        log_alpha = np.empty_like(log_b)
        a = log_pi + log_b[0]
        a -= logsumexp(a)
        log_alpha[0] = a
        for t in range(1, len(X)):
            a = logsumexp(a[:, None] + log_A, axis=0) + log_b[t]
            a -= logsumexp(a)
            log_alpha[t] = a
        return np.exp(log_alpha)

    def predict_regime_filtered(
        self, features: pd.DataFrame | np.ndarray
    ) -> np.ndarray:
        """Filtered MAP state per bar (argmax) — causal by construction,
        verified in test_look_ahead.py."""
        return self.filter_probabilities(features).argmax(axis=1)

    def predict_regime_proba(
        self, features: pd.DataFrame | np.ndarray | None = None
    ) -> np.ndarray:
        """Filtered state probability distribution at the latest bar."""
        if features is not None:
            return self.filter_probabilities(features)[-1]
        if self._last_probs is None:
            raise RuntimeError("no prior prediction; pass features")
        return self._last_probs[-1]

    def _log_emissions(self, X: np.ndarray) -> np.ndarray:
        """Per-state Gaussian log-density of each observation, shape (T, K)."""
        out = np.empty((len(X), self.model.n_components))
        for s in range(self.model.n_components):
            out[:, s] = multivariate_normal(
                mean=self.model.means_[s], cov=self.model.covars_[s],
                allow_singular=True,
            ).logpdf(X)
        return out

    def _prepare(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        self._require_fitted()
        if isinstance(features, pd.DataFrame):
            missing = [c for c in self.feature_columns if c not in features.columns]
            if missing:
                raise ValueError(f"features missing columns: {missing}")
            X = features[self.feature_columns].to_numpy(dtype=float)
        else:
            X = np.asarray(features, dtype=float)
        if X.ndim != 2 or X.shape[1] != len(self.feature_columns):
            raise ValueError(f"expected (T, {len(self.feature_columns)}) features")
        if np.isnan(X).any():
            raise ValueError("features contain NaNs")
        if len(X) == 0:
            raise ValueError("features are empty")
        return X

    def _require_fitted(self) -> None:
        if self.model is None:
            raise RuntimeError("HMMEngine is not fitted; call fit() first")

    # --------------------------------------------- stability / confirmation

    def predict_series(self, features: pd.DataFrame) -> pd.DataFrame:
        """Causally classify every bar with confirmation + flicker filters.

        A regime change confirms only after ``stability_bars`` consecutive
        confident bars; the loop only looks backward, so row t is unchanged
        by appending future bars.
        """
        probs = self.filter_probabilities(features)
        raw = probs.argmax(axis=1)
        top_p = probs.max(axis=1)
        conf_ok = top_p >= self.min_confidence
        T = len(raw)
        index = features.index if isinstance(features, pd.DataFrame) else pd.RangeIndex(T)

        confirmed = np.empty(T, dtype=int)
        changed = np.zeros(T, dtype=bool)
        current = int(raw[0])
        cand, cand_count = -1, 0
        for t in range(T):
            if t > 0 and raw[t] != raw[t - 1]:
                logger.warning(
                    "Regime change detected at %s: %s -> %s (unconfirmed, p=%.2f)",
                    index[t], self.state_to_label[int(raw[t - 1])].value,
                    self.state_to_label[int(raw[t])].value, top_p[t],
                )
            if raw[t] == current:
                cand, cand_count = -1, 0
            elif conf_ok[t]:
                if raw[t] == cand:
                    cand_count += 1
                else:
                    cand, cand_count = int(raw[t]), 1
                if cand_count >= self.stability_bars:
                    logger.info(
                        "Regime change confirmed at %s: %s -> %s after %d bars",
                        index[t], self.state_to_label[current].value,
                        self.state_to_label[cand].value, cand_count,
                    )
                    current = cand
                    changed[t] = True
                    cand, cand_count = -1, 0
            confirmed[t] = current

        # Consecutive bars the confirmed regime has persisted, per bar.
        consecutive = np.ones(T, dtype=int)
        for t in range(1, T):
            consecutive[t] = consecutive[t - 1] + 1 if confirmed[t] == confirmed[t - 1] else 1

        # Flicker: raw-state switches within the trailing window.
        switches = np.zeros(T)
        switches[1:] = raw[1:] != raw[:-1]
        flicker_rate = (
            pd.Series(switches).rolling(self.flicker_window, min_periods=1)
            .sum().to_numpy()
        )
        flickering = flicker_rate > self.flicker_threshold

        df = pd.DataFrame(
            {
                "raw_state": raw,
                "probability": top_p,
                "confirmed_state": confirmed,
                "label": [self.state_to_label[int(s)].value for s in confirmed],
                "is_confirmed": (raw == confirmed) & ~flickering,
                "regime_changed": changed,
                "consecutive_bars": consecutive,
                "flicker_rate": flicker_rate,
                "is_flickering": flickering,
            },
            index=index,
        )
        self._last_run = df
        self._last_probs = probs
        return df

    def predict(self, features: pd.DataFrame) -> RegimeState:
        """Classify the latest bar and package it as a :class:`RegimeState`."""
        df = self.predict_series(features)
        last = df.iloc[-1]
        probs = self._last_probs[-1]
        state_id = int(last["confirmed_state"])
        ts = df.index[-1]
        timestamp = ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else None
        return RegimeState(
            label=RegimeLabel(last["label"]),
            state_id=state_id,
            probability=float(probs[state_id]),
            state_probabilities={int(s): float(p) for s, p in enumerate(probs)},
            timestamp=timestamp,
            is_confirmed=bool(last["is_confirmed"]),
            consecutive_bars=int(last["consecutive_bars"]),
        )

    # ------------------------------------------------------------ accessors

    def _last(self) -> pd.Series:
        if self._last_run is None:
            raise RuntimeError("no prediction yet; call predict()/predict_series()")
        return self._last_run.iloc[-1]

    def get_regime_stability(self) -> int:
        """Consecutive bars the current confirmed regime has persisted."""
        return int(self._last()["consecutive_bars"])

    def detect_regime_change(self) -> bool:
        """True only if a confirmed regime change occurred at the latest bar."""
        return bool(self._last()["regime_changed"])

    def get_regime_flicker_rate(self) -> float:
        """Raw-state switches within the trailing flicker window."""
        return float(self._last()["flicker_rate"])

    def is_flickering(self) -> bool:
        """True when the flicker rate exceeds the threshold (uncertainty mode)."""
        return bool(self._last()["is_flickering"])

    def get_size_multiplier(self) -> float:
        """Position-size multiplier from the classifier's current certainty:
        0.50 while flickering, 0.75 during an unconfirmed transition, else 1.0."""
        last = self._last()
        if last["is_flickering"]:
            return UNCERTAINTY_SIZE_MULT
        if not last["is_confirmed"]:
            return TRANSITION_SIZE_MULT
        return 1.0

    def get_transition_matrix(self) -> pd.DataFrame:
        """Learned transition probabilities, labeled by regime name."""
        self._require_fitted()
        names = [self.state_to_label[s].value
                 for s in range(self.model.n_components)]
        return pd.DataFrame(self.model.transmat_, index=names, columns=names)

    def get_regime_info(self, state_id: int | None = None
                        ) -> RegimeInfo | dict[int, RegimeInfo]:
        """Metadata for one state, or all states when ``state_id`` is None."""
        self._require_fitted()
        return self.regime_info if state_id is None else self.regime_info[state_id]

    def get_diagnostics(self) -> dict[str, Any]:
        """Fitted-model diagnostics: metadata, labels, and transitions."""
        self._require_fitted()
        return {
            **self.metadata,
            "transition_matrix": self.get_transition_matrix().to_dict(),
            "state_means_return": {
                s: info.expected_return for s, info in self.regime_info.items()
            },
        }

    # ---------------------------------------------------------- persistence

    def save(self, path: str | Path) -> None:
        """Pickle the fitted model with its labels and metadata."""
        self._require_fitted()
        payload = {
            "model": self.model,
            "state_to_label": self.state_to_label,
            "regime_info": self.regime_info,
            "feature_columns": self.feature_columns,
            "metadata": self.metadata,
            "trained_bars": self._trained_bars,
            "params": {
                "n_candidates": self.n_candidates,
                "n_init": self.n_init,
                "covariance_type": self.covariance_type,
                "min_train_bars": self.min_train_bars,
                "stability_bars": self.stability_bars,
                "flicker_window": self.flicker_window,
                "flicker_threshold": self.flicker_threshold,
                "min_confidence": self.min_confidence,
                "retrain_interval": self.retrain_interval,
                "return_column": self.return_column,
                "n_iter": self.n_iter,
                "random_state": self.random_state,
            },
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f)
        logger.info("HMM saved to %s (n_regimes=%d, bic=%.1f)", path,
                    self.metadata["n_regimes"], self.metadata["bic"])

    @classmethod
    def load(cls, path: str | Path) -> "HMMEngine":
        """Restore a saved engine. Only load files you created yourself —
        pickle executes code on load."""
        with open(path, "rb") as f:
            payload = pickle.load(f)
        engine = cls(**payload["params"])
        engine.model = payload["model"]
        engine.state_to_label = payload["state_to_label"]
        engine.regime_info = payload["regime_info"]
        engine.feature_columns = payload["feature_columns"]
        engine.metadata = payload["metadata"]
        engine._trained_bars = payload["trained_bars"]
        logger.info("HMM loaded from %s (trained %s)", path,
                    engine.metadata.get("training_date"))
        return engine
