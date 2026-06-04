# 2026 FIFA World Cup Monte Carlo Simulation

Nobody knows who will win the 2026 World Cup. This project does not either. What
it can do is replay the tournament thousands of times, using team ratings to
weight each match, then count how often each team reaches each stage.

If a team wins 1,900 out of 10,000 simulated tournaments, the model reports a
19% title chance. That is the whole idea: many random tournament runs, counted
up into probabilities.

The project uses the [confirmed 2026 field and official group draw](https://inside.fifa.com/organisation/news/groups-match-ups-revealed-game-changing-world-cup-2026),
FIFA group-stage tiebreaker order, and the
[official knockout bracket routing](https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf),
including the 495 Annexe C third-place combinations.

### Monte Carlo

A Monte Carlo simulation is just a careful way of saying: "try the same thing
many times with randomness, then count what happened."

Imagine you want to know how often Germany might win this World Cup in this
model. One simulated tournament is not enough. Maybe Germany get a bad draw,
lose a penalty shootout, and go home early. That can happen. But if you replay
the tournament 10,000 times, the weird one-off runs start to settle into a
pattern. If Germany win 1,900 of those runs, the model reports about a 19%
chance.

So the simulation is not claiming, "Germany will win." It is saying, "given
these ratings, this draw, and this match model, Germany won this often when we
replayed the tournament many times."

### Elo

Elo is a way to put team strength on a number scale. Higher means stronger. The
useful part is that the gap between two ratings can be turned into a win chance.

For example, a team rated 2000 is treated as stronger than a team rated 1700.
That does not mean the stronger team always wins. It means the random match draw
is weighted in its favor. Upsets still happen, which is exactly why we simulate
the tournament many times instead of just picking the highest-rated team.

Elo started in chess, where ratings are updated after players win, lose, or draw.
The same idea is now used in other places too: football rating sites, sports
models, online games, and matchmaking systems.
For chess, that might be an official body such as FIDE. For international
football, public Elo-style lists such as [World Football Elo Ratings](https://www.eloratings.net/)
maintain their own numbers from match results.

This project does not update Elo after simulated matches. It treats the `elo`
values in `data/teams.csv` as fixed starting assumptions, then uses them to
weight match outcomes.

In this project, the `elo` column is the strength input. The `fifa_rank` column is
not used to make teams stronger or weaker in matches; it is only a late official
tiebreaker when teams are still tied after the football criteria.

### Why Not Use FIFA Ranking For Match Strength?

The official FIFA ranking is useful, but it is mainly built to order teams: who is
ranked 1st, 2nd, 3rd, and so on. That is exactly why this project uses it for the
official FIFA tiebreaker.

For simulating matches, though, we need something slightly different. We need to
turn "Team A is stronger than Team B" into "Team A has about this much chance to
win." Elo is better suited for that job because the rating gap has a direct
probability meaning. A small Elo gap is close to a toss-up. A big Elo gap makes
one team a clear favorite, while still leaving room for upsets.

So the split is intentional:

- `elo` answers: "How likely is this team to win this simulated match?"
- `fifa_rank` answers: "If FIFA rules need a final ranking tiebreaker, who is
  officially ranked higher?"

## Official FIFA References

The official tournament structure comes from FIFA sources:

- [FIFA World Cup 26 Regulations, May 2026](https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf):
  Article 12 covers the 48-team format, group stage, Round of 32, and knockout
  match graph; Article 13 covers equal-points and best-third tiebreakers; Annexe
  C contains the 495 third-place routing combinations.
- [FIFA groups and match-ups announcement](https://inside.fifa.com/organisation/news/groups-match-ups-revealed-game-changing-world-cup-2026):
  confirms that the final draw revealed 12 groups of four.
- [FIFA World Cup 2026 match schedule](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums?os=a):
  source for official fixtures, match numbers, venues, and bracket view.
- [FIFA/Coca-Cola Men's World Ranking](https://inside.fifa.com/fifa-world-ranking/men):
  source to update the `fifa_rank` fallback column when rankings change.
- [World Football Elo Ratings](https://www.eloratings.net/):
  a public reference for national-team Elo-style ratings. The current `elo`
  values in this repo are illustrative project inputs, not a dated export from
  this site.

## What You Get

- **A bracket-style heatmap** saved as `wc2026_bracket.png`, with one row per team
  and columns for Round of 32, Round of 16, quarterfinals, semifinals, final, and
  title.
- **A ranked probability table** saved as `wc2026_probabilities.csv`, sorted by
  title probability.

Both also display inside the notebook when you run it.

## Latest Results

A ready-made run lives in the [`results/`](results/) folder, so you can see the
output without running anything yourself. It was generated from a **100,000-run**
Monte Carlo (seed 42):

- [`results/README.md`](results/README.md) — a friendly, no-stats-needed writeup
  of what the run found and how to read it (start here).
- [`results/wc2026_bracket.png`](results/wc2026_bracket.png) — the bracket heatmap.
- [`results/wc2026_probabilities.csv`](results/wc2026_probabilities.csv) — the full
  ranked table for all 48 teams.


## How To Run It

### Google Colab

1. Open [Google Colab](https://colab.research.google.com/) and upload
   `WorldCup2026_MonteCarlo.ipynb`.
2. Upload the full `data/` folder, not just one file. The notebook needs both
   `data/teams.csv` and `data/annex_c.csv`.
3. Click **Runtime -> Run all**.

### Local Jupyter Or VS Code

Install the three external libraries (any recent release works; matplotlib must
be 3.5 or newer for the `RdYlGn` colormap used by the heatmap):

```bash
pip install numpy pandas matplotlib
```

Or install the pinned versions from the included file:

```bash
pip install -r requirements.txt
```

Then open `WorldCup2026_MonteCarlo.ipynb` and run the cells from top to bottom.
Keep the `data/` folder next to the notebook.

## The Main Knob

Near the top of the notebook is:

```python
N_RUNS = 10_000
```

That is how many full tournaments get simulated.

- `1_000` is quick but noisy.
- `10_000` is a reasonable default.
- `50_000+` is smoother but slower.

## Why Do I Get The Same Numbers Every Time?

If you run the simulation twice, you will see the exact same percentages both
times. That is on purpose. It is not a bug, and it does not mean the simulation
forgot to be random.

Here is the part that surprises people: **inside** the simulation, the tournament
is full of surprises. Across the thousands of replays, favorites lose on
penalties, underdogs go on deep runs, and big teams sometimes crash out early,
exactly like a real World Cup. All of that drama really is happening on every run.

So why do the final numbers come out the same each time? Because the computer's
"dice" are told to start from the same place on every run.

Think of it like a recording of someone rolling dice ten thousand times. The
rolls themselves are all over the place; that is the randomness. But if you play
that same recording again tomorrow, you see the same rolls in the same order, so
you land on the same totals. This project presses "play" on the same recording
every time. (The technical name for "start the dice from the same place" is a
*fixed random seed*, but you do not need that term to use the project.)

Why set it up this way?

- **Trust.** Anyone who runs the project gets the same answer, so the numbers in
  this README can be checked instead of taken on faith.
- **Fair comparisons.** If you change a team's `elo` and the numbers move, you
  know your change caused it, not a lucky or unlucky fresh roll of the dice.
- **A steady scoreboard.** The percentages already include all the upsets and
  surprises. Replaying with fresh dice would only nudge them by a few tenths of a
  percent, which does not tell you anything new about the teams.

In short: the unpredictability of football is already captured by replaying the
whole tournament thousands of times. Keeping the dice fixed just gives you a
clean, repeatable scoreboard instead of one that wiggles a little on every run.
If you want the numbers to settle down even more, the better move is to raise
`N_RUNS`, not to unfix the dice.

> **For the curious (optional, not needed for normal use):** inside
> `run_simulation`, the setting `seed=42` is what locks the dice. Changing that
> number gives a different but still repeatable set of runs; removing it makes the
> runs fresh and different every time. For everyday use, leave it as it is.

## Data Files

`data/teams.csv` has five columns:

| Column | Meaning |
|---|---|
| `team` | Team name |
| `elo` | Match-strength rating used by the simulator |
| `fifa_rank` | FIFA-ranking fallback for unresolved group-stage ties; not used to simulate match strength |
| `group` | Official 2026 group letter, A-L |
| `position` | Official draw slot, A1-L4 |

The distinction between `elo` and `fifa_rank` matters:

- `elo` is the only rating used to decide match win/draw/loss probabilities,
  goal-scoring averages, and penalty-shootout favorite status.
- `fifa_rank` is not used to make a team stronger or weaker in a match.
- `fifa_rank` only appears late in FIFA tiebreakers: after points,
  head-to-head criteria, goal difference, goals scored, and team conduct cannot
  separate teams.

So if you change only `fifa_rank`, most simulations will be unchanged unless a
group-stage or best-third-place tie falls all the way to the FIFA-ranking
tiebreaker. If you change `elo`, match probabilities change directly.

`data/annex_c.csv` is a machine-readable copy of FIFA Regulations Annexe C: the
495 possible mappings for the eight best third-placed teams into the Round of
32.

Why 495? There are 12 groups, and exactly eight third-placed teams qualify. The
set of qualifying third-place groups can therefore be any eight groups out of 12:
`C(12, 8) = 495`. Equivalently, four third-place teams miss out, and there are
`C(12, 4) = 495` possible sets of excluded groups. FIFA publishes a bracket
routing for every one of those possibilities.

The CSV columns are:

| Column | Meaning |
|---|---|
| `option` | FIFA Annexe C option number, 1-495 |
| `third_1A` | Which third-place group is assigned to the Round-of-32 slot against `1A` |
| `third_1B` | Which third-place group is assigned to the slot against `1B` |
| `third_1D` | Which third-place group is assigned to the slot against `1D` |
| `third_1E` | Which third-place group is assigned to the slot against `1E` |
| `third_1G` | Which third-place group is assigned to the slot against `1G` |
| `third_1I` | Which third-place group is assigned to the slot against `1I` |
| `third_1K` | Which third-place group is assigned to the slot against `1K` |
| `third_1L` | Which third-place group is assigned to the slot against `1L` |

For example, option 1 begins:

```csv
option,third_1A,third_1B,third_1D,third_1E,third_1G,third_1I,third_1K,third_1L
1,3E,3J,3I,3F,3H,3G,3L,3K
```

That means the third-placed team from Group E goes into the third-place slot
opposite `1A`, the third-placed team from Group J goes opposite `1B`, and so on.
The notebook determines which third-place groups qualified, selects the matching
Annexe C option, and then fills the official Round-of-32 bracket.

If you want to experiment, change the `elo` values. Keep exactly 48 teams and one
official slot from `A1` through `L4` unless you are intentionally changing the
tournament format code.

## How The Simulation Works

### Team Strength

Each team has an Elo-style rating. You do not need to know the history of Elo to
use the notebook; the short version is that a bigger rating means the team gets
more weight in each simulated match. Under the hood, the model turns the rating
gap into a no-draw win probability:

```text
P(A beats B) = 1 / (1 + 10^((Elo_B - Elo_A) / 400))
```

A 400-point Elo gap means the stronger team is about 10 times as likely to win a
non-drawn result.

The ratings in `teams.csv` are illustrative. The official field and groups are
real; the strength assumptions are editable.

The current `elo` values are rough, hand-entered placeholder ratings on an
Elo-like scale. They are not official FIFA numbers and they are not copied from a
specific dated World Football Elo Ratings snapshot. For a more serious run,
replace the `elo` column with a current source you trust, such as
[eloratings.net](https://www.eloratings.net/), and keep the rest of the CSV
structure unchanged.

### One Match

For each match, the simulator:

1. Converts the Elo gap into win/loss chances.
2. Reserves a draw share that starts near 27% for an even matchup and shrinks as
   the Elo gap grows (lopsided games rarely finish level).
3. Samples a scoreline from Poisson goal distributions, resampled so it agrees
   with the result.
4. In knockouts, resolves drawn outcomes by penalties, with the Elo favorite
   winning the shootout 55% of the time.

The result is drawn first; the scoreline is then sampled to be consistent with
it, so a simulated points result and its scoreline never disagree. Outcomes drive
standings, scorelines drive tiebreakers, and the two always match.

### Group Stage

The notebook uses the real 12 groups of four. Each group plays the official
position-pairing pattern from
[FIFA Regulations Article 12.4](https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf):
A1 vs A2, A3 vs A4, then the second and third matchday pairings, repeated for
every group.

When teams are tied on points, the simulator applies
[FIFA Regulations Article 13](https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf)
order:

1. Head-to-head points among the tied teams.
2. Head-to-head goal difference.
3. Head-to-head goals scored.
4. Re-apply those head-to-head rules to any still-tied subset.
5. Overall goal difference.
6. Overall goals scored.
7. Team conduct score.
8. FIFA ranking.

Cards are not modeled, so every team has a neutral conduct score of 0. Exact ties
therefore fall through to `fifa_rank`.

The top two teams in each group qualify. The 12 third-placed teams are ranked by
points, goal difference, goals scored, conduct score, then FIFA ranking; the best
eight also qualify.

### Knockout Stage

The Round of 32 uses the official FIFA match slots M73-M88 from
[FIFA Regulations Article 12.6](https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf).
Most slots are fixed, such as `2A` vs `2B` or `1F` vs `2C`. The third-place slots
depend on which eight third-placed groups qualify, so the notebook looks up the
correct Annexe C option in `data/annex_c.csv`.

The rest of the bracket follows the official match graph:

```text
M73-M88 -> M89-M96 -> M97-M100 -> M101-M102 -> M104
```

The third-place playoff is not simulated because this project only reports
progression to major milestones and the title.

## What This Is Not

- It is not a prediction of who will win.
- It does not model injuries, form, weather, red cards, home advantage, travel,
  tactical matchups, or squad selection.
- The Elo ratings are illustrative, not live official ratings.
- The `fifa_rank` values are only a late FIFA tiebreaker, not match-strength
  inputs.
- The scoreline is sampled to match the result; goals are still only a rough
  Poisson approximation, not a detailed scoring model.

Treat the output as: "given these ratings, this official draw, and this simplified
match model, here is how often each outcome occurs."

## Files

| File | Purpose |
|---|---|
| `WorldCup2026_MonteCarlo.ipynb` | Notebook to run |
| `data/teams.csv` | Official field/draw plus editable ratings |
| `data/annex_c.csv` | Official third-place routing table |
| `build_notebook.py` | Regenerates the notebook from source cells |
| `requirements.txt` | Pinned external library versions |
| `results/` | A saved 100,000-run output: heatmap, ranked CSV, and a beginner-friendly writeup |
