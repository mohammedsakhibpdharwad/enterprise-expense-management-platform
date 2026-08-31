from models.database import execute, fetch_all, fetch_one


def notify(user_id, title, message, link=None):
    if not user_id:
        return

    execute(
        """
        INSERT INTO notifications
        (user_id, title, message, link)
        VALUES (%s, %s, %s, %s)
        """,
        (
            user_id,
            title,
            message[:500],
            link,
        ),
    )


def unread_count(user_id):
    row = fetch_one(
        """
        SELECT COUNT(*) AS c
        FROM notifications
        WHERE user_id = %s
          AND is_read = 0
        """,
        (user_id,),
    )

    return int(
        row["c"] if row else 0
    )


def list_for_user(user_id, limit=30):
    return fetch_all(
        """
        SELECT *
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (
            user_id,
            limit,
        ),
    )


def get_for_user(notification_id, user_id):
    return fetch_one(
        """
        SELECT *
        FROM notifications
        WHERE id = %s
          AND user_id = %s
        LIMIT 1
        """,
        (
            notification_id,
            user_id,
        ),
    )


def mark_read(notification_id, user_id):
    execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = %s
          AND user_id = %s
        """,
        (
            notification_id,
            user_id,
        ),
    )


def mark_all_read(user_id):
    execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = %s
        """,
        (user_id,),
    )