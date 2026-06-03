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

We rely on four standard libraries — all pre-installed in Google Colab and most
data-science environments. If any are missing (e.g. a bare Python install),
uncomment the `pip install` line in the cell below.

| Library | Role in this notebook |
|---|---|
| **numpy** | Random number generation — specifically Poisson sampling for scorelines, and the master random seed for reproducibility. |
| **pandas** | Reads the team data from `data/teams.csv`, builds the final summary table, and exports it to CSV. |
| **matplotlib** | Draws the bracket heatmap and saves it as a PNG. |
| **random** | Python's built-in module, used for the simple coin-flip-style draws (match outcome thresholds and penalty shootouts). |
| **os** | Python's built-in module, used only to locate the `data/teams.csv` file. |

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
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colormaps
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
## 2. Team Data — Elo ratings

To make the simulation realistic, each team needs a **strength number**. We use
**Elo ratings**.

### What is an Elo rating?
Elo is a rating system originally built for chess and now widely used for
national football teams (see *eloratings.net*). Every team has a single number —
stronger teams have higher numbers. The scale is calibrated so that the
*difference* between two teams' ratings maps directly onto a win probability.
The neat property: a team rated **400 points higher** than its opponent is about
**10×** more likely to win.

We use the standard Elo win-probability formula:

$$P(\text{A beats B}) = \frac{1}{1 + 10^{(\text{Elo}_B - \text{Elo}_A) / 400}}$$

**A quick example.** Argentina (2140) vs the USA (1770) is a 370-point gap.
Plugging that in gives Argentina roughly a **89%** chance to win (before we make
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

**A caveat.** The ratings are **approximate, illustrative values** for a plausible
48-team field — not the official live numbers. Swap in better ones for better
answers.

### Where the data lives
The ratings are **not hardcoded in this notebook**. They are loaded from an
external file so the data is cleanly separated from the logic:

```
your-folder/
├── WorldCup2026_MonteCarlo.ipynb   <- this notebook
└── data/
    └── teams.csv                   <- team,elo  (48 rows)
```

To change the field, just edit `data/teams.csv` in any spreadsheet app — no code
changes needed. You can add more teams, remove some, or plug in a different Elo
snapshot; the simulation adapts automatically.

> **Running in Google Colab or elsewhere?** Because the data is a separate file,
> it must sit beside the notebook. Colab's VM won't have your local `data/`
> folder, so first either **upload `teams.csv`** into a `data` folder via the
> Files panel, **mount Google Drive**, or point `load_teams()` at wherever you
> put the file. If the file can't be found, the cell below raises a clear error
> telling you exactly what to do.

`load_teams()` reads the CSV and returns a dictionary mapping
**team name → Elo rating**.
""")

code(r"""
# Folder holding the external data files, relative to this notebook.
DATA_DIR = "data"


def load_teams(path=None):
    '''Load {team_name: elo_rating} for all teams from data/teams.csv.

    The CSV must have two columns: `team` and `elo`. Edit that file to change
    the field — no code changes required. Pass `path=` to read from elsewhere.
    '''
    path = path or os.path.join(DATA_DIR, "teams.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find '{path}'.\n"
            f"Keep the 'data/' folder next to this notebook. In Google Colab, "
            f"upload teams.csv into a 'data' folder via the Files panel, mount "
            f"Google Drive, or call load_teams(path='/your/path/teams.csv')."
        )
    df = pd.read_csv(path)
    expected = {"team", "elo"}
    if not expected.issubset(df.columns):
        raise ValueError(
            f"'{path}' must contain columns {sorted(expected)}; "
            f"found {list(df.columns)}."
        )
    return dict(zip(df["team"].astype(str), df["elo"].astype(int)))


def make_groups(elos, n_groups=12):
    '''Draw the 12 groups of 4 using a deterministic, seeded-by-strength method.

    Mimics FIFA's pot system: teams are ranked by Elo and split into 4 'pots'
    of 12. Each group gets exactly one team from each pot. We assign pots in a
    'snake' order (pot 1 left-to-right, pot 2 right-to-left, ...) so the groups
    come out balanced. This is deterministic, so the draw is identical every run
    and the bracket stays meaningful.
    '''
    teams = sorted(elos, key=lambda t: elos[t], reverse=True)
    pots = [teams[i * n_groups:(i + 1) * n_groups] for i in range(4)]
    groups = [[] for _ in range(n_groups)]
    for p, pot in enumerate(pots):
        for gi, team in enumerate(pot):
            idx = gi if p % 2 == 0 else (n_groups - 1 - gi)  # snake for balance
            groups[idx].append(team)
    return groups


# Quick look at the field and the resulting draw
_elos = load_teams()
print(f"Loaded {len(_elos)} teams.\n")
for gi, grp in enumerate(make_groups(_elos)):
    label = chr(ord('A') + gi)
    print(f"Group {label}: " + ", ".join(f"{t} ({_elos[t]})" for t in grp))
""")

# ===========================================================================
# Match Simulation
# ===========================================================================
md(r"""
## 3. Match Simulation — the randomness model

This is the heart of the simulation: given two teams and their Elo ratings, what
happens when they play? We model randomness in **three independent layers**.

**Layer 1 — Match outcome (who gets the points).**
First we turn the Elo gap into a win probability with the formula from Section 2.
Real football has lots of draws, so we reserve a fixed **~27% chance of a draw**
and split the remaining 73% between the two teams *in proportion to their Elo win
probabilities*. We then draw a single random number and compare it against these
cumulative thresholds to decide: home win / draw / away win. This decides the
**3 / 1 / 0 league points** in the group stage.

**Layer 2 — Scoreline (how many goals).**
Separately, we sample each team's goal count from a **Poisson distribution** — the
standard model for counting rare, independent events like goals. The average
number of goals (`lambda`) is `1.5 ± elo_diff/400`: the stronger team gets the
`+`, the weaker the `−`, floored at 0.5 so no team is impossible to score.
These goals feed the **goal-difference and goals-scored tiebreakers**.

> **Note on the two-layer design:** points (Layer 1) and goals (Layer 2) are
> drawn *independently*, so once in a while the points-outcome and the goal-count
> may disagree (e.g. a "draw" for points with a 2–1 scoreline). This is a
> deliberate simplification from the spec — outcomes drive standings, scorelines
> drive tiebreakers — and it keeps each layer easy to reason about.

**Layer 3 — Penalties (knockout draws).**
A knockout match can't end level. If Layer 1 produced a draw, we go to a shootout,
modeled as a single biased coin flip: the **Elo favorite wins 55%** of shootouts,
the underdog 45%.

### Worked example: Argentina (2140) vs USA (1770)
1. **Result.** The 370-point gap gives Argentina ~89% to win a non-drawn game.
   Reserve 27% for a draw and split the rest by strength, and one match lands near
   **Argentina 65% / draw 27% / USA 8%.** We roll one random number to pick the
   result — usually an Argentina win, but that 8% is how upsets sneak in.
2. **Scoreline.** Separately, goals are sampled with averages of about **2.4 for
   Argentina** and **0.6 for the USA**, so a typical roll might be **2–0**.
3. **Penalties (knockout only).** Had this been a knockout game ending level,
   Argentina (the favorite) would win the shootout 55% of the time.

`simulate_match` returns everything a caller might need: the outcome letter, both
goal counts, and a definitive `winner` (penalty-resolved) for knockout use.
""")

code(r"""
def match_probabilities(elo_a, elo_b, draw_share=0.27):
    '''Return (P(A win), P(draw), P(B win)).

    A fixed share of probability is given to a draw; the rest is split between
    the teams in proportion to their Elo-based win probabilities.
    '''
    p_a = 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))  # P(A beats B), no draws
    remaining = 1.0 - draw_share
    return p_a * remaining, draw_share, (1.0 - p_a) * remaining


def simulate_match(team_a, team_b, elos):
    '''Simulate one match. Returns a dict with the outcome, both scores, and a
    penalty-resolved winner.'''
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

    # --- Layer 2: scoreline (decides tiebreakers), sampled independently ---
    elo_diff = abs(ea - eb)
    strong_lambda = 1.5 + elo_diff / 400.0
    weak_lambda = max(0.5, 1.5 - elo_diff / 400.0)
    if ea >= eb:
        lambda_a, lambda_b = strong_lambda, weak_lambda
    else:
        lambda_a, lambda_b = weak_lambda, strong_lambda
    goals_a = int(np.random.poisson(lambda_a))
    goals_b = int(np.random.poisson(lambda_b))

    # --- Layer 3: definitive winner (penalties on a draw) ---
    if outcome == "A":
        winner = team_a
    elif outcome == "B":
        winner = team_b
    else:
        favorite, underdog = (team_a, team_b) if ea >= eb else (team_b, team_a)
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
1. **Points** (overall)
2. **Goal difference** (GF − GA, overall)
3. **Goals scored** (GF, overall)
4. **Head-to-head points** — only the matches *among the tied teams*
5. **Head-to-head goal difference**
6. **Drawing of lots** — pure random chance (we use a random number)

Our `rank_group` applies points/GD/GF first, then resolves any remaining ties
with the head-to-head mini-table, and finally a random draw of lots. (This is a
faithful, lightly simplified version of FIFA's full procedure.)

### Choosing who advances
- The **top 2 of every group** (24 teams) qualify automatically.
- All **12 third-place teams** are then compared against each other (by points,
  then GD, then GF) and the **best 8** also advance — giving 32 teams for the
  Round of 32.

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

`get_qualifiers` returns the 32 survivors already **ordered as bracket seeds**
(group winners first, then runners-up, then the best thirds), so stronger group
performers are spread across the bracket.
""")

code(r"""
def _break_h2h(tied, head_to_head):
    '''Order teams that are tied on points/GD/GF using head-to-head results
    among themselves, then a random drawing of lots.'''
    h_pts = {t: 0 for t in tied}
    h_gd = {t: 0 for t in tied}
    for a in tied:
        for b in tied:
            if a == b:
                continue
            res = head_to_head.get((a, b)) or head_to_head.get((b, a))
            if res is None:
                continue
            # Express the result from team a's perspective
            if (a, b) in head_to_head:
                ga, gb, outcome_a_first = res["goals_a"], res["goals_b"], True
            else:
                ga, gb, outcome_a_first = res["goals_b"], res["goals_a"], False
            h_gd[a] += ga - gb
            if res["outcome"] == "D":
                h_pts[a] += 1
            else:
                a_won = (res["outcome"] == "A") == outcome_a_first
                if a_won:
                    h_pts[a] += 3
    return sorted(tied, key=lambda t: (h_pts[t], h_gd[t], random.random()), reverse=True)


def rank_group(group, points, gf, ga, head_to_head):
    '''Return group records [(team, points, gd, gf), ...] in finishing order,
    applying the FIFA tiebreaker sequence.'''
    gd = {t: gf[t] - ga[t] for t in group}
    ordered = sorted(group, key=lambda t: (points[t], gd[t], gf[t]), reverse=True)

    # Resolve blocks that are still tied on (points, gd, gf) via head-to-head
    final = []
    i = 0
    while i < len(ordered):
        j = i
        key_i = (points[ordered[i]], gd[ordered[i]], gf[ordered[i]])
        while j < len(ordered) and (points[ordered[j]], gd[ordered[j]], gf[ordered[j]]) == key_i:
            j += 1
        block = ordered[i:j]
        if len(block) > 1:
            block = _break_h2h(block, head_to_head)
        final.extend(block)
        i = j

    return [(t, points[t], gd[t], gf[t]) for t in final]


def simulate_group(group, elos):
    '''Play all 6 round-robin matches in a group and return the ranked records.'''
    points = {t: 0 for t in group}
    gf = {t: 0 for t in group}
    ga = {t: 0 for t in group}
    head_to_head = {}

    for i in range(len(group)):
        for k in range(i + 1, len(group)):
            a, b = group[i], group[k]
            res = simulate_match(a, b, elos)
            # League points from Layer 1 (outcome)
            if res["outcome"] == "A":
                points[a] += 3
            elif res["outcome"] == "B":
                points[b] += 3
            else:
                points[a] += 1
                points[b] += 1
            # Goals from Layer 2 (scoreline)
            gf[a] += res["goals_a"]; ga[a] += res["goals_b"]
            gf[b] += res["goals_b"]; ga[b] += res["goals_a"]
            head_to_head[(a, b)] = res

    return rank_group(group, points, gf, ga, head_to_head)


def get_qualifiers(standings):
    '''From all group standings, return the 32 qualifiers as an ordered list of
    bracket seeds: group winners (best->worst), then runners-up, then the 8 best
    third-placed teams.'''
    winners, runners, thirds = [], [], []
    for records in standings.values():
        winners.append(records[0])
        runners.append(records[1])
        thirds.append(records[2])

    # Sort tiers by (points, gd, gf); random tiebreak for exact ties
    rank_key = lambda rec: (rec[1], rec[2], rec[3], random.random())
    winners.sort(key=rank_key, reverse=True)
    runners.sort(key=rank_key, reverse=True)
    thirds.sort(key=rank_key, reverse=True)

    seeded = winners + runners + thirds[:8]   # 12 + 12 + 8 = 32
    return [rec[0] for rec in seeded]          # team names, seed order
""")

# ===========================================================================
# Knockout Stage
# ===========================================================================
md(r"""
## 5. Knockout Stage — single elimination

From the Round of 32 onward it is win-or-go-home. Each round halves the field:
**32 → 16 → 8 (Quarterfinals) → 4 (Semifinals) → 2 (Final) → 1 (Winner)**.

### Building the bracket
We place the 32 seeded qualifiers into a **standard tournament bracket** so that
the top seeds are kept as far apart as possible (seed 1 and seed 2 can only meet
in the final). `bracket_seed_order` produces the classic seeding pattern
(1 vs 32, 16 vs 17, 8 vs 25, ...) used in real draws.

### Penalty logic
A knockout match cannot be drawn. We reuse `simulate_match`, which already
resolves a drawn outcome via a penalty shootout (Layer 3): the **higher-Elo
team wins the shootout 55% of the time**. So `simulate_match` always hands back a
clean `winner` in knockout rounds.

### Example: penalties and an upset
Picture a Round of 16 tie, **Brazil (2020) vs Croatia (1880)**. Brazil are
favorites, so if regulation ends **1–1** they win the shootout 55% of the time.
But 45% is real — and in this particular simulated run, Croatia hold their nerve
and knock Brazil out. Re-run the tournament and Brazil probably advance; that
back-and-forth across thousands of runs is exactly what we are measuring.

`simulate_knockout_round` takes the current list of teams (already in bracket
order), plays adjacent pairs (0 vs 1, 2 vs 3, ...), and returns the winners — half
as many teams, ready for the next round.
""")

code(r"""
def bracket_seed_order(n):
    '''Return seeds 1..n arranged in standard single-elimination bracket order,
    so higher seeds avoid each other until late rounds.'''
    order = [1, 2]
    while len(order) < n:
        m = len(order) * 2 + 1
        order = [x for s in order for x in (s, m - s)]
    return order


def simulate_knockout_round(teams, elos):
    '''Play one knockout round. `teams` is in bracket order; adjacent pairs meet.
    Returns the list of winners (half the length).'''
    winners = []
    for i in range(0, len(teams), 2):
        res = simulate_match(teams[i], teams[i + 1], elos)
        winners.append(res["winner"])
    return winners
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


def run_tournament(groups, elos):
    '''Play one complete tournament. Returns {team: furthest_stage_reached}.'''
    # Everyone starts as a group-stage exit; we upgrade as they advance.
    reached = {team: "Group" for group in groups for team in group}

    standings = {gi: simulate_group(group, elos) for gi, group in enumerate(groups)}
    qualifiers = get_qualifiers(standings)          # 32 teams, in seed order
    for team in qualifiers:
        reached[team] = "R32"

    # Place seeds into the bracket and play down to a single winner.
    order = bracket_seed_order(32)
    teams = [qualifiers[seed - 1] for seed in order]

    winner_label = {32: "R16", 16: "QF", 8: "SF", 4: "Final", 2: "Winner"}
    while len(teams) > 1:
        label = winner_label[len(teams)]
        teams = simulate_knockout_round(teams, elos)
        for team in teams:
            reached[team] = label

    return reached


def build_summary(counts, elos, n):
    '''Turn raw furthest-stage counts into a ranked probability table.

    For each team we compute the *cumulative* probability of reaching each stage
    (e.g. P(reach QF) = fraction of runs that ended in QF, SF, Final, or Winner).
    '''
    columns = ["Make R32", "Make R16", "Make QF", "Make SF", "Make Final", "Win Title"]
    col_stage = dict(zip(columns, ["R32", "R16", "QF", "SF", "Final", "Winner"]))

    rows = []
    for team, stage_counts in counts.items():
        row = {"Team": team, "Elo": elos[team]}
        for col in columns:
            start = STAGES.index(col_stage[col])
            reached_or_better = sum(stage_counts[s] for s in STAGES[start:])
            row[col] = 100.0 * reached_or_better / n
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["Win Title", "Make Final", "Make SF", "Make QF", "Make R16", "Make R32", "Elo"],
        ascending=False,
    ).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Rank"
    return df, columns


def run_simulation(n=N_RUNS, seed=42):
    '''Run the full Monte Carlo experiment and return a results dict.'''
    # ---- All randomness is seeded here, once. ----
    np.random.seed(seed)
    random.seed(seed)

    elos = load_teams()
    groups = make_groups(elos)
    all_teams = [t for g in groups for t in g]
    counts = {t: {s: 0 for s in STAGES} for t in all_teams}

    for _ in range(n):
        for team, stage in run_tournament(groups, elos).items():
            counts[team][stage] += 1

    summary, columns = build_summary(counts, elos, n)
    return {
        "summary": summary,
        "columns": columns,
        "counts": counts,
        "elos": elos,
        "groups": groups,
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

    cmap = colormaps["RdYlGn"]          # red (low) -> yellow -> green (high)
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
