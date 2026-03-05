#!/usr/bin/env python3
"""
Projection Rebuild CLI — Replays all events from the EventStore and
deterministically rebuilds every projection table.

Usage:
    python -m app.social_platform.tools.replay_social_system
    python app/social_platform/tools/replay_social_system.py
"""
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import text

from app.social_platform.models.base import engine, SessionLocal
from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.projection_engine import ProjectionEngine

PROJECTION_TABLES = [
    "posts",
    "comments",
    "threads",
    "reaction_summary",
    "feed_index",
    "trust_profiles",
    "delegations",
    "knowledge_artifacts",
    "governance_proposals",
]


def wipe_projection_tables(session):
    wiped = []
    for table_name in PROJECTION_TABLES:
        try:
            result = session.execute(text(f"SELECT to_regclass('{table_name}')"))
            exists = result.scalar()
            if exists:
                session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                wiped.append(table_name)
        except Exception as exc:
            print(f"  [SKIP] {table_name}: {exc}")
    session.commit()
    return wiped


def run_replay():
    print("=" * 60)
    print("PROJECTION REBUILD — Social Civic Infrastructure Engine")
    print("=" * 60)
    print()

    start_time = time.time()

    session = SessionLocal()
    event_store = EventStore(session=session)
    projection_engine = ProjectionEngine(event_store)

    print("[1/4] Wiping projection tables...")
    wiped = wipe_projection_tables(session)
    if wiped:
        for t in wiped:
            print(f"  TRUNCATED: {t}")
    else:
        print("  No projection tables found to wipe.")
    print()

    print("[2/4] Loading events from EventStore...")
    events = event_store.replay_events()
    total_events = len(events)
    print(f"  Found {total_events} events.")
    print()

    if total_events == 0:
        elapsed = time.time() - start_time
        print("[3/4] No events to replay.")
        print()
        print(f"[4/4] Complete in {elapsed:.2f}s")
        print()
        _print_summary(0, wiped, elapsed)
        session.close()
        return {"events_processed": 0, "projections_rebuilt": wiped, "elapsed_seconds": elapsed}

    print("[3/4] Replaying events through ProjectionEngine...")
    processed = 0
    domains_seen = set()
    event_types_seen = set()

    for event in events:
        projection_engine.process_event(event)
        processed += 1
        domains_seen.add(event.domain)
        event_types_seen.add(event.event_type)

        if processed % 100 == 0:
            print(f"  Processed {processed}/{total_events} events...")

    print(f"  Processed {processed}/{total_events} events.")
    print()

    elapsed = time.time() - start_time

    print(f"[4/4] Complete in {elapsed:.2f}s")
    print()

    _print_summary(processed, wiped, elapsed, domains_seen, event_types_seen)

    session.close()
    return {
        "events_processed": processed,
        "projections_rebuilt": wiped,
        "elapsed_seconds": round(elapsed, 3),
        "domains": sorted(domains_seen),
        "event_types": sorted(event_types_seen),
    }


def _print_summary(processed, wiped, elapsed, domains=None, event_types=None):
    print("-" * 60)
    print("REPLAY SUMMARY")
    print("-" * 60)
    print(f"  Events processed:     {processed}")
    print(f"  Projections rebuilt:  {len(wiped)}")
    if wiped:
        for t in wiped:
            print(f"    - {t}")
    if domains:
        print(f"  Domains:              {', '.join(sorted(domains))}")
    if event_types:
        print(f"  Event types:          {len(event_types)}")
    print(f"  Execution time:       {elapsed:.2f}s")
    print("-" * 60)


if __name__ == "__main__":
    run_replay()
