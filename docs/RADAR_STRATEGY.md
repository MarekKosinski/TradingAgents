# Opportunity Radar — Strategy & Architecture

> A "radar" for finding high-upside trades early: sentiment-driven squeezes,
> ticker-confusion plays, and fundamentally-grounded thematic megatrends —
> then validating them with the existing TradingAgents deep-DD engine.
>
> Status: **strategy/planning** (no code yet). Captures decisions from the
> design discussion so we don't lose context.

---

## 1. Problem statement

Today's market is driven as much by sentiment/narrative as by fundamentals.
Profitable setups observed by hand:

- **LFVN** — short squeeze: high short interest, low borrow availability, company
  buying back shares. Verified the mechanics, bought calls, profited.
- **SPCE** — ticker-confusion: incoming **SPCX** IPO; retail confused the two,
  ran SPCE +200%.
- **"Materials will become crucial"** — a *solid* (not pump-and-dump) thematic
  thesis; the basket ran.
- **"Memory stocks will go up"** — same: a fundamentally-grounded sector pump.

The goal is a **systematic radar** that surfaces these *early*, filters out traps,
and ranks the best expression — instead of manually browsing Reddit.

### Core architectural insight

TradingAgents is a **"given a ticker, analyze it deeply"** engine (Reddit,
StockTwits, short-squeeze, options, fundamentals — all keyed *by ticker*).
The radar is the **inverse**: a **discovery + triage funnel** that finds *which*
tickers/themes to look at, then feeds survivors into the existing DD engine.

```
DISCOVERY  ->  TRIAGE / SCORE  ->  VERIFY (existing DD)  ->  DECIDE + SIZE + LOG
(wide net)     (rank by signal)    (mechanics/thesis)        (exit rules, feedback)
```

### Two engines (different signal shapes)

| | **Tactical engine** | **Thematic engine** |
|---|---|---|
| Unit | a **ticker** | a **theme → basket** |
| Driver | positioning + reflexivity | real supply/demand imbalance |
| Signal | mention **velocity/acceleration** | thesis **spread + fundamental confirmation** |
| Hold | days–weeks | months–quarters |
| Examples | LFVN, SPCE | materials, memory |
| Killer | dilution, IV crush, late entry | theme already priced in / mainstream |

Both share one data backbone and both funnel into the same deep-DD agents.

---

## 2. Strategy options

### Tactical engine

**A — Social mention-velocity radar.** Extract ticker mentions from social
streams; alert on **acceleration off a low baseline** (z-score / 5–10× 7-day
avg), not absolute volume. The 2nd derivative front-runs price.
- *Pros:* catches LFVN/SPCE-type moves; cheap; reuses existing scrapers.
- *Cons:* noisy; needs a history store; often **late** (you become exit liquidity).

**B — Squeeze-mechanics screener (quant-first).** Start from float/short data;
screen for the LFVN profile (high SI %, high days-to-cover, low borrow
availability / high fee, recent buyback, low float); *then* check social.
- *Pros:* fundamentally grounded, fewer hype traps; catches setups *before* trend.
- *Cons:* high-SI can stay shorted for years; borrow data is paywalled.

**C — Event / ticker-confusion radar. _(PARKED — too rare.)_** Monitor IPO/SPAC
calendars, ticker changes, name/symbol collisions (SPCE↔SPCX); flag misdirected
chatter. High asymmetry (200%+) but events are infrequent and unwind violently,
so not worth systematizing now. Revisit case-by-case by hand. Kept here for
record only.

### Thematic engine

**E — Theme detector (transcript phrase-emergence).** Track keyword/phrase
frequency **QoQ across the earnings-transcript corpus + news**; rising phrases
cited by *multiple unrelated companies* = a real theme forming bottom-up.
Validate with a supply/demand checklist, map the value chain to a basket.
- *Pros:* catches "memory/materials" early; documented institutional method;
  transcript-sentiment alpha is real (see §4).
- *Cons:* needs a paid transcript feed; slower; requires value-chain mapping.

### Positioning / smart-money engines

**F — Options-flow / unusual-activity radar.** Two modes:
- **Confirmation (reuse, free):** on candidates, run the existing
  `options_squeeze_tools.py` — `get_unusual_options_activity` (volume ≫ OI, sweeps),
  `get_put_call_ratio` (directional bias), `get_iv_analysis` (**IV-crush risk before
  buying premium**). Near-strike call-OI buildup → **gamma-squeeze** potential,
  complementing engine B. Belongs in the **VERIFY** stage.
- **Discovery (new):** market-wide scan for unusual call/put volume, sweeps, and
  near-dated OTM call buildup → candidate tickers *independent of social*. Needs a
  market-wide flow feed (Unusual Whales); per-ticker yfinance can't scan the market.
- *Pros:* leading positioning tell; strongest as **confluence** with social velocity
  + squeeze mechanics; IV check directly de-risks option entries.
- *Cons:* flow is ambiguous (hedge vs spread leg vs closing vs directional; can't
  always tell opening/closing) → a **weight in the stack, not a standalone trigger**;
  market-wide flow needs a paid feed.

**G — Insider & political trading radar.** Two modes (discovery *and* confirmation):
- **Insider (Form 4, free EDGAR):** **cluster buying** by multiple insiders is a
  strong pre-move signal; as a trigger *or* as a "are insiders buying too?" confirm.
- **Political / congressional (free STOCK Act disclosures; Quiver / Capitol Trades):**
  members/staff sometimes trade ahead of policy, contracts, or sector tailwinds;
  cluster buys are a tell and pair well with the thematic engine.
- *Pros:* free/cheap, leading, under-watched, strong **de-risking** ("is smart money
  buying alongside the hype?").
- *Cons:* **disclosure lag** — Form 4 ~2 business days (fast-ish); congressional
  filings up to ~30–45 days (**laggy → thematic confirmation, not a fast trigger**).
  Sells are noisy (many reasons to sell); small samples; correlation ≠ causation.

### Recommended: **D — Hybrid funnel**

Run **B** as always-on universe filter, **A** as the trigger, and **E** as the
thematic track (C is parked). Layer **F** (options flow) and **G** (insider/political)
as **confluence overlays** — they don't trigger alone but sharply raise conviction
when they coincide. A small-cap lighting up on **social velocity AND options flow AND
squeeze mechanics AND insider/politician buys**, with dilution clear, is the highest-
conviction setup (the LFVN profile with a positioning tell on top). Everything that
passes triage gets the full multi-agent DD.

---

## 3. Build vs. buy (don't reinvent the wheel)

Research finding: most of the funnel is **commoditized** — consume APIs, don't
rebuild scrapers. The genuinely unserved niche is **small-cap-granular theme
detection**.

| Layer | Decision | Tooling |
|---|---|---|
| Reddit/StockTwits discovery (mainstream subs) | **Buy/poll** | ApeWisdom public API (free), Quiver |
| Mention **velocity/acceleration** | **Build** | our SQLite history + scoring (the differentiation) |
| Feeder-venue discovery (Discord/X/niche subs) | **Build _only if pursued_** | official APIs (X, Discord), not HTML scraping |
| Short-squeeze mechanics | **Buy** | Ortex / Fintel (Short Squeeze Score 0–100) behind existing tool |
| Real borrow availability/fee | **Buy** | IBKR API (real-time shortable shares + fee) if you have an account |
| Earnings transcripts | **Buy** | **FMP** (transcripts + fundamentals + filings in one) → recommended start |
| Theme detection | **Build (proven recipe)** | keyword-freq QoQ across corpus (BlackRock/AlphaSense method); FinBERT |
| Options confirmation (per-ticker) | **Reuse** | existing `options_squeeze_tools.py` (unusual activity, P/C, IV) |
| Options flow (market-wide discovery) | **Buy** | Unusual Whales (flow, sweeps, dark pool) |
| Deep DD on survivors | **Reuse** | existing TradingAgents agents |
| Dilution / insider screens | **Build** | SEC EDGAR full-text + Form 4 (free) |
| Political / congressional trades | **Buy/consume** | Quiver / Capitol Trades / free STOCK Act disclosures |
| Bot / coordination scoring | **Build _(nice-to-have)_** | raw Reddit author-level via `reddit.py`, on candidates only |

**Custom scrapers — decision.** Do **not** build a general WSB scraper; it
reinvents a commoditized wheel. ApeWisdom already streams mainstream subs, counts
indirect mentions, and dedupes per-user/day. We get our velocity/novelty edge by
**polling ApeWisdom on a schedule and storing snapshots** (poll-and-store ≠
scraping) to build the time series they don't keep. The **only** custom collection
worth the maintenance is **feeder venues ApeWisdom doesn't cover** (Discord/Telegram/
X cashtags, niche/ticker-specific subs) — and even there prefer **official APIs**
over HTML scraping. The repo's existing `reddit.py`/`stocktwits.py` are lightweight
per-ticker fetchers — keep them for the **VERIFY** stage, not discovery.

**Existing trackers' method (reference):** stream comments → extract direct +
indirect mentions → **dedupe per-user/day** (anti-bot) → rank by 24h mentions →
refresh 5–15 min. They expose absolute counts + crude rank delta; **none expose
proper acceleration off a per-ticker baseline or gate by mechanics** → our opening.

**Transcript feed pick:** start with **FMP** (~$20–80/mo) — collapses transcripts,
fundamentals, ratios, and SEC filings into one API. Add EarningsCall.biz later for
clean speaker-segmented Q&A if needed.

### Bot / coordination scoring _(nice-to-have)_

Feeds the pump-and-dump screen (§4/§5): estimate how much of a ticker's chatter is
**manufactured vs organic**, used as a *de-risking filter* on conviction — not proof.

**Not possible from ApeWisdom alone** — it returns only per-ticker aggregates
(mentions, upvotes, rank, sentiment) and already dedupes per-user/day, so the
author-level distribution needed for bot detection isn't exposed. Requires pulling
**raw Reddit** (existing `reddit.py` JSON endpoints) for the **candidate tickers
ApeWisdom already flagged** — targeted, per-ticker, not a firehose.

Heuristics, strongest/cheapest first:
1. **Author concentration** — 500 mentions from 20 accounts vs 400 (unique-author
   ratio / author-Gini). Best single signal.
2. **Account age & karma** — spike driven by new, low-karma accounts.
3. **Account-creation clustering** — many participants created the same week.
4. **Text similarity / copypasta** — near-duplicate bodies across posters.
5. **Posting cadence** — regular-interval or burst/off-hours rhythm.
6. **Default-username pattern** — auto-generated `word-word-1234` handles.
7. **Cross-sub copy-paste** — same content seeded across subs simultaneously.

**Free cross-check (no extra data):** compare ApeWisdom's per-user/day-deduped count
vs the **raw** mention count from our own fetch. Raw ≫ deduped ⇒ few accounts posting
repeatedly ⇒ inflation flag.

**Limits:** catches *crude* pumps only; aged/high-karma sockpuppets pass every check.
Astroturf via Discord/Telegram never appears in Reddit author data. Mind Reddit API
rate limits (fine for a few candidates).

---

## 4. Where the biggest gains are

Ranked by edge, with the supporting evidence:

1. **Structural: micro/small-cap, under-followed names.** Funds physically can't
   take meaningful positions in illiquid sub-$1B names without moving them — **you
   can**. This is the single most durable edge. LFVN and squeeze setups live here.
   *Fish where the whales can't.*
2. **Trap-avoidance (negative screens).** Post-GME research: meme strategies show
   **positive short-term, negative long-term alpha** → avoiding losers ≈ the whole
   game. Highest-ROI screens:
   - **Dilution kill-switch** (EDGAR S-3/424B5/ATM): a company that can print
     shares caps your squeeze. Almost no retail checks this.
   - **Pump-and-dump structure** (coordinated new/low-karma accounts, copypasta).
3. **Thematic value-chain lead-lag.** When company A guides up on a driver, its
   suppliers/customers often **haven't repriced yet** — trade the laggard. The
   transcript corpus builds the map.
4. **Transcript-sentiment alpha (documented).** ExtractAlpha/FactSet transcripts
   model: long-short US ~**13.7% annual, 2.57 Sharpe** (2006–2024). Worth paying for.
5. **Speed of synthesis.** An LLM reading every transcript + filing + DD in minutes
   is a real retail-scale superpower — this is what the project *is*.
6. **Earliness via feeders.** Smaller venues (r/pennystocks, r/shortsqueeze,
   StockTwits, Discord, X) lead r/wallstreetbets by hours. Trigger on the *upstream*
   spike + **first-appearance/novelty**, not the already-ranked top-10.
7. **Free leading signals to stack:** insider-buying clusters (Form 4),
   government contract awards (USAspending.gov), earnings-revision breadth,
   Google Trends / app downloads / web traffic, congressional + 13F clustering.
8. **Positioning confluence (engines F + G).** Options flow (smart-money call
   buying / gamma buildup) + insider/politician buys are *independent* confirmations
   of a social/squeeze setup. Their value is in the **overlap**: hype + positioning
   together is far higher-conviction than either alone.

**Edge principle:** no single signal beats the market anymore. **The *product* of
many weak, independent signals does** — sentiment velocity × mechanics × insider
buys × revision breadth × dilution-clear × right lifecycle stage. Then concentrate
where you're structurally unbeatable: **small, fast, under-followed names with a
real catalyst.**

---

## 5. Where the major problems are

### Signal / market risks
- **You're the exit liquidity.** By the time something ranks on WSB, early entrants
  are selling. The radar's only job is to put you *earlier + faster* with a
  disciplined exit.
- **Edge decay / survivorship bias.** LFVN/SPCE worked; you don't see the dozens
  that fizzled. Predictability largely died post-GME. Backtest honestly (see §6).
- **Late entry + IV crush.** Trending names already have elevated IV → you buy
  expensive premium and get crushed even when directionally right. Prefer shares or
  spreads; size down when IV is blown out.
- **Theme already priced in.** A *new thematic ETF launching* for the theme is
  usually a late/distribution (sell) tell, not a buy. Track narrative lifecycle:
  `niche → DD spreads → retail → CNBC/ETF → exhaustion`.

### Data risks
- **Short interest lag** (FINRA bi-weekly, ~1–2 wk delay) — "high SI" may already be
  covered. Borrow availability/fee is paywalled.
- **Bot/astroturf contamination** of mention counts; ticker-extraction false
  positives (`DD`, `CEO`, `YOLO`, `OPEN`) → need `$`-prefix + context words + stop-list.
- **Dilution risk** silently kills squeezes — must be screened, not assumed.
- **Point-in-time data** is the hard part for backtesting (see §6).

### Execution / behavioral risks
- **Discipline gap.** Long-term-negative-alpha means **exit rules ARE the alpha**.
  Bake stops/targets/time-stops + sizing into the tool, not willpower.
- **Complexity rot.** A dead scraper looks identical to "no signal." Need health
  checks/alerting on every data source.

### Legal / ethical
- Detecting pumps is fine; **do not amplify or participate** in manipulation.
- This tooling is for **screening/decision support**, not personalized buy/sell
  advice.

---

## 6. Can we backtest this?

**Yes — partially, and carefully.** Some layers are cleanly backtestable; others
(real-time social velocity) are hard without historical capture. Plan:

### What's backtestable now
- **Thematic / transcript signals (engine E):** strongest candidate. Transcripts,
  fundamentals, and prices are historical and **timestamped** → reconstruct
  "phrase frequency QoQ" as-of each date and test forward basket returns. Academic
  precedent + open-source replications exist.
- **Mechanics screens (engine B):** historical short interest, float, and price are
  available → test "high-SI + low-float + buyback" forward returns. *Caveat:* borrow
  availability/fee history is paywalled (Ortex/Fintel) — may need to proxy.
- **Insider / contract / revision signals:** Form 4, USAspending, estimate
  revisions are historical → standard event-study backtests.

### What's hard to backtest
- **Real-time social velocity (engine A):** ApeWisdom/StockTwits give *current*
  snapshots, not deep history. Options:
  1. **Start capturing now** — stand up the collector first, accumulate our own
     time series, backtest in a few months (forward test).
  2. **Buy historical** social datasets (Quiver, Context Analytics) where available.
  3. **Reddit archives** (Pushshift-style dumps) to reconstruct mention history —
     coverage/quality varies.

### Methodology (avoid fooling ourselves)
- **Point-in-time / as-of data only** — no using restated fundamentals or revised
  SI. Look-ahead bias is the #1 way these backtests lie.
- **Survivorship-free universe** — include delisted/dead tickers (meme stocks die).
- **Realistic costs** — slippage, spread, borrow cost, **options IV/theta**, and
  **small-cap liquidity caps** (can you actually fill the size?).
- **Walk-forward / out-of-sample**, not a single in-sample fit.
- **Regime awareness** — split pre/post-GME; report by regime.
- **Honest metrics** — hit rate, avg win/loss, max drawdown, Sharpe, *and*
  capacity (at what AUM does the edge vanish?).

### Proposed backtest harness (incremental)
1. **Outcome logger first** — every radar alert → entry/exit/outcome in SQLite.
   This is the cheapest path: live **forward test** that also calibrates which
   signals pay, and prunes the rest. Compounds forever.
2. **Historical thematic backtest** on FMP transcripts + prices (engine E).
3. **Historical mechanics backtest** on SI/float/price (engine B).
4. **Stand up the social collector** now so engine A becomes backtestable later.

---

## 7. Recommended build order (edge-per-effort)

1. **EDGAR dilution/shelf + Form 4 insider screen** — free data, huge
   trap-avoidance value, nobody does it; slots into the existing squeeze analyst.
2. **Social collector + acceleration/novelty scoring** over *feeder* subs (ApeWisdom
   + StockTwits) → also unlocks future backtesting of engine A.
3. **FMP-fed theme detector** — phrase-emergence QoQ → value-chain basket.
4. **Positioning confirmations (engines F + G)** — wire existing per-ticker options
   tools into VERIFY; add Form 4 insider + congressional (Quiver/Capitol Trades)
   checks. Cheap, high de-risking value.
5. **Automated thesis-verification DD** — reuse existing agents to confirm the
   mechanical/thematic claim and rank best expression.
6. **Outcome-logging feedback loop** — self-calibration + forward test.
7. **Market-wide options-flow discovery (engine F)** — only if paying for Unusual Whales.
8. **Backtest harness** for engines E and B once data plumbing exists.

---

## 8. Open decisions

- [ ] Transcript feed: confirm **FMP** vs EarningsCall.biz (budget, Q&A segmentation needs).
- [ ] Borrow data: pay for **Ortex/Fintel**, or use **IBKR API** (need account)?
- [ ] Social history: capture-from-now vs buy historical (Quiver/Pushshift)?
- [ ] First build target: dilution/insider screen (rec.) vs theme detector?
- [ ] Options flow: pay for **Unusual Whales** (market-wide discovery), or
      reuse per-ticker options tools as confirmation-only for now?
- [ ] Political trades: **Quiver** API vs free Capitol Trades / STOCK Act scraping?
- [ ] Risk rules: define default exit/stop/sizing policy to encode.

---

## Appendix — key sources

- ApeWisdom (free Reddit mention API) · SwaggyStocks · Tradestie
- Ortex / Fintel — short interest, CTB, utilization, Short Squeeze Score
- FMP / EarningsCall.biz / API Ninjas — transcript feeds
- ExtractAlpha & FactSet — Transcripts Model (13.7% / 2.57 Sharpe, 2006–2024)
- BlackRock "Tomorrow's Themes, Today" — thematic alpha methodology
- AlphaSense — QoQ mention-change theme extraction
- Academic: WSB return predictability largely eliminated post-GME; positive
  short-term / negative long-term alpha (Review of Financial Studies; GameStop study)
- SEC EDGAR (S-3/424B5/ATM, Form 4 ~2 biz-day lag) · USAspending.gov — free signals
- Quiver Quantitative / Capitol Trades — congressional trades (STOCK Act, ~30–45d lag)
- Unusual Whales / Quiver Quantitative — options flow + social/alt-data APIs
