from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4

from app.schemas.ai_travel import AiMode, AiTravelRequest
from app.schemas.recommendation import Preference, RouteRecommendation


@dataclass(slots=True)
class ConversationSnapshot:
    conversation_id: str
    routes: list[RouteRecommendation] = field(default_factory=list)
    start_station_id: int | None = None
    end_station_id: int | None = None
    preference: Preference = Preference.BALANCED
    selected_route_id: str | None = None


class ConversationStore:
    """Small process-local LRU store for short-lived assistant conversations."""

    def __init__(self, max_conversations: int = 500) -> None:
        self.max_conversations = max_conversations
        self._items: OrderedDict[str, ConversationSnapshot] = OrderedDict()
        self._lock = RLock()

    def get(self, conversation_id: str | None) -> ConversationSnapshot | None:
        if not conversation_id:
            return None
        with self._lock:
            snapshot = self._items.get(conversation_id)
            if snapshot is not None:
                self._items.move_to_end(conversation_id)
            return snapshot

    def save(self, snapshot: ConversationSnapshot) -> None:
        with self._lock:
            self._items[snapshot.conversation_id] = snapshot
            self._items.move_to_end(snapshot.conversation_id)
            while len(self._items) > self.max_conversations:
                self._items.popitem(last=False)

    def create_id(self) -> str:
        return uuid4().hex

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


@dataclass(frozen=True, slots=True)
class IntentResolution:
    mode: AiMode
    action: str
    start_station_id: int | None
    end_station_id: int | None
    preference: Preference
    route_id: str | None
    route_index: int | None = None


class RuleBasedTravelOrchestrator:
    _ALTERNATIVE_WORDS = ("换一条", "换一个", "另一条", "其他路线", "别的路线")
    _EXPLAIN_WORDS = ("为什么", "解释", "原因", "为何")
    _SUGGEST_WORDS = ("推荐", "怎么走", "路线推荐", "出行方案", "如何去")

    def resolve(
        self,
        request: AiTravelRequest,
        snapshot: ConversationSnapshot | None,
    ) -> IntentResolution:
        question = request.question or ""
        action = "answer"
        if any(word in question for word in self._ALTERNATIVE_WORDS):
            inferred_mode = AiMode.SUGGEST
            action = "alternative"
        elif any(word in question for word in self._EXPLAIN_WORDS):
            inferred_mode = AiMode.EXPLAIN
        elif any(word in question for word in self._SUGGEST_WORDS):
            inferred_mode = AiMode.SUGGEST
        else:
            inferred_mode = AiMode.QA

        mode = request.mode or inferred_mode
        if request.mode == AiMode.SUGGEST and action == "answer":
            action = "recommend"

        start_station_id = (
            request.start_station_id
            or _extract_station_id(question, is_start=True)
            or (snapshot.start_station_id if snapshot else None)
        )
        end_station_id = (
            request.end_station_id
            or _extract_station_id(question, is_start=False)
            or (snapshot.end_station_id if snapshot else None)
        )
        extracted_preference = _extract_preference(question)
        if (
            request.mode is None
            and mode == AiMode.QA
            and snapshot is not None
            and not snapshot.routes
            and start_station_id is not None
            and end_station_id is not None
        ):
            mode = AiMode.SUGGEST
            action = "recommend"
        if (
            request.mode is None
            and mode == AiMode.QA
            and snapshot is not None
            and snapshot.routes
            and (
                extracted_preference is not None
                or "preference" in request.model_fields_set
            )
        ):
            mode = AiMode.SUGGEST
            action = "recommend"
        if mode == AiMode.SUGGEST and action == "answer" and (
            request.start_station_id is not None
            or request.end_station_id is not None
            or _extract_station_id(question, is_start=True) is not None
            or _extract_station_id(question, is_start=False) is not None
        ):
            action = "recommend"
        preference = extracted_preference or request.preference
        if (
            extracted_preference is None
            and preference == Preference.BALANCED
            and snapshot is not None
            and "preference" not in request.model_fields_set
        ):
            preference = snapshot.preference

        return IntentResolution(
            mode=mode,
            action=action,
            start_station_id=start_station_id,
            end_station_id=end_station_id,
            preference=preference,
            route_id=request.route_id or _extract_route_id(question),
            route_index=_extract_route_index(question),
        )


def _extract_station_id(question: str, *, is_start: bool) -> int | None:
    patterns = (
        (
            r"(?:起点|起始站|出发站)(?:是|为|站|编号|ID|id|[:：#])?\s*(\d+)",
            r"从\s*(?:站点|站|#)?\s*(\d+)",
        )
        if is_start
        else (
            r"(?:终点|目的地|到达站)(?:是|为|站|编号|ID|id|[:：#])?\s*(\d+)",
            r"到\s*(?:站点|站|#)?\s*(\d+)",
        )
    )
    for pattern in patterns:
        match = re.search(pattern, question)
        if match and int(match.group(1)) > 0:
            return int(match.group(1))
    return None


def _extract_preference(question: str) -> Preference | None:
    mappings = (
        (("不挤", "宽松", "舒适", "有座"), Preference.COMFORT),
        (("少走", "少步行"), Preference.LESS_WALKING),
        (("少换乘", "不换乘", "直达"), Preference.LESS_TRANSFER),
        (("最快", "时间最短", "赶时间"), Preference.FASTEST),
        (("均衡", "综合"), Preference.BALANCED),
    )
    for words, preference in mappings:
        if any(word in question for word in words):
            return preference
    return None


def _extract_route_id(question: str) -> str | None:
    match = re.search(r"\broute[-_][A-Za-z0-9_-]+\b", question, re.IGNORECASE)
    return match.group(0) if match else None


def _extract_route_index(question: str) -> int | None:
    match = re.search(r"第\s*(\d+)\s*条", question)
    return int(match.group(1)) - 1 if match and int(match.group(1)) > 0 else None


conversation_store = ConversationStore()
