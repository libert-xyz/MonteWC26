# 2026tmap World Cup, simulation

Nobody knows who's going to win the 2026 World Cup. This project doesn't either. What it *can* do is play the whole tournament out over and over — ten thousand times by default — and then tell you how often each team ended up winning, reaching the final, getting knocked out early, and so on.

If a team lifts the trophy in 1,900 out of 10,000 simulated tournaments, we say it has about a 19% chance. That's the whole idea. You'll end up with a colorful chart (heatmap) and a table showing every team's odds of reaching each stage.

It's meant to be something you can read, run, and tinker with — not a crystal ball.

## What is "Monte Carlo"?

It's named after the casino town, and the connection is exactly what you'd guess: it's the same logic as rolling dice a bunch of times to see what comes up most.

Say you want to know your odds of rolling a 7 with two dice. You could do the math, or you could just roll them a few thousand times and count. Roll enough times and the count gets really close to the true answer.

That's all we're doing here, except instead of dice we "roll" entire tournaments. One simulated World Cup is basically one roll. It doesn't tell you much on its own — maybe the favorite has a bad day and goes out in the group stage. But run it ten thousand times and add randomnes, leaving you with the patterns that actually hold up.

The dice aren't fair, and that's the point. Stronger teams are more likely to win their matches (more on how we measure "stronger" below).

## What you get when you run it

Two main things:

- **A bracket-style heatmap.** Every team gets a row. Each column is a milestone — making the Round of 32, the Round of 16, quarterfinals, semis, the final, and winning it all. Each box shows the percentage, colored green (likely) to red (long shot). It saves as `wc2026_bracket.png`.
- **A ranked table** of all 48 teams sorted by their chance of winning, saved as `wc2026_probabilities.csv` so you can open it in Excel or Google Sheets.

Both also show up right inside the notebook as you run it.

## How to run it

You don't need to install anything fancy. Pick whichever of these fits you.

### The easy way: Google Colab

If you've never run Python before, this is the path of least resistance — it runs in your browser, nothing to install.

1. Go to [Google Colab](https://colab.research.google.com/) and upload `WorldCup2026_MonteCarlo.ipynb`.
2. Upload the team data too: in the Files panel on the left, make a folder called `data` and put `teams.csv` inside it. (This is the one slightly fiddly step — Colab doesn't automatically have the file, so you have to hand it over.)
3. Click **Runtime → Run all**, and wait a minute or two.

### On your own computer (Jupyter or VS Code)

If you've got Python set up locally:

1. Make sure the three libraries it uses are installed:
   ```
   pip install numpy pandas matplotlib
   ```
2. Open `WorldCup2026_MonteCarlo.ipynb` in Jupyter or VS Code.
3. Run the cells from top to bottom.

Just keep the `data/` folder sitting next to the notebook and it'll find the team ratings on its own. If it can't find the file, it'll stop and tell you exactly what went wrong — no cryptic errors.

## The one knob worth knowing about

Near the top there's a setting called `N_RUNS`. It's how many times the tournament gets replayed, and it's set to 10,000.

Here's the trade-off, in plain terms:

- **Turn it down (say, 1,000)** and it finishes in seconds — but the numbers get jumpy. Run it twice and a team's odds might wobble by a point or two.
- **Leave it at 10,000** and you get steady, trustworthy numbers in a reasonable amount of time. Good default.
- **Crank it way up (100,000+)** and the numbers barely move between runs, but you'll be waiting a few minutes.

If you're just poking around, drop it to 1,000 so you're not waiting. Bump it back up when you want a clean final result. Anywhere from 10,000 to 50,000 is the sweet spot for most people.

## Want to change the teams?

Open `data/teams.csv`. It's just two columns — the team name and its rating — and you can edit it in any spreadsheet app. Change a number, add a team, drop one you don't like. The simulation reads whatever's in that file, so you don't have to touch any code. That separation is on purpose: the data lives in one place, the logic in another.

## How the simulation actually works

This is the part most people are curious about, so let's walk through it from the ground up — how we measure how good a team is, then the action from a single match all the way to the trophy.

### Measuring team strength: Elo (and why not the FIFA rankings)

Every team carries one number called its **Elo rating**. Higher means stronger. Elo was invented to rank chess players and has since spread across sports because of one genuinely handy property: the *gap* between two ratings tells you, directly, how likely one side is to beat the other.

There's a clean little formula for it:

```
P(A beats B) = 1 / (1 + 10^((Elo_B − Elo_A) / 400))
```

The thing to take away is the "400" rule of thumb: a team rated **400 points higher than its opponent wins about 10 times as often.** A small gap is close to a coin flip; a big gap is a mismatch.

So why Elo instead of the official FIFA world rankings? Honestly, because they're built for different jobs. The FIFA rankings exist to *rank and seed* teams — to decide who goes in which pot for the draw. They hand you an order and a points total, but no agreed way to turn "Team A is 60 FIFA points ahead" into "Team A has a 64% chance to win." Elo was designed from the start to answer exactly that question, which is precisely what a simulation needs on every single match.

A few other things make Elo a comfortable fit:

- **It reacts to real results.** Elo updates after every match based on who you beat, by how much, and how surprising it was. The FIFA formula can lag, and it's sensitive to *which* games a team chooses to schedule.
- **It's transparent and free.** The method is public (see eloratings.net), so the numbers are reproducible rather than a black box.
- **It speaks in probabilities.** That's the whole currency of this project.

Same honest caveat as before: the ratings in `data/teams.csv` are reasonable stand-ins, not the official live numbers. Swap in better ones and you'll get better answers.

### A single match

Everything is built on simulating one match between two teams. Here's what happens under the hood, with a real example — Argentina (rated 2140) against the USA (rated 1770):

1. **Decide the result.** Put the gap into the formula and Argentina come out around 89% to win a non-drawn game. The model then sets aside about **27% for a draw** (roughly how often international matches end level) and splits the rest by strength. For this game that lands near **Argentina 65% / draw 27% / USA 8%.** The computer rolls a random number and reads off the result. Most of the time Argentina win — but not always, and that 8% is how upsets sneak in.
2. **Roll a scoreline.** Separately, each team gets a goal count drawn at random, with the stronger side tipped to score more — here Argentina average about 2.4 goals, the USA about 0.6. A typical roll might come out **Argentina 2, USA 0.** (In the group stage the win/draw/loss decides the points; the scoreline is mostly there to break ties in the table.)
3. **If it's a knockout game and the result was a draw,** it goes to a penalty shootout. The favorite wins it 55% of the time — better than a coin flip, but a long way from a sure thing.

That's the whole engine. Stack thousands of these on top of each other and you've got a tournament.

### The group stage

The 48 teams are split into 12 groups of four. Inside each group everyone plays everyone once — three matches each — and you collect the usual **3 points for a win, 1 for a draw, 0 for a loss.** A finished group might look like this:

| Team | Pld | W | D | L | GF | GA | GD | Pts |
|---|----|---|---|---|----|----|----|-----|
| Spain | 3 | 3 | 0 | 0 | 6 | 0 | +6 | 9 |
| Mexico | 3 | 2 | 0 | 1 | 4 | 2 | +2 | 6 |
| Iran | 3 | 1 | 0 | 2 | 2 | 4 | −2 | 3 |
| Iraq | 3 | 0 | 0 | 3 | 0 | 6 | −6 | 0 |

The **top two of every group go through** — here, Spain and Mexico. When teams are level on points, the model breaks the tie the same way FIFA does, in this order: goal difference, then goals scored, then the result of the match between the tied teams, and if it's *still* deadlocked, a coin flip (a "drawing of lots").

The 2026 format adds one twist: finishing third isn't automatically the end. After every group is done, the **eight best third-placed teams** (compared across groups by points, then goal difference, then goals) also squeak through. So Iran above isn't necessarily out — it depends how the other third-place teams did. Add it up — 24 group winners and runners-up, plus 8 third-placed teams — and **32 teams** move on to the knockouts.

### The knockout rounds

From here it's win-or-go-home. The 32 survivors are slotted into a bracket arranged so the strongest teams can't meet until late, and each round cuts the field in half:

**Round of 32 → Round of 16 → Quarterfinals → Semifinals → Final**

The only new rule is that a knockout game can't end in a draw — if it's level, it goes to penalties. And penalties are where the bracket gets interesting. Picture a Round of 16 tie between Brazil (2020) and Croatia (1880). Brazil are favorites, so if it ends 1–1 they'd win the shootout 55% of the time. But 45% is real, and in this particular simulated run Croatia hold their nerve and knock Brazil out. Run the tournament again and Brazil probably go through. That back-and-forth across thousands of runs is exactly what we're measuring.

### The final

The final is just one more knockout match — but it's the one the whole project is really counting. Whoever wins it is logged as the champion of that simulated tournament; the loser is recorded as having "reached the Final."

Then comes the payoff. After all 10,000 runs, you simply count: if Argentina lifted the trophy in 1,900 of them, that's a **19% chance of winning the World Cup.** Do that for every team and you've got the "Win Title" column in the table and the far-right stripe of the bracket chart. The same counting works for every milestone — a team that reaches the semis in 3,300 of the 10,000 runs has a 33% chance of making the semifinals.

## What this is *not*

Worth being upfront about this, because it's easy to read too much into a number like "19%."

- **It's not a prediction of who'll win.** It's a "given these ratings and these rules, here's how the odds shake out" machine. Reality has injuries, red cards, weather, a striker's hot streak, a manager's bad night — none of that is in here.
- **The ratings are illustrative, not official.** They're reasonable ballpark numbers for a plausible 48-team field, not the real, current, authoritative Elo ratings. If you want better answers, feed it better numbers (see above). Garbage in, garbage out — good stuff in, better stuff out.
- **The matchups aren't the real draw.** Until the actual groups are set, the project sorts teams into balanced groups based on strength. So treat the specific bracket as a plausible example, not the official schedule.
- **It's a simplified model.** A few corners are cut on purpose to keep things readable — for instance, a match's result and its scoreline are rolled separately, so once in a while they don't perfectly line up. It's a learning tool first.
- **There's no home advantage, no form, no head-to-head history** beyond what the ratings already capture.

Think of it as a thoughtful guess with the math shown — not a forecast you'd bet the house on.

## What's in the folder

| File | What it's for |
|---|---|
| `WorldCup2026_MonteCarlo.ipynb` | The notebook you actually run. Start here. |
| `data/teams.csv` | The team names and their ratings. Edit this to change the field. |
| `build_notebook.py` | A helper script that generates the notebook. You don't need it to run anything — it's just how the notebook was built, kept around in case you want to regenerate or tweak it. |

## A note before you go

If you've never run a simulation before, this is a friendly place to start. Open the notebook, read the explanations between the code (they're written for someone who isn't a statistician), run it, then go change a rating in the CSV and watch the odds shift. That little loop — change something, re-run, see what happens — is the fun part, and honestly the best way to get a feel for how this stuff works.
