from __future__ import annotations

import html
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

import frontend_services as svc


st.set_page_config(
    page_title="NFL POA",
    page_icon="NFL",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --poa-ink: #111827;
        --poa-muted: #64748b;
        --poa-line: #dbe3ee;
        --poa-field: #0f5132;
        --poa-gold: #d99a16;
        --poa-red: #c2410c;
        --poa-cyan: #0e7490;
        --poa-panel: #ffffff;
        --poa-soft: #f6f8fb;
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
        max-width: 1440px;
    }
    [data-testid="stSidebar"] {
        background: #0b1320;
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stToggle label {
        color: #f8fafc !important;
    }
    h1, h2, h3 {
        letter-spacing: 0 !important;
    }
    h1 {
        font-size: 2.05rem !important;
        margin-bottom: 0.25rem !important;
    }
    h2 {
        font-size: 1.35rem !important;
    }
    h3 {
        font-size: 1rem !important;
    }
    div[data-testid="stMetric"] {
        background: var(--poa-panel);
        border: 1px solid var(--poa-line);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        min-height: 112px;
    }
    div[data-testid="stMetric"] label {
        color: var(--poa-muted) !important;
        font-size: 0.78rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: var(--poa-ink);
        font-size: 1.45rem !important;
    }
    .poa-band {
        border-top: 1px solid var(--poa-line);
        padding-top: 1rem;
        margin-top: 1rem;
    }
    .poa-chip {
        display: inline-block;
        padding: 0.22rem 0.55rem;
        border-radius: 999px;
        background: #e8f3ed;
        color: #14532d;
        border: 1px solid #b7dec8;
        font-size: 0.78rem;
        font-weight: 650;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
    }
    .poa-chip-link {
        display: inline-block;
        padding: 0.22rem 0.55rem;
        border-radius: 999px;
        background: #e8f3ed;
        color: #14532d !important;
        border: 1px solid #b7dec8;
        font-size: 0.78rem;
        font-weight: 650;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
        text-decoration: none !important;
    }
    .poa-table-wrap {
        border: 1px solid #283241;
        border-radius: 8px;
        overflow: auto;
        max-height: 440px;
        margin-bottom: 1rem;
    }
    .poa-link-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
    }
    .poa-link-table th {
        background: #1f2430;
        color: #aeb8c7;
        font-weight: 500;
        text-align: left;
        padding: 0.7rem 0.75rem;
        border-bottom: 1px solid #313846;
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .poa-link-table td {
        padding: 0.68rem 0.75rem;
        border-bottom: 1px solid #252c38;
        color: #f8fafc;
    }
    .poa-link-table a {
        color: #93c5fd !important;
        font-weight: 700;
        text-decoration: none !important;
    }
    .poa-link-table a:hover {
        text-decoration: underline !important;
    }
    .poa-num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .poa-note {
        color: var(--poa-muted);
        font-size: 0.88rem;
    }
    .stButton > button,
    .stFormSubmitButton > button {
        border-radius: 8px;
        border: 1px solid #164e63;
        background: #155e75;
        color: white;
        font-weight: 700;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: #0f766e;
        border-color: #0f766e;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


TEAM_OPTIONS = svc.get_team_options()
POSITION_OPTIONS = ["All", "QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "DB"]
ROOM_OPTIONS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "DB"]


def percent(value: float) -> str:
    return svc.format_probability(value, precision=1)


def team_select(label: str, default: str, key: str) -> str:
    default_index = TEAM_OPTIONS.index(default) if default in TEAM_OPTIONS else 0
    return st.selectbox(label, TEAM_OPTIONS, index=default_index, format_func=svc.display_team, key=key)


def styled_player_table(df: pd.DataFrame, height: int = 360) -> None:
    if df.empty:
        st.info("No matching players found.")
        return

    display = df.copy()
    columns = ["player", "team_name", "side", "pos", "raw", "archetype"]
    display = display[[column for column in columns if column in display.columns]]
    display = display.rename(
        columns={
            "player": "Player",
            "team_name": "Team",
            "side": "Side",
            "pos": "Pos",
            "raw": "Rating",
            "archetype": "Archetype",
        }
    )
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        height=height,
        column_config={
            "Rating": st.column_config.NumberColumn(format="%.1f"),
        },
    )


def metric_row(metrics: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics):
        col.metric(label, value, delta=delta)


def render_ai_summary(summary: str | None, title: str = "AI Summary") -> None:
    if summary:
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.write(summary)


def render_profile_tables(tables: dict[str, pd.DataFrame], expanded_first: int = 2) -> None:
    if not tables:
        st.info("No raw stat tables found for this profile.")
        return

    for index, (table_name, table) in enumerate(tables.items()):
        with st.expander(table_name.replace("_", " ").title(), expanded=index < expanded_first):
            st.dataframe(table, hide_index=True, width="stretch")


def route_url(view: str, **params: str) -> str:
    values = {"view": view}
    values.update({key: value for key, value in params.items() if value})
    return "?" + urlencode(values)


def team_link(team: str, label: str | None = None) -> str:
    team = svc.normalize_team(team)
    label = label or svc.display_team(team)
    return (
        f'<a class="poa-chip-link" target="_self" href="{route_url("team", team=team)}">'
        f"{html.escape(label)}</a>"
    )


def player_link(player: str, team: str, label: str | None = None) -> str:
    label = label or player
    return (
        f'<a target="_self" href="{route_url("player", team=team, player=player)}">'
        f"{html.escape(label)}</a>"
    )


def render_roster_link_table(roster: pd.DataFrame) -> None:
    if roster.empty:
        st.info("No players match those filters.")
        return

    rows = []
    for row in roster.itertuples():
        rows.append(
            "<tr>"
            f"<td>{player_link(row.player, row.team)}</td>"
            f"<td>{html.escape(str(row.side))}</td>"
            f"<td>{html.escape(str(row.pos))}</td>"
            f"<td class='poa-num'>{float(row.raw):.1f}</td>"
            f"<td>{html.escape(str(row.archetype))}</td>"
            "</tr>"
        )

    table = (
        "<div class='poa-table-wrap'>"
        "<table class='poa-link-table'>"
        "<thead><tr>"
        "<th>Player</th><th>Side</th><th>Pos</th><th>Rating</th><th>Archetype</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    st.markdown(table, unsafe_allow_html=True)


def render_player_rating_table(ratings: pd.DataFrame) -> None:
    if ratings.empty:
        st.info("No model ratings found for this player.")
        return

    rows = []
    for row in ratings.itertuples():
        rows.append(
            "<tr>"
            f"<td>{team_link(row.team, row.team_name)}</td>"
            f"<td>{html.escape(str(row.side))}</td>"
            f"<td>{html.escape(str(row.pos))}</td>"
            f"<td class='poa-num'>{float(row.raw):.1f}</td>"
            f"<td class='poa-num'>{float(row.normalized):.1f}</td>"
            f"<td>{html.escape(str(row.archetype))}</td>"
            "</tr>"
        )

    table = (
        "<div class='poa-table-wrap'>"
        "<table class='poa-link-table'>"
        "<thead><tr>"
        "<th>Team</th><th>Side</th><th>Pos</th><th>Rating</th><th>Normalized</th><th>Archetype</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    st.markdown(table, unsafe_allow_html=True)


with st.sidebar:
    st.title("NFL POA")
    page = st.radio(
        "Workspace",
        [
            "Teams",
            "Matchup Lab",
            "Season Simulator",
            "Data Browser",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    matchup_ai = st.toggle("Matchup AI summaries", value=False)
    if not svc.ai_available():
        st.warning("GROQ_API_KEY is not set.")
    st.caption("Team and player profiles load cached AI summaries automatically when a key is available.")


def render_matchup_lab() -> None:
    st.title("Matchup Lab")

    with st.form("matchup_form"):
        col_a, col_b, col_submit = st.columns([1, 1, 0.55])
        with col_a:
            team_a = team_select("Team A", "ravens", "matchup_team_a")
        with col_b:
            team_b = team_select("Team B", "chiefs", "matchup_team_b")
        with col_submit:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Run matchup", width="stretch")

    if "matchup_pair" not in st.session_state:
        st.session_state.matchup_pair = ("ravens", "chiefs", False)
        st.session_state.ml_matchup = svc.simulate_ml_matchup("ravens", "chiefs", include_ai=False)
        st.session_state.rating_matchup = svc.simulate_rating_matchup("ravens", "chiefs", include_ai=False)

    requested_pair = (team_a, team_b, matchup_ai)
    if submitted or requested_pair != st.session_state.matchup_pair:
        if team_a == team_b:
            st.error("Choose two different teams.")
            return
        with st.spinner("Running matchup models..."):
            st.session_state.ml_matchup = svc.simulate_ml_matchup(team_a, team_b, include_ai=matchup_ai)
            st.session_state.rating_matchup = svc.simulate_rating_matchup(team_a, team_b, include_ai=matchup_ai)
            st.session_state.matchup_pair = requested_pair

    ml = st.session_state.ml_matchup
    rating = st.session_state.rating_matchup

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Personnel ML")
        metric_row(
            [
                ("Prediction", svc.display_team(ml["winner"]), None),
                ("Confidence", percent(ml["confidence"]), None),
                ("Run Edge", percent(ml["rush_edge"]), None),
            ]
        )
        metric_row(
            [
                ("Pass Edge", percent(ml["pass_edge"]), None),
                ("WR Separation", percent(ml["separation_edge"]), None),
                ("Insights", str(len(ml["insights"])), None),
            ]
        )
        if ml["insights"]:
            st.markdown("#### Conditional Scenarios")
            for insight in ml["insights"]:
                st.markdown(f"- {insight}")
        st.markdown("#### Feature Edges")
        feature_edges = ml["feature_edges"].copy()
        st.dataframe(
            feature_edges,
            hide_index=True,
            width="stretch",
            height=330,
            column_config={
                "Edge": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        render_ai_summary(ml.get("ai_summary"))

    with col_right:
        st.subheader("Ratings Matchup")
        team_a_label = svc.display_team(rating["team_a"])
        team_b_label = svc.display_team(rating["team_b"])
        metric_row(
            [
                ("Prediction", svc.display_team(rating["winner"]), None),
                (team_a_label, percent(rating["probability_a"]), None),
                (team_b_label, percent(rating["probability_b"]), None),
            ]
        )
        profile_a = rating["profile_a"]
        profile_b = rating["profile_b"]
        metric_row(
            [
                (f"{team_a_label} Overall", f"{profile_a['overall_sum']:.1f}", None),
                (f"{team_b_label} Overall", f"{profile_b['overall_sum']:.1f}", None),
                ("Spread", f"{profile_a['overall_sum'] - profile_b['overall_sum']:.1f}", None),
            ]
        )
        st.markdown("#### Unit Matchups")
        units = rating["units"].copy()
        st.dataframe(
            units[["Unit", "Advantage %"]],
            hide_index=True,
            width="stretch",
            height=330,
            column_config={
                "Advantage %": st.column_config.ProgressColumn(
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                )
            },
        )
        render_ai_summary(rating.get("ai_summary"))


def render_season_simulator() -> None:
    st.title("Season Simulator")

    with st.form("season_form"):
        col_model, col_runs, col_seed, col_button = st.columns([1, 1, 1, 0.55])
        with col_model:
            model_name = st.selectbox("Probability model", list(svc.MODEL_REGISTRY.keys()), index=0)
        with col_runs:
            runs = st.slider("Runs", min_value=1, max_value=250, value=25, step=1)
        with col_seed:
            seed = st.number_input("Seed", min_value=0, max_value=999999, value=42, step=1)
        with col_button:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Simulate", width="stretch")

    if "season_result" not in st.session_state or submitted:
        with st.spinner("Simulating season outcomes..."):
            st.session_state.season_result = svc.simulate_many_seasons(model_name, runs=runs, seed=int(seed))
            st.session_state.season_meta = {"model": model_name, "runs": runs, "seed": int(seed)}

    result = st.session_state.season_result
    meta = st.session_state.season_meta
    st.subheader(f"{meta['model']} model")

    top = result["summary"].head(8)
    metric_row(
        [
            ("Runs", str(meta["runs"]), None),
            ("Top Avg Wins", f"{top['avg_wins'].max():.2f}", None),
            ("Most Stable Rank", str(result["summary"].sort_values("avg_rank").iloc[0]["Team"]), None),
        ]
    )

    chart_df = result["summary"].head(16).set_index("Team")[["avg_wins"]]
    st.bar_chart(chart_df, height=320)

    tab_summary, tab_last, tab_games = st.tabs(["Average Standings", "Last Run", "Last Game Log"])
    with tab_summary:
        summary = result["summary"].rename(
            columns={
                "avg_wins": "Avg Wins",
                "avg_losses": "Avg Losses",
                "best_wins": "Best Wins",
                "worst_wins": "Worst Wins",
                "avg_rank": "Avg Rank",
                "first_place_rate": "First Place %",
            }
        )
        st.dataframe(summary, hide_index=True, width="stretch", height=520)
    with tab_last:
        st.dataframe(result["last_standings"], hide_index=True, width="stretch", height=520)
    with tab_games:
        st.dataframe(result["last_games"], hide_index=True, width="stretch", height=520)


def render_team_browser() -> None:
    st.title("Teams")

    try:
        team = svc.normalize_team(st.query_params.get("team", "ravens"))
    except ValueError:
        team = "ravens"

    selected_team = team_select("Team", team, f"reference_team_{team}")
    if selected_team != team:
        st.query_params["view"] = "team"
        st.query_params["team"] = selected_team
        st.rerun()

    with st.spinner("Loading team profile..."):
        breakdown = svc.get_team_breakdown(team, include_ai=True)

    profile = breakdown["profile"]
    offense = profile["offense"]
    defense = profile["defense"]

    st.markdown(f"<span class='poa-chip'>League</span><span class='poa-chip'>{profile['display']}</span>", unsafe_allow_html=True)
    render_ai_summary(breakdown.get("ai_summary"), title=f"{profile['display']} Summary")

    metric_row(
        [
            ("Overall", f"{profile['overall_sum']:.1f}", None),
            ("Offense", f"{offense.get('total', 0):.1f}", None),
            ("Defense", f"{defense.get('total', 0):.1f}", None),
            ("Prominent Room", breakdown["prominent_room"], None),
        ]
    )

    st.markdown("#### Team Ratings")
    ratings_df = pd.DataFrame(
        [
            {"Unit": "Offense", "Rushing": offense.get("rushing", 0), "Passing": offense.get("passing", 0), "Scoring": offense.get("scoring", 0), "Total": offense.get("total", 0)},
            {"Unit": "Defense", "Rushing": defense.get("rushing", 0), "Passing": defense.get("passing", 0), "Scoring": defense.get("scoring", 0), "Total": defense.get("total", 0)},
        ]
    )
    st.dataframe(
        ratings_df,
        hide_index=True,
        width="stretch",
        column_config={column: st.column_config.NumberColumn(format="%.1f") for column in ["Rushing", "Passing", "Scoring", "Total"]},
    )

    st.markdown("#### Roster")
    col_query, col_pos, col_side, col_rating = st.columns([1.35, 0.7, 0.75, 0.75])
    with col_query:
        roster_query = st.text_input("Find player on team", value="")
    with col_pos:
        roster_position = st.selectbox("Position", POSITION_OPTIONS, key="team_roster_position")
    with col_side:
        roster_side = st.selectbox("Side", ["All", "Offense", "Defense"], key="team_roster_side")
    with col_rating:
        roster_min_rating = st.number_input("Min rating", min_value=0.0, max_value=150.0, value=0.0, step=5.0, key="team_roster_min_rating")

    roster = svc.get_team_roster(
        team,
        position=roster_position,
        side=roster_side,
        query=roster_query,
        min_rating=roster_min_rating,
    )
    render_roster_link_table(roster)

    st.markdown("#### Team Stat Tables")
    render_profile_tables(breakdown["stat_tables"], expanded_first=1)


def render_player_record() -> None:
    player_name = st.query_params.get("player", "")
    team = st.query_params.get("team", None)
    if not player_name:
        render_team_browser()
        return

    try:
        team = svc.normalize_team(team) if team else None
    except ValueError:
        team = None

    with st.spinner("Loading player profile..."):
        profile = svc.get_player_profile(player_name, team=team, include_ai=True)

    ratings = profile["ratings"].copy()
    if ratings.empty:
        st.title(player_name)
        st.info("No model ratings found for this player.")
        return

    primary = ratings.iloc[0]
    primary_team = str(primary.get("team", team or ""))

    st.title(str(primary.get("player", player_name)))
    team_rows = ratings[["team", "team_name"]].drop_duplicates()
    team_chips = "".join(team_link(row.team, row.team_name) for row in team_rows.itertuples())
    st.markdown(team_chips, unsafe_allow_html=True)

    render_ai_summary(profile.get("ai_blurb"), title=f"{primary.get('player', player_name)} Summary")

    metric_row(
        [
            ("Rating", f"{ratings['raw'].max():.1f}", None),
            ("Normalized", f"{ratings['normalized'].max():.1f}", None),
            ("Position", str(primary.get("pos", "")), None),
            ("Side", str(primary.get("side", "")), None),
        ]
    )
    st.markdown(f"**Archetype:** {primary.get('archetype', '')}")

    st.markdown("#### Player Ratings")
    render_player_rating_table(ratings)

    st.markdown("#### Player Stats")
    render_profile_tables(profile["stat_rows"], expanded_first=3)

    if primary_team:
        st.markdown("#### Team Context")
        roster = svc.get_team_roster(primary_team)
        render_roster_link_table(roster)


def render_player_finder() -> None:
    st.title("Player Profiles")

    col_query, col_team, col_pos, col_side, col_rating = st.columns([1.4, 1, 0.75, 0.75, 0.75])
    with col_query:
        query = st.text_input("Search", value="")
    with col_team:
        team_filter = st.selectbox("Team", ["All"] + TEAM_OPTIONS, format_func=lambda x: x if x == "All" else svc.display_team(x))
    with col_pos:
        position = st.selectbox("Position", POSITION_OPTIONS)
    with col_side:
        side = st.selectbox("Side", ["All", "Offense", "Defense"])
    with col_rating:
        min_rating = st.number_input("Min rating", min_value=0.0, max_value=150.0, value=0.0, step=5.0)

    players = svc.search_players(query, team_filter, position, side, min_rating)
    if players.empty:
        metric_row(
            [
                ("Matches", "0", None),
                ("Top Rating", "0.0", None),
                ("Teams", "0", None),
            ]
        )
        st.info("No matching players found.")
        return

    labels = [
        f"{row.player} | {row.team_name} | {row.pos} | {row.side}"
        for row in players.itertuples()
    ]
    selection = st.selectbox("Player profile", labels)
    selected_name = selection.split(" | ", 1)[0]

    with st.spinner("Loading player profile and AI summary..."):
        profile = svc.get_player_profile(selected_name, include_ai=True)

    ratings = profile["ratings"].copy()
    if not ratings.empty:
        primary = ratings.iloc[0]
        st.subheader(selected_name)
        render_ai_summary(profile.get("ai_blurb"), title="Profile Summary")
        metric_row(
            [
                ("Best Rating", f"{ratings['raw'].max():.1f}", None),
                ("Team", str(primary.get("team_name", "")), None),
                ("Position", str(primary.get("pos", "")), None),
                ("Archetype", str(primary.get("archetype", "")), None),
            ]
        )
        st.markdown("#### Model Ratings")
        styled_player_table(ratings, height=220)

    st.markdown("#### Player Stats")
    render_profile_tables(profile["stat_rows"], expanded_first=3)

    st.markdown("#### Search Results")
    metric_row(
        [
            ("Matches", str(len(players)), None),
            ("Top Rating", f"{players['raw'].max():.1f}", None),
            ("Teams", str(players["team"].nunique()), None),
        ]
    )
    styled_player_table(players, height=300)


def render_team_explorer() -> None:
    st.title("Team Profiles")

    col_team, col_room = st.columns([1, 1])
    with col_team:
        team = team_select("Team", "ravens", "team_explorer_team")
    with col_room:
        st.write("")
        st.write("")
        st.markdown(f"<span class='poa-chip'>{svc.display_team(team)}</span>", unsafe_allow_html=True)

    with st.spinner("Loading team profile and AI summary..."):
        breakdown = svc.get_team_breakdown(team, include_ai=True)

    profile = breakdown["profile"]
    offense = profile["offense"]
    defense = profile["defense"]
    render_ai_summary(breakdown.get("ai_summary"), title="Profile Summary")

    metric_row(
        [
            ("Overall", f"{profile['overall_sum']:.1f}", None),
            ("Off Total", f"{offense.get('total', 0):.1f}", None),
            ("Def Total", f"{defense.get('total', 0):.1f}", None),
            ("Prominent Room", breakdown["prominent_room"], None),
        ]
    )

    st.markdown("#### Model Ratings")
    ratings_df = pd.DataFrame(
        [
            {"Unit": "Offense", "Rushing": offense.get("rushing", 0), "Passing": offense.get("passing", 0), "Scoring": offense.get("scoring", 0), "Total": offense.get("total", 0)},
            {"Unit": "Defense", "Rushing": defense.get("rushing", 0), "Passing": defense.get("passing", 0), "Scoring": defense.get("scoring", 0), "Total": defense.get("total", 0)},
        ]
    )
    st.dataframe(
        ratings_df,
        hide_index=True,
        width="stretch",
        column_config={column: st.column_config.NumberColumn(format="%.1f") for column in ["Rushing", "Passing", "Scoring", "Total"]},
    )

    st.markdown("#### Team Stats")
    render_profile_tables(breakdown["stat_tables"], expanded_first=4)

    col_off, col_def = st.columns(2)
    with col_off:
        st.subheader("Top Offense")
        styled_player_table(breakdown["top_offense"], height=310)
    with col_def:
        st.subheader("Top Defense")
        styled_player_table(breakdown["top_defense"], height=310)

    st.subheader("Position Units")
    units = breakdown["position_units"].rename(
        columns={"pos": "Position", "side": "Side", "players": "Players", "avg_rating": "Avg Rating", "top_rating": "Top Rating"}
    )
    st.dataframe(
        units,
        hide_index=True,
        width="stretch",
        height=360,
        column_config={
            "Avg Rating": st.column_config.NumberColumn(format="%.1f"),
            "Top Rating": st.column_config.NumberColumn(format="%.1f"),
        },
    )


def render_position_rooms() -> None:
    st.title("Position Rooms")

    col_team, col_position = st.columns([1, 0.7])
    with col_team:
        team = team_select("Team", "ravens", "room_team")
    with col_position:
        position = st.selectbox("Room", ROOM_OPTIONS, index=ROOM_OPTIONS.index("WR"))

    with st.spinner("Loading position room..."):
        result = svc.get_position_room(team, position, include_ai=True)

    summary = result["summary"]
    metric_row(
        [
            ("Players", str(summary["players"]), None),
            ("Average Rating", f"{summary['avg_rating']:.1f}", None),
            ("Top Rating", f"{summary['top_rating']:.1f}", None),
        ]
    )
    styled_player_table(result["room"], height=430)

    if not result["room"].empty:
        chart = result["room"].head(12).set_index("player")[["raw"]]
        st.bar_chart(chart, height=320)

    render_ai_summary(result.get("ai_summary"))


def render_data_browser() -> None:
    st.title("Data Browser")

    ratings = svc.load_team_ratings()
    players = svc.load_player_ratings()

    tab_team, tab_players, tab_tables = st.tabs(["Team Ratings", "Player Ratings", "Player Stat Tables"])
    with tab_team:
        offense = ratings["offense"].reset_index()
        offense["Team"] = offense["team"].map(svc.display_team)
        defense = ratings["defense"].reset_index()
        defense["Team"] = defense["team"].map(svc.display_team)
        col_off, col_def = st.columns(2)
        with col_off:
            st.subheader("Offense")
            st.dataframe(offense[["Team", "rushing", "passing", "scoring", "total"]], hide_index=True, width="stretch", height=560)
        with col_def:
            st.subheader("Defense")
            st.dataframe(defense[["Team", "rushing", "passing", "scoring", "total"]], hide_index=True, width="stretch", height=560)
    with tab_players:
        st.dataframe(
            players[["player", "team_name", "side", "pos", "raw", "normalized", "archetype"]],
            hide_index=True,
            width="stretch",
            height=620,
            column_config={
                "raw": st.column_config.NumberColumn("Rating", format="%.1f"),
                "normalized": st.column_config.NumberColumn("Normalized", format="%.3f"),
            },
        )
    with tab_tables:
        tables = svc.load_player_stat_tables()
        selected = st.selectbox("Table", list(tables.keys()), format_func=lambda name: name.replace("_", " ").title())
        st.dataframe(tables[selected], hide_index=True, width="stretch", height=620)


if page == "Teams":
    if st.query_params.get("view") == "player":
        render_player_record()
    else:
        render_team_browser()
elif page == "Matchup Lab":
    render_matchup_lab()
elif page == "Season Simulator":
    render_season_simulator()
else:
    render_data_browser()
