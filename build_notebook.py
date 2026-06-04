"""Generates WorldCup2026_MonteCarlo.ipynb from the cell sources defined below.

Run:  python3 build_notebook.py
This avoids hand-editing fragile notebook JSON. The notebook itself has no
dependency on this script.
"""
import json

cells = []


def _next_id():
    return f"cell-{len(cells):02d}"


def md(text):
    cells.append({
        "cell_type": "markdown",
        "id": _next_id(),
        "metadata": {},
        "source": text.strip("\n").splitlines(keepends=True),
    })


def code(text):
    cells.append({
        "cell_type": "code",
        "id": _next_id(),
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": text.strip("\n").splitlines(keepends=True),
    })


# ===========================================================================
# Title
# ===========================================================================
md(r"""
# 2026 FIFA World Cup — Monte Carlo Simulation

This notebook simulates the **entire 2026 FIFA World Cup** thousands of times to
estimate each team's chance of reaching every stage of the tournament — from
surviving the group stage all the way to lifting the trophy.

**The idea in one sentence:** we don't know what *will* happen, so instead we
let the tournament play out at random — using each team's strength to weight the
dice — over and over again, and count how often each outcome occurs. The fraction
of simulations in which a team wins the cup *is* its estimated probability of
winning. This technique is called a **Monte Carlo simulation**.

### What you get at the end
- A **bracket-style heatmap** showing every team's probability of reaching each
  round (green = likely, red = unlikely).
- A **ranked summary table** of all 48 teams by title probability, exported to CSV.
- A saved **PNG** of the bracket figure.

### How the tournament is structured (2026 format)
- **48 teams** split into **12 groups of 4**.
- Group stage: round-robin within each group (everyone plays everyone once).
- The **top 2 of each group** (24 teams) **plus the 8 best 3rd-placed teams**
  advance to a **Round of 32**.
- From there it is straight single-elimination knockout:
  **Round of 32 → Round of 16 → Quarterfinals → Semifinals → Final**.

### How to run it
Run the cells top to bottom. The only thing you may want to change is `N_RUNS`
in the **Setup** section. The code runs the same in Jupyter, Google Colab, and
VS Code Notebooks, with no network or API calls.

> **One requirement:** the team ratings are loaded from `data/teams.csv`, so keep
> the `data/` folder next to this notebook. (Editing that one file is how you
> change the teams — see Section 2. Colab users: see the note there on uploading
> the file.)
""")

# ===========================================================================
# Setup & Imports
# ===========================================================================
md(r"""
## 1. Setup & Imports

We rely on three external libraries plus a few Python standard-library helpers.
The external libraries are pre-installed in Google Colab and most data-science
environments. If any are missing (e.g. a bare Python install), uncomment the
`pip install` line in the cell below.

| Library | Role in this notebook |
|---|---|
| **numpy** | Random number generation — specifically Poisson sampling for scorelines, and the master random seed for reproducibility. |
| **pandas** | Reads `data/teams.csv` and `data/annex_c.csv`, builds the final summary table, and exports it to CSV. |
| **matplotlib** | Draws the bracket heatmap and saves it as a PNG. |
| **random** | Python's built-in module, used for the simple coin-flip-style draws (match outcome thresholds and penalty shootouts). |
| **math** | Python's built-in module, used for the gap-dependent draw share. |
| **os** | Python's built-in module, used only to locate the `data/teams.csv` file. |
| **itertools** | Python's built-in module, used to identify the correct Annexe C option. |

### The one knob you control: `N_RUNS`

`N_RUNS` is how many times we replay the *whole* tournament. More runs = smoother,
more trustworthy probabilities, but more waiting.

> **Tradeoff — read this before changing it:**
> - **1,000 runs** → fast (seconds), but the probabilities are *noisy*: run it
>   twice and a team's win chance might wobble by a percentage point or two.
> - **10,000 runs (default)** → a good balance; results are stable to roughly a
>   few tenths of a percent.
> - **100,000+ runs** → very stable, publication-grade numbers, but noticeably
>   slower (can take several minutes in pure Python).
>
> **Recommended range: 10,000–50,000** for most uses. Start at the default,
> lower it to 1,000 while you experiment, then raise it for a final clean run.
""")

code(r"""
# If a library is missing (e.g. a minimal Python install), uncomment this line:
# !pip install numpy pandas matplotlib

import os
import math
import random
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

# -------------------------------------------------------------------------
# THE ONE CONFIGURABLE KNOB
# Number of full-tournament simulations. See the note above for the tradeoff.
# Try 1_000 for quick experiments; 10_000-50_000 for trustworthy results.
# -------------------------------------------------------------------------
N_RUNS = 10_000

print(f"Configured to run the tournament {N_RUNS:,} times.")
""")

# ===========================================================================
# Team Data
# ===========================================================================
md(r"""
## 2. Team Data — official field, draw, and ratings

The simulator now uses the confirmed **2026 FIFA World Cup field and group draw**.
The match model still needs a strength number for each team, so `data/teams.csv`
stores an illustrative **Elo rating** alongside each team's official group slot.

### What is an Elo rating?
Elo is a rating system originally built for chess and now widely used for
national football teams (see *eloratings.net*). Every team has a single number —
stronger teams have higher numbers. The scale is calibrated so that the
*difference* between two teams' ratings maps directly onto a win probability.
The neat property: a team rated **400 points higher** than its opponent is about
**10×** more likely to win.

We use the standard Elo win-probability formula:

$$P(\text{A beats B}) = \frac{1}{1 + 10^{(\text{Elo}_B - \text{Elo}_A) / 400}}$$

**A quick example.** Argentina (2113) vs the USA (1733) is a 380-point gap.
Plugging that in gives Argentina roughly a **90%** chance to win (before we make
room for draws — see the next section). Close the gap and it heads toward a coin
flip; widen it and it becomes a mismatch.

### Why Elo, not the FIFA rankings?
Because they are built for different jobs. The FIFA rankings exist to **rank and
seed** teams — to decide who lands in which pot for the draw. They give you an
order and a points total, but no agreed way to turn "Team A is 60 FIFA points
ahead" into "Team A has a 64% chance to win." Elo was designed from the start to
answer exactly that question — which is what a simulation needs on *every* match.
Elo also reacts to every result (who you beat, by how much, how surprising it
was), and its method is public and reproducible (*eloratings.net*).

**A caveat.** The field and draw are real, but the Elo ratings are still
**approximate, illustrative values**. Swap in better ratings for better answers.
The `fifa_rank` column is only used as the last group-stage tiebreaker, matching
FIFA's Article 13 procedure after football results and team conduct cannot split
teams.

### Where the data lives
The tournament data is **not hardcoded in this notebook**. It is loaded from the
`data/` folder so the data is cleanly separated from the logic:

```
your-folder/
├── WorldCup2026_MonteCarlo.ipynb   <- this notebook
└── data/
    ├── teams.csv                   <- team, elo, fifa_rank, group, position
    └── annex_c.csv                 <- FIFA's 495 third-place bracket routings
```

To experiment, edit the `elo` numbers in `data/teams.csv`. Keep exactly 48 teams
and one official position from `A1` through `L4` unless you also intend to change
the tournament format code.

> **Running in Google Colab or elsewhere?** Because the data is a separate file,
> it must sit beside the notebook. Colab's VM won't have your local `data/`
> folder, so first either **upload the full `data/` folder** via the Files panel,
> **mount Google Drive**, or point the loaders at wherever you put the files.
> If a file can't be found, the cell below raises a clear error.

`load_team_data()` reads the team CSV and returns Elo ratings, FIFA-ranking
tiebreakers, and the official groups. `load_annex_c()` reads FIFA's third-place
bracket routing table.
""")

code(r"""
# Folder holding the external data files, relative to this notebook.
DATA_DIR = "data"
GROUP_ORDER = list("ABCDEFGHIJKL")
GROUP_MATCH_PAIRINGS = [(0, 1), (2, 3), (0, 2), (3, 1), (3, 0), (1, 2)]
ANNEX_COLUMNS = ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"]


def load_team_data(path=None):
    '''Load teams, ratings, FIFA-rank tiebreakers, and official group positions.

    The CSV must contain 48 unique teams with one official slot from A1 through L4.
    Edit `elo` to change the strength assumptions; keep group/position unless you
    are intentionally changing the official draw.
    '''
    path = path or os.path.join(DATA_DIR, "teams.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find '{path}'.\n"
            f"Keep the 'data/' folder next to this notebook. In Google Colab, "
            f"upload the full data folder, mount Google Drive, or call "
            f"load_team_data(path='/your/path/teams.csv')."
        )
    df = pd.read_csv(path)
    required = ["team", "elo", "fifa_rank", "group", "position"]
    if not set(required).issubset(df.columns):
        raise ValueError(
            f"'{path}' must contain columns {required}; "
            f"found {list(df.columns)}."
        )

    df = df[required].copy()
    df["team"] = df["team"].astype(str).str.strip()
    df["group"] = df["group"].astype(str).str.strip().str.upper()
    df["position"] = df["position"].astype(str).str.strip().str.upper()
    df["elo"] = df["elo"].astype(int)
    df["fifa_rank"] = df["fifa_rank"].astype(int)

    if len(df) != 48 or not df["team"].is_unique:
        raise ValueError(f"'{path}' must contain exactly 48 unique teams.")

    expected_positions = {f"{group}{slot}" for group in GROUP_ORDER for slot in range(1, 5)}
    actual_positions = set(df["position"])
    if actual_positions != expected_positions:
        missing = sorted(expected_positions - actual_positions)
        extra = sorted(actual_positions - expected_positions)
        raise ValueError(f"Official positions must be A1-L4. Missing={missing}; extra={extra}.")

    if any(row.position[0] != row.group for row in df.itertuples()):
        raise ValueError("Each row's `position` must start with its `group` letter.")

    df["_slot"] = df["position"].str[1:].astype(int)
    df = df.sort_values(["group", "_slot"]).drop(columns="_slot")
    groups = {
        group: df.loc[df["group"] == group, "team"].tolist()
        for group in GROUP_ORDER
    }
    if any(len(teams) != 4 for teams in groups.values()):
        raise ValueError("Each group A-L must contain exactly four teams.")

    return {
        "df": df.reset_index(drop=True),
        "elos": dict(zip(df["team"], df["elo"])),
        "fifa_ranks": dict(zip(df["team"], df["fifa_rank"])),
        "groups": groups,
        "teams": df["team"].tolist(),
    }


def load_annex_c(path=None):
    '''Load FIFA Regulations Annexe C third-place routing table.

    Rows are keyed by option number 1..495. Values map winner slots 1A, 1B,
    1D, 1E, 1G, 1I, 1K, and 1L to the third-place group they face.
    '''
    path = path or os.path.join(DATA_DIR, "annex_c.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find '{path}'. Keep annex_c.csv in the data folder."
        )
    df = pd.read_csv(path)
    expected = {"option", *[f"third_{col}" for col in ANNEX_COLUMNS]}
    if not expected.issubset(df.columns):
        raise ValueError(f"'{path}' must contain columns {sorted(expected)}.")

    annex = {}
    for row in df.itertuples(index=False):
        option = int(getattr(row, "option"))
        annex[option] = tuple(getattr(row, f"third_{col}") for col in ANNEX_COLUMNS)
    if set(annex) != set(range(1, 496)):
        raise ValueError("Annexe C must contain exactly options 1 through 495.")
    return annex


# Quick look at the official field and draw
_team_data = load_team_data()
_annex_c = load_annex_c()
print(f"Loaded {len(_team_data['teams'])} teams and {len(_annex_c)} Annexe C bracket options.\n")
for label, grp in _team_data["groups"].items():
    print(f"Group {label}: " + ", ".join(f"{t} ({_team_data['elos'][t]})" for t in grp))
""")

# ===========================================================================
# Match Simulation
# ===========================================================================
md(r"""
## 3. Match Simulation — the randomness model

This is the heart of the simulation: given two teams and their Elo ratings, what
happens when they play? We model randomness in **three layers**. The second layer
is conditioned on the first, so the points result and the scoreline always agree.

**Layer 1 — Match outcome (who gets the points).**
First we turn the Elo gap into a win probability with the formula from Section 2.
Real football has lots of draws, so we reserve a **draw share** — about **27% for
an even matchup**, shrinking as the Elo gap grows (lopsided games rarely finish
level), following `draw_share = 0.27 · exp(-|Elo gap| / 500)`. The leftover
probability is split between the two teams *in proportion to their Elo win
probabilities*. We then draw a single random number and compare it against these
cumulative thresholds to decide: home win / draw / away win. This decides the
**3 / 1 / 0 league points** in the group stage.

**Layer 2 — Scoreline (how many goals).**
We sample each team's goal count from a **Poisson distribution** — the standard
model for counting rare events like goals. The average number of goals (`lambda`)
is `1.5 ± elo_diff/400`: the stronger team gets the `+`, the weaker the `−`,
floored at 0.5 so no team is impossible to score. Crucially, we **resample the
scoreline until it agrees with the Layer 1 result** (a win is outscored, a draw is
level), so the goals that feed the **goal-difference and goals-scored tiebreakers**
never contradict who actually took the points.

> **Note on the two layers:** because the scoreline is conditioned on the result,
> a "win" for points always comes with a winning scoreline and a "draw" with a
> level one. Outcomes drive standings, scorelines drive tiebreakers, and the two
> stay consistent. (A rare extreme upset that can't find a matching scoreline
> within a few tries falls back to a minimal consistent one.)

**Layer 3 — Penalties (knockout draws).**
A knockout match can't end level. If Layer 1 produced a draw, we go to a shootout,
modeled as a single biased coin flip: the **Elo favorite wins 55%** of shootouts,
the underdog 45% (an even matchup is a true 50/50).

### Worked example: Argentina (2113) vs USA (1733)
1. **Result.** The 380-point gap gives Argentina ~90% to win a non-drawn game.
   The draw share at this gap is about **13%** (down from 27% for an even game),
   so one match lands near **Argentina 78% / draw 13% / USA 9%.** We roll one
   random number to pick the result — usually an Argentina win, but that 9% is how
   upsets sneak in.
2. **Scoreline.** Goals are sampled with averages of about **2.5 for Argentina**
   and **0.5 for the USA**, then re-rolled if needed so the scoreline matches the
   result — so an Argentina win shows up as something like **2–0**.
3. **Penalties (knockout only).** Had this been a knockout game ending level,
   Argentina (the favorite) would win the shootout 55% of the time.

`simulate_match` returns everything a caller might need: the outcome letter, both
goal counts, and a definitive `winner` (penalty-resolved) for knockout use.
""")

code(r"""
# Draw model: an even matchup ends level about DRAW_BASE of the time; that chance
# shrinks as the Elo gap grows, since lopsided games rarely finish tied.
DRAW_BASE = 0.27
DRAW_SCALE = 500.0


def match_probabilities(elo_a, elo_b, draw_base=DRAW_BASE, draw_scale=DRAW_SCALE):
    '''Return (P(A win), P(draw), P(B win)).

    The draw share starts at `draw_base` for an even matchup and decays as the
    Elo gap widens (draw_share = draw_base * exp(-|gap| / draw_scale)). The
    remaining probability is split between the teams in proportion to their
    Elo-based win probabilities.
    '''
    p_a = 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))  # P(A beats B), no draws
    draw_share = draw_base * math.exp(-abs(elo_a - elo_b) / draw_scale)
    remaining = 1.0 - draw_share
    return p_a * remaining, draw_share, (1.0 - p_a) * remaining


def _consistent_scoreline(outcome, lambda_a, lambda_b, max_tries=20):
    '''Sample (goals_a, goals_b) from the Poisson goal model, conditioned to
    agree with the points outcome ("A" win, "B" win, or "D" draw).

    We resample until the scoreline matches the result, so points and goals can
    never contradict each other. The rare extreme upset that never matches within
    `max_tries` falls back to a minimal consistent scoreline built from the last
    draw, which keeps the goal magnitudes realistic.
    '''
    goals_a = goals_b = 0
    for _ in range(max_tries):
        goals_a = int(np.random.poisson(lambda_a))
        goals_b = int(np.random.poisson(lambda_b))
        if outcome == "A" and goals_a > goals_b:
            return goals_a, goals_b
        if outcome == "B" and goals_b > goals_a:
            return goals_a, goals_b
        if outcome == "D" and goals_a == goals_b:
            return goals_a, goals_b
    # Fallback: force consistency using the magnitudes we just drew.
    hi, lo = max(goals_a, goals_b), min(goals_a, goals_b)
    if outcome == "D":
        return lo, lo
    if hi == lo:
        hi = lo + 1
    return (hi, lo) if outcome == "A" else (lo, hi)


def simulate_match(team_a, team_b, elos):
    '''Simulate one match. Returns a dict with the outcome, both scores, and a
    penalty-resolved winner. The scoreline is sampled to agree with the points
    outcome, so the two never contradict each other.'''
    ea, eb = elos[team_a], elos[team_b]

    # --- Layer 1: outcome (decides league points) ---
    p_a_win, p_draw, p_b_win = match_probabilities(ea, eb)
    r = random.random()
    if r < p_a_win:
        outcome = "A"
    elif r < p_a_win + p_draw:
        outcome = "D"
    else:
        outcome = "B"

    # --- Layer 2: scoreline (decides tiebreakers), made consistent with Layer 1 ---
    elo_diff = abs(ea - eb)
    strong_lambda = 1.5 + elo_diff / 400.0
    weak_lambda = max(0.5, 1.5 - elo_diff / 400.0)
    if ea >= eb:
        lambda_a, lambda_b = strong_lambda, weak_lambda
    else:
        lambda_a, lambda_b = weak_lambda, strong_lambda
    goals_a, goals_b = _consistent_scoreline(outcome, lambda_a, lambda_b)

    # --- Layer 3: definitive winner (penalties on a draw) ---
    if outcome == "A":
        winner = team_a
    elif outcome == "B":
        winner = team_b
    elif ea == eb:
        winner = team_a if random.random() < 0.5 else team_b  # even shootout
    else:
        favorite, underdog = (team_a, team_b) if ea > eb else (team_b, team_a)
        winner = favorite if random.random() < 0.55 else underdog

    return {"outcome": outcome, "goals_a": goals_a, "goals_b": goals_b, "winner": winner}
""")

# ===========================================================================
# Group Stage
# ===========================================================================
md(r"""
## 4. Group Stage — round-robin and qualifier selection

Each group of 4 plays a **round-robin**: every team meets every other team once
(6 matches per group). We award **3 points for a win, 1 for a draw, 0 for a loss**,
and track each team's **goals for (GF)** and **goals against (GA)** from the
Poisson scorelines.

### FIFA tiebreaker rules
When teams finish level on points, FIFA breaks ties in this exact order:
1. **Head-to-head points** among the tied teams
2. **Head-to-head goal difference**
3. **Head-to-head goals scored**
4. Re-apply those head-to-head rules to any remaining tied subset
5. **Overall goal difference**
6. **Overall goals scored**
7. **Team conduct score** from yellow/red cards
8. **FIFA/Coca-Cola Men's World Ranking**

This simulator does not model cards, so every team has a neutral conduct score
of 0 and exact football ties fall through to the `fifa_rank` column in
`data/teams.csv`.

### Choosing who advances
- The **top 2 of every group** (24 teams) qualify automatically.
- All **12 third-place teams** are then compared against each other (by points,
  GD, GF, conduct score, then FIFA ranking) and the **best 8** also advance —
  giving 32 teams for the Round of 32.

### Example: a finished group
One simulated group might end up like this:

| Team | Pld | W | D | L | GF | GA | GD | Pts |
|------|-----|---|---|---|----|----|----|-----|
| Spain  | 3 | 3 | 0 | 0 | 6 | 0 | +6 | 9 |
| Mexico | 3 | 2 | 0 | 1 | 4 | 2 | +2 | 6 |
| Iran   | 3 | 1 | 0 | 2 | 2 | 4 | −2 | 3 |
| Iraq   | 3 | 0 | 0 | 3 | 0 | 6 | −6 | 0 |

Spain and Mexico go through as the top two. Iran finishes third — **not out yet**:
it competes with the other 11 third-placed teams for the 8 best-third spots. Iraq
is eliminated.

`get_qualifier_slots` returns the official bracket slots (`1A`, `2A`, `3A`, ...)
plus the Annexe C third-place routing needed for the Round of 32.
""")

code(r"""
def _partition_by_metric(teams, metric_fn, reverse=True):
    '''Group teams by a tiebreak metric, preserving ranked metric order.'''
    buckets = {}
    for team in teams:
        buckets.setdefault(metric_fn(team), []).append(team)
    ranked_keys = sorted(buckets, reverse=reverse)
    return [buckets[key] for key in ranked_keys]


def _h2h_metrics(teams, head_to_head):
    '''Return head-to-head points/GD/GF for the tied subset of teams.'''
    metrics = {team: {"points": 0, "gd": 0, "gf": 0} for team in teams}
    teams = list(teams)
    for i, a in enumerate(teams):
        for b in teams[i + 1:]:
            res = head_to_head.get((a, b)) or head_to_head.get((b, a))
            if res is None:
                continue
            if (a, b) in head_to_head:
                goals_a, goals_b, a_first = res["goals_a"], res["goals_b"], True
            else:
                goals_a, goals_b, a_first = res["goals_b"], res["goals_a"], False

            metrics[a]["gf"] += goals_a
            metrics[a]["gd"] += goals_a - goals_b
            metrics[b]["gf"] += goals_b
            metrics[b]["gd"] += goals_b - goals_a

            if res["outcome"] == "D":
                metrics[a]["points"] += 1
                metrics[b]["points"] += 1
            else:
                a_won = (res["outcome"] == "A") == a_first
                metrics[a if a_won else b]["points"] += 3
    return metrics


def _rank_by_overall(teams, stats, fifa_ranks):
    '''Apply FIFA step two/three: overall GD, GF, conduct, then FIFA rank.'''
    groups = [list(teams)]
    criteria = [
        (lambda t: stats[t]["gd"], True),
        (lambda t: stats[t]["gf"], True),
        (lambda t: stats[t]["conduct_score"], True),
        (lambda t: fifa_ranks[t], False),
    ]
    for metric_fn, reverse in criteria:
        next_groups = []
        for group in groups:
            if len(group) == 1:
                next_groups.append(group)
            else:
                next_groups.extend(_partition_by_metric(group, metric_fn, reverse=reverse))
        groups = next_groups
    ranked = []
    for group in groups:
        ranked.extend(sorted(group))
    return ranked


def _rank_h2h_recursive(teams, stats, head_to_head, fifa_ranks):
    '''Apply FIFA head-to-head criteria, reapplying to any still-tied subset.'''
    metrics = _h2h_metrics(teams, head_to_head)
    for key in ("points", "gd", "gf"):
        partitions = _partition_by_metric(teams, lambda t, k=key: metrics[t][k], reverse=True)
        if len(partitions) > 1:
            ranked = []
            for part in partitions:
                if len(part) == 1:
                    ranked.extend(part)
                else:
                    ranked.extend(_rank_h2h_recursive(part, stats, head_to_head, fifa_ranks))
            return ranked
    return _rank_by_overall(teams, stats, fifa_ranks)


def rank_group(group_label, group, stats, head_to_head, fifa_ranks):
    '''Return group records in official finishing order.'''
    point_groups = _partition_by_metric(group, lambda t: stats[t]["points"], reverse=True)
    ordered = []
    for tied in point_groups:
        if len(tied) == 1:
            ordered.extend(tied)
        else:
            ordered.extend(_rank_h2h_recursive(tied, stats, head_to_head, fifa_ranks))

    records = []
    for position, team in enumerate(ordered, start=1):
        rec = stats[team].copy()
        rec["team"] = team
        rec["group"] = group_label
        rec["position"] = position
        records.append(rec)
    return records


def simulate_group(group_label, group, elos, fifa_ranks):
    '''Play the six official-position pairings in a group and rank the records.'''
    stats = {
        team: {
            "points": 0,
            "gf": 0,
            "ga": 0,
            "gd": 0,
            "conduct_score": 0,  # Cards are not modeled; neutral for every team.
            "fifa_rank": fifa_ranks[team],
        }
        for team in group
    }
    head_to_head = {}

    for i, j in GROUP_MATCH_PAIRINGS:
        a, b = group[i], group[j]
        res = simulate_match(a, b, elos)
        if res["outcome"] == "A":
            stats[a]["points"] += 3
        elif res["outcome"] == "B":
            stats[b]["points"] += 3
        else:
            stats[a]["points"] += 1
            stats[b]["points"] += 1

        stats[a]["gf"] += res["goals_a"]
        stats[a]["ga"] += res["goals_b"]
        stats[b]["gf"] += res["goals_b"]
        stats[b]["ga"] += res["goals_a"]
        stats[a]["gd"] = stats[a]["gf"] - stats[a]["ga"]
        stats[b]["gd"] = stats[b]["gf"] - stats[b]["ga"]
        head_to_head[(a, b)] = res

    return rank_group(group_label, group, stats, head_to_head, fifa_ranks)


def _third_place_sort_key(record):
    '''Official ranking for third-placed teams across groups.'''
    return (
        -record["points"],
        -record["gd"],
        -record["gf"],
        -record["conduct_score"],
        record["fifa_rank"],
        record["team"],
    )


def _third_place_option(qualifying_groups):
    '''Return FIFA Annexe C option number for the eight qualifying third groups.'''
    qualifying_groups = set(qualifying_groups)
    excluded = tuple(group for group in GROUP_ORDER if group not in qualifying_groups)
    option_lookup = {
        combo: option
        for option, combo in enumerate(combinations(GROUP_ORDER, 4), start=1)
    }
    return option_lookup[excluded]


def get_qualifier_slots(standings, annex_c):
    '''Return bracket slots and Annexe C routing for the 32 qualifiers.'''
    slots = {}
    qualifiers = []
    thirds = []

    for group_label in GROUP_ORDER:
        records = standings[group_label]
        slots[f"1{group_label}"] = records[0]["team"]
        slots[f"2{group_label}"] = records[1]["team"]
        slots[f"3{group_label}"] = records[2]["team"]
        qualifiers.extend([records[0]["team"], records[1]["team"]])
        thirds.append(records[2])

    best_thirds = sorted(thirds, key=_third_place_sort_key)[:8]
    qualifiers.extend(record["team"] for record in best_thirds)
    qualifying_groups = {record["group"] for record in best_thirds}
    option = _third_place_option(qualifying_groups)
    third_for_winner = dict(zip(ANNEX_COLUMNS, annex_c[option]))

    return slots, third_for_winner, qualifiers, option
""")

# ===========================================================================
# Knockout Stage
# ===========================================================================
md(r"""
## 5. Knockout Stage — single elimination

From the Round of 32 onward it is win-or-go-home. Each round halves the field:
**32 → 16 → 8 (Quarterfinals) → 4 (Semifinals) → 2 (Final) → 1 (Winner)**.

### Building the bracket
The bracket follows the official FIFA Regulations match graph:

- **Round of 32:** M73-M88 use group finish slots such as `1E`, `2A`, and the
  Annexe C third-place assignments.
- **Round of 16:** M89-M96 use the published winner pairings.
- **Quarterfinals, semifinals, final:** M97-M104 follow the official route to the
  trophy.

The only dynamic part is the third-place routing. Once the eight qualifying
third-place groups are known, `annex_c.csv` tells us which third-place team goes
to each applicable winner slot.

### Penalty logic
A knockout match cannot be drawn. We reuse `simulate_match`, which already
resolves a drawn outcome via a penalty shootout (Layer 3): the **higher-Elo
team wins the shootout 55% of the time**. So `simulate_match` always hands back a
clean `winner` in knockout rounds.

### Example: penalties and an upset
Picture a Round of 16 tie, **Brazil (1988) vs Croatia (1908)**. Brazil are
favorites, so if regulation ends **1–1** they win the shootout 55% of the time.
But 45% is real — and in this particular simulated run, Croatia hold their nerve
and knock Brazil out. Re-run the tournament and Brazil probably advance; that
back-and-forth across thousands of runs is exactly what we are measuring.

`simulate_official_knockouts` resolves the official match graph and reports which
teams reach each milestone.
""")

code(r"""
R32_MATCHES = [
    (73, "2A", "2B"),
    (74, "1E", "THIRD:1E"),
    (75, "1F", "2C"),
    (76, "1C", "2F"),
    (77, "1I", "THIRD:1I"),
    (78, "2E", "2I"),
    (79, "1A", "THIRD:1A"),
    (80, "1L", "THIRD:1L"),
    (81, "1D", "THIRD:1D"),
    (82, "1G", "THIRD:1G"),
    (83, "2K", "2L"),
    (84, "1H", "2J"),
    (85, "1B", "THIRD:1B"),
    (86, "1J", "2H"),
    (87, "1K", "THIRD:1K"),
    (88, "2D", "2G"),
]

R16_MATCHES = [
    (89, 74, 77),
    (90, 73, 75),
    (91, 76, 78),
    (92, 79, 80),
    (93, 83, 84),
    (94, 81, 82),
    (95, 86, 88),
    (96, 85, 87),
]

QF_MATCHES = [(97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96)]
SF_MATCHES = [(101, 97, 98), (102, 99, 100)]
FINAL_MATCH = (104, 101, 102)


def _resolve_competitor(code, slots, third_for_winner):
    '''Resolve a bracket code like 1A, 2B, or THIRD:1E to a team name.'''
    if code.startswith("THIRD:"):
        code = third_for_winner[code.split(":", 1)[1]]
    return slots[code]


def _play_match(match_no, team_a, team_b, elos):
    res = simulate_match(team_a, team_b, elos)
    return res["winner"]


def simulate_official_knockouts(slots, third_for_winner, elos):
    '''Play the official FIFA knockout match graph and return winners by stage.'''
    winners = {}
    stages = {"R16": [], "QF": [], "SF": [], "Final": [], "Winner": []}

    for match_no, code_a, code_b in R32_MATCHES:
        team_a = _resolve_competitor(code_a, slots, third_for_winner)
        team_b = _resolve_competitor(code_b, slots, third_for_winner)
        winners[match_no] = _play_match(match_no, team_a, team_b, elos)
        stages["R16"].append(winners[match_no])

    for match_no, a_prev, b_prev in R16_MATCHES:
        winners[match_no] = _play_match(match_no, winners[a_prev], winners[b_prev], elos)
        stages["QF"].append(winners[match_no])

    for match_no, a_prev, b_prev in QF_MATCHES:
        winners[match_no] = _play_match(match_no, winners[a_prev], winners[b_prev], elos)
        stages["SF"].append(winners[match_no])

    for match_no, a_prev, b_prev in SF_MATCHES:
        winners[match_no] = _play_match(match_no, winners[a_prev], winners[b_prev], elos)
        stages["Final"].append(winners[match_no])

    match_no, a_prev, b_prev = FINAL_MATCH
    winners[match_no] = _play_match(match_no, winners[a_prev], winners[b_prev], elos)
    stages["Winner"].append(winners[match_no])
    return stages
""")

# ===========================================================================
# Run Simulation
# ===========================================================================
md(r"""
## 6. Run Simulation — the Monte Carlo loop

### What "Monte Carlo" means
A single simulated tournament is just *one* possible future — maybe the favorite
gets knocked out early, maybe a dark horse runs the table. One run tells us almost
nothing. But if we replay the tournament **thousands of times** and count how
often each team reaches each stage, those counts converge on the true
probabilities implied by our model. **The fraction of runs in which something
happens is its probability.** That's Monte Carlo: estimate hard-to-calculate odds
by brute-force repetition with weighted randomness.

### Why more runs = more stable results
Each run is like one flip of a very elaborate coin. With few flips your estimate
is jumpy; with many it settles down (the *law of large numbers*). Roughly, the
noise in a probability estimate shrinks like `1/√N_RUNS` — so going from 1,000 to
10,000 runs cuts the wobble by about 3×, and 100,000 cuts it by ~10×.

### Reproducibility
`run_simulation` seeds the random generators **once at the top**
(`np.random.seed(seed)` for the Poisson scorelines and `random.seed(seed)` for the
outcome/penalty draws), defaulting to `seed=42`. Same seed → identical results
every time, on any machine. Both generators are seeded because we use both
libraries; change the seed to see a different (but equally valid) set of runs.

### What we record
`run_tournament` plays one full event and reports the **furthest stage each team
reached** (`Group`, `R32`, `R16`, `QF`, `SF`, `Final`, or `Winner`).
`run_simulation` accumulates these across all `N_RUNS` runs and converts the
counts into probabilities.

### The final, and turning counts into probabilities
The final is just one more knockout match — but it's the one we care most about
counting. Its winner is logged as that tournament's champion. After all the runs,
the probability is simple division: if Argentina lift the trophy in **1,900 of
10,000** runs, that's a **19% chance of winning the World Cup**. The same counting
gives every other milestone — reach the semifinals in 3,300 runs and that's a 33%
chance of making the semis. These percentages are exactly what the table and
bracket in the next section display.
""")

code(r"""
# Stages in order of progression. A team's "furthest stage" is one of these.
STAGES = ["Group", "R32", "R16", "QF", "SF", "Final", "Winner"]


def run_tournament(groups, elos, fifa_ranks, annex_c):
    '''Play one complete tournament. Returns {team: furthest_stage_reached}.'''
    # Everyone starts as a group-stage exit; we upgrade as they advance.
    reached = {team: "Group" for group in groups.values() for team in group}

    standings = {
        label: simulate_group(label, group, elos, fifa_ranks)
        for label, group in groups.items()
    }
    slots, third_for_winner, qualifiers, _option = get_qualifier_slots(standings, annex_c)
    for team in qualifiers:
        reached[team] = "R32"

    knockout_stages = simulate_official_knockouts(slots, third_for_winner, elos)
    for stage in ["R16", "QF", "SF", "Final", "Winner"]:
        for team in knockout_stages[stage]:
            reached[team] = stage

    return reached


def build_summary(counts, elos, fifa_ranks, n):
    '''Turn raw furthest-stage counts into a ranked probability table.

    For each team we compute the *cumulative* probability of reaching each stage
    (e.g. P(reach QF) = fraction of runs that ended in QF, SF, Final, or Winner).
    '''
    columns = ["Make R32", "Make R16", "Make QF", "Make SF", "Make Final", "Win Title"]
    col_stage = dict(zip(columns, ["R32", "R16", "QF", "SF", "Final", "Winner"]))

    rows = []
    for team, stage_counts in counts.items():
        row = {"Team": team, "Elo": elos[team], "FIFA Rank": fifa_ranks[team]}
        for col in columns:
            start = STAGES.index(col_stage[col])
            reached_or_better = sum(stage_counts[s] for s in STAGES[start:])
            row[col] = 100.0 * reached_or_better / n
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["Win Title", "Make Final", "Make SF", "Make QF", "Make R16", "Make R32", "Elo", "FIFA Rank"],
        ascending=[False, False, False, False, False, False, False, True],
    ).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Rank"
    return df, columns


def run_simulation(n=N_RUNS, seed=42):
    '''Run the full Monte Carlo experiment and return a results dict.'''
    # ---- All randomness is seeded here, once. ----
    np.random.seed(seed)
    random.seed(seed)

    team_data = load_team_data()
    annex_c = load_annex_c()
    elos = team_data["elos"]
    fifa_ranks = team_data["fifa_ranks"]
    groups = team_data["groups"]
    all_teams = team_data["teams"]
    counts = {t: {s: 0 for s in STAGES} for t in all_teams}

    for _ in range(n):
        for team, stage in run_tournament(groups, elos, fifa_ranks, annex_c).items():
            counts[team][stage] += 1

    summary, columns = build_summary(counts, elos, fifa_ranks, n)
    return {
        "summary": summary,
        "columns": columns,
        "counts": counts,
        "elos": elos,
        "fifa_ranks": fifa_ranks,
        "groups": groups,
        "annex_c": annex_c,
        "n": n,
        "seed": seed,
    }
""")

# ===========================================================================
# Results & Visualization
# ===========================================================================
md(r"""
## 7. Results & Visualization

Now we run the experiment and look at the output.

### How to read the bracket heatmap
- **Each row is a team**, sorted from most to least likely to win the title.
- **Each column is a milestone** — reaching the Round of 32, Round of 16,
  Quarterfinals, Semifinals, Final, and finally winning it all.
- **Each cell shows the probability** (as a %) that the team reaches *at least*
  that stage, with a **color scale**: deep **green = very likely**, **yellow =
  a coin flip**, **red = unlikely**. Reading left to right, the numbers can only
  shrink — it's harder to reach later rounds.

### The summary table
Below the figure is a full ranking of all 48 teams by **title probability**,
which we export to `wc2026_probabilities.csv`. The bracket figure is saved to
`wc2026_bracket.png`. Both land in the notebook's working directory.

> **Sanity check:** the "Win Title" column should sum to ~100% across all teams
> (exactly one champion per run), and the favorites should match their Elo order.
""")

code(r"""
def plot_bracket(results, top_n=None, save_path="wc2026_bracket.png"):
    '''Draw the bracket-style probability heatmap and save it as a PNG.

    top_n: show only the top N teams (None = all 48).
    '''
    df = results["summary"]
    columns = results["columns"]
    data = df if top_n is None else df.head(top_n)

    teams = data["Team"].tolist()
    matrix = data[columns].to_numpy(dtype=float)

    cmap = plt.get_cmap("RdYlGn")       # red (low) -> yellow -> green (high)
    norm = Normalize(vmin=0, vmax=100)

    fig_h = max(4.0, 0.34 * len(teams) + 1.5)
    fig_w = 1.5 * len(columns) + 3.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(columns, fontsize=10, fontweight="bold")
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.set_yticks(range(len(teams)))
    ax.set_yticklabels(teams, fontsize=8)

    # Annotate each cell with its percentage
    for i in range(len(teams)):
        for j in range(len(columns)):
            val = matrix[i, j]
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=7, color="black")

    # Light grid between cells
    ax.set_xticks(np.arange(-0.5, len(columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(teams), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", length=0)

    title = (f"2026 FIFA World Cup - Probability of Reaching Each Stage\n"
             f"Monte Carlo, {results['n']:,} simulations (seed={results['seed']})")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=18)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved bracket figure to: {save_path}")
    plt.show()
""")

code(r"""
# ---- Run the whole experiment ----
results = run_simulation(N_RUNS, seed=42)

# Draw and save the bracket heatmap
plot_bracket(results)
""")

code(r"""
# ---- Ranked summary table for all 48 teams ----
summary = results["summary"].copy()

# Pretty-print percentages with one decimal place
display_df = summary.copy()
for col in results["columns"]:
    display_df[col] = display_df[col].map(lambda v: f"{v:.1f}%")

# Export the raw (numeric) table to CSV
summary.to_csv("wc2026_probabilities.csv")
print("Saved summary table to: wc2026_probabilities.csv\n")

display_df
""")

code(r"""
# ---- Quick sanity checks ----
total_win = results["summary"]["Win Title"].sum()
print(f"Sum of all title probabilities: {total_win:.2f}%  (should be ~100%)")

top5 = results["summary"].head(5)[["Team", "Elo", "Win Title", "Make Final"]]
print("\nTop 5 contenders:")
print(top5.to_string())
""")

# ===========================================================================
# Write the notebook
# ===========================================================================
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.x"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT = "WorldCup2026_MonteCarlo.ipynb"
with open(OUT, "w") as f:
    json.dump(notebook, f, indent=1)
print(f"Wrote {OUT} with {len(cells)} cells.")
