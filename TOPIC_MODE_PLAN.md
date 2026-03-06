# Topic Mode — Research Brief & Implementation Plan

## 1. Research Brief: Topic-Centric Narrative Detection in Intelligence Practice

Modern OSINT and strategic communications analysts at bodies like the EU East StratCom Task Force, NATO StratCom COE, the US State Department GEC, and RAND's Information Environment team have converged on a key methodological insight: analyzing individual outlets in isolation produces a fragmented picture. The more powerful analytic frame is **topic-centric** — choosing a specific geopolitical event or claim, then mapping how different outlets diverge from neutral reference framing. This approach draws directly from the IOTA (Information Operations Threat Assessment) methodology, where the *baseline deviation score* — how far a source's framing drifts from established neutral coverage — is considered more analytically reliable than any single outlet's content score in isolation.

The operational rationale is **amplification detection**. Pro-Kremlin or other coordinated IO campaigns rarely manufacture entirely false stories; they amplify real events with selective framing, emotional loading, and missing context. EU East StratCom's EUvsDisinfo database documents that the same 5–7 core narratives (NATO aggression, Western hypocrisy, Ukrainian Nazism, etc.) appear across dozens of geographically and linguistically distinct outlets within hours of a triggering event — a signal that coordinated messaging infrastructure exists. The detection method is therefore: identify when outlets that have no editorial relationship nonetheless choose near-identical framing angles within a short temporal window on the same topic.

**Outlet clustering** is the third pillar. RAND's "Firehose of Falsehood" framework and NATO's Counter Disinformation Toolkit both recommend hierarchical clustering of outlets by narrative cosine similarity on a given topic, over a rolling time window. Outlets that cluster tightly around divergent-from-neutral framing, across topics they have no organic reason to track, are the highest-priority targets for further analysis. This is distinct from Outlet Mode (which characterises a single known-suspect outlet) — Topic Mode generates the suspect list itself, which is operationally more useful for early warning.

---

## 2. Architecture Decisions

### 2a. New Database Models (`src/cddbs/models.py`)

```python
class TopicRun(Base):
    __tablename__ = "topic_runs"
    id            = Column(Integer, primary_key=True, index=True)
    topic         = Column(String, nullable=False)         # e.g. "NATO expansion eastward"
    num_outlets   = Column(Integer, default=5)
    date_filter   = Column(String, default="m")
    status        = Column(String, default="pending")      # pending/running/completed/failed
    baseline_summary = Column(Text, nullable=True)         # Gemini neutral baseline text
    baseline_raw  = Column(Text, nullable=True)            # raw Gemini response
    created_at    = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at  = Column(DateTime, nullable=True)
    error         = Column(Text, nullable=True)
    outlet_results = relationship("TopicOutletResult", back_populates="topic_run")

class TopicOutletResult(Base):
    __tablename__ = "topic_outlet_results"
    id                   = Column(Integer, primary_key=True, index=True)
    topic_run_id         = Column(Integer, ForeignKey("topic_runs.id"), nullable=False)
    outlet_name          = Column(String, nullable=False)   # discovered domain
    outlet_domain        = Column(String, nullable=True)
    articles_analyzed    = Column(Integer, default=0)
    divergence_score     = Column(Integer, nullable=True)   # 0-100
    amplification_signal = Column(String, nullable=True)    # low/medium/high
    propaganda_techniques = Column(JSON, nullable=True)     # list of strings
    framing_summary      = Column(Text, nullable=True)
    gemini_raw           = Column(Text, nullable=True)
    article_links        = Column(JSON, nullable=True)      # [{title, url, date}]
    created_at           = Column(DateTime, default=lambda: datetime.now(UTC))
    topic_run = relationship("TopicRun", back_populates="outlet_results")
```

**Rationale**: One `TopicOutletResult` row per outlet (one-to-many) allows `ORDER BY divergence_score DESC` in SQL, per-outlet incremental updates, and independent inspectability. `article_links` is JSON rather than FK-linked rows because these are ephemeral discovery artefacts, not the primary analysis subjects. `init_db()` uses `Base.metadata.create_all` so new tables are created automatically — no migration needed.

### 2b. New API Endpoints (`src/cddbs/api/main.py`)

```
POST /topic-runs        → creates TopicRun, fires background task
GET  /topic-runs        → list all, ordered by created_at desc
GET  /topic-runs/{id}   → detail with outlet_results ordered by divergence_score desc
```

New Pydantic schemas: `TopicRunCreateRequest`, `TopicRunStatusResponse`, `TopicOutletResultResponse`, `TopicRunDetailResponse`.

### 2c. New Backend Pipeline (`src/cddbs/pipeline/topic_pipeline.py`)

```
run_topic_pipeline(topic_run_id, topic, num_outlets, date_filter, serpapi_key, google_api_key):

  Step 1 — Baseline fetch:
    For each of REFERENCE_OUTLETS = ["reuters.com", "bbc.com", "apnews.com", "afp.com"]:
      SerpAPI: q=f'"{topic}" site:{domain}', engine=google_news, tbs=qdr:{date_filter}, limit=3
    Concatenate into baseline_articles_data

  Step 2 — Baseline Gemini call:
    prompt = get_baseline_prompt(topic, baseline_articles_data)
    Parse: { baseline_summary, key_facts, neutral_framing }
    Update TopicRun.baseline_summary, status="running", commit

  Step 3 — Broad discovery:
    SerpAPI: q=topic (no site: filter), engine=google_news, tbs=qdr:{date_filter}, limit=40
    Extract domains, exclude REFERENCE_DOMAINS
    Rank by article frequency (= amplification proxy), take top num_outlets

  Step 4 — Per-outlet comparative analysis:
    For each discovered outlet:
      articles = SerpAPI q=f'"{topic}" site:{domain}', limit=5
      prompt = get_comparative_prompt(topic, baseline_summary, domain, articles_data)
      Parse: { divergence_score, amplification_signal, propaganda_techniques, framing_summary }
      Insert TopicOutletResult row, commit incrementally

  Step 5 — Finalize:
    TopicRun.status="completed", completed_at=now(), commit
```

### 2d. New Prompt Templates (`src/cddbs/pipeline/topic_prompt_templates.py`)

- `get_baseline_prompt(topic, articles_data)` → JSON: `{ baseline_summary, key_facts, neutral_framing }`
- `get_comparative_prompt(topic, baseline_summary, outlet_domain, articles_data)` → JSON: `{ divergence_score, amplification_signal, propaganda_techniques, framing_summary, divergence_explanation }`

Both include the same STRICT RULES block as `prompt_templates.py` (no invented claims, attribute statements, neutral language).

### 2e. Frontend Changes

**`api.ts`** — add `CreateTopicRunPayload`, `TopicRunStatus`, `TopicOutletResult`, `TopicRunDetail` interfaces and `createTopicRun()`, `fetchTopicRuns()`, `fetchTopicRun()` functions.

**`NewAnalysisDialog.tsx`** — add `ToggleButtonGroup` ("Outlet" / "Topic") at the top. Topic form: single Topic text field + num_outlets number input + Time Period (reused). On submit, calls `createTopicRun()` vs `createAnalysisRun()` based on mode.

**New `TopicRunsTable.tsx`** — mirrors `RunsTable.tsx`. Columns: Topic | Outlets Found | Status | Created | Actions.

**New `TopicRunDetail.tsx`** — shows baseline reference box + outlet cards ranked by divergence score, each with a score bar, amplification chip (colour-coded), propaganda techniques chips, framing summary, article links. Auto-polls while status is "running".

**`App.tsx`** — add `"topic-runs"` to `ViewType`, sidebar nav item (`TravelExploreIcon`), topic runs query, and rendering logic.

---

## 3. Step-by-Step Implementation Order

| Step | What | Depends on |
|------|------|-----------|
| 1 | Add `TopicRun` + `TopicOutletResult` ORM models | — |
| 2 | `topic_prompt_templates.py` | — |
| 3 | `topic_pipeline.py` | 1, 2 |
| 4 | API endpoints in `main.py` | 1, 3 |
| 5 | `api.ts` additions | — |
| 6 | `NewAnalysisDialog` mode toggle | 5 |
| 7 | `TopicRunsTable.tsx` | 5 |
| 8 | `TopicRunDetail.tsx` | 5 |
| 9 | `App.tsx` integration | 6, 7, 8 |
| 10 | End-to-end smoke test | all |

---

## 4. Key Design Decisions

- **Baseline as a single separate Gemini call**: computed once, stored in `TopicRun.baseline_summary`, passed as text to each comparative prompt. Avoids sending the full reference corpus 5–10 times (context + cost).
- **Discovery via article frequency, not an outlet registry**: domain extraction from the broad SerpAPI sweep + Python frequency count. Top-N most-appearing non-reference domains = highest amplification candidates. No new external service needed.
- **Incremental DB commits per outlet**: each `TopicOutletResult` is committed as it's produced. The UI can poll and show partial results as the pipeline runs.
- **Mode toggle in existing dialog**: keeps "New Analysis" as the single entry point; no second AppBar button. The `onCreated` callback in `App.tsx` switches between refreshing the outlet runs list or the topic runs list based on which mode was used.
- **`article_links` as JSON, not FK rows**: topic discovery articles are transient artefacts. Storing as JSON avoids bloating the `articles` table and keeps `TopicOutletResult` self-contained.
