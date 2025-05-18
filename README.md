# NFL Prediction Model

A structured, player-based NFL simulation framework built to reflect real football dynamics — not just averages, but impact, matchups, and game-breaking scenarios.

---

## Overview

This project predicts NFL game outcomes by combining:

* Statistical modeling (Z-scores, Bayesian updates, Elo ratings, logistic regression)
* Player-specific performance ratings that roll up into team unit ratings
* Matchup evaluation (e.g., QB under pressure vs. pass rush efficiency)

The model is split into two interconnected components:

* **Prediction Engine** — responsible for simulating games, seasons, and outcomes based on raw team and player data
* **Reasoning Engine** — designed to explain why outcomes occur, analyze positional matchups, and highlight key strategic differences between teams

---

## Core Philosophy

> "If a QB gets injured, the passing offense rating should drop. If WR5 is out, that shouldn't shift anything."

This model reflects football logic:

* Player ratings build team strength — it’s not flat averaging
* Matchups matter: who’s playing who, and how they match up
* Stats are pulled from reliable public sources and mapped into a unified format
* Outcomes aren’t just simulated — they’re explained

---

## Project Structure

```
NFL_predict/
├── data_loader.py         # Loads team-level CSVs (to be renamed team.py)
├── scraper.py             # Scrapes player data from web (to be renamed player.py)
├── offense.py / defense.py / special_teams.py
├── probability_models.py  # Statistical logic for win probabilities
├── predict.py             # Runs simulations based on ratings (Prediction Engine)
├── reasoning_engine.py    # Analyzes matchups and key player impacts (Reasoning Engine)
├── Main.py                # Entry point for simulations
├── constants.py           # Weights, formulas, and static team info
├── /NFL/ /NFC/ /AFC/      # Cleaned CSVs for each team
├── /Notebooks/            # For prototyping and experiments
├── README.md              # Project overview
└── .gitignore             # File exclusion for Git
```

---

## Features

* Supports both deterministic and probabilistic outcome predictions
* Unit matchups are evaluated using real player tendencies and context
* Distinguishes between statistically likely and strategically meaningful outcomes
* Pulls and cleans real player stats from Pro-Football-Reference
* Mapping system adapts to changing stat names across sources
* Framework is API-ready for future real-time integrations

---

## How to Run

```bash
python Main.py
```

This runs a full team-vs-team simulation using preloaded and scraped data.

Use outputs from the Prediction Engine for results, and feed those into the Reasoning Engine for deeper game breakdowns.

---

## Roadmap

*

---

## Contribute or Review

This is an open and growing system. Contributions are welcome — whether you’re testing, tuning, or proposing new features.

If you’re experienced in sports analytics, machine learning, or systems design, feel free to clone it, fork it, and provide feedback.

---

## About

**Caleb (ChillCaleb)**
Computer Science @ Morgan State
Focused on predictive modeling and applied data systems.
