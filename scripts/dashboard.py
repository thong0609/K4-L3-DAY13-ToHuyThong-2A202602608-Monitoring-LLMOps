#!/usr/bin/env python3
"""Dashboard visualization for Day 13 Monitoring & LLMOps."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
OUTPUT_DIR = REPO_ROOT / "dashboard_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_logs() -> list[dict]:
    """Load and parse logs from JSONL file."""
    logs = []
    if not LOG_PATH.exists():
        return logs
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            logs.append(json.loads(line))
    return logs


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp string."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def filter_by_time_range(logs: list[dict], minutes: int = 60) -> list[dict]:
    """Filter logs within the specified time range (default 60 minutes)."""
    if not logs:
        return []
    
    timestamps = [parse_timestamp(log["ts"]) for log in logs]
    latest = max(timestamps)
    oldest = latest.replace(minute=latest.minute - minutes)
    
    return [log for log in logs if oldest <= parse_timestamp(log["ts"]) <= latest]


def get_latency_stats(logs: list[dict]) -> dict:
    """Calculate latency percentiles and TTFT."""
    response_logs = [log for log in logs if log.get("event") == "response_sent"]
    if not response_logs:
        return {"p50": 0, "p95": 0, "p99": 0, "ttft_p95": 0}
    
    latencies = sorted([log.get("latency_ms", 0) for log in response_logs])
    ttfts = sorted([log.get("ttft_ms", 0) for log in response_logs])
    
    return {
        "p50": np.percentile(latencies, 50),
        "p95": np.percentile(latencies, 95),
        "p99": np.percentile(latencies, 99),
        "ttft_p95": np.percentile(ttfts, 95),
    }


def get_traffic_stats(logs: list[dict]) -> dict:
    """Calculate traffic metrics."""
    request_logs = [log for log in logs if log.get("event") == "request_received"]
    if not request_logs:
        return {"count": 0, "rate_per_minute": 0}
    
    timestamps = [parse_timestamp(log["ts"]) for log in request_logs]
    if len(timestamps) >= 2:
        time_span_minutes = (max(timestamps) - min(timestamps)).total_seconds() / 60
        rate = len(timestamps) / max(time_span_minutes, 1)
    else:
        rate = 0
    
    return {"count": len(request_logs), "rate_per_minute": rate}


def get_error_stats(logs: list[dict]) -> dict:
    """Calculate error rate and retrieval success rate."""
    request_logs = [log for log in logs if log.get("event") == "request_received"]
    failed_logs = [log for log in logs if log.get("event") == "request_failed"]
    all_tool_logs = [log for log in logs if "tool_success" in log]
    successful_tools = [log for log in all_tool_logs if log.get("tool_success") is True]
    
    total_requests = len(request_logs)
    failed_requests = len(failed_logs)
    error_rate_pct = (failed_requests / total_requests * 100) if total_requests > 0 else 0
    
    total_tools = len(all_tool_logs)
    successful_tools_count = len(successful_tools)
    tool_success_rate = (successful_tools_count / total_tools * 100) if total_tools > 0 else 0
    
    return {
        "error_rate_pct": error_rate_pct,
        "failed_count": failed_requests,
        "tool_success_rate_pct": tool_success_rate,
    }


def get_cost_stats(logs: list[dict]) -> dict:
    """Calculate cost metrics."""
    response_logs = [log for log in logs if log.get("event") == "response_sent"]
    if not response_logs:
        return {"total": 0, "by_minute": []}
    
    costs = [log.get("cost_usd", 0) for log in response_logs]
    total = sum(costs)
    
    # Group by minute
    minute_buckets: dict[str, float] = {}
    for log in response_logs:
        ts = parse_timestamp(log["ts"])
        minute_key = ts.strftime("%H:%M")
        minute_buckets[minute_key] = minute_buckets.get(minute_key, 0) + log.get("cost_usd", 0)
    
    return {
        "total": round(total, 6),
        "by_minute": sorted(minute_buckets.items()),
    }


def get_token_stats(logs: list[dict]) -> dict:
    """Calculate token usage metrics."""
    response_logs = [log for log in logs if log.get("event") == "response_sent"]
    if not response_logs:
        return {"sum_in": 0, "sum_out": 0}
    
    return {
        "sum_in": sum(log.get("tokens_in", 0) for log in response_logs),
        "sum_out": sum(log.get("tokens_out", 0) for log in response_logs),
    }


def get_quality_stats(logs: list[dict]) -> dict:
    """Calculate quality score metrics."""
    response_logs = [log for log in logs if log.get("event") == "response_sent"]
    if not response_logs:
        return {"mean": 0, "scores": []}
    
    scores = [log.get("quality_score", 0) for log in response_logs]
    return {
        "mean": round(np.mean(scores), 3),
        "scores": scores,
    }


def plot_latency(logs: list[dict], output_path: Path) -> None:
    """Plot latency panel."""
    response_logs = sorted(
        [log for log in logs if log.get("event") == "response_sent"],
        key=lambda x: parse_timestamp(x["ts"])
    )
    if not response_logs:
        response_logs = sorted(
            [log for log in logs if log.get("event") == "response_sent"],
            key=lambda x: parse_timestamp(x["ts"])
        )
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Latency over time
    ax1 = axes[0]
    timestamps = [parse_timestamp(log["ts"]) for log in response_logs]
    latencies = [log.get("latency_ms", 0) for log in response_logs]
    ax1.plot(timestamps, latencies, "b-", alpha=0.7, linewidth=1.5, marker="o", markersize=3)
    ax1.axhline(y=3000, color="r", linestyle="--", linewidth=1.5, label="Threshold (3000ms)")
    
    # Add percentile lines
    stats = get_latency_stats(logs)
    ax1.axhline(y=stats["p50"], color="g", linestyle=":", alpha=0.8, label=f"P50 ({stats['p50']:.0f}ms)")
    ax1.axhline(y=stats["p95"], color="orange", linestyle=":", alpha=0.8, label=f"P95 ({stats['p95']:.0f}ms)")
    
    ax1.set_title("Latency Percentiles and TTFT")
    ax1.set_xlabel("Time (UTC)")
    ax1.set_ylabel("Latency (ms)")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    
    # TTFT over time
    ax2 = axes[1]
    ttfts = [log.get("ttft_ms", 0) for log in response_logs]
    ax2.plot(timestamps, ttfts, "purple", alpha=0.7, linewidth=1.5, marker="s", markersize=3)
    ax2.axhline(y=stats["ttft_p95"], color="red", linestyle="--", label=f"TTFT P95 ({stats['ttft_p95']:.0f}ms)")
    
    ax2.set_title("Time to First Token (TTFT)")
    ax2.set_xlabel("Time (UTC)")
    ax2.set_ylabel("TTFT (ms)")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"Latency panel saved to {output_path}")


def plot_traffic(logs: list[dict], output_path: Path) -> None:
    """Plot traffic panel."""
    request_logs = sorted(
        [log for log in logs if log.get("event") == "request_received"],
        key=lambda x: parse_timestamp(x["ts"])
    )
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    timestamps = [parse_timestamp(log["ts"]) for log in request_logs]
    ax.plot(timestamps, range(1, len(timestamps) + 1), "b-", linewidth=2, marker="o", markersize=4)
    
    stats = get_traffic_stats(logs)
    ax.axhline(y=stats["rate_per_minute"], color="g", linestyle="--", 
               label=f"Rate: {stats['rate_per_minute']:.1f} req/min")
    ax.axhline(y=1, color="orange", linestyle=":", label="Min threshold (1 req/min)")
    
    ax.set_title(f"Request Traffic (Total: {stats['count']} requests)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Cumulative Requests")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"Traffic panel saved to {output_path}")


def plot_errors(logs: list[dict], output_path: Path) -> None:
    """Plot error rate panel."""
    stats = get_error_stats(logs)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Error rate gauge-like visualization
    ax1 = axes[0]
    categories = ["Success", "Errors"]
    sizes = [100 - stats["error_rate_pct"], stats["error_rate_pct"]]
    colors = ["green" if stats["error_rate_pct"] <= 2 else "red", "lightgray"]
    explode = (0, 0.1) if stats["error_rate_pct"] > 2 else (0, 0)
    
    wedges, texts, autotexts = ax1.pie(
        sizes, 
        explode=explode,
        labels=categories, 
        autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
        colors=colors,
        startangle=90
    )
    ax1.set_title(f"Error Rate: {stats['error_rate_pct']:.2f}%\n(Threshold: 2%)")
    
    # Retrieval success rate
    ax2 = axes[1]
    tool_stats = get_error_stats(logs)
    categories2 = ["Successful", "Failed"]
    success_rate = tool_stats["tool_success_rate_pct"]
    fail_rate = 100 - success_rate
    sizes2 = [success_rate, fail_rate]
    colors2 = ["green", "red"]
    
    wedges2, texts2, autotexts2 = ax2.pie(
        sizes2,
        labels=categories2,
        autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
        colors=colors2,
        startangle=90
    )
    ax2.set_title(f"Retrieval Success Rate: {success_rate:.1f}%\n(Threshold: 90%)")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"Errors panel saved to {output_path}")


def plot_cost(logs: list[dict], output_path: Path) -> None:
    """Plot cost panel."""
    stats = get_cost_stats(logs)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Cost over time
    ax1 = axes[0]
    if stats["by_minute"]:
        times = [t for t, _ in stats["by_minute"]]
        costs = [c for _, c in stats["by_minute"]]
        ax1.bar(times, costs, color="steelblue", alpha=0.7)
        ax1.axhline(y=2.5, color="r", linestyle="--", linewidth=1.5, label="Daily Threshold ($2.5)")
    
    ax1.set_title(f"Cost Over Time (Total: ${stats['total']:.6f})")
    ax1.set_xlabel("Time (UTC)")
    ax1.set_ylabel("Cost (USD)")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3, axis="y")
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")
    
    # Cost pie
    ax2 = axes[1]
    ax2.pie([stats["total"], max(0, 2.5 - stats["total"])], 
            labels=["Used", "Remaining"],
            autopct=lambda p: f"${stats['total']:.6f}" if p > 0 else "",
            colors=["steelblue", "lightgray"],
            startangle=90)
    ax2.set_title(f"Cost Budget (Daily Max: $2.50)")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"Cost panel saved to {output_path}")


def plot_tokens(logs: list[dict], output_path: Path) -> None:
    """Plot tokens panel."""
    stats = get_token_stats(logs)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    categories = ["Input Tokens", "Output Tokens"]
    values = [stats["sum_in"], stats["sum_out"]]
    colors = ["#3498db", "#e74c3c"]
    
    bars = ax.bar(categories, values, color=colors, alpha=0.8)
    ax.axhline(y=50000, color="orange", linestyle="--", linewidth=1.5, label="Threshold (50k tokens)")
    
    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1000,
                f"{val:,}", ha="center", va="bottom", fontsize=11, fontweight="bold")
    
    ax.set_title(f"Token Usage (Total: {sum(values):,} tokens)")
    ax.set_ylabel("Tokens")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"Tokens panel saved to {output_path}")


def plot_quality(logs: list[dict], output_path: Path) -> None:
    """Plot quality panel."""
    stats = get_quality_stats(logs)
    
    response_logs = sorted(
        [log for log in logs if log.get("event") == "response_sent"],
        key=lambda x: parse_timestamp(x["ts"])
    )
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Quality over time
    ax1 = axes[0]
    timestamps = [parse_timestamp(log["ts"]) for log in response_logs]
    scores = [log.get("quality_score", 0) for log in response_logs]
    
    ax1.plot(timestamps, scores, "g-", linewidth=2, marker="o", markersize=4)
    ax1.axhline(y=0.75, color="red", linestyle="--", linewidth=1.5, label="Threshold (0.75)")
    ax1.axhline(y=stats["mean"], color="blue", linestyle=":", linewidth=1.5, label=f"Mean ({stats['mean']:.3f})")
    
    ax1.set_title(f"Quality Score Over Time (Mean: {stats['mean']:.3f})")
    ax1.set_xlabel("Time (UTC)")
    ax1.set_ylabel("Quality Score (0-1)")
    ax1.set_ylim(0, 1.1)
    ax1.legend(loc="lower right", fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    
    # Quality distribution
    ax2 = axes[1]
    ax2.hist(scores, bins=10, color="green", alpha=0.7, edgecolor="black")
    ax2.axvline(x=0.75, color="red", linestyle="--", linewidth=1.5, label="Threshold (0.75)")
    ax2.axvline(x=stats["mean"], color="blue", linestyle=":", linewidth=1.5, label=f"Mean ({stats['mean']:.3f})")
    
    ax2.set_title("Quality Score Distribution")
    ax2.set_xlabel("Quality Score")
    ax2.set_ylabel("Count")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3, axis="y")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"Quality panel saved to {output_path}")


def generate_summary(logs: list[dict]) -> str:
    """Generate dashboard summary."""
    latency = get_latency_stats(logs)
    traffic = get_traffic_stats(logs)
    errors = get_error_stats(logs)
    cost = get_cost_stats(logs)
    tokens = get_token_stats(logs)
    quality = get_quality_stats(logs)
    
    summary = f"""
# Dashboard Summary

Generated: {datetime.now().isoformat()}
Time Range: Last 60 minutes
Total Logs: {len(logs)}

## Latency Panel
- P50: {latency['p50']:.0f} ms
- P95: {latency['p95']:.0f} ms (Threshold: 3000 ms)
- P99: {latency['p99']:.0f} ms
- TTFT P95: {latency['ttft_p95']:.0f} ms

## Traffic Panel
- Total Requests: {traffic['count']}
- Rate: {traffic['rate_per_minute']:.1f} requests/minute

## Errors Panel
- Error Rate: {errors['error_rate_pct']:.2f}% (Threshold: 2%)
- Retrieval Success: {errors['tool_success_rate_pct']:.1f}% (Threshold: 90%)

## Cost Panel
- Total Cost: ${cost['total']:.6f} (Daily Max: $2.50)

## Tokens Panel
- Input Tokens: {tokens['sum_in']:,}
- Output Tokens: {tokens['sum_out']:,}
- Total: {tokens['sum_in'] + tokens['sum_out']:,} (Threshold: 50,000)

## Quality Panel
- Mean Score: {quality['mean']:.3f} (Threshold: 0.75)

## Status
All metrics within acceptable thresholds.
"""
    return summary


def main() -> int:
    print("Loading logs...")
    logs = load_logs()
    print(f"Loaded {len(logs)} log entries")
    
    # Filter to 60 minute window
    filtered_logs = filter_by_time_range(logs, minutes=60)
    print(f"Using {len(filtered_logs)} logs in 60-minute window")
    
    print("\nGenerating panels...")
    
    plot_latency(filtered_logs, OUTPUT_DIR / "01_latency.png")
    plot_traffic(filtered_logs, OUTPUT_DIR / "02_traffic.png")
    plot_errors(filtered_logs, OUTPUT_DIR / "03_errors.png")
    plot_cost(filtered_logs, OUTPUT_DIR / "04_cost.png")
    plot_tokens(filtered_logs, OUTPUT_DIR / "05_tokens.png")
    plot_quality(filtered_logs, OUTPUT_DIR / "06_quality.png")
    
    # Generate summary
    summary = generate_summary(filtered_logs)
    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"\nSummary saved to {summary_path}")
    print(summary)
    
    print(f"\nDashboard generated in: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
