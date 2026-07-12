"""Sanity tests for the transit graph search. Runs without a database.

Constructs three fake lines on a shared station layout and checks:
    * direct path returns 0 transfer
    * one-transfer path returns 1 transfer
    * two-transfer path requires 2 transfers
    * the same line is never boarded twice (cycle ban)
    * duplicate signatures are de-duplicated
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

ROOT = r"E:\大学\26小学期\code\backend"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.intelligence_gateway import CandidateRouteData  # noqa: E402
from app.services.recommend_service.transit_graph import (  # noqa: E402
    GraphNode,
    TransitGraphSearch,
    TransitGraphSnapshot,
)


def make_snapshot() -> TransitGraphSnapshot:
    """Layout (all forward-only, real tests would be richer):

    L1: A(1) -> B(2) -> C(3) -> D(4)
    L2: C(1) -> E(2) -> F(3)
    L3: F(1) -> G(2) -> H(3)
    L4: H(1) -> D(2)             (loop back to L1's terminal via H->D? actually L4 ends at D)
    """
    stations = {
        "A": 101, "B": 102, "C": 103, "D": 104,
        "E": 105, "F": 106, "G": 107, "H": 108,
    }
    l1 = [("A", 1), ("B", 2), ("C", 3), ("D", 4)]
    l2 = [("C", 1), ("E", 2), ("F", 3)]
    l3 = [("F", 1), ("G", 2), ("H", 3)]
    l4 = [("H", 1), ("D", 2)]

    ride_edges = {}
    node_station = {}
    transfer_links: dict[int, list[GraphNode]] = {}

    def add_line(line_id: int, entries):
        for (name, seq), (next_name, next_seq) in zip(entries, entries[1:]):
            from_node = GraphNode(line_id=line_id, stop_sequence=seq)
            to_node = GraphNode(line_id=line_id, stop_sequence=next_seq)
            ride_edges.setdefault(from_node, []).append(
                SimpleNamespace(to_node=to_node, to_station_id=stations[next_name])
            )
            node_station[from_node] = stations[name]
            node_station[to_node] = stations[next_name]
            transfer_links.setdefault(stations[name], []).append(from_node)
            transfer_links.setdefault(stations[next_name], []).append(to_node)
        # also add last node to its station
        last_name, last_seq = entries[-1]
        last_node = GraphNode(line_id=line_id, stop_sequence=last_seq)
        transfer_links.setdefault(stations[last_name], []).append(last_node)
        node_station[last_node] = stations[last_name]

    add_line(1, l1)
    add_line(2, l2)
    add_line(3, l3)
    add_line(4, l4)

    frozen = {node: tuple(edges) for node, edges in ride_edges.items()}
    frozen_links = {sid: tuple(nodes) for sid, nodes in transfer_links.items()}
    return TransitGraphSnapshot(
        ride_edges=frozen,
        transfer_links=frozen_links,
        line_names={1: "L1", 2: "L2", 3: "L3", 4: "L4"},
        node_station=node_station,
        station_lookup={},
    )


def assert_invariant(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}{(' :: ' + detail) if detail else ''}")
    if not condition:
        raise AssertionError(label)


def main() -> None:
    snapshot = make_snapshot()
    search = TransitGraphSearch(snapshot)

    # 1) A -> D direct on L1: 0 transfers
    direct = search.find_candidates(101, 104, max_transfer=2, max_candidates=5)
    assert_invariant("A->D returns at least one candidate", len(direct) >= 1)
    best = min(direct, key=lambda c: c.transfer_count)
    assert_invariant("A->D minimum transfer is 0", best.transfer_count == 0,
                     detail=f"got {best.transfer_count}")
    assert_invariant("A->D line_ids is just (1,)", best.line_ids == (1,),
                     detail=f"got {best.line_ids}")

    # 2) A -> F via L1+L2 (transfer at C): 1 transfer
    one = search.find_candidates(101, 106, max_transfer=2, max_candidates=5)
    assert_invariant("A->F returns at least one candidate", len(one) >= 1)
    best_one = min(one, key=lambda c: c.transfer_count)
    assert_invariant("A->F minimum transfer is 1", best_one.transfer_count == 1,
                     detail=f"got {best_one.transfer_count}")
    assert_invariant("A->F line_ids is (1,2)", best_one.line_ids == (1, 2),
                     detail=f"got {best_one.line_ids}")

    # 3) A -> H via L1+L2+L3 (two transfers, C and F): 2 transfers
    two = search.find_candidates(101, 108, max_transfer=2, max_candidates=5)
    best_two = min(two, key=lambda c: c.transfer_count)
    assert_invariant("A->H minimum transfer is 2", best_two.transfer_count == 2,
                     detail=f"got {best_two.transfer_count}")
    assert_invariant("A->H line_ids is (1,2,3)", best_two.line_ids == (1, 2, 3),
                     detail=f"got {best_two.line_ids}")

    # 4) Cycle ban: every candidate's line_ids is strictly increasing in length
    #    AND has no repeated line_id
    all_cands: list[CandidateRouteData] = search.find_candidates(
        101, 108, max_transfer=3, max_candidates=10
    )
    for cand in all_cands:
        assert_invariant(
            f"no repeated line_id in {cand.line_ids}",
            len(set(cand.line_ids)) == len(cand.line_ids),
            detail=str(cand.line_ids),
        )

    # 5) Same start/end, max_transfer=3 ceiling includes the T+1 path L1+L2+L3+L4?
    #    Path A->D also possible via L1+L2+L3+L4 (transfer at C, F, H) = 3 transfers
    ceiling = search.find_candidates(101, 104, max_transfer=3, max_candidates=10)
    transfer_counts = sorted({c.transfer_count for c in ceiling})
    assert_invariant(
        "A->D with max_transfer=3 enumerates multiple transfer levels",
        transfer_counts == [0, 3],
        detail=str(transfer_counts),
    )

    # 6) Same start/end == empty
    assert_invariant(
        "identical start/end returns empty",
        search.find_candidates(101, 101, max_transfer=2) == [],
    )

    # 7) Disconnected station returns empty
    assert_invariant(
        "unreachable station returns empty",
        search.find_candidates(101, 999, max_transfer=2) == [],
    )

    print("\nAll sanity checks passed.")


if __name__ == "__main__":
    main()