"""Parameterized persistence and reporting queries for analysis cases/runs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .database import DatabaseUnavailable, session_scope


def _text(sql: str):
    try:
        from sqlalchemy import text
    except ModuleNotFoundError as exc:
        raise DatabaseUnavailable("SQLAlchemy is not installed. Install backend/requirements.txt.") from exc
    return text(sql)


def _json_text(sql: str):
    from sqlalchemy import JSON, bindparam
    return _text(sql).bindparams(bindparam("payload", type_=JSON))


def _decode_payload(value):
    return json.loads(value) if isinstance(value, (str, bytes)) else value


def _utc_dates(payload: dict) -> dict:
    # MySQL's UTC session returns naive datetime objects; label them so browsers
    # convert to local time rather than treating UTC as already-local time.
    return {key: value.replace(tzinfo=timezone.utc) if isinstance(value, datetime) and value.tzinfo is None else value
            for key, value in payload.items()}


def _case_payload(row: dict) -> dict:
    return _utc_dates({key: row[key] for key in ("case_id", "title", "idea_text", "status", "created_at", "updated_at")})


def create_case(title: str, idea_text: str, owner_user_id: str | None = None) -> dict:
    case_id = str(uuid4())
    with session_scope() as session:
        session.execute(_text("""
            INSERT INTO analysis_cases(case_id, owner_user_id, title, idea_text, status)
            VALUES (:case_id, :owner_user_id, :title, :idea_text, 'draft')
        """), {"case_id": case_id, "owner_user_id": owner_user_id, "title": title, "idea_text": idea_text})
        row = session.execute(_text("SELECT * FROM analysis_cases WHERE case_id=:case_id"), {"case_id": case_id}).mappings().one()
        return _case_payload(row)


def list_cases(limit: int = 50, offset: int = 0) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(_text("""
            SELECT case_id, title, idea_text, status, created_at, updated_at
            FROM analysis_cases ORDER BY updated_at DESC LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset}).mappings()
        cases = [_case_payload(row) for row in rows]
        by_id = {case["case_id"]: case for case in cases}
        for case in cases:
            case["runs"] = []
        runs = session.execute(_text("""
            SELECT r.run_id, r.case_id, r.query_id, r.gnn_mode, r.top_k,
                   r.run_status, r.started_at, r.completed_at
            FROM analysis_runs r JOIN (
                SELECT case_id FROM analysis_cases
                ORDER BY updated_at DESC LIMIT :limit OFFSET :offset
            ) selected ON selected.case_id=r.case_id
            ORDER BY r.started_at DESC, r.run_id DESC
        """), {"limit": limit, "offset": offset}).mappings()
        for run in runs:
            if run["case_id"] in by_id:
                by_id[run["case_id"]]["runs"].append(_utc_dates(dict(run)))
        return cases


def get_case(case_id: str) -> dict | None:
    with session_scope() as session:
        row = session.execute(_text("SELECT * FROM analysis_cases WHERE case_id=:case_id"), {"case_id": case_id}).mappings().first()
        if row is None:
            return None
        case = _case_payload(row)
        runs = session.execute(_text("""
            SELECT run_id, query_id, gnn_mode, top_k, run_status, started_at, completed_at
            FROM analysis_runs WHERE case_id=:case_id ORDER BY started_at DESC
        """), {"case_id": case_id}).mappings()
        case["runs"] = [_utc_dates(dict(item)) for item in runs]
        return case


def get_run(case_id: str, run_id: str) -> dict | None:
    """Restore an immutable run snapshot, not the browser's last local state."""
    with session_scope() as session:
        row = session.execute(_text("""
            SELECT r.*, c.title AS case_title, c.idea_text AS case_idea
            FROM analysis_runs r JOIN analysis_cases c ON c.case_id=r.case_id
            WHERE r.case_id=:case_id AND r.run_id=:run_id
        """), {"case_id": case_id, "run_id": run_id}).mappings().first()
        if row is None:
            return None
        pipeline = _decode_payload(row["pipeline_payload"])
        if pipeline is not None:
            pipeline = {**pipeline, "case_id": case_id, "run_id": run_id, "persistence_status": "persisted"}
        evaluation = session.execute(_text(
            "SELECT payload FROM evaluation_metrics WHERE run_id=:run_id"
        ), {"run_id": run_id}).scalar()
        evaluation = _decode_payload(evaluation)
        improvement = _decode_payload(row["improvement_payload"])
        for payload in (evaluation, improvement):
            if payload is not None:
                payload["persistence_status"] = "persisted"
        return {
            "case_id": case_id, "run_id": run_id, "case_title": row["case_title"],
            "idea_text": row["idea_text"] or row["case_idea"],
            "top_k": row["top_k"], "gnn_mode": row["gnn_mode"],
            "started_at": _utc_dates({"started_at": row["started_at"]})["started_at"], "pipeline_result": pipeline,
            "evaluation_result": evaluation, "improvement_result": improvement,
        }


def update_case(case_id: str, title: str | None, idea_text: str | None, status: str | None) -> dict | None:
    changes = {key: value for key, value in {"title": title, "idea_text": idea_text, "status": status}.items() if value is not None}
    if not changes:
        return get_case(case_id)
    assignments = ", ".join(f"{column}=:{column}" for column in changes)
    with session_scope() as session:
        result = session.execute(_text(f"UPDATE analysis_cases SET {assignments} WHERE case_id=:case_id"), {**changes, "case_id": case_id})
        if result.rowcount == 0:
            return None
    return get_case(case_id)


def delete_case(case_id: str) -> bool:
    with session_scope() as session:
        return session.execute(_text("DELETE FROM analysis_cases WHERE case_id=:case_id"), {"case_id": case_id}).rowcount > 0


def persist_pipeline_result(
    idea: str, top_k: int, gnn_mode: str, pipeline_result: dict, case_id: str | None = None, case_title: str | None = None,
) -> dict:
    """Persist a completed pipeline run and its result rows in one transaction."""
    with session_scope() as session:
        if case_id is None:
            case_id = str(uuid4())
            session.execute(_text("""
                INSERT INTO analysis_cases(case_id, title, idea_text, status)
                VALUES (:case_id, :title, :idea_text, 'active')
            """), {"case_id": case_id, "title": case_title or idea[:250], "idea_text": idea})
        else:
            exists = session.execute(_text("SELECT 1 FROM analysis_cases WHERE case_id=:case_id"), {"case_id": case_id}).first()
            if not exists:
                raise ValueError(f"Analysis case '{case_id}' does not exist.")

        run_id = str(uuid4())
        session.execute(_json_text("""
            INSERT INTO analysis_runs(run_id, case_id, query_id, idea_text, gnn_mode, top_k, run_status, completed_at, pipeline_payload)
            VALUES (:run_id, :case_id, :query_id, :idea, :gnn_mode, :top_k, 'completed', :completed_at, :payload)
        """), {
            "run_id": run_id, "case_id": case_id, "query_id": pipeline_result.get("query_id"),
            "idea": idea, "gnn_mode": gnn_mode, "top_k": top_k,
            "completed_at": datetime.now(timezone.utc).replace(tzinfo=None), "payload": pipeline_result,
        })
        for hit in pipeline_result.get("results", []):
            patent_id = hit.get("patent_id")
            if not patent_id:
                continue
            exists = session.execute(_text("SELECT 1 FROM patents WHERE patent_id=:patent_id"), {"patent_id": patent_id}).first()
            if not exists:
                continue
            session.execute(_text("""
                INSERT INTO run_patent_results(run_id, patent_id, rank_position, source, expansion_type,
                                               semantic_score, graph_score, combined_score, novelty_score)
                VALUES (:run_id, :patent_id, :rank_position, :source, :expansion_type,
                        :semantic_score, :graph_score, :combined_score, :novelty_score)
            """), {
                "run_id": run_id, "patent_id": patent_id, "rank_position": hit.get("rank", 1),
                "source": hit.get("source", "faiss"), "expansion_type": hit.get("expansion_type"),
                "semantic_score": hit.get("semantic_score"), "graph_score": hit.get("graph_score"),
                "combined_score": hit.get("combined_score"), "novelty_score": hit.get("novelty_score"),
            })
        session.execute(_text("""
            UPDATE analysis_cases SET status='active', updated_at=CURRENT_TIMESTAMP
            WHERE case_id=:case_id
        """), {"case_id": case_id})
        return {"case_id": case_id, "run_id": run_id, "persistence_status": "persisted"}


def persist_evaluation(run_id: str, evaluation: dict) -> None:
    with session_scope() as session:
        if session.execute(_text("SELECT 1 FROM analysis_runs WHERE run_id=:run_id"), {"run_id": run_id}).first() is None:
            raise ValueError("Analysis run does not exist.")
        session.execute(_json_text("""
            INSERT INTO evaluation_metrics(run_id, patentability_score, risk, verdict, payload)
            VALUES (:run_id, :score, :risk, :verdict, :payload)
            ON DUPLICATE KEY UPDATE patentability_score=VALUES(patentability_score), risk=VALUES(risk),
                                    verdict=VALUES(verdict), payload=VALUES(payload)
        """), {"run_id": run_id, "score": evaluation["patentability_score"], "risk": evaluation["risk"],
                 "verdict": evaluation["verdict"], "payload": evaluation})


def persist_improvements(run_id: str, improvement: dict) -> None:
    """Replace stored recommendation rows with the current agent output."""
    strategies = improvement.get("strategies", [])
    with session_scope() as session:
        exists = session.execute(_text("SELECT 1 FROM analysis_runs WHERE run_id=:run_id"), {"run_id": run_id}).first()
        if not exists:
            raise ValueError("Analysis run does not exist.")
        session.execute(_json_text("""
            UPDATE analysis_runs SET improvement_payload=:payload WHERE run_id=:run_id
        """), {"run_id": run_id, "payload": improvement})
        session.execute(_text("DELETE FROM improvement_recommendations WHERE run_id=:run_id"), {"run_id": run_id})
        for position, strategy in enumerate(strategies, start=1):
            session.execute(_text("""
                INSERT INTO improvement_recommendations(run_id, position, category, recommendation, rationale)
                VALUES (:run_id, :position, :category, :recommendation, :rationale)
            """), {
                "run_id": run_id, "position": position,
                "category": strategy.get("impact", "strategy"),
                "recommendation": strategy.get("strategy", ""), "rationale": strategy.get("reason"),
            })


def report_rows(report: str, limit: int = 20) -> list[dict]:
    queries = {
        "domain_year": "SELECT * FROM vw_domain_year_counts ORDER BY publication_year DESC, patent_count DESC LIMIT :limit",
        "top_assignees": """
            SELECT a.name AS assignee, COUNT(*) AS patent_count FROM patent_assignees pa
            JOIN assignees a ON a.assignee_id=pa.assignee_id GROUP BY a.assignee_id, a.name
            ORDER BY patent_count DESC LIMIT :limit
        """,
        "top_inventors": """
            SELECT i.name AS inventor, COUNT(*) AS patent_count FROM patent_inventors pi
            JOIN inventors i ON i.inventor_id=pi.inventor_id GROUP BY i.inventor_id, i.name
            ORDER BY patent_count DESC LIMIT :limit
        """,
        "cpc_distribution": "SELECT section, COUNT(*) AS patent_cpc_count FROM cpc_codes c JOIN patent_cpc_codes pc ON pc.cpc_code=c.cpc_code GROUP BY section ORDER BY patent_cpc_count DESC",
        "family_sizes": "SELECT patent_id, COUNT(*) AS family_size FROM patent_families GROUP BY patent_id HAVING COUNT(*) > 1 ORDER BY family_size DESC LIMIT :limit",
        "case_risk": "SELECT * FROM vw_case_risk_summary ORDER BY started_at DESC LIMIT :limit",
    }
    if report not in queries:
        raise ValueError(f"Unknown report '{report}'.")
    with session_scope() as session:
        return [dict(row) for row in session.execute(_text(queries[report]), {"limit": limit}).mappings()]
