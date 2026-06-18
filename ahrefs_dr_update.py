#!/usr/bin/env python3
"""Update missing site weights from Ahrefs free Domain Rating API."""

import argparse
import concurrent.futures
import json
import sqlite3
from typing import Optional
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

from backlink_common import DB_PATH, migrate_database


API_ENDPOINT = "https://api.ahrefs.com/v3/public/domain-rating-free"


def extract_domain(site_url: str) -> Optional[str]:
    """Return a lowercase bare domain suitable for Ahrefs, or None."""
    value = (site_url or "").strip()
    if not value:
        return None
    if "://" not in value:
        value = f"https://{value}"
    try:
        parsed = urlparse(value)
        domain = parsed.hostname
    except ValueError:
        return None
    if not domain or any(ch.isspace() for ch in domain):
        return None
    domain = domain.rstrip(".").lower()
    if domain.startswith("www."):
        domain = domain[4:]
    if "." not in domain:
        return None
    return domain


def parse_domain_rating(payload: str) -> Optional[int]:
    """Parse Ahrefs JSON and return rounded integer DR, or None."""
    try:
        data = json.loads(payload)
        raw = data.get("domain_rating", {}).get("domain_rating")
        if raw is None:
            return None
        return int(round(float(raw)))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def build_api_url(domain: str) -> str:
    return f"{API_ENDPOINT}?{urlencode({'target': domain})}"


def fetch_dr(site_id: int, site_url: str, timeout: int) -> tuple[int, str, Optional[int], str]:
    domain = extract_domain(site_url)
    if not domain:
        return site_id, site_url, None, "invalid_url"
    try:
        with urlopen(build_api_url(domain), timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:
        return site_id, site_url, None, f"request_failed: {exc}"

    dr = parse_domain_rating(payload)
    if dr is None:
        return site_id, site_url, None, "missing_dr"
    return site_id, site_url, dr, "ok"


def get_missing_weight_sites(limit: Optional[int] = None) -> list[tuple[int, str]]:
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        query = "SELECT id, site_url FROM sites WHERE weight IS NULL ORDER BY id"
        params: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def apply_weight_updates(results: list[tuple[int, str, Optional[int], str]]) -> int:
    rows = [(dr, site_id) for site_id, _, dr, status in results if status == "ok" and dr is not None]
    if not rows:
        return 0
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executemany("UPDATE sites SET weight = ? WHERE id = ? AND weight IS NULL", rows)
        conn.commit()
        return conn.total_changes
    finally:
        conn.close()


def run_update(limit: Optional[int], workers: int, timeout: int, dry_run: bool) -> int:
    sites = get_missing_weight_sites(limit)
    if not sites:
        print("没有 weight 为空的站点")
        return 0

    print(f"待查询站点: {len(sites)}")
    results: list[tuple[int, str, Optional[int], str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_dr, site_id, site_url, timeout) for site_id, site_url in sites]
        for future in concurrent.futures.as_completed(futures):
            site_id, site_url, dr, status = future.result()
            results.append((site_id, site_url, dr, status))
            if status == "ok":
                print(f"OK   ID={site_id} DR={dr} {site_url}")
            else:
                print(f"SKIP ID={site_id} {status} {site_url}")

    success = sum(1 for _, _, dr, status in results if status == "ok" and dr is not None)
    if dry_run:
        print(f"Dry run: {success} 个站点可更新，未写入数据库")
        return success

    updated = apply_weight_updates(results)
    print(f"已更新: {updated} 个站点")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="用 Ahrefs 免费 DR API 补齐 sites.weight")
    parser.add_argument("--limit", type=int, help="只处理前 N 个 weight 为空的站点")
    parser.add_argument("--workers", type=int, default=10, help="并发数，默认 10")
    parser.add_argument("--timeout", type=int, default=8, help="单次请求超时秒数，默认 8")
    parser.add_argument("--dry-run", action="store_true", help="只查询和打印结果，不写数据库")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit 必须大于 0")
    if args.workers < 1:
        parser.error("--workers 必须大于 0")
    if args.timeout < 1:
        parser.error("--timeout 必须大于 0")

    run_update(args.limit, args.workers, args.timeout, args.dry_run)


if __name__ == "__main__":
    main()
