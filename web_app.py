"""Flask 網頁版入口：保留原本 Tkinter 配色與卡片感，並加上手機響應式版面。

啟動方式：
    pip install -r requirements-web.txt
    python web_app.py
然後打開 http://127.0.0.1:5000
"""
from __future__ import annotations

from datetime import date, datetime, time as dt_time
import os
import sqlite3
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from functools import wraps
from typing import Any, Dict, List

import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from daily_tech_analysis import generate_daily_tech_dashboard
from screener_core import (
    TOP_RECOMMENDATIONS_CSV_PATH,
    USER_AGENT,
    build_avg_revenue_growth_map,
    build_official_financial_map,
    build_preferred_dashboard,
    build_twse_history_map,
    build_twse_valuation_map,
    build_universe,
    load_dashboard_cache,
    default_config,
    fetch_market_index,
    fetch_realtime_quotes,
    fetch_stock_metrics_with_retry,
    save_csv,
)
from tw_stock_gui import (
    build_condition_rows,
    build_sell_reasons,
    format_podcast_signal_source,
    load_json_payload,
    load_podcast_recommendations,
    load_podcast_report_meta,
    fallback_business_summary,
    load_watchlist_data,
    rank_badge,
    save_watchlist_data,
    strategy_lines,
    trend_text,
)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-this-secret-key")

@app.after_request
def add_no_cache_headers(response):
    if request.path in ("/", "/login", "/register", "/signup"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = Path(BASE_DIR)
DB_PATH = os.environ.get("AI_WEB_DB_PATH", os.path.join(BASE_DIR, "users.db"))
TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def taiwan_now() -> datetime:
    return datetime.now(TAIPEI_TZ)


def taiwan_now_text(seconds: bool = True) -> str:
    return taiwan_now().strftime("%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M")


def is_tw_market_session(dt: datetime | None = None) -> bool:
    dt = dt or taiwan_now()
    # 台股一般交易時間：週一至週五 09:00-13:30（不判斷國定假日；休市日會使用最近報價）
    return dt.weekday() < 5 and dt_time(9, 0) <= dt.time() <= dt_time(13, 30)

_dashboard_cache: Dict[str, Any] | None = None
_watch_rows_cache: List[Dict[str, Any]] = []
_analysis_cache: Dict[str, Any] | None = None
_last_error: str = ""
_live_payload_cache: Dict[str, Any] | None = None
_last_live_fetch_at: float = 0.0
LIVE_REFRESH_SECONDS = 0
SERVER_LIVE_COOLDOWN_SECONDS = 0




def db_conn() -> sqlite3.Connection:
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                real_name TEXT DEFAULT '',
                display_name TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS virtual_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT DEFAULT '',
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity INTEGER NOT NULL DEFAULT 1000,
                status TEXT NOT NULL DEFAULT 'open',
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                profit_loss REAL,
                profit_loss_pct REAL,
                is_win INTEGER,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(user_id, stock_code),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        try:
            conn.execute("ALTER TABLE users ADD COLUMN real_name TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        conn.commit()


def current_user() -> Dict[str, Any] | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    with db_conn() as conn:
        user = conn.execute("SELECT id, username, real_name, display_name, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(user) if user else None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("請先登入或註冊後再使用系統。")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapper


def order_stats(user_id: int | None = None) -> Dict[str, Any]:
    where = "WHERE user_id = ?" if user_id else ""
    params = (user_id,) if user_id else ()
    with db_conn() as conn:
        rows = conn.execute(f"SELECT status, is_win, profit_loss, profit_loss_pct FROM virtual_orders {where}", params).fetchall()
    total = len(rows)
    closed_rows = [r for r in rows if r["status"] == "closed"]
    wins = sum(1 for r in closed_rows if r["is_win"] == 1)
    losses = sum(1 for r in closed_rows if r["is_win"] == 0)
    closed = len(closed_rows)
    total_pl = sum(float(r["profit_loss"] or 0) for r in closed_rows)
    avg_pct = (sum(float(r["profit_loss_pct"] or 0) for r in closed_rows) / closed) if closed else 0
    return {
        "total": total,
        "open": total - closed,
        "closed": closed,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / closed * 100) if closed else 0,
        "total_pl": total_pl,
        "avg_pct": avg_pct,
    }


def leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    with db_conn() as conn:
        users = conn.execute("SELECT id, username, display_name FROM users ORDER BY id ASC").fetchall()
    result = []
    for user in users:
        stats = order_stats(user["id"])
        if stats["closed"] > 0 or stats["open"] > 0:
            result.append({"username": user["display_name"] or user["username"], **stats})
    result.sort(key=lambda x: (x["win_rate"], x["closed"], x["total_pl"]), reverse=True)
    return result[:limit]


def user_orders(user_id: int) -> List[Dict[str, Any]]:
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM virtual_orders
            WHERE user_id = ?
            ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, opened_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_realtime_quote_map(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    clean_codes = sorted({str(code).strip() for code in codes if str(code).strip()})
    if not clean_codes:
        return {}
    try:
        with requests.Session() as req_session:
            req_session.headers.update({"User-Agent": USER_AGENT})
            return fetch_realtime_quotes(req_session, [{"code": code} for code in clean_codes])
    except Exception:
        return {}


def user_watchlist_payload(user_id: int) -> Dict[str, Any]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT stock_code AS code, stock_name AS name FROM user_watchlist WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return {"stocks": [dict(row) for row in rows], "history": {}}


def add_user_watchlist(user_id: int, code: str, name: str) -> None:
    with db_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_watchlist (user_id, stock_code, stock_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, code, name, taiwan_now_text()),
        )
        conn.commit()


def delete_user_watchlist(user_id: int, code: str) -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM user_watchlist WHERE user_id = ? AND stock_code = ?", (user_id, code))
        conn.commit()


def user_watchlist_rows(user_id: int) -> List[Dict[str, Any]]:
    payload = user_watchlist_payload(user_id)
    return fetch_watchlist_rows([item.get("code") for item in payload.get("stocks", [])])


def watchlist_view_for_user(user_id: int) -> List[Dict[str, Any]]:
    payload = user_watchlist_payload(user_id)
    rows = user_watchlist_rows(user_id)
    rows_by_code = {item.get("code"): item for item in rows}
    result = []
    for item in payload.get("stocks", []):
        code = item.get("code")
        row = rows_by_code.get(code)
        if row:
            level, reasons = build_sell_reasons(row)
            result.append({"code": code, "name": row.get("name") or item.get("name", code), "price": fmt(row.get("price")), "trend": css_trend(row), "previous_close": fmt(row.get("previous_close")), "sell_level": level, "sell_reasons": reasons, "updated": row.get("realtime_at") or taiwan_now().date().isoformat(), "history": {}})
        else:
            result.append({"code": code, "name": item.get("name", code), "price": "--", "trend": {"text": "--", "class": "flat"}, "previous_close": "--", "sell_level": "--", "sell_reasons": [], "updated": "--", "history": {}})
    return result


def enrich_orders_with_live(orders: List[Dict[str, Any]], quotes: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    quotes = quotes if quotes is not None else get_realtime_quote_map([o.get("stock_code") for o in orders if o.get("status") == "open"])
    enriched = []
    for order in orders:
        item = dict(order)
        if item.get("status") == "open":
            quote = quotes.get(str(item.get("stock_code"))) or {}
            current_price = quote.get("price")
            item["current_price"] = current_price
            item["current_at"] = quote.get("realtime_at") or "--"
            try:
                if current_price is not None:
                    entry = float(item.get("entry_price") or 0)
                    qty = int(item.get("quantity") or 0)
                    item["unrealized_pl"] = (float(current_price) - entry) * qty
                    item["unrealized_pct"] = ((float(current_price) - entry) / entry * 100) if entry else 0
                else:
                    item["unrealized_pl"] = 0
                    item["unrealized_pct"] = 0
            except Exception:
                item["unrealized_pl"] = 0
                item["unrealized_pct"] = 0
        else:
            item["current_price"] = item.get("exit_price")
            item["current_at"] = item.get("closed_at") or "--"
            item["unrealized_pl"] = item.get("profit_loss") or 0
            item["unrealized_pct"] = item.get("profit_loss_pct") or 0
        enriched.append(item)
    return enriched


def portfolio_stats(user_id: int) -> Dict[str, Any]:
    orders = user_orders(user_id)
    enriched = enrich_orders_with_live(orders)
    base = order_stats(user_id)
    open_pl = sum(float(o.get("unrealized_pl") or 0) for o in enriched if o.get("status") == "open")
    open_cost = sum(float(o.get("entry_price") or 0) * int(o.get("quantity") or 0) for o in enriched if o.get("status") == "open")
    closed_cost = 0.0
    for o in orders:
        if o.get("status") == "closed":
            closed_cost += float(o.get("entry_price") or 0) * int(o.get("quantity") or 0)
    total_cost = open_cost + closed_cost
    cumulative_pl = float(base.get("total_pl") or 0) + open_pl
    cumulative_pct = (cumulative_pl / total_cost * 100) if total_cost else 0
    return {**base, "open_pl": open_pl, "cumulative_pl": cumulative_pl, "cumulative_pct": cumulative_pct, "total_cost": total_cost}


def all_user_performance(limit: int = 30) -> List[Dict[str, Any]]:
    with db_conn() as conn:
        users = conn.execute("SELECT id, username, display_name FROM users ORDER BY id ASC").fetchall()
    result = []
    for user in users:
        stats = portfolio_stats(user["id"])
        if stats["total"] > 0:
            result.append({"username": user["display_name"] or user["username"], **stats})
    result.sort(key=lambda x: (x["cumulative_pl"], x["cumulative_pct"], x["win_rate"]), reverse=True)
    return result[:limit]


def chat_messages(limit: int = 50) -> List[Dict[str, Any]]:
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT chat_messages.id, chat_messages.message, chat_messages.created_at, COALESCE(NULLIF(users.display_name, ''), users.username) AS username
            FROM chat_messages JOIN users ON users.id = chat_messages.user_id
            ORDER BY chat_messages.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]

def fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value is None or value == "":
        return "--"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def css_trend(row: Dict[str, Any]) -> Dict[str, str]:
    text, color = trend_text(row)
    cls = "flat"
    if text.startswith("▲"):
        cls = "up"
    elif text.startswith("▼"):
        cls = "down"
    return {"text": text, "class": cls, "color": color}


def condition_view(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"label": label, "passed": bool(passed)} for label, passed in build_condition_rows(row)]


def display_rows(dashboard: Dict[str, Any], limit: int = 5) -> tuple[List[Dict[str, Any]], str]:
    rows = (dashboard.get("top_stocks") or [])[:limit]
    mode = dashboard.get("display_mode") or ("passed" if dashboard.get("passed_stocks") else "fallback")
    return rows, mode


def summary_items(rows: List[Dict[str, Any]], mode: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for index, row in enumerate(rows):
        summary = fallback_business_summary(row)
        quality = row.get("selection_tier") or ("精選" if row.get("hard_filter_pass") else "候補")
        items.append(
            {
                "rank": rank_badge(index),
                "quality": quality,
                "code": row.get("code", ""),
                "name": row.get("name", ""),
                "price": fmt(row.get("price")),
                "score": fmt(row.get("recommendation_score")),
                "roe": fmt(row.get("roe"), suffix="%"),
                "summary": summary.get("summary", ""),
                "label": summary.get("label", ""),
                "url": summary.get("url", ""),
            }
        )
    return items


def load_mobile_dashboard() -> Dict[str, Any]:
    cached = load_dashboard_cache(require_fresh=False)
    if cached:
        return cached
    return load_dashboard(force=False)


def watchlist_snapshot_view() -> List[Dict[str, Any]]:
    payload = load_watchlist_data()
    history = payload.get("history") or {}
    gui_snapshot = load_json_payload(BASE_PATH / "tw_stock_gui_snapshot.json")
    snapshot_rows = gui_snapshot.get("watch_rows") or []
    snapshot_rows_by_code = {str(row.get("code") or ""): row for row in snapshot_rows if row.get("code")}
    result = []
    for item in payload.get("stocks", []):
        code = item.get("code")
        snapshot_row = snapshot_rows_by_code.get(str(code))
        if snapshot_row:
            level, reasons = build_sell_reasons(snapshot_row)
            result.append(
                {
                    "code": code,
                    "name": snapshot_row.get("name") or item.get("name", code),
                    "price": fmt(snapshot_row.get("price")),
                    "trend": css_trend(snapshot_row),
                    "previous_close": fmt(snapshot_row.get("previous_close")),
                    "sell_level": level,
                    "sell_reasons": reasons,
                    "sell_message": "；".join(reasons) if reasons else f"{level}，目前沒有明確賣出訊號。",
                    "updated": snapshot_row.get("realtime_at") or "--",
                    "history": history.get(code, {}),
                }
            )
            continue
        code_history = history.get(code) or {}
        latest_date = max(code_history) if code_history else "--"
        latest = code_history.get(latest_date, {}) if code_history else {}
        change_pct = latest.get("change_pct")
        trend_class = "flat"
        trend_text_value = "--"
        if change_pct is not None:
            trend_class = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
            trend_text_value = f"{change_pct:+.2f}%"
        result.append(
            {
                "code": code,
                "name": item.get("name", code),
                "price": fmt(latest.get("price")),
                "trend": {"text": trend_text_value, "class": trend_class},
                "previous_close": fmt(latest.get("previous_close")),
                "sell_level": "資料不足",
                "sell_reasons": [],
                "sell_message": "尚未同步賣出訊號，請先在桌面版更新一次自選股。",
                "updated": latest_date,
                "history": code_history,
            }
        )
    return result


def mobile_snapshot_context() -> Dict[str, Any]:
    dashboard = load_mobile_dashboard()
    rows, mode = display_rows(dashboard, limit=5)
    watchlist_rows = watchlist_view()
    snapshot_rows = watchlist_snapshot_view()
    gui_snapshot = load_json_payload(BASE_PATH / "tw_stock_gui_snapshot.json")
    snapshot_by_code = {str(item.get("code") or ""): item for item in snapshot_rows}
    merged_watchlist = []
    for item in watchlist_rows:
        code = str(item.get("code") or "")
        snapshot_item = snapshot_by_code.get(code, {})
        merged_watchlist.append(
            {
                **snapshot_item,
                **item,
                "sell_level": item.get("sell_level") if item.get("sell_level") not in (None, "", "--") else snapshot_item.get("sell_level", "--"),
                "sell_reasons": item.get("sell_reasons") or snapshot_item.get("sell_reasons", []),
                "sell_message": "；".join(item.get("sell_reasons") or snapshot_item.get("sell_reasons", []))
                or (
                    item.get("sell_level")
                    if item.get("sell_level") not in (None, "", "--")
                    else snapshot_item.get("sell_message", "尚未同步賣出訊號，請先在桌面版更新一次自選股。")
                ),
                "updated": item.get("updated") if item.get("updated") not in (None, "", "--") else snapshot_item.get("updated", "--"),
            }
        )
    if not any(item.get("price") not in (None, "", "--") for item in merged_watchlist):
        merged_watchlist = snapshot_rows
    analysis = load_analysis()
    if not analysis and isinstance(gui_snapshot.get("analysis"), dict):
        analysis = gui_snapshot.get("analysis")
    podcast_block = gui_snapshot.get("podcast") if isinstance(gui_snapshot.get("podcast"), dict) else {}
    podcast_meta = load_podcast_report_meta()
    if not podcast_meta.get("summary") and isinstance(podcast_block.get("meta"), dict):
        podcast_meta = podcast_block.get("meta")
    podcast_rows = load_podcast_recommendations()
    if not podcast_rows and isinstance(podcast_block.get("rows"), list):
        podcast_rows = podcast_block.get("rows")
    return {
        "dashboard": dashboard,
        "rows": rows,
        "summaries": summary_items(rows, mode),
        "mode": mode,
        "watchlist": merged_watchlist,
        "analysis": analysis or {},
        "podcast_meta": podcast_meta,
        "podcast_rows": podcast_rows[:10],
        "podcast_signal_source": format_podcast_signal_source(
            (podcast_meta or {}).get("signal_source", "rule"),
            (podcast_meta or {}).get("generation_mode", ""),
        ),
        "generated_at": taiwan_now_text(),
    }


def trend_payload(price_change_pct: Any) -> Dict[str, str]:
    value = None
    try:
        value = float(price_change_pct)
    except (TypeError, ValueError):
        value = None
    if value is None:
        return {"text": "--", "class": "flat"}
    if value > 0:
        return {"text": f"▲ {value:.2f}%", "class": "up"}
    if value < 0:
        return {"text": f"▼ {value:.2f}%", "class": "down"}
    return {"text": "0.00%", "class": "flat"}


def apply_live_quotes(rows: List[Dict[str, Any]], quotes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated = []
    for row in rows:
        code = row.get("code")
        quote = quotes.get(str(code)) if code else None
        if quote:
            row.update({
                "price": quote.get("price", row.get("price")),
                "previous_close": quote.get("previous_close", row.get("previous_close")),
                "price_change": quote.get("price_change", row.get("price_change")),
                "price_change_pct": quote.get("price_change_pct", row.get("price_change_pct")),
                "last_volume": quote.get("last_volume", row.get("last_volume")),
                "realtime_at": quote.get("realtime_at", row.get("realtime_at")),
            })
        updated.append(row)
    return updated


def row_live_view(row: Dict[str, Any], index: int | None = None) -> Dict[str, Any]:
    match_count = (row.get("hard_filter_match_count", 0) or 0) + (row.get("condition_match_count", 0) or 0)
    trend = trend_payload(row.get("price_change_pct"))
    result = {
        "code": row.get("code"),
        "name": row.get("name"),
        "rank": rank_badge(index) if index is not None else "",
        "price": fmt(row.get("price")),
        "trend_text": trend["text"],
        "trend_class": trend["class"],
        "previous_close": fmt(row.get("previous_close")),
        "score": fmt(row.get("recommendation_score")),
        "match_count": match_count,
        "roe": fmt(row.get("roe")),
        "eps_growth": fmt(row.get("eps_growth")),
        "revenue_growth": fmt(row.get("avg_revenue_growth_3m")),
        "pct_change_20d": fmt(row.get("pct_change_20d")),
        "realtime_at": row.get("realtime_at") or "--",
    }
    return result


def market_live_view(data: Dict[str, Any] | None) -> Dict[str, str]:
    if not data:
        return {"title": "台股大盤指數 --", "detail": "等待即時報價刷新", "class": "flat"}
    trend = trend_payload(data.get("change_pct"))
    return {
        "title": f"台股大盤指數 {fmt(data.get('price'))}",
        "detail": f"漲跌 {fmt(data.get('change'))} / {fmt(data.get('change_pct'), suffix='%')}｜{data.get('realtime_at') or ''}",
        "class": trend["class"],
    }


def build_live_payload(force: bool = False, user_id: int | None = None) -> Dict[str, Any]:
    global _live_payload_cache, _last_live_fetch_at
    now_ts = time.time()
    if user_id is None and (not force) and _live_payload_cache and now_ts - _last_live_fetch_at < 3600:
        return _live_payload_cache

    dashboard = load_dashboard(force=force)
    rows, mode = display_rows(dashboard)
    analysis = load_analysis()
    analysis_companies = (analysis or {}).get("companies") or []
    payload = {
        "ok": True,
        "error": "",
        "server_time": taiwan_now_text(),
        "market_session": False,
        "next_refresh_seconds": 0,
        "snapshot_date": dashboard.get("snapshot_date"),
        "mode": mode,
        "market_index": market_index_view(),
        "top": [row_live_view(row, index) for index, row in enumerate(rows)],
        "watchlist": watchlist_view_for_user(user_id) if user_id else [],
        "analysis_companies": [
            {"code": str(company.get("code") or ""), "name": company.get("name", ""), "price": "--", "trend_text": "--", "trend_class": "flat", "realtime_at": dashboard.get("snapshot_date") or "--"}
            for company in analysis_companies
        ],
        "virtual_orders": enrich_orders_with_live(user_orders(user_id)) if user_id else [],
        "my_stats": portfolio_stats(user_id) if user_id else None,
        "leaderboard": all_user_performance() if user_id else [],
    }
    if user_id is None:
        _live_payload_cache = payload
        _last_live_fetch_at = now_ts
    return payload

def fetch_watchlist_rows(codes: List[str]) -> List[Dict[str, Any]]:
    clean_codes = [str(code).strip() for code in codes if str(code).strip()]
    if not clean_codes:
        return []
    config = default_config()
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        universe = build_universe(session)
        candidate_map = {item.code: item for item in universe}
        candidates = [candidate_map[code] for code in clean_codes if code in candidate_map]
        if not candidates:
            return []
        history_map = build_twse_history_map(session)
        financial_map = build_official_financial_map(session, candidates)
        valuation_map = build_twse_valuation_map(session, candidates)
        revenue_map = build_avg_revenue_growth_map(session)
        rows = []
        for candidate in candidates:
            stock = fetch_stock_metrics_with_retry(candidate, config, revenue_map, history_map, financial_map, valuation_map)
            if stock:
                rows.append(stock)
    order = {code: index for index, code in enumerate(clean_codes)}
    rows.sort(key=lambda item: order.get(item["code"], 9999))
    update_watch_history(rows)
    return rows


def update_watch_history(rows: List[Dict[str, Any]]) -> None:
    payload = load_watchlist_data()
    today_text = taiwan_now().date().isoformat()
    history = payload.setdefault("history", {})
    for row in rows:
        code = row.get("code")
        if not code:
            continue
        history.setdefault(code, {})[today_text] = {
            "price": row.get("price"),
            "change_pct": row.get("price_change_pct"),
            "previous_close": row.get("previous_close"),
        }
    save_watchlist_data(payload)


def load_dashboard(force: bool = False) -> Dict[str, Any]:
    global _dashboard_cache, _watch_rows_cache, _last_error
    if _dashboard_cache is not None and not force:
        return _dashboard_cache
    try:
        dashboard = build_preferred_dashboard(30, use_cache=not force)
        save_csv(TOP_RECOMMENDATIONS_CSV_PATH, (dashboard.get("top_stocks") or [])[:10])
        _watch_rows_cache = []
        _dashboard_cache = dashboard
        _last_error = ""
    except Exception as exc:
        _last_error = str(exc)
        if _dashboard_cache is None:
            _dashboard_cache = {"passed_stocks": [], "fallback_stocks": [], "snapshot_date": "--", "analyzed_count": 0, "failed_count": 0}
    return _dashboard_cache


def load_analysis(force: bool = False) -> Dict[str, Any] | None:
    global _analysis_cache
    if _analysis_cache is not None and not force:
        return _analysis_cache
    try:
        _analysis_cache = generate_daily_tech_dashboard(hours=24, limit=5)
    except Exception:
        _analysis_cache = None
    return _analysis_cache


def market_index_view() -> Dict[str, str]:
    try:
        with requests.Session() as session:
            session.headers.update({"User-Agent": USER_AGENT})
            data = fetch_market_index(session)
    except Exception:
        data = None
    if not data:
        return {"title": "台股大盤指數 --", "detail": "等待即時報價刷新", "class": "flat"}
    change_pct = data.get("change_pct")
    cls = "flat"
    if change_pct and change_pct > 0:
        cls = "up"
    elif change_pct and change_pct < 0:
        cls = "down"
    return {
        "title": f"台股大盤指數 {fmt(data.get('price'))}",
        "detail": f"漲跌 {fmt(data.get('change'))} / {fmt(change_pct, suffix='%')}｜{data.get('realtime_at') or ''}",
        "class": cls,
    }


def watchlist_view() -> List[Dict[str, Any]]:
    watchlist = load_watchlist_data()
    rows_by_code = {item.get("code"): item for item in _watch_rows_cache}
    result = []
    for item in watchlist.get("stocks", []):
        code = item.get("code")
        row = rows_by_code.get(code)
        if row:
            level, reasons = build_sell_reasons(row)
            result.append({"code": code, "name": row.get("name") or item.get("name", code), "price": fmt(row.get("price")), "trend": css_trend(row), "previous_close": fmt(row.get("previous_close")), "sell_level": level, "sell_reasons": reasons, "updated": row.get("realtime_at") or taiwan_now().date().isoformat(), "history": (watchlist.get("history") or {}).get(code, {})})
        else:
            result.append({"code": code, "name": item.get("name", code), "price": "--", "trend": {"text": "--", "class": "flat"}, "previous_close": "--", "sell_level": "--", "sell_reasons": [], "updated": "--", "history": (watchlist.get("history") or {}).get(code, {})})
    return result


@app.route("/")
def index():
    user = current_user()
    if not user:
        return render_template(
            "index.html",
            auth_only=True,
            dashboard={"snapshot_date": "--", "analyzed_count": 0, "failed_count": 0},
            rows=[],
            mode="passed",
            strategy_lines=[],
            summary_items=[],
            market_index={"title": "登入後可查看台股大盤與個人化內容", "detail": "請先註冊或登入", "class": "flat"},
            watchlist=[],
            analysis=None,
            last_error="",
            now=taiwan_now_text(),
            fmt=fmt,
            css_trend=css_trend,
            condition_view=condition_view,
            rank_badge=rank_badge,
            current_user=None,
            virtual_orders=[],
            my_stats=None,
            leaderboard=[],
            messages=[],
        )

    dashboard = load_dashboard(force=request.args.get("refresh") == "1")
    rows, mode = display_rows(dashboard)
    analysis = load_analysis(force=request.args.get("analysis_refresh") == "1")
    orders = enrich_orders_with_live(user_orders(user["id"]))
    return render_template(
        "index.html",
        auth_only=False,
        dashboard=dashboard,
        rows=rows,
        mode=mode,
        strategy_lines=strategy_lines(),
        summary_items=summary_items(rows, mode),
        market_index=market_index_view(),
        watchlist=watchlist_view_for_user(user["id"]),
        analysis=analysis,
        last_error=_last_error,
        now=taiwan_now_text(),
        fmt=fmt,
        css_trend=css_trend,
        condition_view=condition_view,
        rank_badge=rank_badge,
        current_user=user,
        virtual_orders=orders,
        my_stats=portfolio_stats(user["id"]),
        leaderboard=all_user_performance(),
        messages=chat_messages(),
    )


@app.route("/mobile")
def mobile():
    return render_template("mobile_snapshot.html", **mobile_snapshot_context())


@app.route("/mobile/download")
def mobile_download():
    path = BASE_PATH / "mobile_snapshot_offline.html"
    if not path.exists():
        return redirect(url_for("mobile"))
    return send_file(path, as_attachment=True, download_name="mobile_snapshot_offline.html", mimetype="text/html")


@app.post("/watchlist/add")
@login_required
def add_watchlist():
    code = request.form.get("code", "").strip()
    if not code or not code.isdigit():
        return redirect(url_for("index", tab="watchlist"))
    name = code
    try:
        with requests.Session() as req_session:
            req_session.headers.update({"User-Agent": USER_AGENT})
            candidate_map = {item.code: item for item in build_universe(req_session)}
            if code in candidate_map:
                name = candidate_map[code].name
    except Exception:
        pass
    add_user_watchlist(session["user_id"], code, name)
    return redirect(url_for("index", tab="watchlist"))

@app.post("/watchlist/delete/<code>")
@login_required
def delete_watchlist(code: str):
    delete_user_watchlist(session["user_id"], code)
    return redirect(url_for("index", tab="watchlist"))



def _handle_register():
    username = request.form.get("username", "").strip()
    real_name = request.form.get("real_name", "").strip()
    display_name = request.form.get("display_name", "").strip()
    password = request.form.get("password", "")

    if not username:
        flash("請輸入帳號。")
        return redirect(url_for("register_page"))
    if not password:
        flash("請輸入密碼。")
        return redirect(url_for("register_page"))
    if not real_name or not display_name:
        flash("請填寫個人姓名與中文名稱。")
        return redirect(url_for("register_page"))

    try:
        with db_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, real_name, display_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, real_name, display_name, generate_password_hash(password), taiwan_now_text()),
            )
            conn.commit()
            session.clear()
            session["user_id"] = cursor.lastrowid
        flash("註冊成功，已自動登入。")
        return redirect(url_for("index", tab="recommend"))
    except sqlite3.IntegrityError:
        flash("這個帳號已經被註冊，請換一個帳號。")
        return redirect(url_for("register_page"))
    except Exception as exc:
        flash(f"註冊失敗：{exc}")
        return redirect(url_for("register_page"))


def _handle_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        flash("請輸入帳號與密碼。")
        return redirect(url_for("login_page"))
    with db_conn() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        flash("帳號或密碼錯誤。")
        return redirect(url_for("login_page"))
    session.clear()
    session["user_id"] = user["id"]
    flash("登入成功。")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        return _handle_login()
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template(
        "index.html",
        auth_only=True,
        dashboard={"snapshot_date": "--", "analyzed_count": 0, "failed_count": 0},
        rows=[],
        mode="passed",
        strategy_lines=[],
        summary_items=[],
        market_index={"title": "登入後可查看台股大盤與個人化內容", "detail": "請先註冊或登入", "class": "flat"},
        watchlist=[],
        analysis=None,
        last_error="",
        now=taiwan_now_text(),
        fmt=fmt,
        css_trend=css_trend,
        condition_view=condition_view,
        rank_badge=rank_badge,
        current_user=None,
        virtual_orders=[],
        my_stats=None,
        leaderboard=[],
        messages=[],
    )


@app.route("/register", methods=["GET", "POST"])
def register_page():
    # 重要：註冊頁永遠要能打開。
    # 之前這裡如果 session 裡已有 user_id 就會 302 導回首頁，
    # 使用者點「註冊」時就永遠看不到註冊表單。
    if request.method == "POST":
        return _handle_register()
    return render_template("register.html", now=taiwan_now_text())




@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    return register_page()

@app.post("/auth/register")
def register():
    return _handle_register()


@app.post("/auth/login")
def login():
    return _handle_login()


@app.post("/auth/logout")
def logout():
    session.clear()
    flash("已登出。")
    return redirect(url_for("login_page"))



def find_stock_name(code: str) -> str:
    try:
        with requests.Session() as req_session:
            req_session.headers.update({"User-Agent": USER_AGENT})
            candidate_map = {item.code: item for item in build_universe(req_session)}
            if code in candidate_map:
                return candidate_map[code].name
    except Exception:
        pass
    return code


def latest_stock_price(code: str) -> tuple[float | None, str, str]:
    quotes = get_realtime_quote_map([code])
    quote = quotes.get(str(code)) or {}
    price = quote.get("price") or quote.get("previous_close")
    quote_time = quote.get("realtime_at") or taiwan_now_text()
    session_note = "盤中即時價" if is_tw_market_session() else "非台股開盤時間，使用最近可取得報價"
    try:
        return (float(price), quote_time, session_note) if price is not None else (None, quote_time, session_note)
    except (TypeError, ValueError):
        return None, quote_time, session_note


@app.post("/virtual-orders/add")
@login_required
def add_virtual_order():
    stock_code = request.form.get("stock_code", "").strip()
    try:
        quantity = int(float(request.form.get("quantity", "0")))
    except ValueError:
        flash("股數格式錯誤。")
        return redirect(url_for("index", tab="virtual_orders"))
    if not stock_code or not stock_code.isdigit() or quantity <= 0:
        flash("請輸入有效的股票代號與股數。")
        return redirect(url_for("index", tab="virtual_orders"))

    entry_price, quote_time, price_note = latest_stock_price(stock_code)
    if entry_price is None or entry_price <= 0:
        flash("目前抓不到這檔股票的即時/最近報價，請確認股票代號或稍後再試。")
        return redirect(url_for("index", tab="virtual_orders"))

    stock_name = find_stock_name(stock_code)
    opened_at = taiwan_now_text(seconds=False)
    note = f"{price_note}；報價時間：{quote_time}"
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO virtual_orders
            (user_id, stock_code, stock_name, entry_price, quantity, status, opened_at, note, created_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)
            """,
            (session["user_id"], stock_code, stock_name, entry_price, quantity, opened_at, note, taiwan_now_text()),
        )
        conn.commit()
    flash(f"虛擬單已建立：{stock_code} 以 {entry_price:.2f} 元開倉，時間採台灣時間。")
    return redirect(url_for("index", tab="virtual_orders"))


@app.post("/virtual-orders/close/<int:order_id>")
@login_required
def close_virtual_order(order_id: int):
    try:
        exit_price = float(request.form.get("exit_price", "0"))
    except ValueError:
        flash("賣出價格格式錯誤。")
        return redirect(url_for("index"))
    if exit_price <= 0:
        flash("請輸入有效賣出價格。")
        return redirect(url_for("index"))
    closed_at = request.form.get("closed_at", "").strip() or taiwan_now_text(seconds=False)
    with db_conn() as conn:
        order = conn.execute(
            "SELECT * FROM virtual_orders WHERE id = ? AND user_id = ? AND status = 'open'",
            (order_id, session["user_id"]),
        ).fetchone()
        if not order:
            flash("找不到可平倉的虛擬單。")
            return redirect(url_for("index"))
        profit_loss = (exit_price - float(order["entry_price"])) * int(order["quantity"])
        profit_loss_pct = ((exit_price - float(order["entry_price"])) / float(order["entry_price"])) * 100
        conn.execute(
            """
            UPDATE virtual_orders
            SET exit_price = ?, status = 'closed', closed_at = ?, profit_loss = ?, profit_loss_pct = ?, is_win = ?
            WHERE id = ? AND user_id = ?
            """,
            (exit_price, closed_at, profit_loss, profit_loss_pct, 1 if profit_loss > 0 else 0, order_id, session["user_id"]),
        )
        conn.commit()
    flash("虛擬單已平倉並更新勝率。")
    return redirect(url_for("index"))


@app.post("/virtual-orders/delete/<int:order_id>")
@login_required
def delete_virtual_order(order_id: int):
    with db_conn() as conn:
        conn.execute("DELETE FROM virtual_orders WHERE id = ? AND user_id = ?", (order_id, session["user_id"]))
        conn.commit()
    flash("虛擬單已刪除。")
    return redirect(url_for("index"))


@app.post("/chat/add")
@login_required
def add_chat_message():
    message = request.form.get("message", "").strip()
    if not message:
        flash("留言內容不能空白。")
        return redirect(url_for("index", tab="chat"))
    if len(message) > 500:
        flash("留言最多 500 個字。")
        return redirect(url_for("index", tab="chat"))
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, message, created_at) VALUES (?, ?, ?)",
            (session["user_id"], message, taiwan_now_text()),
        )
        conn.commit()
    return redirect(url_for("index", tab="chat"))


@app.route("/api/live")
@login_required
def api_live():
    return jsonify(build_live_payload(force=request.args.get("force") == "1", user_id=session.get("user_id")))


@app.route("/api/status")
@login_required
def api_status():
    return jsonify(build_live_payload(user_id=session.get("user_id")))


init_db()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
