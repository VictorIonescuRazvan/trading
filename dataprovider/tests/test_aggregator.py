from datetime import datetime, timedelta, timezone

import exchange_calendars as xcals

from dataprovider.aggregator import Aggregator


def make_aggregator() -> Aggregator:
    aggregator = Aggregator.__new__(Aggregator)
    aggregator.provider_interval = 1
    aggregator.provider_config = {
        "max_query_size": 5000,
        "exchange_calendar": "XNYS",
    }
    return aggregator


def test_split_query_counts_exchange_minutes_not_wall_clock_minutes():
    aggregator = make_aggregator()
    start = datetime(2024, 1, 2, tzinfo=timezone.utc)
    end = datetime(2024, 2, 28, tzinfo=timezone.utc)

    intervals = aggregator.split_query(("AAPL", start, end))

    assert len(intervals) > 1
    first_start, first_end = intervals[0][1:]
    calendar = xcals.get_calendar("XNYS")
    assert len(calendar.minutes_in_range(first_start, first_end)) <= 4999
    assert first_end > start + timedelta(minutes=4999)