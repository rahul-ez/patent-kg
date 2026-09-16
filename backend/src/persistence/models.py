"""SQLAlchemy 2.0 mapping of the normalized MySQL schema.

The SQL files in database/sql are the portable, reviewable schema source. These
models support application persistence and intentionally mirror that schema.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index,
    Integer, MetaData, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Domain(Base):
    __tablename__ = "domains"
    domain_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Patent(Base, Timestamped):
    __tablename__ = "patents"
    patent_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer)
    legal_status: Mapped[Optional[str]] = mapped_column(String(50))
    cited_by_patent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(2048))
    domain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("domains.domain_id"))
    __table_args__ = (
        CheckConstraint("publication_year IS NULL OR publication_year BETWEEN 1800 AND 2200", name="publication_year"),
        CheckConstraint("cited_by_patent_count >= 0", name="citation_count"),
        Index("ix_patents_year_domain", "publication_year", "domain_id"),
    )


class Assignee(Base):
    __tablename__ = "assignees"
    assignee_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)


class Inventor(Base):
    __tablename__ = "inventors"
    inventor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)


class CPCCode(Base):
    __tablename__ = "cpc_codes"
    cpc_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    section: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)


class NPLReference(Base):
    __tablename__ = "npl_references"
    npl_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class PatentAssignee(Base):
    __tablename__ = "patent_assignees"
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), primary_key=True)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("assignees.assignee_id"), primary_key=True)


class PatentInventor(Base):
    __tablename__ = "patent_inventors"
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), primary_key=True)
    inventor_id: Mapped[int] = mapped_column(ForeignKey("inventors.inventor_id"), primary_key=True)


class PatentCPC(Base):
    __tablename__ = "patent_cpc_codes"
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), primary_key=True)
    cpc_code: Mapped[str] = mapped_column(ForeignKey("cpc_codes.cpc_code"), primary_key=True)


class PatentNPL(Base):
    __tablename__ = "patent_npl_references"
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), primary_key=True)
    npl_id: Mapped[int] = mapped_column(ForeignKey("npl_references.npl_id"), primary_key=True)


class PatentFamily(Base):
    __tablename__ = "patent_families"
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), primary_key=True)
    related_patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    __table_args__ = (CheckConstraint("patent_id <> related_patent_id", name="distinct_members"),)


class CitationSnapshot(Base, Timestamped):
    __tablename__ = "citation_snapshots"
    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id", ondelete="CASCADE"), nullable=False)
    cited_by_count: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    __table_args__ = (UniqueConstraint("patent_id", "observed_on"), CheckConstraint("cited_by_count >= 0", name="nonnegative"))


class User(Base, Timestamped):
    __tablename__ = "app_users"
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Role(Base):
    __tablename__ = "roles"
    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.user_id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)


class AnalysisCase(Base, Timestamped):
    __tablename__ = "analysis_cases"
    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("app_users.user_id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    idea_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    __table_args__ = (CheckConstraint("status IN ('draft','active','archived')", name="valid_status"),)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("analysis_cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    query_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    gnn_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    run_status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    pipeline_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    __table_args__ = (CheckConstraint("top_k BETWEEN 1 AND 100", name="top_k_range"),)


class RunPatentResult(Base):
    __tablename__ = "run_patent_results"
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True)
    patent_id: Mapped[str] = mapped_column(ForeignKey("patents.patent_id"), primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    expansion_type: Mapped[Optional[str]] = mapped_column(String(32))
    semantic_score: Mapped[Optional[float]] = mapped_column(Float)
    graph_score: Mapped[Optional[float]] = mapped_column(Float)
    combined_score: Mapped[Optional[float]] = mapped_column(Float)
    novelty_score: Mapped[Optional[float]] = mapped_column(Float)
    __table_args__ = (UniqueConstraint("run_id", "rank"), CheckConstraint("rank > 0", name="positive_rank"))


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"
    metric_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), unique=True, nullable=False)
    patentability_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    verdict: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class ImprovementRecommendation(Base):
    __tablename__ = "improvement_recommendations"
    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("run_id", "position"), CheckConstraint("position > 0", name="positive_position"))
