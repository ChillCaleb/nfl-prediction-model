import math
import numpy as np


def z_score(value, mean, std):
    if std == 0:
        return 0.0
    return (value - mean) / std


def normal_cdf(value):
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def outperform_probability(team1_value, team2_value, stat_series):
    mean = stat_series.mean()
    std = stat_series.std()
    z1 = z_score(team1_value, mean, std)
    z2 = z_score(team2_value, mean, std)
    return normal_cdf(z1 - z2)


def logistic_win_probability(rating_diff, b0=0.0, b1=None, scale=12.0):
    coefficient = 1 / scale if b1 is None else b1
    exponent = -(b0 + coefficient * rating_diff)
    return 1 / (1 + np.exp(exponent))


def bayesian_update(prior, likelihood, evidence):
    if evidence == 0:
        return 0.0
    return (likelihood * prior) / evidence


def elo_expected(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))


def elo_update(r1, r2, k=20, outcome=1):
    expected = elo_expected(r1, r2)
    return r1 + k * (outcome - expected)


MODEL_REGISTRY = {
    "outperform": outperform_probability,
    "logistic": logistic_win_probability,
    "bayesian": bayesian_update,
    "elo_expected": elo_expected,
}
