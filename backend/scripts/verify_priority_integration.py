"""Run the BusMind same-day priority API integration checks.

This script only calls existing endpoints. It does not create tables, seed transit
data, or change business code. Registration creates one uniquely named test user,
so run it against a development or staging database, not production.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import secrets
from typing import Any, Callable

import httpx


Validator = Callable[[dict[str, Any]], tuple[bool, str]]


@dataclass(slots=True)
class CheckResult:
    module: str
    name: str
    method: str
    path: str
    status: str
    http_status: int | None
    detail: str


def api_data(payload: dict[str, Any]) -> Any:
    return payload.get("data") if isinstance(payload, dict) else None


def validate_success(payload: dict[str, Any]) -> tuple[bool, str]:
    ok = payload.get("code") == 0 and "trace_id" in payload
    return ok, "code=0 且包含 trace_id" if ok else "缺少统一成功响应字段"


def validate_register(payload: dict[str, Any]) -> tuple[bool, str]:
    ok, detail = validate_success(payload)
    data = api_data(payload) or {}
    ok = ok and bool(data.get("user_id")) and bool(data.get("username"))
    return ok, "返回 user_id/username" if ok else detail


def validate_login(payload: dict[str, Any]) -> tuple[bool, str]:
    ok, detail = validate_success(payload)
    data = api_data(payload) or {}
    ok = ok and bool(data.get("access_token")) and isinstance(data.get("user"), dict)
    return ok, "返回 access_token/user" if ok else detail


def validate_list(key: str, require_data: bool = True) -> Validator:
    def validator(payload: dict[str, Any]) -> tuple[bool, str]:
        ok, detail = validate_success(payload)
        data = api_data(payload) or {}
        items = data.get(key)
        ok = ok and isinstance(items, list)
        if not ok:
            return False, f"data.{key} 不是数组；{detail}"
        if require_data and not items:
            return False, f"data.{key} 为空，无法验证页面展示"
        return True, f"data.{key}={len(items)}"

    return validator


def validate_line_detail(payload: dict[str, Any]) -> tuple[bool, str]:
    ok, detail = validate_success(payload)
    data = api_data(payload) or {}
    stations = data.get("stations")
    ok = ok and bool(data.get("line_id")) and isinstance(stations, list)
    return ok, f"line_id={data.get('line_id')}，stations={len(stations or [])}" if ok else detail


def validate_ai(payload: dict[str, Any]) -> tuple[bool, str]:
    ok, detail = validate_success(payload)
    data = api_data(payload) or {}
    ok = ok and bool(data.get("answer")) and isinstance(data.get("fallback"), bool)
    return ok, f"answer 已返回，fallback={data.get('fallback')}" if ok else detail


def validate_recommend(payload: dict[str, Any]) -> tuple[bool, str]:
    ok, detail = validate_success(payload)
    data = api_data(payload) or {}
    items = data.get("items")
    ok = ok and isinstance(items, list) and bool(items)
    return ok, f"data.items={len(items or [])}" if ok else detail


class Runner:
    def __init__(self, base_url: str, timeout: float) -> None:
        # Integration targets are normally localhost/LAN services. Ignoring
        # workstation proxy variables prevents local checks from requiring
        # optional SOCKS dependencies or being routed outside the machine.
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            trust_env=False,
        )
        self.results: list[CheckResult] = []

    def close(self) -> None:
        self.client.close()

    def blocked(self, module: str, name: str, method: str, path: str, detail: str) -> None:
        self.results.append(CheckResult(module, name, method, path, "BLOCKED", None, detail))

    def call(
        self,
        module: str,
        name: str,
        method: str,
        path: str,
        expected_status: int,
        validator: Validator,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        try:
            response = self.client.request(method, path, json=json_body, headers=headers)
        except httpx.RequestError as exc:
            self.results.append(
                CheckResult(module, name, method, path, "FAIL", None, f"连接失败：{exc}")
            )
            return None

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        valid, detail = validator(payload)
        status = "PASS" if response.status_code == expected_status and valid else "FAIL"
        if response.status_code != expected_status:
            message = payload.get("message") or (payload.get("detail") or {}).get("message")
            detail = f"期望 HTTP {expected_status}，实际 {response.status_code}；{message or detail}"
        self.results.append(
            CheckResult(module, name, method, path, status, response.status_code, detail)
        )
        return payload if status == "PASS" else None


def build_markdown(results: list[CheckResult], base_url: str) -> str:
    counts = {status: sum(item.status == status for item in results) for status in ("PASS", "FAIL", "BLOCKED")}
    lines = [
        "# BusMind 重点接口联调检查结果",
        "",
        f"> 目标：`{base_url}`；生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        f"通过 {counts['PASS']}，失败 {counts['FAIL']}，阻塞 {counts['BLOCKED']}。",
        "",
        "| 模块 | 检查 | 请求 | 状态 | HTTP | 说明 |",
        "|---|---|---|---|---:|---|",
    ]
    for item in results:
        request = f"`{item.method} {item.path}`"
        http_status = "-" if item.http_status is None else str(item.http_status)
        lines.append(
            f"| {item.module} | {item.name} | {request} | {item.status} | {http_status} | {item.detail} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查登录注册、线路、地图、AI 和推荐重点接口")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--report", type=Path, help="可选 Markdown 报告输出路径")
    args = parser.parse_args()

    suffix = datetime.now().strftime("%m%d%H%M%S")
    username = f"jointest_{suffix}"
    password = f"Join-{secrets.token_urlsafe(9)}"
    runner = Runner(args.base_url, args.timeout)

    try:
        runner.call("环境", "API v1 健康检查", "GET", "/api/v1/", 200, validate_success)
        runner.call(
            "登录注册",
            "注册",
            "POST",
            "/api/v1/users/register",
            201,
            validate_register,
            json_body={
                "username": username,
                "password": password,
                "nickname": "联调检查用户",
                "role": "passenger",
            },
        )
        login = runner.call(
            "登录注册",
            "登录",
            "POST",
            "/api/v1/users/login",
            200,
            validate_login,
            json_body={"username": username, "password": password},
        )
        token = ((api_data(login) or {}).get("access_token") if login else None)
        if token:
            runner.call(
                "登录注册",
                "Bearer Token",
                "GET",
                "/api/v1/users/me",
                200,
                validate_success,
                headers={"Authorization": f"Bearer {token}"},
            )

        lines_payload = runner.call(
            "线路列表", "列表与分页", "GET", "/api/v1/lines?page=1&limit=20", 200, validate_list("lines")
        )
        line_items = ((api_data(lines_payload) or {}).get("lines") or []) if lines_payload else []
        detail_payload: dict[str, Any] | None = None
        if line_items:
            line_id = line_items[0].get("line_id")
            detail_payload = runner.call(
                "线路详情", "详情与站序", "GET", f"/api/v1/lines/{line_id}", 200, validate_line_detail
            )
        else:
            runner.blocked("线路详情", "详情与站序", "GET", "/api/v1/lines/{line_id}", "线路列表无可展示数据")

        runner.call("地图", "站点坐标", "GET", "/api/v1/map/stations", 200, validate_list("stations"))
        runner.call("地图", "线路折线", "GET", "/api/v1/map/lines", 200, validate_list("lines"))
        runner.call(
            "AI 助手",
            "QA 与 fallback",
            "POST",
            "/api/v1/ai/travel",
            200,
            validate_ai,
            json_body={"mode": "qa", "question": "当前公交出行有什么建议？", "preference": "balanced"},
        )

        stations = ((api_data(detail_payload) or {}).get("stations") or []) if detail_payload else []
        if len(stations) >= 2:
            start_id = stations[0].get("station_id")
            end_id = stations[-1].get("station_id")
            runner.call(
                "路线推荐",
                "综合推荐",
                "POST",
                "/api/v1/recommend-routes",
                200,
                validate_recommend,
                json_body={
                    "start_station_id": start_id,
                    "end_station_id": end_id,
                    "preference": "balanced",
                    "allow_transfer": True,
                    "max_transfer_count": 1,
                },
            )
        else:
            runner.blocked("路线推荐", "综合推荐", "POST", "/api/v1/recommend-routes", "线路详情不足两个站点")
    finally:
        runner.close()

    markdown = build_markdown(runner.results, args.base_url)
    print(markdown)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown, encoding="utf-8")

    return 0 if all(item.status == "PASS" for item in runner.results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
