"""Smoke test: MySQLTransitGateway delegates to TransitGraphService when
repository.get_candidate_routes returns empty.

This avoids needing a real MySQL connection. We mock the TransitRepository
and BusStation so the gateway thinks both endpoints exist, while forcing the
candidate-route query to return an empty list.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

ROOT = r"E:\大学\26小学期\code\backend"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.intelligence_gateway_mysql import MySQLTransitGateway
from app.services.recommend_service.transit_graph import TransitGraphSnapshot, TransitGraphService, GraphNode, RideEdge


@dataclass
class FakeStation:
    station_id: int
    station_name: str
    longitude: float
    latitude: float


class FakeRepository:
    """Stand-in for TransitRepository with just enough plumbing."""

    def __init__(self, nodes_for_line: dict[int, list[tuple[int, int]]], stations):
        # nodes_for_line[line_id] = [(stop_sequence, station_id), ...]
        self._nodes_for_line = nodes_for_line
        self._stations = {s.station_id: s for s in stations}

    def get_station(self, station_id):
        return self._stations.get(station_id)

    def get_candidate_routes(self, start, end, max_transfer_count, limit=5):
        # Force empty so the gateway must fall through to the graph.
        return []

    @property
    def db(self):
        return self  # used by TransitGraphBuilder._session fallback; we override build() instead


def make_static_graph_service() -> TransitGraphService:
    """Service that bypasses the SQL builder and uses a hand-built snapshot."""

    stations = {
        "A": 101, "B": 102, "C": 103, "D": 104,
        "E": 105, "F": 106, "G": 107, "H": 108,
    }
    station_objs = [FakeStation(sid, name, 0.0, 0.0) for name, sid in stations.items()]
    _ = station_objs  # kept only for potential future use

    l1 = [("A", 1), ("B", 2), ("C", 3), ("D", 4)]
    l2 = [("C", 1), ("E", 2), ("F", 3)]
    l3 = [("F", 1), ("G", 2), ("H", 3)]
    l4 = [("H", 1), ("D", 2)]

    ride_edges = {}
    node_station = {}
    transfer_links = {}

    def add_line(line_id, entries):
        for (name, seq), (next_name, next_seq) in zip(entries, entries[1:]):
            from_node = GraphNode(line_id=line_id, stop_sequence=seq)
            to_node = GraphNode(line_id=line_id, stop_sequence=next_seq)
            ride_edges.setdefault(from_node, []).append(
                RideEdge(to_node=to_node, to_station_id=stations[next_name])
            )
            node_station[from_node] = stations[name]
            node_station[to_node] = stations[next_name]
            transfer_links.setdefault(stations[name], []).append(from_node)
            transfer_links.setdefault(stations[next_name], []).append(to_node)
        last_name, last_seq = entries[-1]
        last_node = GraphNode(line_id=line_id, stop_sequence=last_seq)
        transfer_links.setdefault(stations[last_name], []).append(last_node)
        node_station[last_node] = stations[last_name]

    for lid, l in [(1, l1), (2, l2), (3, l3), (4, l4)]:
        add_line(lid, l)

    snapshot = TransitGraphSnapshot(
        ride_edges={n: tuple(e) for n, e in ride_edges.items()},
        transfer_links={s: tuple(n) for s, n in transfer_links.items()},
        line_names={1: "L1", 2: "L2", 3: "L3", 4: "L4"},
        node_station=node_station,
        station_lookup={s.station_id: s for s in station_objs},
    )

    service = TransitGraphService(db=FakeRepository({}, []))
    service._snapshot = snapshot  # type: ignore[attr-defined]
    return service


async def main() -> None:
    repo = FakeRepository(nodes_for_line={}, stations=[
        FakeStation(101, "A", 0.0, 0.0),
        FakeStation(108, "H", 0.0, 0.0),
    ])
    graph_service = make_static_graph_service()
    gateway = MySQLTransitGateway(db=repo, graph_service=graph_service)

    results = await gateway.get_candidate_routes(101, 108, max_transfer_count=2)
    assert results, "expected at least one candidate from graph search"
    best = min(results, key=lambda c: c.transfer_count)
    assert best.transfer_count == 2, f"expected min 2 transfers, got {best.transfer_count}"
    assert best.line_ids == (1, 2, 3), f"unexpected line_ids {best.line_ids}"
    print(f"[PASS] gateway delegates to graph: best has {best.transfer_count} transfers via {best.line_ids}")
    print(f"[PASS] gateway returned {len(results)} candidates total")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())