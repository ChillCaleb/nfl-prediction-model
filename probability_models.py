import numpy as np
from scipy.stats import norm

# ========================
# Core Probability Models
# ========================

# Basic Z-Score function
def z_score(value, mean, std):
    if std == 0:
        return 0.0  # Avoid division by zero
    return (value - mean) / std

# Outperform probability using z-score difference and standard normal CDF
def outperform_probability(team1_value, team2_value, stat_series):
    mean = stat_series.mean()
    std = stat_series.std()
    z1 = z_score(team1_value, mean, std)
    z2 = z_score(team2_value, mean, std)
    return norm.cdf(z1 - z2)

# Logistic win probability model based on rating difference
def logistic_win_probability(rating_diff, b0=0, b1=1):
    return 1 / (1 + np.exp(-(b0 + b1 * rating_diff)))

# Bayesian update of win probability given prior and likelihood
def bayesian_update(prior, likelihood, evidence):
    if evidence == 0:
        return 0.0
    return (likelihood * prior) / evidence

# Elo rating adjustment functions
import numpy as np

def elo_expected(r1, r2):
    """
    Compute the expected score for team 1 against team 2.

    Parameters:
    - r1: Rating of team 1
    - r2: Rating of team 2

    Returns:
    - Expected win probability for team 1
    """
    return 1 / (1 + 10 ** ((r2 - r1) / 400))


def elo_update(r1, r2, k=20, outcome=1):
    """
    Update Elo rating for team 1 after a game against team 2.

    Parameters:
    - r1: Rating of team 1 (before game)
    - r2: Rating of team 2 (before game)
    - k: K-factor (default 20)
    - outcome: 1 if team 1 wins, 0 if team 1 loses, 0.5 for tie

    Returns:
    - Updated rating for team 1
    """
    expected = elo_expected(r1, r2)
    return r1 + k * (outcome - expected)

# ========================
# Model Selector Registry
# ========================

MODEL_REGISTRY = {
    "outperform": outperform_probability,
    "logistic": logistic_win_probability,
    "bayesian": bayesian_update,
    "elo_expected": elo_expected,
    "elo_update": elo_update
}
