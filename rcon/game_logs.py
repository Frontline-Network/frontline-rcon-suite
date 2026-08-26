import datetime
import logging

import unicodedata
from dateutil import parser
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from rcon.log_queries import server_time_bounds, server_time_order
from rcon.logs.loop import LogLoop
from rcon.models import LogLine, PlayerID, enter_session
from rcon.rcon import LOG_ACTIONS
from rcon.types import (
    ParsedLogsType,
    StructuredLogLineWithMetaData,
)
from rcon.utils import (
    strtobool,
)

logger = logging.getLogger(__name__)


def is_player(search_str, player, exact_match=False):
    if exact_match:
        return search_str == player

    if not player or not search_str:
        return None

    if search_str.lower() in player.lower():
        return True

    normalize_search = (
        unicodedata.normalize("NFD", search_str)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    normalize_player = (
        unicodedata.normalize("NFD", player).encode("ascii", "ignore").decode("utf-8")
    )

    if normalize_search in normalize_player:
        return True

    return False


def is_action(action_filter, action, exact_match=False):
    """Test whether the passed in log line `action` is in `action_filter`."""
    if not action_filter or not action:
        return None
    if not isinstance(action_filter, list):
        action_filter = [action_filter]

    for filter_ in action_filter:
        if not exact_match:
            if action.lower().startswith(filter_.lower()):
                return True
        elif filter_ == action:
            return True

    return False


def get_recent_logs(
    start: int = 0,
    end: int = 100000,
    player_search: list[str] | str = [],
    action_filter: list[str] = [],
    min_timestamp: float | None = None,
    exact_player_match: bool = False,
    exact_action: bool = False,
    inclusive_filter: bool = True,
    log_history=None,
) -> ParsedLogsType:
    # The default behavior is to only show log lines with actions in `actions_filter`
    # inclusive_filter=True retains this default behavior
    # inclusive_filter=False will do the opposite, show all lines except what is passed in
    # `actions_filter`
    if not isinstance(start, int):
        start = 0

    if not isinstance(end, int):
        end = 1000

    start = max(0, start)
    end = max(start, end)

    log_list = log_history if log_history is not None else LogLoop.get_log_history_list()
    # Read large/time-based ranges page by page so the timestamp check below
    # can stop before older Redis pages are transferred and deserialized.
    iter_range = getattr(log_list, "iter_range", None)
    if callable(iter_range):
        all_logs = iter_range(start=start, stop=end)
    else:
        # Preserve support for injected plain lists used by callers/tests.
        all_logs = iter(log_list[start:end])

    if not isinstance(min_timestamp, float) and min_timestamp:
        min_timestamp = float(min_timestamp)

    exact_player_match = strtobool(exact_player_match)
    exact_action = strtobool(exact_action)
    inclusive_filter = strtobool(inclusive_filter)

    logs: list[StructuredLogLineWithMetaData] = []
    all_players = set()
    actions = set(LOG_ACTIONS)
    if player_search and not isinstance(player_search, list):
        player_search = [player_search]
    # flatten that shit
    line: StructuredLogLineWithMetaData
    for idx, line in enumerate(all_logs):
        if idx >= end - start:
            break
        if not isinstance(line, dict):
            continue
        if min_timestamp and line["timestamp_ms"] / 1000 < min_timestamp:
            logger.debug("Stopping log read due to old timestamp at index %s", idx)
            break
        if player_search:
            for player_name_search in player_search:
                if is_player(
                    player_name_search, line["player_name_1"], exact_player_match
                ) or is_player(
                    player_name_search, line["player_name_2"], exact_player_match
                ):
                    # Filter out anything that isn't in action_filter
                    if (
                        action_filter
                        and inclusive_filter
                        and is_action(action_filter, line["action"], exact_action)
                    ):
                        logs.append(line)
                        break
                    # Filter out any action in action_filter
                    elif (
                        action_filter
                        and not inclusive_filter
                        and not is_action(action_filter, line["action"], exact_action)
                    ):
                        logs.append(line)
                        break
                    # Handle action_filter being empty
                    elif not action_filter:
                        logs.append(line)
                        break
        elif action_filter:
            # Filter out anything that isn't in action_filter
            if inclusive_filter and is_action(
                action_filter, line["action"], exact_action
            ):
                logs.append(line)
            # Filter out any action in action_filter
            elif not inclusive_filter and not is_action(
                action_filter, line["action"], exact_action
            ):
                logs.append(line)
        elif not player_search and not action_filter:
            logs.append(line)

        if p1 := line["player_name_1"]:
            all_players.add(p1)
        if p2 := line["player_name_2"]:
            all_players.add(p2)
        actions.add(line["action"])

    return {
        "actions": sorted(list(actions)),
        "players": list(all_players),
        "logs": logs,
    }


def get_recent_logs_summary(
    end: int = 15_000,
    per_action_limit: int = 100,
    log_history=None,
) -> dict:
    """Build the dashboard projection without retaining a full log payload."""
    if not isinstance(end, int):
        end = 15_000
    if not isinstance(per_action_limit, int):
        per_action_limit = 100
    end = min(max(end, 0), 100_000)
    per_action_limit = min(max(per_action_limit, 1), 500)

    log_list = log_history if log_history is not None else LogLoop.get_log_history_list()
    iter_range = getattr(log_list, "iter_range", None)
    if callable(iter_range):
        source = iter_range(start=0, stop=end)
    else:
        source = iter(log_list[:end])

    groups: dict[str, list[dict]] = {}
    admin_logs: list[dict] = []

    def project(line):
        return {
            "player_id_1": line.get("player_id_1"),
            "player_name_1": line.get("player_name_1"),
            "player_id_2": line.get("player_id_2"),
            "player_name_2": line.get("player_name_2"),
            "message": line.get("message"),
            "timestamp_ms": line.get("timestamp_ms"),
            "action": line.get("action"),
        }

    for line in source:
        if not isinstance(line, dict):
            continue
        action = line.get("action")
        if not action:
            continue
        bucket = groups.setdefault(action, [])
        projected = None
        if len(bucket) < per_action_limit:
            projected = project(line)
            bucket.append(projected)
        if action.startswith("CHAT") and "!admin" in (line.get("message") or ""):
            admin_logs.append(projected or project(line))

    return {
        "groups": [
            {"group": action, "logs": logs} for action, logs in groups.items()
        ],
        "admin_logs": admin_logs,
    }


def get_historical_logs_records(
    sess: Session,
    player_name: str | None = None,
    action: str | None = None,
    player_id: str | None = None,
    limit: int = 1000,
    from_: datetime.datetime | None = None,
    till: datetime.datetime | None = None,
    time_sort: str = "desc",
    exact_player_match: bool = False,
    exact_action: bool = True,
    server_filter: str | None = None,
):
    limit = int(limit)
    exact_player_match = strtobool(exact_player_match)
    exact_action = strtobool(exact_action)

    if isinstance(from_, str):
        from_ = parser.parse(from_)

    if isinstance(till, str):
        till = parser.parse(till)

    name_filters = []

    q = sess.query(LogLine)
    if action and not exact_action:
        q = q.filter(LogLine.type.ilike(f"%{action}%"))
    elif action and exact_action:
        q = q.filter(LogLine.type == action)

    if server_filter:
        q = q.filter(*server_time_bounds(server_filter, from_, till))
    else:
        time_filter = []
        if from_:
            time_filter.append(LogLine.event_time >= from_)

        if till:
            time_filter.append(LogLine.event_time <= till)

        q = q.filter(and_(*time_filter))

    if player_id:
        # Handle not found
        player = (
            sess.query(PlayerID).filter(PlayerID.player_id == player_id).one_or_none()
        )
        id_ = player.id if player else 0
        q = q.filter(
            or_(LogLine.player1_player_id == id_, LogLine.player2_player_id == id_)
        )

    if player_name and not exact_player_match:
        name_filters.extend(
            [
                LogLine.player1_name.ilike("%{}%".format(player_name)),
                LogLine.player2_name.ilike("%{}%".format(player_name)),
            ]
        )
    elif player_name and exact_player_match:
        name_filters.extend(
            [
                LogLine.player1_name == player_name,
                LogLine.player2_name == player_name,
            ]
        )

    if name_filters:
        q = q.filter(or_(*name_filters))

    if time_sort:
        descending = time_sort == "desc"
        order = (
            server_time_order(descending)
            if server_filter
            else (
                LogLine.event_time.desc()
                if descending
                else LogLine.event_time.asc(),
            )
        )
        q = q.order_by(*order).limit(limit)

    return q.all()


def get_historical_logs(
    player_name: str | None = None,
    action: str | None = None,
    player_id: str | None = None,
    limit: int = 1000,
    from_: datetime.datetime | None = None,
    till: datetime.datetime | None = None,
    time_sort="desc",
    exact_player_match: bool = False,
    exact_action: bool = True,
    server_filter: str | None = None,
):
    with enter_session() as sess:
        res = get_historical_logs_records(
            sess,
            player_name,
            action,
            player_id,
            limit,
            from_,
            till,
            time_sort,
            exact_player_match,
            exact_action,
            server_filter,
        )

        return [row.to_dict() for row in res]
