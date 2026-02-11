import json
import os
import sys

import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from server import MeetManagerService

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class MockContext:
    def set_code(self, code):
        pass

    def set_details(self, details):
        pass


class MockMeetManagerService(MeetManagerService):
    def __init__(self):
        self._data_cache = {}
        # Load fixtures into cache
        for name in ["Relay", "RelayNames", "Entry", "Event", "Session", "Team", "Scoring", "Athlete"]:
            try:
                with open(os.path.join(FIXTURES_DIR, f"{name}.json")) as f:
                    self._data_cache[name] = json.load(f)
            except FileNotFoundError:
                self._data_cache[name] = []
        self.config = {"meet_name": "Mock Meet", "meet_description": "Mock Description"}

    def _get_table(self, table_name):
        return self._data_cache.get(table_name, [])


@pytest.fixture
def service():
    return MockMeetManagerService()


def test_get_relays_legs(service):
    # Relay 0 (from debug output) has swimmers?
    # Relay.json first item: Relay_no 2381. Team 145.
    # RelayNames should have entries for Relay_no 2381.
    resp = service.GetRelays(None, None)
    assert len(resp.relays) > 0

    # Check if any relay has leg names
    has_legs = False
    for r in resp.relays:
        if r.leg1_name or r.leg2_name:
            has_legs = True
            break

    # Currently expected to FAIL
    if not has_legs:
        pytest.fail("Relays missing leg names")


def test_get_entries_seed_time(service):
    resp = service.GetEntries(None, None)
    assert len(resp.entries) > 0

    # Check if any entry has seed time != "NT"
    has_seed = False
    for e in resp.entries:
        if e.seed_time and e.seed_time != "NT":
            has_seed = True
            break

    if not has_seed:
        pytest.fail("All entries have NT seed time")


def test_get_entries_event_name(service):
    resp = service.GetEntries(None, None)
    assert len(resp.entries) > 0

    # Check if event_name is populated
    has_name = False
    for e in resp.entries:
        if e.event_name:
            has_name = True
            break

    if not has_name:
        pytest.fail("Entries missing event_name")


def test_get_scores(service):
    resp = service.GetScores(None, None)
    # Check if any team has > 0 points
    has_points = False
    for s in resp.scores:
        if s.total_points > 0:
            has_points = True
            break

    if not has_points:
        pytest.fail("All scores are 0")


def test_get_sessions_start_time(service):
    resp = service.GetSessions(None, None)
    assert len(resp.sessions) > 0

    # Check format of start_time (should be HH:MM AM/PM)
    # Currently it returns raw int "45120" or similar
    import re

    time_pat = re.compile(r"\d{1,2}:\d{2}\s?(AM|PM)")

    valid_format = False
    for s in resp.sessions:
        if s.start_time and time_pat.match(s.start_time):
            valid_format = True
            break

    if not valid_format:
        pytest.fail(f"Session start time not formatted: {resp.sessions[0].start_time}")
