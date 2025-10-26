from src.cddbs.database import SessionLocal
from src.cddbs.pipeline.analyze import analyze_article
from src.cddbs.pipeline.digest import digest_content
from src.cddbs.pipeline.fetch import fetch_articles
from src.cddbs.pipeline.summarize import summarize_digest
from src.cddbs import models
from src.cddbs.pipeline.translate import translate_text


def run_pipeline(outlet: str, country: str):
    articles = fetch_articles(outlet, country)
    summaries = []
    session = SessionLocal()
    try:
        out = session.query(models.Outlet).filter(models.Outlet.name==outlet).one_or_none()
        if not out:
            out = models.Outlet(name=outlet, url=None)
            session.add(out)
            session.commit()

        for a in articles:
            analysis = analyze_article(a)
            digest = digest_content(a, analysis)
            translated = translate_text(str(digest))
            summary = summarize_digest(outlet, country, digest)
            summaries.append(summary)

            art = models.Article(
                outlet_id=out.id,
                title=a.get('title'),
                link=a.get('link'),
                snippet=a.get('snippet'),
                date=a.get('date'),
                meta=a.get('meta'),
                full_text=a.get('full_text')
            )
            session.add(art)

        report = models.Report(outlet=outlet, country=country,
                               final_report='\n\n'.join(summaries), data={})
        session.add(report)
        session.commit()
    finally:
        session.close()
    return {
        "outlet": outlet,
        "country": country,
        "articles": articles,
        "summaries": summaries,
        "final_report": '\n\n'.join(summaries)
    }
