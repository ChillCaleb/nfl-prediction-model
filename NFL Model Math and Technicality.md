---

tags:

- CS

- machine-learning

- sports-analytics

- random-forest

- calibration

- feature-engineering

- python

---

# NFL Prediction Model Math and Technicality

## 1. What It Is

This model predicts an NFL matchup by converting two teams into a numeric feature vector, then estimating the probability that `team_a` beats `team_b`.

The main idea:

```text
Turn football personnel + ratings into matchup features.
Train a classifier on historical winner/loser pairs.
Use calibrated probability to estimate win chance.
Use an LLM only to explain the result.
```

The model is not just asking:

```text
Who has more elite players?
```

It is now asking:

```text
How do Team A's ratings, position groups, archetypes, and matchup edges compare to Team B's?
```

---

## 2. Packages Used

|Package|Purpose|
|---|---|
|`pandas`|DataFrames, feature tables, aggregation, numeric cleanup|
|`sqlite3`|Loads team and player ratings from local SQLite databases|
|`re`|Turns archetype names into safe feature names|
|`functools.lru_cache`|Caches rating-table loads so feature generation is faster|
|`joblib`|Saves and loads the trained model|
|`math`|Sigmoid-style display probabilities for unit edges|
|`requests`|Calls Groq API for analyst summaries|
|`python-dotenv`|Loads Groq API keys and model settings from `.env`|
|`sklearn.ensemble.RandomForestClassifier`|Core matchup classifier|
|`sklearn.calibration.CalibratedClassifierCV`|Turns raw forest outputs into calibrated probabilities|
|`sklearn.model_selection.train_test_split`|Splits training and test data|
|`sklearn.metrics.classification_report`|Precision, recall, F1, accuracy report|

---

## 3. The Prediction Target

Each training row is a matchup:

```text
x = features(team_a, team_b)
y = 1 if team_a wins
y = 0 if team_a loses
```

For every completed game, the training set adds two rows:

```text
features(winner, loser) -> 1
features(loser, winner) -> 0
```

This makes the labels balanced:

```text
P(y = 1) = P(y = 0) = 0.5
```

That balance is useful because the model does not learn a fake bias toward `team_a`.

---

## 4. Feature Vector

The core object is:

```text
φ(A, B)
```

where:

```text
A = team_a
B = team_b
φ(A, B) = all numeric matchup features for A against B
```

The current model builds about:

```text
582 model features
```

These features come from:

- Team ratings
- Offensive and defensive unit ratings
- Player raw ratings
- Positional group aggregates
- Archetype flags
- Archetype counts
- Archetype top-player strength
- Matchup deltas

---

## 5. Team Rating Features

Each team has offensive and defensive ratings:

```text
O_t = [rush_off_t, pass_off_t, score_off_t, total_off_t]
D_t = [rush_def_t, pass_def_t, score_def_t, total_def_t]
```

The model creates combined team values:

```text
team_total_t = total_off_t + total_def_t
team_pass_net_t = pass_off_t + pass_def_t
team_rush_net_t = rush_off_t + rush_def_t
team_score_net_t = score_off_t + score_def_t
```

For a matchup, it also creates differences:

```text
diff_team_total = team_total_A - team_total_B
diff_off_total = total_off_A - total_off_B
diff_def_total = total_def_A - total_def_B
```

These differences give the model relative strength instead of just raw standalone values.

---

## 6. Player Aggregation

For each position group, the model aggregates players using raw rating values.

For a position group `G`:

```text
ratings_G = sorted player raw ratings in descending order
```

The model computes:

```text
count_G = number of players in group
top_raw_G = max(ratings_G)
top3_raw_mean_G = mean(top 3 ratings)
top5_raw_sum_G = sum(top 5 ratings)
starter_raw_count_G = count(rating >= 50)
impact_raw_count_G = count(rating >= 80)
```

This gives the model both star power and depth.

Example:

```text
Ravens RB room has Derrick Henry at the top.
Ravens QB room has Lamar Jackson at the top.
Bills front has Gregory Rousseau near the top.
```

The model does not need to know those names directly to predict, but those player ratings affect the numeric features.

---

## 7. Position Groups

The offense is grouped as:

|Group|Positions|
|---|---|
|QB|`QB`|
|RB|`RB`|
|WR|`WR`|
|TE|`TE`|
|OL|`OL`|

The defense is grouped as:

|Group|Positions|
|---|---|
|CB|`C`, `CB`, `DB`, `LCB`, `RCB`|
|DL|`D`, `DL`, `DE`, `DT`, `EDGE`, `NT`, `LE`, `RE`|
|LB|`L`, `LB`, `MLB`, `ILB`, `OLB`|
|S|`S`, `SS`, `FS`|

This lets the model compare position rooms instead of only full teams.

---

## 8. Archetype Features

Each player has an archetype such as:

```text
All-Around Elite QB
Power Runner
YAC Specialist
Pass Rush Specialist
Coverage Safety
Blitzer Safety
Balanced C
```

The model converts archetypes into numeric features.

For each archetype `a` and team `t`:

```text
has_arch_a(t) = 1 if team has at least one player with archetype a
count_arch_a(t) = number of players with archetype a
top_raw_arch_a(t) = best raw rating among players with archetype a
```

So an archetype is not only a yes/no flag.

It also has:

```text
presence
volume
strength
```

This matters because a team having one weak archetype player is different from having a star with that archetype.

---

## 9. Matchup Edge Features

The most football-specific features are direct matchup deltas.

Passing offense against pass defense:

```text
pass_edge_A = pass_off_A - pass_def_B
pass_edge_B = pass_off_B - pass_def_A
```

Rushing offense against run defense:

```text
rush_edge_A = rush_off_A - rush_def_B
rush_edge_B = rush_off_B - rush_def_A
```

Quarterback against secondary:

```text
qb_vs_secondary_A = top_qb_raw_A - top_cb_raw_B
qb_vs_secondary_B = top_qb_raw_B - top_cb_raw_A
```

Receivers against corners:

```text
wr_vs_cb_A = mean_top3_wr_A - mean_top3_cb_B
wr_vs_cb_B = mean_top3_wr_B - mean_top3_cb_A
```

Run game against front:

```text
run_game_A =
    mean_top3_rb_A
    + top_ol_A
    - mean_top3_dl_B
    - mean_top3_lb_B
```

Pass protection against rush:

```text
pass_pro_A =
    top_ol_A
    - mean_top3_dl_B
    - mean_top3_lb_B
```

These features are what add "texture" to the percentage.

They let the model say:

```text
This is not just Ravens vs Bills.
This is Lamar/Henry/OL against Buffalo's front,
and Allen/Cook/Shakir against Baltimore's secondary/front.
```

---

## 10. The Random Forest

The model uses:

```python
RandomForestClassifier(
    n_estimators=200,
    max_depth=6,
    min_samples_leaf=8,
    class_weight="balanced",
    random_state=42,
)
```

A random forest is an ensemble of decision trees.

Each tree learns rules like:

```text
if diff_team_total > threshold:
    go right
else:
    go left
```

At each split, the tree tries to reduce impurity.

The default impurity measure is Gini impurity:

```text
Gini(S) = 1 - Σ p_k^2
```

For binary classification:

```text
Gini(S) = 1 - p_win^2 - p_loss^2
```

The tree chooses splits that maximize impurity reduction:

```text
gain = Gini(parent)
       - weighted_avg(Gini(left), Gini(right))
```

---

## 11. Forest Probability

Each tree outputs a class probability from the leaf node it lands in.

For tree `j`:

```text
p_j = P(y = 1 | leaf_j)
```

The forest averages all trees:

```text
p_RF = (1 / T) Σ p_j
```

where:

```text
T = 200 trees
```

If:

```text
p_RF > 0.5
```

then the model predicts:

```text
team_a wins
```

Otherwise:

```text
team_b wins
```

---

## 12. Probability Calibration

Raw random forest probabilities can be overconfident.

So the model wraps the forest in:

```python
CalibratedClassifierCV(
    base_model,
    method="sigmoid",
    cv=5,
)
```

This uses cross-validation and sigmoid calibration.

The idea is similar to Platt scaling:

```text
p_calibrated = 1 / (1 + e^(-z))
```

where `z` is learned from validation predictions.

The goal is:

```text
When the model says 70%, it should be right about 70% of the time.
```

Calibration is why the model no longer says `100%` unless the evidence truly supports extreme confidence.

---

## 13. Final Prediction

At inference time:

```text
x = φ(team_a, team_b)
p = calibrated_model.predict_proba(x)
```

The predicted class is:

```text
ŷ = argmax(p)
```

If:

```text
ŷ = 1
```

then:

```text
team_a is predicted winner
```

If:

```text
ŷ = 0
```

then:

```text
team_b is predicted winner
```

Displayed confidence is:

```text
confidence = max(P(team_a wins), P(team_b wins))
```

Example:

```text
P(team_a wins) = 0.39
P(team_b wins) = 0.61

winner = team_b
confidence = 61%
```

---

## 14. Unit Matchup Display

The terminal also shows unit matchup estimates.

These are not the random forest prediction.

They are display-layer probabilities created from rating edges.

The formula is:

```text
unit_probability = 1 / (1 + e^(-edge / scale))
```

This is a sigmoid.

It turns a raw edge into a readable percentage.

Example:

```text
edge = a_run_game_vs_b_front
scale = 60

rush_edge = sigmoid(edge / scale)
```

This makes the output easier to read:

```text
BILLS Rush Edge -> 68% vs RAVENS Front
```

But the actual win probability still comes from the calibrated random forest.

---

## 15. Groq Summary Layer

Groq does not make the prediction.

Groq explains the prediction.

The local model sends Groq:

- Predicted winner
- Confidence
- Unit matchup estimates
- Conditional insights
- Top offensive players
- Top defensive players
- Position groups
- Player archetypes
- Player ratings
- Matchup rating edges

The LLM is instructed:

```text
Use only player names from the scouting packet.
Do not invent players.
Explain both teams' paths to winning.
Discuss trenches, coverage, and swing players.
```

So the architecture is:

```text
Random forest = prediction engine
Groq = explanation engine
```

---

## 16. Why The Model Used To Flatten Toward 50%

Before the rating features were added, the model mostly had binary flags:

```text
has_elite_receiver
has_lockdown_cb
has_star_rusher
has_route_runner
team_elite_archetype_count
```

Most of those features were constant.

For example:

```text
has_lockdown_cb = 0 for every team
has_star_rusher = 0 for every team
has_route_runner = 0 for every team
```

That meant many teams collapsed into the same vector.

Example:

```text
Bills vs Ravens
Ravens vs Falcons
Falcons vs Ravens
```

could look almost identical to the model.

When identical feature rows have a 50/50 historical win rate, the calibrated model should output about:

```text
50%
```

The fix was not to remove calibration.

The fix was to give the model more meaningful features.

---

## 17. Why More Flags Can Add Noise

Binary flags are not automatically safe.

A sparse flag can create noise if:

- It appears for only a few teams
- It is caused by inconsistent labeling
- It captures a player name indirectly
- It does not repeat enough for the model to learn reliably

Example:

```text
has_obscure_archetype = 1 for one team only
```

The model might treat that as important even if it is just a data artifact.

The safer design is:

```text
archetype presence
+ archetype count
+ archetype top rating
+ min_samples_leaf regularization
+ calibration
```

That is what the current model does.

---

## 18. Current Validation Snapshot

After adding rating and matchup features:

```text
Training rows: 570
Model features: 582
Unique feature rows: 456
Held-out accuracy: about 0.746
Max all-pair confidence: about 86.6%
Near-50 confidence pairs: much lower than before
```

This means the model has more signal than the old flag-only version, while still avoiding fake 100% certainty.

---

## 19. Important Caveats

The model is better, but not finished.

Important technical caveats:

1. The reverse-row strategy balances labels, but creates paired examples.

2. A random train/test split can leak matchup structure because reversed or similar rows may appear across splits.

3. A stronger validation strategy would group by actual game or split by time.

4. The model still depends heavily on rating quality.

5. Player names are not used directly by the model, only by the Groq explanation layer.

6. Feature importances should be reviewed regularly to remove weak or noisy features.

---

## 20. Mental Model

Think of the pipeline like this:

```text
SQLite ratings
    ↓
team/player/position/archetype features
    ↓
matchup deltas φ(A, B)
    ↓
calibrated random forest
    ↓
P(team_a wins)
    ↓
winner + confidence
    ↓
Groq analyst summary
```

The model is not simulating a game play-by-play.

It is learning:

```text
Given this matchup profile,
how often does team_a look like the winner?
```

That is the core math behind the system.

