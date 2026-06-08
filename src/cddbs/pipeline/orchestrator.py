import json
from datetime import datetime, UTC
from src.cddbs.config import settings
from src.cddbs.database import SessionLocal
from src.cddbs.pipeline.fetch import fetch_articles
from src.cddbs import models
from src.cddbs.utils.genai_client import call_gemini
from src.cddbs.pipeline.prompt_templates import get_consolidated_prompt
from src.cddbs.quality import score_briefing
from src.cddbs.narratives import match_narratives_from_report
from src.cddbs.pipeline.output_validator import validate_analysis_output
from src.cddbs.utils.input_sanitizer import sanitize_text
from src.cddbs.utils.logger import get_logger

logger = get_logger(__name__)

# Length caps for externally-sourced article fields before prompt interpolation
_MAX_ARTICLE_TITLE_LENGTH = 500
_MAX_ARTICLE_TEXT_LENGTH = 6000


def run_pipeline(
    outlet: str,
    country: str,
    report_id: int = None,
    num_articles: int = None,
    url: str = None,
    serpapi_key: str = None,
    google_api_key: str = None,
    date_filter: str = "m"
):
    logger.info(f"run_pipeline started outlet={outlet} country={country} report_id={report_id} num_articles={num_articles} url={url} date_filter={date_filter}")
    articles = fetch_articles(outlet, country, num_articles=num_articles, url=url, api_key=serpapi_key, time_period=date_filter)
    logger.info(f"fetch_articles returned {len(articles)} articles outlet={outlet}")

    session = SessionLocal()
    try:
        out = session.query(models.Outlet).filter(models.Outlet.name == outlet).one_or_none()
        if not out:
            logger.info(f"Creating new outlet for {outlet}")
            out = models.Outlet(name=outlet, url=None)
            session.add(out)
            session.flush() # Get outlet id

        # Build batch prompt
        # Article title/snippet/full_text originate from external outlets (SerpAPI) and
        # are untrusted — sanitise and structurally fence them before prompt interpolation
        # to defend against embedded prompt-injection payloads (OWASP LLM01).
        articles_data = ""
        for i, a in enumerate(articles):
            safe_title = sanitize_text(a.get('title') or '', _MAX_ARTICLE_TITLE_LENGTH)
            safe_text = sanitize_text(a.get('full_text') or a.get('snippet') or '', _MAX_ARTICLE_TEXT_LENGTH)
            articles_data += f"--- Article {i+1} ---\n"
            articles_data += "[BEGIN UNTRUSTED ARTICLE DATA]\n"
            articles_data += f"Title: {safe_title}\n"
            articles_data += f"Link: {a.get('link')}\n"
            articles_data += f"Text: {safe_text}\n"
            articles_data += "[END UNTRUSTED ARTICLE DATA]\n\n"

        if not articles_data:
            logger.warning(f"No articles data to send to Gemini outlet={outlet} country={country}")
            articles_data = "No articles found for this search."

        prompt = get_consolidated_prompt(outlet, country, articles_data, date_filter=date_filter)

        # Single Gemini call
        logger.info(f"Calling Gemini outlet={outlet} country={country}")
        raw_response = call_gemini(prompt, api_key=google_api_key)
        logger.info(f"Gemini raw response length={len(raw_response)} outlet={outlet}")

        # Try to parse JSON from response
        try:
            import re

            # 1. Try to find content within markdown code blocks (```json ... ``` or ``` ... ```)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)

            if json_match:
                clean_response = json_match.group(1).strip()
            else:
                # 2. If no code blocks, try to find the first '{' and last '}'
                json_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
                if json_match:
                    clean_response = json_match.group(1).strip()
                else:
                    # 3. Fallback to just stripping the whole thing
                    clean_response = raw_response.strip()

            payload = json.loads(clean_response)
        except Exception as e:
            logger.warning(f"JSON parsing failed outlet={outlet}: {e}. Falling back to raw_response.")
            payload = {"individual_analyses": [], "final_briefing": raw_response}

        final_report = payload.get("final_briefing", raw_response)
        individual_analyses = {idx: analysis for idx, analysis in enumerate(payload.get("individual_analyses", []))}

        # Get or create report
        report = None
        if report_id:
            logger.debug(f"Looking up report report_id={report_id}")
            report = session.query(models.Report).filter(models.Report.id == report_id).first()
            if report:
                logger.debug(f"Found report report_id={report_id}")
            else:
                logger.warning(f"Report report_id={report_id} not found in this session")

        if not report:
            logger.info(f"Creating new report outlet={outlet} country={country} (no report_id provided or not found)")
            report = models.Report(outlet=outlet, country=country)
            session.add(report)
            session.flush() # Get report id

        # --- Output validation (H-2) ---
        validation = validate_analysis_output(payload)
        analysis_status = "completed" if validation.is_valid else "partial"
        validation_warnings = (validation.errors + validation.warnings) or None
        if not validation.is_valid:
            logger.warning(f"Output validation failed report_id={report.id}: {validation.errors}")
        elif validation.warnings:
            logger.info(f"Output validation warnings report_id={report.id}: {validation.warnings}")

        report.analysis_status = analysis_status
        report.final_report = final_report
        report.raw_response = raw_response

        # Preserve existing data and update specific fields
        current_data = report.data or {}
        report.data = {
            **current_data,
            "articles_analyzed": len(articles),
            "parsing_successful": "individual_analyses" in payload,
            "url": url or current_data.get("url"),
            "status": "completed",
            "analysis_date": datetime.now(UTC).isoformat(),
            "structured_briefing": payload.get("structured_briefing"),
            "analysis_status": analysis_status,
        }

        # Update outlet URL if provided and not already set
        if url and not out.url:
            out.url = url

        # Persist articles
        logger.info(f"Persisting {len(articles)} articles report_id={report.id}")
        for i, a in enumerate(articles):
            analysis = individual_analyses.get(i, {})

            art = models.Article(
                outlet_id=out.id,
                report_id=report.id,
                title=a.get('title'),
                link=a.get('link'),
                snippet=a.get('snippet'),
                date=a.get('date'),
                meta={
                    **(a.get('meta') if isinstance(a.get('meta'), dict) else {}),
                    "analysis": analysis
                },
                full_text=a.get('full_text')
            )
            session.add(art)

        # --- Sprint 4: Quality Scoring ---
        logger.debug(f"Running quality scoring report_id={report.id}")
        quality_scorecard = None
        try:
            quality_scorecard = score_briefing(payload)
            logger.info(
                f"Quality score report_id={report.id}: "
                f"{quality_scorecard['total_score']}/{quality_scorecard['max_score']} ({quality_scorecard['rating']})"
            )

            briefing = models.Briefing(
                report_id=report.id,
                briefing_json=payload,
                quality_score=quality_scorecard["total_score"],
                quality_rating=quality_scorecard["rating"],
                quality_details=quality_scorecard,
                prompt_version="v1.3",
                model_version=settings.GEMINI_MODEL,
                validation_warnings=validation_warnings,
            )
            session.add(briefing)
        except Exception as e:
            logger.warning(f"Quality scoring failed (non-fatal) report_id={report.id}: {e}")

        # --- Sprint 4: Narrative Matching ---
        logger.debug(f"Running narrative matching report_id={report.id}")
        try:
            narrative_matches = match_narratives_from_report(
                report_text=final_report or raw_response,
                articles=articles,
            )
            logger.info(f"Found {len(narrative_matches)} narrative matches report_id={report.id}")

            for nm in narrative_matches:
                match_row = models.NarrativeMatch(
                    report_id=report.id,
                    narrative_id=nm["narrative_id"],
                    narrative_name=nm["narrative_name"],
                    category=nm.get("category", ""),
                    confidence=nm.get("confidence", "low"),
                    matched_keywords=nm.get("matched_keywords", []),
                    match_count=nm.get("match_count", 0),
                )
                session.add(match_row)
        except Exception as e:
            logger.warning(f"Narrative matching failed (non-fatal) report_id={report.id}: {e}")

        # Update report data with quality and narrative info
        report.data = {
            **report.data,
            "quality_score": quality_scorecard["total_score"] if quality_scorecard else None,
            "quality_rating": quality_scorecard["rating"] if quality_scorecard else None,
            "narrative_matches_count": len(narrative_matches) if 'narrative_matches' in dir() else 0,
        }

        session.commit()
        logger.info(f"session.commit() done report_id={report.id}")
        session.refresh(report)

        return {
            "report_id": report.id,
            "outlet": outlet,
            "country": country,
            "articles": articles,
            "final_report": final_report,
            "raw_response": raw_response,
            "quality_score": quality_scorecard,
        }
    except Exception as e:
        logger.error(f"run_pipeline error outlet={outlet} country={country} report_id={report_id}: {e}", exc_info=True)
        session.rollback()
        raise e
    finally:
        session.close()
