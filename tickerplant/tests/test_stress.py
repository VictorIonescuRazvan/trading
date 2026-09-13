import asyncio
import os

import httpx
import pytest
from fastapi import FastAPI


@pytest.mark.stress
def test_100k_requests_approximately_concurrently(client: object) -> None:
    if os.environ.get("RUN_STRESS_TESTS") != "1":
        pytest.skip("set RUN_STRESS_TESTS=1 to run the 100k-request stress test")

    request_count = int(os.environ.get("STRESS_REQUEST_COUNT", "100000"))
    concurrency = int(os.environ.get("STRESS_CONCURRENCY", "1000"))

    async def send_requests(app: FastAPI) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            for offset in range(0, request_count, concurrency):
                batch_size = min(concurrency, request_count - offset)
                await asyncio.gather(
                    *(
                        http.get(
                            "/getpending",
                            params={
                                "start": "2024-01-01T00:00:00Z",
                                "end": "2024-01-31T23:59:59Z",
                            },
                        )
                        for _ in range(batch_size)
                    )
                )

    import tickerplant.api as api

    asyncio.run(send_requests(api.app))


@pytest.mark.stress
def test_100k_mixed_requests_cover_all_api_endpoints(client: object) -> None:
    if os.environ.get("RUN_STRESS_TESTS") != "1":
        pytest.skip("set RUN_STRESS_TESTS=1 to run the 100k-request stress test")

    request_count = int(os.environ.get("STRESS_REQUEST_COUNT", "100000"))
    concurrency = int(os.environ.get("STRESS_CONCURRENCY", "1000"))

    async def send_requests(app: FastAPI) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            for offset in range(0, request_count, concurrency):
                batch_size = min(concurrency, request_count - offset)
                requests = []
                for request_number in range(offset, offset + batch_size):
                    symbol = f"S{request_number:05d}"
                    endpoint_number = request_number % 5
                    if endpoint_number == 0:
                        requests.append(
                            http.post(
                                "/data",
                                json={
                                    "data": {
                                        symbol: [
                                            {
                                                "date": "2024-01-15T14:30:00Z",
                                                "low": 184.10,
                                                "high": 185.20,
                                                "open": 184.50,
                                                "close": 184.90,
                                                "volume": request_number,
                                            }
                                        ]
                                    }
                                },
                            )
                        )
                    elif endpoint_number == 1:
                        requests.append(
                            http.post(
                                "/getdata",
                                json={
                                    "start": "2024-01-01T00:00:00Z",
                                    "end": "2024-01-31T23:59:59Z",
                                    "symbols": [symbol],
                                },
                            )
                        )
                    elif endpoint_number == 2:
                        requests.append(
                            http.get(
                                "/meta",
                                params={
                                    "symbol": symbol,
                                    "start": "2024-01-01T00:00:00Z",
                                    "end": "2024-01-31T23:59:59Z",
                                },
                            )
                        )
                    elif endpoint_number == 3:
                        requests.append(
                            http.get(
                                "/getpending",
                                params={
                                    "start": "2024-01-01T00:00:00Z",
                                    "end": "2024-01-31T23:59:59Z",
                                },
                            )
                        )
                    else:
                        requests.append(
                            http.post(
                                "/setdone",
                                json={"symbol": symbol, "year": 2024, "month": 1},
                            )
                        )
                await asyncio.gather(*requests)

    import tickerplant.api as api

    asyncio.run(send_requests(api.app))