"""Tests for core.hmm_engine: model selection, labeling, and filters."""

import pytest

from core.hmm_engine import HMMEngine, Regime


class TestModelSelection:
    """select_model picks a reasonable state count from candidates."""

    @pytest.mark.skip(reason="skeleton — implement with hmm_engine")
    def test_selects_from_candidates(self) -> None:
        """Chosen n_states is one of the configured candidates."""
        raise NotImplementedError

    @pytest.mark.skip(reason="skeleton — implement with hmm_engine")
    def test_rejects_insufficient_history(self) -> None:
        """fit raises ValueError below min_train_bars."""
        raise NotImplementedError


class TestStateLabeling:
    """States map to low/mid/high vol regimes by emission volatility."""

    @pytest.mark.skip(reason="skeleton — implement with hmm_engine")
    def test_labels_ordered_by_volatility(self) -> None:
        raise NotImplementedError


class TestFilters:
    """Confidence floor, stability, and flicker filters."""

    @pytest.mark.skip(reason="skeleton — implement with hmm_engine")
    def test_low_confidence_returns_unknown(self) -> None:
        """Posterior below min_confidence yields Regime.UNKNOWN."""
        raise NotImplementedError

    @pytest.mark.skip(reason="skeleton — implement with hmm_engine")
    def test_unstable_regime_not_trusted(self) -> None:
        """A regime younger than stability_bars is flagged unstable."""
        raise NotImplementedError

    @pytest.mark.skip(reason="skeleton — implement with hmm_engine")
    def test_flicker_detection(self) -> None:
        """More than flicker_threshold switches in flicker_window flags
        flickering."""
        raise NotImplementedError
