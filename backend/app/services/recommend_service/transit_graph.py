"""Backend adapters for the shared transit graph route search."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithm.routing.transit_graph import (
    CandidateRoute,
    GraphNode,
    InternalCandidate,
    RideEdge,
    TransitGraphSearch,
    TransitGraphSnapshot,
)
from app.models.bus_line import BusLine, BusStation, LineStation
from app.models.bus_vehicle import BusVehicle
from app.services.intelligence_gateway import CandidateRouteData, RouteSegmentData


class TransitGraphBuilder:
    """Builds a shared ``TransitGraphSnapshot`` from the backend database."""

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
        active_line_ids = (
            select(BusVehicle.line_id)
            .where(BusVehicle.status != "offline")
            .distinct()
        )
        line_station_rows = (
            session.execute(
                select(
                    LineStation.line_id,
                    LineStation.order_index,
                    LineStation.station_id,
                    LineStation.line_name,
                    BusLine.line_name.label("parent_line_name"),
                    BusLine.line_code,
                    BusLine.status,
                )
                .join(BusLine, BusLine.line_id == LineStation.line_id)
                .where(BusLine.status.in_(("running", "active")))
                .where(LineStation.line_id.in_(active_line_ids))
                .order_by(LineStation.line_id, LineStation.order_index)
            )
            .all()
        )

        per_line: dict[int, list[tuple[int, int]]] = defaultdict(list)
        line_names: dict[int, str] = {}
        for line_id, order_index, station_id, line_name, parent_line_name, service_no, _status in line_station_rows:
            per_line[int(line_id)].append((int(order_index), int(station_id)))
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

        active_station_ids = set(node_station.values())
        station_lookup = {
            int(station.station_id): station
            for station in session.execute(
                select(BusStation).where(BusStation.station_id.in_(active_station_ids))
            ).scalars()
        } if active_station_ids else {}

        return TransitGraphSnapshot(
            ride_edges={node: tuple(edges) for node, edges in ride_edges.items()},
            transfer_links={station_id: tuple(nodes) for station_id, nodes in station_to_nodes.items()},
            line_names=line_names,
            node_station=node_station,
            station_lookup=station_lookup,
        )


def _to_backend_candidate(candidate: CandidateRoute) -> CandidateRouteData:
    return CandidateRouteData(
        route_id=candidate.route_id,
        vehicle_id=candidate.vehicle_id,
        line_ids=candidate.line_ids,
        segments=tuple(
            RouteSegmentData(
                segment_order=segment.segment_order,
                line_id=segment.line_id,
                line_name=segment.line_name,
                boarding_station_id=segment.boarding_station_id,
                alighting_station_id=segment.alighting_station_id,
                ride_time_minutes=segment.ride_time_minutes,
            )
            for segment in candidate.segments
        ),
        boarding_station_id=candidate.boarding_station_id,
        alighting_station_id=candidate.alighting_station_id,
        walk_time_minutes=candidate.walk_time_minutes,
        ride_time_minutes=candidate.ride_time_minutes,
        transfer_count=candidate.transfer_count,
    )


@dataclass
class TransitGraphService:
    """Backend wrapper that owns the snapshot lifecycle."""

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
        routes = TransitGraphSearch(self.snapshot).find_candidates(
            start_station_id=start_station_id,
            end_station_id=end_station_id,
            max_transfer=max_transfer,
            max_candidates=max_candidates,
        )
        return [_to_backend_candidate(route) for route in routes]


__all__ = [
    "GraphNode",
    "RideEdge",
    "TransitGraphSnapshot",
    "TransitGraphBuilder",
    "TransitGraphSearch",
    "TransitGraphService",
    "InternalCandidate",
]
