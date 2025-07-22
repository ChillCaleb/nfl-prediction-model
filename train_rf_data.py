import itertools
import pandas as pd
import numpy as np
from player_injection import inject_all_teams


def extract_archetype_flags(player_list):
    flags = {
        "has_dual_threat_qb": 0,
        "has_elite_receiver": 0,
        "has_lockdown_cb": 0,
        "has_star_rusher": 0,
        "has_route_runner": 0,
        "team_elite_archetype_count": 0
    }
    for player in player_list:
        label = player["label"].lower()
        pos = player["position"].lower()
        archetype = player["archetype"].lower()

        if "dual" in archetype and pos == "qb":
            flags["has_dual_threat_qb"] = 1
        if any(x in archetype for x in ["yac specialist", "deep threat", "route runner"]):
            if pos in ["wr", "te"]:
                flags["has_elite_receiver"] = 1
        if "lockdown corner" in archetype:
            flags["has_lockdown_cb"] = 1
        if any(x in archetype for x in ["disrupter", "closer"]):
            if pos in ["lb", "dl"]:
                flags["has_star_rusher"] = 1
        if "route runner" in archetype and pos == "wr":
            flags["has_route_runner"] = 1
        if any(x in archetype for x in ["elite", "lockdown", "disrupter", "closer"]):
            flags["team_elite_archetype_count"] += 1

    return flags


def generate_training_set():
    team_data = inject_all_teams()
    features = []
    labels = []

    for team_a, team_b in itertools.permutations(team_data.keys(), 2):
        roster_a = team_data[team_a]
        roster_b = team_data[team_b]

        flags_a = extract_archetype_flags(roster_a)
        flags_b = extract_archetype_flags(roster_b)

        feature_row = {
            "team_a": team_a,
            "team_b": team_b,
        }
        for key in flags_a:
            feature_row[f"a_{key}"] = flags_a[key]
        for key in flags_b:
            feature_row[f"b_{key}"] = flags_b[key]

        # For now, simulate label: team_a wins if more elite archetypes
        label = int(flags_a["team_elite_archetype_count"] >= flags_b["team_elite_archetype_count"])
        features.append(feature_row)
        labels.append(label)

    X = pd.DataFrame(features)
    y = pd.Series(labels)
    return X, y


if __name__ == "__main__":
    X, y = generate_training_set()
    print("Training set size:", X.shape)
    print(X.head())
