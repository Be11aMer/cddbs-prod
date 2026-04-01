# Phase 4: Disinformation Network Graph + ML Predictions

> **Status**: TODO — Requires further refinement and brainstorming  
> **Prerequisites**: Phases 1-3 must be completed. 3-6 months of accumulated analysis data needed for ML.  
> **Last updated**: 2026-03-31

---

## Vision

Build a living graph of actors, outlets, narratives, and their relationships over time.
Eventually use ML to detect coordinated campaigns and predict upcoming disinformation events.

This phase has three sub-phases that should be built incrementally.

---

## 4A: Source Credibility Index (Short-term)

**Goal**: Automatically track per-domain credibility using data already produced by Phases 1-3.

**Zero API cost** — computed entirely from existing data in the database:

| Metric | Source | Computation |
|--------|--------|-------------|
| `avg_propaganda_score` | SitReps & framing analyses | Rolling average of AI-assigned scores per domain |
| `framing_divergence` | Framing analysis | How often a source diverges from consensus |
| `coordination_count` | Framing analysis | How often a source appears in coordination indicators |
| `burst_participation` | Burst detection | How often a source appears during narrative bursts |
| `reliability_trend` | All above | Is the source getting more or less reliable over time? |

### New DB Model: `SourceCredibility`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `source_domain` | String UNIQUE | e.g. "rt.com" |
| `total_articles` | Integer | Total articles seen from this domain |
| `avg_propaganda_score` | Float | Rolling average (0.0-1.0) |
| `framing_divergence_score` | Float | How often this source diverges from consensus (0.0-1.0) |
| `coordination_count` | Integer | Times flagged in coordination indicators |
| `burst_participation_count` | Integer | Times appeared during narrative bursts |
| `reliability_index` | Float | Composite credibility score (0.0-1.0, lower = less credible) |
| `trend_direction` | String | "improving" / "stable" / "degrading" |
| `last_computed_at` | DateTime | |
| `created_at` | DateTime | |

### Implementation Notes

- Scheduled recomputation: daily or after every SitRep cycle
- Alert mechanism: if a previously reputable source (`reliability_index > 0.7`) drops below `0.4`, flag it as "potentially compromised" or "shifting editorial stance"
- Feed this into the existing Outlet Network Graph

---

## 4B: Disinformation Network Graph (Medium-term)

**Goal**: Enhance the existing `OutletNetworkGraph.tsx` to show the full disinformation ecosystem.

### Graph Node Types

| Node Type | Visual | Data Source |
|-----------|--------|-------------|
| Source/Outlet | Blue circle, sized by article volume | `raw_articles` + `SourceCredibility` |
| Narrative | Amber circle, sized by match count | `NarrativeMatch` + `known_narratives.json` |
| State Actor | Red diamond, linked to outlets | Manual curation + AI detection |
| Event | Green square, sized by article count | `EventCluster` |

### Graph Edge Types

| Edge | Weight | Meaning |
|------|--------|---------|
| Source → Narrative | propaganda_score avg | This source amplifies this narrative |
| Source → Source | coordination signals | These sources are behaviorally linked |
| Source → Event | article count | This source covered this event |
| State Actor → Source | TBD | This actor controls/influences this source |

### UI Features

- **Temporal slider**: Show how the network evolves over weeks/months
- **Cluster highlighting**: Click a narrative node to see all sources that amplify it
- **Community detection visualization**: Color-coded groups of coordinated sources
- **Filter by**: time range, event type, narrative category, risk level

### Technical Considerations

- Graph layout: force-directed (existing) or hierarchical for state actor relationships
- Performance: for large graphs, consider server-side layout computation
- Data aggregation: pre-compute graph data on the backend, serve via `/stats/disinformation-network`

---

## 4C: ML Predictions (Long-term)

**Goal**: Use accumulated data to predict and detect coordinated disinformation campaigns.

### Prerequisites

- Minimum 3-6 months of continuous data collection
- Sufficient SitRep and framing analysis outputs
- Twitter/Telegram integration (for social media correlation)

### ML Models to Explore

#### 1. Time-Series Anomaly Detection
- **Input**: Daily `reliability_index` per source domain
- **Method**: ARIMA, Prophet, or simple z-score on rolling windows
- **Output**: Alert when a trusted source starts degrading unexpectedly
- **Library**: `statsmodels` or `prophet` (both lightweight)

#### 2. Narrative Lifecycle Prediction
- **Input**: Burst patterns (z-scores over time), article counts per narrative keyword
- **Method**: Regression on time-series features (peak timing, growth rate, decay rate)
- **Output**: Predicted peak date, predicted total reach, predicted lifespan
- **Use case**: "This narrative about X is trending — based on past patterns, it will peak in ~3 days"

#### 3. Coordinated Campaign Detection
- **Input**: Source-narrative bipartite graph, temporal publication patterns
- **Method**: Graph-based community detection (Louvain algorithm, Label Propagation)
- **Output**: Groups of sources that behave in suspiciously coordinated ways
- **Library**: `networkx` (already a lightweight dependency)
- **Indicators**:
  - Multiple sources publishing within the same narrow time window
  - Identical or near-identical phrasing across sources
  - Sources sharing the same set of unusual narratives

#### 4. Social Media Amplification Chain Detection (Requires Twitter/Telegram)
- **Input**: Social media posts + timing + content similarity to media articles
- **Method**: Diffusion chain reconstruction (who published first → who amplified)
- **Output**: Amplification chains: e.g. "RT.com published → @account_A tweeted within 10min → Telegram channel forwarded within 30min"
- **Value**: Proves state-sponsored outlets are using social media accounts for coordinated amplification

### Open Questions for Future Refinement

1. **Which ML framework?** Keep it lightweight (scikit-learn + networkx) or invest in PyTorch for more complex models?
2. **Training data**: Do we need labeled examples of known coordinated campaigns? Where to source them? (EU DisinfoLab reports, Stanford Internet Observatory datasets)
3. **Real-time vs. batch**: Should ML predictions run in real-time (per article) or in batch (daily)?
4. **Explainability**: How to present ML predictions to analysts in a trustworthy way? (Confidence intervals, feature importance, similar past cases)
5. **Integration with Phases 1-3**: Should ML predictions feed back into risk scores and SitReps?

---

## Resource Considerations

Phase 4A and 4B are **zero API cost** — they only use local computation on existing data.

Phase 4C ML models are also local (scikit-learn, networkx, statsmodels) — no cloud ML services needed.

The main cost is **developer time** and **data accumulation patience**.

---

## References & Inspiration

- [EU DisinfoLab](https://www.disinfo.eu/) — methodology for coordinated inauthentic behavior detection
- [Stanford Internet Observatory](https://cyber.fsi.stanford.edu/io) — academic research on influence operations
- [Bellingcat](https://www.bellingcat.com/) — open-source investigation techniques
- [GDELT Project](https://www.gdeltproject.org/) — global event database methodology
- [Louvain Algorithm](https://en.wikipedia.org/wiki/Louvain_method) — community detection in graphs
