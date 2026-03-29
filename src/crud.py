from datetime import datetime, date

from .db import get_connection


def _row_dict(cursor, row):
    cols = [desc[0] for desc in cursor.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def get_open_session() -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, start_time, end_time, location, notes, status, created_at
                FROM meetup_sessions
                WHERE status = 'open'
                ORDER BY start_time DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def start_session(location: str | None, notes: str | None) -> dict:
    current = get_open_session()
    if current:
        return current

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO meetup_sessions (start_time, location, notes, status)
                VALUES (NOW(), %s, %s, 'open')
                RETURNING id, start_time, end_time, location, notes, status, created_at
                """,
                (location, notes),
            )
            return _row_dict(cur, cur.fetchone())


def end_session(session_id: int) -> int:
    """End session and auto-checkout remaining participants. Returns auto-checkout count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE meetup_checkins
                SET checkout_time = NOW()
                WHERE session_id = %s AND checkout_time IS NULL
                """,
                (session_id,),
            )
            auto_checkouts = cur.rowcount
            cur.execute(
                """
                UPDATE meetup_sessions
                SET status = 'closed', end_time = NOW()
                WHERE id = %s
                """,
                (session_id,),
            )
            return auto_checkouts


def update_session_revenue(session_id: int, amount: float) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE meetup_sessions SET kiosk_revenue = %s WHERE id = %s",
                (amount, session_id),
            )


def get_session_revenue(session_id: int) -> float:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(kiosk_revenue, 0) FROM meetup_sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            return float(row[0]) if row else 0.0


def get_player_by_card_id(card_id: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.uuid, p.name, p.tag, p.email, p.telephone, p.total_events, c.card_id
                FROM players p
                JOIN card_ids c ON c.player_uuid = p.uuid
                WHERE c.card_id = %s
                LIMIT 1
                """,
                (card_id,),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def get_player_by_uuid(player_uuid: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT uuid, name, tag, email, telephone, total_events
                FROM players
                WHERE uuid = %s
                LIMIT 1
                """,
                (player_uuid,),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def get_player_by_tag(tag: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT uuid, name, tag, email, telephone
                FROM players
                WHERE LOWER(tag) = LOWER(%s)
                LIMIT 1
                """,
                (tag,),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def create_player(name: str, tag: str, telephone: str = "", email: str = "") -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO players (uuid, name, tag, telephone, email)
                VALUES (gen_random_uuid()::text, %s, %s, %s, %s)
                RETURNING uuid, name, tag, email, telephone
                """,
                (name, tag, telephone, email),
            )
            return _row_dict(cur, cur.fetchone())


def search_players_by_name(query: str) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    like = f"%{q}%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT uuid, name, tag, email, telephone, total_events
                FROM players
                WHERE LOWER(COALESCE(name, '')) LIKE %s
                   OR LOWER(COALESCE(tag, '')) LIKE %s
                ORDER BY COALESCE(name, '') ASC
                LIMIT 10
                """,
                (like, like),
            )
            rows = cur.fetchall()
            return [_row_dict(cur, r) for r in rows]


def link_card(player_uuid: str, card_id: str) -> tuple[bool, str | None]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT player_uuid FROM card_ids WHERE card_id = %s", (card_id,))
            existing = cur.fetchone()
            if existing and existing[0] != player_uuid:
                return False, "Kort-ID redan kopplat till annan spelare"
            if existing and existing[0] == player_uuid:
                return True, None
            cur.execute(
                "INSERT INTO card_ids (card_id, player_uuid) VALUES (%s, %s)",
                (card_id, player_uuid),
            )
            return True, None


def create_checkin(
    session_id: int,
    player_uuid: str | None,
    guest_name: str | None,
    method: str,
    created_by: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO meetup_checkins (session_id, player_uuid, guest_name, method, checkin_time, created_by)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                RETURNING id, session_id, player_uuid, guest_name, method, checkin_time, checkout_time, created_by
                """,
                (session_id, player_uuid, guest_name, method, created_by),
            )
            return _row_dict(cur, cur.fetchone())


def get_checkin_for_player(session_id: int, player_uuid: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, player_uuid, guest_name, method, checkin_time, checkout_time, created_by
                FROM meetup_checkins
                WHERE session_id = %s AND player_uuid = %s
                LIMIT 1
                """,
                (session_id, player_uuid),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def get_checkin_by_id(checkin_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, player_uuid, guest_name, method, checkin_time, checkout_time, created_by
                FROM meetup_checkins
                WHERE id = %s
                LIMIT 1
                """,
                (checkin_id,),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def convert_guest_to_player(checkin_id: int, player_uuid: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE meetup_checkins
                SET player_uuid = %s, guest_name = NULL
                WHERE id = %s
                RETURNING id, session_id, player_uuid, guest_name, method, checkin_time, checkout_time, created_by
                """,
                (player_uuid, checkin_id),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def count_checkins(session_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM meetup_checkins WHERE session_id = %s", (session_id,))
            return int(cur.fetchone()[0])


def count_present(session_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM meetup_checkins
                WHERE session_id = %s AND checkout_time IS NULL
                """,
                (session_id,),
            )
            return int(cur.fetchone()[0])


def get_session_checkins(session_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.checkin_time, c.checkout_time, c.method, c.guest_name, p.name
                FROM meetup_checkins c
                LEFT JOIN players p ON p.uuid = c.player_uuid
                WHERE c.session_id = %s
                ORDER BY c.checkin_time ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()

    result = []
    for idx, row in enumerate(rows, 1):
        checkin_id, checkin_time, checkout_time, method, guest_name, player_name = row
        result.append(
            {
                "number": idx,
                "name": player_name or guest_name or "Guest",
                "checkin_time": checkin_time,
                "checkout_time": checkout_time,
                "checked_out": checkout_time is not None,
                "method": method,
                "checkin_id": checkin_id,
                "is_guest": player_name is None,
            }
        )
    return result


def checkout_player(session_id: int, player_uuid: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE meetup_checkins
                SET checkout_time = NOW()
                WHERE id = (
                    SELECT id
                    FROM meetup_checkins
                    WHERE session_id = %s
                      AND player_uuid = %s
                      AND checkout_time IS NULL
                    LIMIT 1
                )
                RETURNING id, session_id, player_uuid, guest_name, method, checkin_time, checkout_time, created_by
                """,
                (session_id, player_uuid),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def checkout_checkin(checkin_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE meetup_checkins
                SET checkout_time = NOW()
                WHERE id = %s AND checkout_time IS NULL
                """,
                (checkin_id,),
            )
            return cur.rowcount > 0


def undo_checkout(checkin_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE meetup_checkins SET checkout_time = NULL WHERE id = %s AND checkout_time IS NOT NULL",
                (checkin_id,),
            )
            return cur.rowcount > 0


def create_headcount(session_id: int, count: int, created_by: str | None = None) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO meetup_headcounts (session_id, count, recorded_at, created_by)
                VALUES (%s, %s, NOW(), %s)
                RETURNING id, session_id, count, recorded_at, created_by
                """,
                (session_id, count, created_by),
            )
            return _row_dict(cur, cur.fetchone())


def get_session_headcounts(session_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count, recorded_at
                FROM meetup_headcounts
                WHERE session_id = %s
                ORDER BY recorded_at ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "count": row[0],
            "recorded_at": row[1],
        }
        for row in rows
    ]


def get_sessions_for_month(year: int, month: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.start_time, s.end_time, s.status,
                       COALESCE(s.location, '') AS location,
                       COALESCE(s.kiosk_revenue, 0) AS kiosk_revenue,
                       COUNT(c.id) AS total_checkins,
                       COALESCE(MAX(h.count), 0) AS peak_headcount
                FROM meetup_sessions s
                LEFT JOIN meetup_checkins c ON c.session_id = s.id
                LEFT JOIN meetup_headcounts h ON h.session_id = s.id
                WHERE EXTRACT(YEAR FROM s.start_time) = %s
                  AND EXTRACT(MONTH FROM s.start_time) = %s
                GROUP BY s.id
                ORDER BY s.start_time ASC
                """,
                (year, month),
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [{cols[i]: r[i] for i in range(len(cols))} for r in rows]


def get_all_sessions() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.start_time, s.end_time, COALESCE(s.location, '') AS location,
                       COALESCE(s.notes, '') AS notes, s.status, COUNT(c.id) AS total_checkins
                FROM meetup_sessions s
                LEFT JOIN meetup_checkins c ON c.session_id = s.id
                GROUP BY s.id
                ORDER BY s.start_time DESC
                """
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [{cols[i]: r[i] for i in range(len(cols))} for r in rows]


def get_session_by_id(session_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, start_time, end_time, location, notes, status, created_at,
                       COALESCE(kiosk_revenue, 0) AS kiosk_revenue
                FROM meetup_sessions
                WHERE id = %s
                LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return _row_dict(cur, row) if row else None


def delete_session(session_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM meetup_headcounts WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM meetup_checkins WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM meetup_sessions WHERE id = %s", (session_id,))
            return cur.rowcount > 0


def delete_checkin(checkin_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM meetup_checkins WHERE id = %s", (checkin_id,))
            return cur.rowcount > 0


def get_all_members(search: str | None = None) -> list[dict]:
    conditions = []
    params = []
    if search:
        like = f"%{search.strip().lower()}%"
        conditions.append(
            "(LOWER(COALESCE(p.name, '')) LIKE %s OR LOWER(COALESCE(p.tag, '')) LIKE %s OR LOWER(COALESCE(p.email, '')) LIKE %s)"
        )
        params.extend([like, like, like])

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT p.uuid, p.name, p.tag, p.email, p.telephone, p.total_events,
                       COUNT(c.card_id) AS card_count
                FROM players p
                LEFT JOIN card_ids c ON c.player_uuid = p.uuid
                {where_sql}
                GROUP BY p.uuid
                ORDER BY COALESCE(p.name, '') ASC
                """,
                params,
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [{cols[i]: r[i] for i in range(len(cols))} for r in rows]


def log_action(action: str, detail: str | None = None, created_by: str | None = None) -> None:
    with get_connection(timeout=0.2) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (timestamp, user_name, action, target_table, details)
                VALUES (NOW(), %s, %s, 'meetups', %s)
                """,
                (created_by or "system", action, detail),
            )


def get_audit_log(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT timestamp AS created_at, action, details AS detail, user_name AS created_by
                FROM audit_log
                WHERE target_table = 'meetups'
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [{cols[i]: r[i] for i in range(len(cols))} for r in rows]


def get_overview_stats() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM players")
            total_members = int(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM meetup_sessions WHERE status = 'closed'")
            total_sessions = int(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM meetup_checkins")
            total_checkins = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT p.name, COUNT(c.id) AS cnt
                FROM meetup_checkins c
                JOIN players p ON p.uuid = c.player_uuid
                GROUP BY p.uuid
                ORDER BY cnt DESC
                LIMIT 1
                """
            )
            most_active = cur.fetchone()

    avg = round(total_checkins / total_sessions, 1) if total_sessions > 0 else 0
    return {
        "total_members": total_members,
        "total_sessions": total_sessions,
        "total_checkins": total_checkins,
        "avg_per_session": avg,
        "most_active": most_active[0] if most_active else "-",
    }


def get_session_stats(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.start_time,
                       COUNT(c.id) AS total_checkins,
                       COALESCE(MAX(h.count), 0) AS peak_headcount
                FROM meetup_sessions s
                LEFT JOIN meetup_checkins c ON c.session_id = s.id
                LEFT JOIN meetup_headcounts h ON h.session_id = s.id
                WHERE s.status = 'closed'
                GROUP BY s.id
                ORDER BY s.start_time DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    result = []
    for _, start_time, total_checkins, peak_headcount in rows:
        result.append(
            {
                "date": start_time.strftime("%Y-%m-%d") if start_time else "",
                "weekday": start_time.strftime("%A") if start_time else "",
                "total_checkins": int(total_checkins or 0),
                "peak_headcount": int(peak_headcount or 0),
            }
        )
    return result


def get_member_stats() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.name,
                       COUNT(c.id) AS total_sessions,
                       MAX(c.checkin_time) AS last_attended,
                       AVG(
                           CASE
                               WHEN c.checkout_time IS NOT NULL
                               THEN EXTRACT(EPOCH FROM (c.checkout_time - c.checkin_time)) / 60
                               ELSE NULL
                           END
                       ) AS avg_duration_minutes
                FROM players p
                JOIN meetup_checkins c ON c.player_uuid = p.uuid
                GROUP BY p.uuid
                ORDER BY total_sessions DESC
                """
            )
            rows = cur.fetchall()

    result = []
    for name, total_sessions, last_attended, avg_duration_minutes in rows:
        result.append(
            {
                "name": name,
                "total_sessions": int(total_sessions or 0),
                "last_attended": last_attended.strftime("%Y-%m-%d") if last_attended else "",
                "avg_duration_minutes": round(avg_duration_minutes) if avg_duration_minutes is not None else None,
            }
        )
    return result


def get_member_streak(player_uuid: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM meetup_sessions
                WHERE status = 'closed'
                ORDER BY start_time DESC
                """
            )
            session_ids = [row[0] for row in cur.fetchall()]

            streak = 0
            for session_id in session_ids:
                cur.execute(
                    """
                    SELECT 1
                    FROM meetup_checkins
                    WHERE session_id = %s AND player_uuid = %s
                    LIMIT 1
                    """,
                    (session_id, player_uuid),
                )
                if cur.fetchone():
                    streak += 1
                else:
                    break
            return streak


def get_checkins_for_export(start_date: date, end_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.start_time, s.end_time,
                       p.uuid, p.name,
                       c.guest_name, c.checkin_time, c.checkout_time, c.method
                FROM meetup_checkins c
                JOIN meetup_sessions s ON s.id = c.session_id
                LEFT JOIN players p ON p.uuid = c.player_uuid
                WHERE s.start_time >= %s::date
                  AND s.start_time <= (%s::date + INTERVAL '1 day' - INTERVAL '1 second')
                ORDER BY s.start_time ASC, c.checkin_time ASC
                """,
                (start_date, end_date),
            )
            rows = cur.fetchall()

    result = []
    for row in rows:
        (
            session_start,
            session_end,
            player_uuid,
            player_name,
            guest_name,
            checkin_time,
            checkout_time,
            method,
        ) = row
        result.append(
            {
                "session_start": session_start,
                "session_end": session_end,
                "player_uuid": player_uuid,
                "player_name": player_name,
                "guest_name": guest_name,
                "checkin_time": checkin_time,
                "checkout_time": checkout_time,
                "method": method,
            }
        )
    return result
