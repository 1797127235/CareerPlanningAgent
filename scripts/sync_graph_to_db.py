"""
Sync data/graph.json nodes and edges into the job_nodes, job_edges, job_scores tables.

Replaces old pipeline-based DB import.
Idempotent: can be run multiple times safely (upserts).

Usage:
    python -m scripts.sync_graph_to_db
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from backend.db import engine, SessionLocal, Base
from backend.models import JobNode, JobEdge, JobScore

GRAPH_PATH = PROJECT_ROOT / "data" / "graph.json"


def sync_nodes(session, nodes: list[dict]) -> int:
    """Upsert graph nodes into job_nodes table."""
    count = 0
    for n in nodes:
        nid = n["node_id"]
        existing = session.query(JobNode).filter_by(node_id=nid).first()
        if existing:
            # Update existing
            existing.label = n.get("label", nid)
            existing.role_family = n.get("role_family", "other")
            existing.salary_p50 = n.get("salary_p50")
            existing.must_skills = n.get("must_skills", [])
            existing.core_tasks = n.get("core_tasks", [])
        else:
            # Insert via raw SQL to fill legacy NOT NULL columns
            # that the ORM model no longer defines
            session.execute(
                text("""
                    INSERT INTO job_nodes (
                        node_id, label, role_family, salary_p50,
                        must_skills, core_tasks,
                        community_id, community_label,
                        soft_skills, certificates, top_cities, top_industries,
                        soft_skill_weights, ai_velocity, physical_tag,
                        collab_level_required, collab_tools, collab_weeks_to_next,
                        human_tasks
                    ) VALUES (
                        :nid, :label, :family, :salary,
                        :skills, :tasks,
                        0, :family,
                        '[]', '[]', '[]', '["互联网"]',
                        '{}', 5, 0,
                        3, '[]', 6,
                        '[]'
                    )
                """),
                {
                    "nid": nid,
                    "label": n.get("label", nid),
                    "family": n.get("role_family", "other"),
                    "salary": n.get("salary_p50"),
                    "skills": json.dumps(n.get("must_skills", []), ensure_ascii=False),
                    "tasks": json.dumps(n.get("core_tasks", []), ensure_ascii=False),
                },
            )
        count += 1
    return count


def sync_edges(session, edges: list[dict]) -> int:
    """Upsert graph edges into job_edges table."""
    # Clear old edges and rewrite (edges are cheap and change with graph rebuilds)
    session.query(JobEdge).delete()
    count = 0
    for e in edges:
        edge = JobEdge(
            source_id=e["source"],
            target_id=e["target"],
            edge_type=e.get("edge_type", "related"),
            difficulty=e.get("difficulty", "中"),
        )
        session.add(edge)
        count += 1
    return count


def sync_scores(session, nodes: list[dict]) -> int:
    """Upsert terrain scores into job_scores table."""
    count = 0
    for n in nodes:
        nid = n["node_id"]
        existing = session.query(JobScore).filter_by(node_id=nid).first()
        rp = n.get("replacement_pressure", 50)
        hal = n.get("human_ai_leverage", 50)
        zone = n.get("zone", "transition")

        if existing:
            existing.replacement_pressure = rp
            existing.human_ai_leverage = hal
            existing.zone = zone
        else:
            score = JobScore(
                node_id=nid,
                replacement_pressure=rp,
                human_ai_leverage=hal,
                zone=zone,
            )
            session.add(score)
        count += 1
    return count


def main():
    if not GRAPH_PATH.exists():
        print(f"[ERROR] {GRAPH_PATH} not found")
        sys.exit(1)

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["edges"]

    print(f"Graph: {len(nodes)} nodes, {len(edges)} edges")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        n_nodes = sync_nodes(session, nodes)
        n_edges = sync_edges(session, edges)
        n_scores = sync_scores(session, nodes)
        session.commit()
        print(f"Synced: {n_nodes} nodes, {n_edges} edges, {n_scores} scores")

        # Clear stale job_scores and node intros (new node IDs won't match old rows)
        current_node_ids = {n["node_id"] for n in nodes}
        stale_scores = session.query(JobScore).filter(
            JobScore.node_id.notin_(current_node_ids)
        ).count()
        if stale_scores:
            session.query(JobScore).filter(
                JobScore.node_id.notin_(current_node_ids)
            ).delete(synchronize_session=False)
            session.commit()
            print(f"Cleared {stale_scores} stale job_scores")

        from backend.models import JobNodeIntro
        stale = session.query(JobNodeIntro).count()
        if stale:
            session.query(JobNodeIntro).delete()
            session.commit()
            print(f"Cleared {stale} stale node intros (will regenerate on demand)")

    except Exception as e:
        session.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        session.close()

    print("Done.")


if __name__ == "__main__":
    main()
