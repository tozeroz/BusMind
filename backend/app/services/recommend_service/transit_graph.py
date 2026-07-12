"""In-memory directed transit graph and 0-1 BFS route search.

The graph is built once from ``line_station`` rows. Each node is identified by
``(line_id, stop_sequence)`` so a single station passed twice on a circular line
becomes two distinct nodes and cannot be shortcut.

Two kinds of directed edges are produced:

* Ride edges  (weight 0)  -- same ``line_id``, ``stop_sequence`` increases by one.
* Transfer edges (weight 1) -- same ``station_id`` but different ``line_id``.

Because every edge weight is 0 or 1, the minimum-transfer path between two
stations can be computed with a 0-1 BFS in ``O(V + E)`` time without any
external dependency. The algorithm also yields a ranked candidate set bounded
by the caller's ``max_candidates`` argument for the recommendation pipeline to
score.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bus_line import BusLine, BusStation, LineStation
from app.services.intelligence_gateway import CandidateRouteData, RouteSegmentData


@dataclass(frozen=True, slots=True)
class GraphNode:
    line_id: int
    stop_sequence: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.line_id, self.stop_sequence)


@dataclass(frozen=True, slots=True)
class RideEdge:
    to_node: GraphNode
    to_station_id: int


@dataclass(frozen=True, slots=True)
class TransitGraphSnapshot:
    """Serializable snapshot of the in-memory graph for caching layers."""

    ride_edges: dict[GraphNode, tuple[RideEdge, ...]]
    transfer_links: dict[int, tuple[GraphNode, ...]]
    line_names: dict[int, str]
    node_station: dict[GraphNode, int]
    station_lookup: dict[int, BusStation]

    def node_for_station(self, station_id: int) -> tuple[GraphNode, ...]:
        return self.transfer_links.get(station_id, ())


@dataclass(frozen=True, slots=True)
class InternalCandidate:
    line_ids: tuple[int, ...]
    nodes: tuple[GraphNode, ...]
    station_path: tuple[int, ...]
    transfer_count: int

    def signature(self) -> tuple[tuple[int, ...], int]:
        return (self.line_ids, self.transfer_count)


class TransitGraphBuilder:
    """Builds a ``TransitGraphSnapshot`` from the SQLAlchemy session."""

    def __init__(self, db: Session | object) -> None:
        self.db = db

    def _session(self) -> Session:
        if isinstance(self.db, Session):
            return self.db
        raw_db = getattr(self.db, "db", None)
        if isinstance(raw_db, Session):
            return raw_db
        raise TypeError("TransitGraphBuilder requires a SQLAlchemy Session or TransitRepository")

    def build(self) -> TransitGraphSnapshot:
        session = self._session()
        line_station_rows = (
            session.execute(
                select(
                    LineStation.line_id,
                    LineStation.order_index,
                    LineStation.station_id,
                    LineStation.line_name,
                    BusLine.line_name.label("parent_line_name"),
                    BusLine.service_no,
                    BusLine.status,
                )
                .join(BusLine, BusLine.line_id == LineStation.line_id)
                .where(BusLine.status.in_(("running", "active")))
                .order_by(LineStation.line_id, LineStation.order_index)
            )
            .all()
        )

        per_line: dict[int, list[tuple[int, int]]] = defaultdict(list)
        line_names: dict[int, str] = {}
        for line_id, order_index, _station_id, line_name, parent_line_name, service_no, _status in line_station_rows:
            per_line[int(line_id)].append((int(order_index), int(_station_id)))
            name = line_name or parent_line_name or service_no or f"line-{line_id}"
            line_names[int(line_id)] = str(name)

        ride_edges: dict[GraphNode, list[RideEdge]] = defaultdict(list)
        station_to_nodes: dict[int, list[GraphNode]] = defaultdict(list)
        node_station: dict[GraphNode, int] = {}

        for line_id, entries in per_line.items():
            entries.sort(key=lambda item: item[0])
            for (order_index, station_id), (next_order, next_station_id) in zip(entries, entries[1:]):
                from_node = GraphNode(line_id=line_id, stop_sequence=order_index)
                to_node = GraphNode(line_id=line_id, stop_sequence=next_order)
                ride_edges[from_node].append(RideEdge(to_node=to_node, to_station_id=next_station_id))
                node_station[from_node] = station_id
                node_station[to_node] = next_station_id
                station_to_nodes[station_id].append(from_node)
                station_to_nodes[next_station_id].append(to_node)

        station_lookup = {
            int(station.station_id): station
            for station in session.execute(select(BusStation)).scalars()
        }

        transfer_links: dict[int, tuple[GraphNode, ...]] = {
            station_id: tuple(nodes) for station_id, nodes in station_to_nodes.items()
        }

        frozen_edges: dict[GraphNode, tuple[RideEdge, ...]] = {
            node: tuple(edges) for node, edges in ride_edges.items()
        }

        return TransitGraphSnapshot(
            ride_edges=frozen_edges,
            transfer_links=transfer_links,
            line_names=line_names,
            node_station=node_station,
            station_lookup=station_lookup,
        )


@dataclass
class TransitGraphSearch:
    """0-1 BFS route search over a pre-built ``TransitGraphSnapshot``."""

    snapshot: TransitGraphSnapshot
    _state_parents: dict[GraphNode, GraphNode] = field(default_factory=dict, init=False, repr=False)

    def find_candidates(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer: int = 2,
        max_candidates: int = 8,
    ) -> list[CandidateRouteData]:
        if start_station_id == end_station_id:
            return []

        start_nodes = self.snapshot.node_for_station(start_station_id)
        end_nodes = set(self.snapshot.node_for_station(end_station_id))
        if not start_nodes or not end_nodes:
            return []

        min_transfer = self._minimum_transfer(start_nodes, end_nodes, max_transfer)
        if min_transfer is None:
            return []

        ceiling = max_transfer
        internal = self._enumerate_within(
            start_nodes=start_nodes,
            end_nodes=end_nodes,
            max_transfer=ceiling,
            max_candidates=max_candidates,
        )
        return [self._to_candidate(item, route_index) for route_index, item in enumerate(internal)]


    def _minimum_transfer(
        self,
        start_nodes: Iterable[GraphNode],
        end_nodes: set[GraphNode],
        max_transfer: int,
    ) -> int | None:
        distance: dict[GraphNode, int] = {node: 0 for node in start_nodes}
        queue: deque[GraphNode] = deque(start_nodes)
        best: int | None = None

        while queue:
            node = queue.popleft()
            current = distance[node]
            if best is not None and current > best:
                continue

            if node in end_nodes:
                if best is None or current < best:
                    best = current
                continue

            for edge in self.snapshot.ride_edges.get(node, ()):
                if edge.to_node in distance and distance[edge.to_node] <= current:
                    continue
                distance[edge.to_node] = current
                queue.appendleft(edge.to_node)

            if current >= max_transfer:
                continue

            transfer_targets = self.snapshot.transfer_links.get(self._station_for(node), ())
            for target in transfer_targets:
                if target == node or target.line_id == node.line_id:
                    continue
                if target in distance and distance[target] <= current + 1:
                    continue
                distance[target] = current + 1
                queue.append(target)

        return best

    def _enumerate_within(
        self,
        start_nodes: Sequence[GraphNode],
        end_nodes: set[GraphNode],
        max_transfer: int,
        max_candidates: int,
    ) -> list[InternalCandidate]:
        seen_signatures: set[tuple[tuple[int, ...], int]] = set()
        results: list[InternalCandidate] = []
        visited_states: set[tuple[GraphNode, frozenset[int]]] = set()
        self._state_parents = {}

        initial_states: list[tuple[GraphNode, frozenset[int]]] = [
            (node, frozenset({node.line_id})) for node in start_nodes
        ]
        queue: deque[tuple[GraphNode, frozenset[int]]] = deque(initial_states)
        for node, line_set in initial_states:
            visited_states.add((node, line_set))

        while queue:
            node, line_set = queue.popleft()
            current = len(line_set) - 1

            if node in end_nodes:
                path = self._reconstruct_state((node, line_set))
                if path is None:
                    continue
                candidate = self._build_internal_candidate(path)
                if candidate is None:
                    continue
                if candidate.transfer_count > max_transfer:
                    continue
                signature = candidate.signature()
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                results.append(candidate)
                if len(results) >= max_candidates:
                    break
                continue

            for edge in self.snapshot.ride_edges.get(node, ()):
                next_state = (edge.to_node, line_set)
                if next_state in visited_states:
                    continue
                visited_states.add(next_state)
                self._state_parents[edge.to_node] = node
                queue.appendleft(next_state)

            if current >= max_transfer:
                continue

            transfer_targets = self.snapshot.transfer_links.get(self._station_for(node), ())
            for target in transfer_targets:
                if target.line_id in line_set:
                    continue
                next_state = (target, line_set | {target.line_id})
                if next_state in visited_states:
                    continue
                visited_states.add(next_state)
                self._state_parents[target] = node
                queue.append(next_state)

        return results

    def _reconstruct_state(
        self,
        end_state: tuple[GraphNode, frozenset[int]],
    ) -> list[GraphNode] | None:
        end_node, _line_set = end_state
        path: list[GraphNode] = [end_node]
        cursor = end_node
        visited: set[GraphNode] = {end_node}
        while cursor in self._state_parents:
            previous = self._state_parents[cursor]
            if previous in visited:
                return None
            visited.add(previous)
            path.append(previous)
            cursor = previous
        path.reverse()
        return path

    def _build_internal_candidate(self, nodes: Sequence[GraphNode]) -> InternalCandidate | None:
        if len(nodes) < 2:
            return None

        line_sequence: list[int] = []
        station_path: list[int] = []
        for index, node in enumerate(nodes):
            station_id = self._station_for(node)
            station_path.append(station_id)
            if index == 0:
                line_sequence.append(node.line_id)
                continue
            if node.line_id != line_sequence[-1]:
                line_sequence.append(node.line_id)

        transfer_count = max(0, len(line_sequence) - 1)
        return InternalCandidate(
            line_ids=tuple(line_sequence),
            nodes=tuple(nodes),
            station_path=tuple(station_path),
            transfer_count=transfer_count,
        )

    def _to_candidate(
        self,
        internal: InternalCandidate,
        route_index: int,
    ) -> CandidateRouteData:
        segments: list[RouteSegmentData] = []
        cumulative_ride = 0.0
        for segment_order, segment_line_id in enumerate(internal.line_ids, start=1):
            segment_nodes = [
                node for node in internal.nodes if node.line_id == segment_line_id
            ]
            if not segment_nodes:
                continue
            segment_nodes.sort(key=lambda node: node.stop_sequence)
            boarding_station_id = self._station_for(segment_nodes[0])
            alighting_station_id = self._station_for(segment_nodes[-1])
            ride_time = self._estimate_segment_ride_minutes(
                line_id=segment_line_id,
                boarding=segment_nodes[0],
                alighting=segment_nodes[-1],
            )
            cumulative_ride += ride_time
            segments.append(
                RouteSegmentData(
                    segment_order=segment_order,
                    line_id=segment_line_id,
                    line_name=self.snapshot.line_names.get(segment_line_id, f"line-{segment_line_id}"),
                    boarding_station_id=boarding_station_id,
                    alighting_station_id=alighting_station_id,
                    ride_time_minutes=ride_time,
                )
            )

        walk_time = 4.0 + 2.0 * internal.transfer_count
        route_id = (
            f"graph_{internal.signature()[0]}_{internal.station_path[0]}_{internal.station_path[-1]}_{route_index}"
        )
        return CandidateRouteData(
            route_id=route_id,
            vehicle_id=0,
            line_ids=tuple(internal.line_ids),
            segments=tuple(segments),
            boarding_station_id=internal.station_path[0],
            alighting_station_id=internal.station_path[-1],
            walk_time_minutes=walk_time,
            ride_time_minutes=round(cumulative_ride, 1),
            transfer_count=internal.transfer_count,
        )

    def _station_for(self, node: GraphNode) -> int:
        return self.snapshot.node_station[node]

    @staticmethod
    def _estimate_segment_ride_minutes(
        *,
        line_id: int,
        boarding: GraphNode,
        alighting: GraphNode,
    ) -> float:
        stop_count = max(1, alighting.stop_sequence - boarding.stop_sequence)
        return round(max(3.0, stop_count * 2.0), 1)


@dataclass
class TransitGraphService:
    """Convenience wrapper that owns the snapshot lifecycle."""

    db: Session | object
    _snapshot: TransitGraphSnapshot | None = field(default=None, init=False)

    def refresh(self) -> TransitGraphSnapshot:
        self._snapshot = TransitGraphBuilder(self.db).build()
        return self._snapshot

    @property
    def snapshot(self) -> TransitGraphSnapshot:
        if self._snapshot is None:
            self._snapshot = TransitGraphBuilder(self.db).build()
        return self._snapshot

    def find_candidates(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer: int = 2,
        max_candidates: int = 8,
    ) -> list[CandidateRouteData]:
        return TransitGraphSearch(self.snapshot).find_candidates(
            start_station_id=start_station_id,
            end_station_id=end_station_id,
            max_transfer=max_transfer,
            max_candidates=max_candidates,
        )


__all__ = [
    "GraphNode",
    "RideEdge",
    "TransitGraphSnapshot",
    "TransitGraphBuilder",
    "TransitGraphSearch",
    "TransitGraphService",
    "InternalCandidate",
]
