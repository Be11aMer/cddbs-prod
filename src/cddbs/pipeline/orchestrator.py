import json
from datetime import datetime, UTC
from src.cddbs.database import SessionLocal
from src.cddbs.pipeline.fetch import fetch_articles
from src.cddbs import models
from src.cddbs.utils.genai_client import call_gemini
from src.cddbs.pipeline.prompt_templates import get_consolidated_prompt


def run_pipeline(
    outlet: str, 
    country: str, 
    report_id: int = None, 
    num_articles: int = None, 
    url: str = None,
    serpapi_key: str = None,
    google_api_key: str = None
):
    print(f"DEBUG: run_pipeline started for outlet={outlet}, country={country}, report_id={report_id}, num_articles={num_articles}, url={url}")
    articles = fetch_articles(outlet, country, num_articles=num_articles, url=url, api_key=serpapi_key)
    print(f"DEBUG: fetch_articles returned {len(articles)} articles")
    
    session = SessionLocal()
    try:
        out = session.query(models.Outlet).filter(models.Outlet.name == outlet).one_or_none()
        if not out:
            print(f"DEBUG: Creating new outlet for {outlet}")
            out = models.Outlet(name=outlet, url=None)
            session.add(out)
            session.flush() # Get outlet id

        # Build batch prompt
        articles_data = ""
        for i, a in enumerate(articles):
            articles_data += f"--- Article {i+1} ---\n"
            articles_data += f"Title: {a.get('title')}\n"
            articles_data += f"Link: {a.get('link')}\n"
            articles_data += f"Text: {a.get('full_text') or a.get('snippet') or ''}\n\n"

        if not articles_data:
            print("DEBUG: No articles data to send to Gemini")
            articles_data = "No articles found for this search."

        prompt = get_consolidated_prompt(outlet, country, articles_data)
        
        # Single Gemini call
        print("DEBUG: Calling Gemini...")
        raw_response = call_gemini(prompt, api_key=google_api_key)
        print(f"DEBUG: Gemini raw response length: {len(raw_response)}")
        
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
            print(f"DEBUG: JSON parsing failed: {e}. Final fallback to raw_response.")
            payload = {"individual_analyses": [], "final_briefing": raw_response}

        final_report = payload.get("final_briefing", raw_response)
        individual_analyses = {idx: analysis for idx, analysis in enumerate(payload.get("individual_analyses", []))}

        # Get or create report
        report = None
        if report_id:
            print(f"DEBUG: Looking for report with id={report_id}")
            report = session.query(models.Report).filter(models.Report.id == report_id).first()
            if report:
                print(f"DEBUG: Found report {report_id}")
            else:
                print(f"DEBUG: Report {report_id} NOT found in this session")

        if not report:
            print("DEBUG: Creating new report because no report_id provided or not found")
            report = models.Report(outlet=outlet, country=country)
            session.add(report)
            session.flush() # Get report id

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
        }
        
        # Update outlet URL if provided and not already set
        if url and not out.url:
            out.url = url

        # Persist articles
        print(f"DEBUG: Persisting {len(articles)} articles for report {report.id}")
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

        session.commit()
        print(f"DEBUG: session.commit() done for report id={report.id}")
        session.refresh(report)
        
        return {
            "report_id": report.id,
            "outlet": outlet,
            "country": country,
            "articles": articles,
            "final_report": final_report,
            "raw_response": raw_response
        }
    except Exception as e:
        print(f"DEBUG: run_pipeline ERROR: {e}")
        session.rollback()
        raise e
    finally:
        session.close()
