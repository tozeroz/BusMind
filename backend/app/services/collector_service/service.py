from __future__ import annotations

from dataclasses import asdict

from backend.app.cache import CacheProvider, memory_cache_provider
from backend.app.cache.cache_keys import bus_arrival_service, bus_arrival_stop
from backend.app.core.time_utils import now_local
from backend.app.services.lta_service import LtaDataMallClient


class LtaCollectorService:
    def __init__(
        self,
        lta_client: LtaDataMallClient,
        cache: CacheProvider | None = None,
        arrival_ttl_seconds: int = 75,
    ) -> None:
        self.lta_client = lta_client
        self.cache = cache or memory_cache_provider
        self.arrival_ttl_seconds = arrival_ttl_seconds

    async def refresh_bus_arrival(
        self,
        bus_stop_code: str,
        service_no: str | None = None,
    ) -> list[dict[str, object]]:
        arrivals = await self.lta_client.get_bus_arrivals(bus_stop_code, service_no)
        collected_at = now_local().isoformat()
        payloads: list[dict[str, object]] = []
        for arrival in arrivals:
            payload = asdict(arrival)
            payload["estimated_arrival"] = arrival.estimated_arrival.isoformat()
            payload["query_time"] = collected_at
            payloads.append(payload)
            self.cache.set(
                bus_arrival_service(arrival.bus_stop_code, arrival.service_no),
                payload,
                ttl_seconds=self.arrival_ttl_seconds,
            )
        self.cache.set(
            bus_arrival_stop(bus_stop_code),
            payloads,
            ttl_seconds=self.arrival_ttl_seconds,
        )
        return payloads
