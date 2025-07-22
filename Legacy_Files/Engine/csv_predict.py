overall_weights = (0.4, 0.4, 0.2)  # offense, defense, special teams

def calc_overall_rating(team_abbr, sos_dict, league_avg):
    offense = calc_total_offense(team_abbr, sos_dict, league_avg)
    defense = calc_total_defense(team_abbr, sos_dict, league_avg)
    special = calc_special_teams_rating(team_abbr)

    w_off, w_def, w_st = overall_weights
    score = (
        offense * w_off +
        defense * w_def +
        special * w_st
    )

    from Engine.data_loader import update_df
    update_df(team_abbr, overall_rating=score)
    return score

def simulate_season(sos_dict, league_avg, model_name="outperform"):
    from Engine.probability_models import MODEL_REGISTRY, logistic_win_probability

    print(f"\n📅 Starting simulation using '{model_name}' model...")
    schedule = get_schedule_df()
    schedule = schedule.dropna(subset=["Winner/tie", "Loser/tie"])

    teams = pd.unique(schedule[["Winner/tie", "Loser/tie"]].values.ravel())
    wins = {team: 0 for team in teams}
    losses = {team: 0 for team in teams}

    model_func = MODEL_REGISTRY.get(model_name)
    if model_func is None:
        raise ValueError(f"Unknown model: {model_name}")

    for _, game in schedule.iterrows():
        team1 = game["Winner/tie"]
        team2 = game["Loser/tie"]

        r1 = calc_overall_rating(team1, sos_dict, league_avg)
        r2 = calc_overall_rating(team2, sos_dict, league_avg)

        # Choose input format based on model type
        if model_name == "outperform":
            prob = model_func(r1, r2, pd.Series([r1, r2]))
        elif model_name == "bayesian":
            prior = 0.5
            likelihood = logistic_win_probability(r1 - r2)
            evidence = 1.0
            prob = model_func(prior, likelihood, evidence)
        elif model_name == "elo_expected":
            prob = model_func(r1, r2)
        elif model_name == "elo_update":
            outcome = 1  # Assume team1 is expected to win initially
            prob = model_func(r1, r2, k=20, outcome=1)
        else:
            prob = model_func(r1 - r2)

        winner = team1 if np.random.rand() < prob else team2
        loser = team2 if winner == team1 else team1

        wins[winner] += 1
        losses[loser] += 1

    standings = pd.DataFrame({
        "Team": list(wins.keys()),
        "Wins": list(wins.values()),
        "Losses": list(losses.values())
    }).sort_values(["Wins", "Losses"], ascending=[False, True]).reset_index(drop=True)

    print("\n🎲 Probabilistic Season Results Using Model:", model_name)
    print(standings.to_string(index=False))
