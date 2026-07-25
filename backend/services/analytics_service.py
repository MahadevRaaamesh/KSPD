import re
from adapters.database import execute_query
from models.schemas import OverviewStats, TrendDataPoint, DistrictStat, IPCStat, StationStat
from typing import List, Optional


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


async def _anchor_date() -> str:
    """Latest reported date in the data — all rolling windows anchor here."""
    res = await execute_query("SELECT MAX(date_reported) as anchor FROM FIRs")
    return res[0]["anchor"] or "2026-07-25"


async def get_overview_stats() -> OverviewStats:
    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs")
    total_firs = res[0]["cnt"]

    res = await execute_query("SELECT COUNT(*) as cnt FROM Accused")
    total_accused = res[0]["cnt"]

    res = await execute_query("SELECT COUNT(*) as cnt FROM Victims")
    total_victims = res[0]["cnt"]

    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs WHERE status IN ('Charge Sheeted', 'Closed')")
    cases_solved = res[0]["cnt"]

    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs WHERE status = 'Under Investigation'")
    cases_pending = res[0]["cnt"]

    res = await execute_query("SELECT COUNT(*) as cnt FROM Chargesheets")
    chargesheets_filed = res[0]["cnt"]

    return OverviewStats(
        total_firs=total_firs,
        total_accused=total_accused,
        total_victims=total_victims,
        cases_solved=cases_solved,
        cases_pending=cases_pending,
        chargesheets_filed=chargesheets_filed
    )


async def get_crime_trends(
    district: Optional[str] = None,
    crime_category: Optional[str] = None,
    months: int = 12,
) -> List[TrendDataPoint]:
    anchor = await _anchor_date()
    # Align the window to a month boundary so the first bucket is a whole
    # month — a mid-month cut-off renders as a phantom dip on the trend line.
    query = """
        SELECT SUBSTR(date_reported, 1, 7) as period, COUNT(*) as count
        FROM FIRs
        WHERE date_reported >= date(:anchor, :window, 'start of month')
    """
    params = {"anchor": anchor, "window": f"-{max(1, int(months)) - 1} months"}
    if district:
        query += " AND district = :district"
        params["district"] = district
    if crime_category:
        query += " AND crime_major_head = :category"
        params["category"] = crime_category

    query += " GROUP BY period ORDER BY period"
    results = await execute_query(query, params)
    return [TrendDataPoint(period=row["period"], count=row["count"]) for row in results if row["period"]]


async def get_district_stats() -> List[DistrictStat]:
    query = """
        SELECT district, COUNT(*) as total,
        SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved,
        SUM(CASE WHEN status = 'Under Investigation' THEN 1 ELSE 0 END) as pending
        FROM FIRs
        GROUP BY district
        ORDER BY total DESC
    """
    results = await execute_query(query)
    return [DistrictStat(
        district=row["district"],
        total_cases=row["total"],
        solved=row["solved"] or 0,
        pending=row["pending"] or 0
    ) for row in results if row["district"]]


async def get_top_ipc_sections(limit: int = 15) -> List[IPCStat]:
    query = """
        SELECT i.section_number as section, COUNT(*) as count, i.description
        FROM FIR_IPC_Map m
        JOIN IPCSections i ON m.ipc_rowid = i.ROWID
        GROUP BY i.section_number, i.description
        ORDER BY count DESC
        LIMIT :limit
    """
    results = await execute_query(query, {"limit": limit})
    return [IPCStat(
        section=row["section"],
        count=row["count"],
        description=row["description"]
    ) for row in results]


async def get_station_stats(district: Optional[str] = None) -> List[StationStat]:
    query = """
        SELECT police_station as station_name, district, COUNT(*) as total,
        SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved
        FROM FIRs
        WHERE 1=1
    """
    params = {}
    if district:
        query += " AND district = :district"
        params["district"] = district

    query += " GROUP BY police_station, district ORDER BY total DESC"
    results = await execute_query(query, params)
    return [StationStat(
        station_name=row["station_name"],
        district=row["district"],
        total_cases=row["total"],
        solved=row["solved"] or 0
    ) for row in results if row["station_name"]]


# ---------------------------------------------------------------------------
# Insights: real spike detection + clearance + growth signals
# ---------------------------------------------------------------------------

async def get_insights() -> List[dict]:
    anchor = await _anchor_date()

    rows = await execute_query("""
        SELECT district, crime_minor_head as minor,
          SUM(CASE WHEN date_reported > date(:anchor, '-30 days') THEN 1 ELSE 0 END) as last30,
          SUM(CASE WHEN date_reported <= date(:anchor, '-30 days')
                    AND date_reported > date(:anchor, '-120 days') THEN 1 ELSE 0 END) as prior90
        FROM FIRs
        WHERE district IS NOT NULL AND crime_minor_head IS NOT NULL
        GROUP BY district, crime_minor_head
    """, {"anchor": anchor})

    spikes = []
    for r in rows:
        last30 = r["last30"] or 0
        baseline = (r["prior90"] or 0) / 3.0
        if last30 >= 4 and last30 > 1.5 * baseline:
            baseline_f = max(baseline, 1.0 / 3.0)
            ratio = last30 / baseline_f
            pct = int(round((last30 - baseline_f) / baseline_f * 100))
            spikes.append({
                "id": f"spike-{_slug(r['district'])}-{_slug(r['minor'])}",
                "type": "spike",
                "severity": "critical" if ratio >= 2.5 else "warning",
                "title": f"{r['minor']} surge — {r['district']}",
                "description": (
                    f"{last30} cases in the last 30 days vs a baseline of "
                    f"{baseline:.1f}/month (+{pct}%)."
                ),
                "metric": f"+{pct}%",
                "district": r["district"],
                "category": r["minor"],
                "_pct": pct,
            })
    spikes.sort(key=lambda s: s["_pct"], reverse=True)
    spikes = spikes[:6]
    for s in spikes:
        s.pop("_pct", None)

    insights = list(spikes)

    # Success insight: chargesheet momentum, last quarter vs previous quarter
    cs = await execute_query("""
        SELECT
          SUM(CASE WHEN filing_date > date(:anchor, '-90 days') THEN 1 ELSE 0 END) as last_q,
          SUM(CASE WHEN filing_date <= date(:anchor, '-90 days')
                    AND filing_date > date(:anchor, '-180 days') THEN 1 ELSE 0 END) as prev_q
        FROM Chargesheets
    """, {"anchor": anchor})
    last_q = cs[0]["last_q"] or 0
    prev_q = cs[0]["prev_q"] or 0
    clr = await execute_query("""
        SELECT COUNT(*) as total,
          SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved
        FROM FIRs
    """)
    clearance = (clr[0]["solved"] or 0) / max(clr[0]["total"] or 1, 1) * 100
    cs_pct = int(round((last_q - prev_q) / max(prev_q, 1) * 100))
    insights.append({
        "id": "clearance-momentum",
        "type": "success",
        "severity": "info",
        "title": "Chargesheet filings " + ("up" if cs_pct >= 0 else "down") + " this quarter",
        "description": (
            f"{last_q} chargesheets filed in the last quarter vs {prev_q} in the previous "
            f"({'+' if cs_pct >= 0 else ''}{cs_pct}%). Statewide clearance stands at {clearance:.0f}%."
        ),
        "metric": f"{'+' if cs_pct >= 0 else ''}{cs_pct}%",
        "district": None,
        "category": None,
    })

    # Info insight: fastest-growing crime category over 6 months
    growth = await execute_query("""
        SELECT crime_major_head as category,
          SUM(CASE WHEN date_reported > date(:anchor, '-90 days') THEN 1 ELSE 0 END) as recent,
          SUM(CASE WHEN date_reported <= date(:anchor, '-90 days')
                    AND date_reported > date(:anchor, '-180 days') THEN 1 ELSE 0 END) as prior
        FROM FIRs
        WHERE crime_major_head IS NOT NULL
        GROUP BY crime_major_head
    """, {"anchor": anchor})
    best = None
    for g in growth:
        recent, prior = g["recent"] or 0, g["prior"] or 0
        if recent < 10:
            continue
        g_pct = (recent - prior) / max(prior, 1) * 100
        if best is None or g_pct > best[1]:
            best = (g["category"], g_pct, recent)
    if best:
        insights.append({
            "id": f"growth-{_slug(best[0])}",
            "type": "info",
            "severity": "info",
            "title": f"{best[0]} is the fastest-growing category",
            "description": (
                f"{best[2]} {best[0]} cases in the last 3 months, "
                f"{'+' if best[1] >= 0 else ''}{best[1]:.0f}% over the previous quarter."
            ),
            "metric": f"{'+' if best[1] >= 0 else ''}{best[1]:.0f}%",
            "district": None,
            "category": best[0],
        })

    return insights[:8]


# ---------------------------------------------------------------------------
# District risk scores
# ---------------------------------------------------------------------------

def _risk_level(score: int) -> str:
    if score < 35:
        return "low"
    if score < 55:
        return "moderate"
    if score < 70:
        return "elevated"
    if score < 85:
        return "high"
    return "critical"


async def get_risk_scores() -> List[dict]:
    anchor = await _anchor_date()

    rows = await execute_query("""
        SELECT district,
          COUNT(*) as total90,
          SUM(CASE WHEN date_reported > date(:anchor, '-30 days') THEN 1 ELSE 0 END) as last30,
          SUM(CASE WHEN date_reported <= date(:anchor, '-30 days')
                    AND date_reported > date(:anchor, '-60 days') THEN 1 ELSE 0 END) as prior30,
          SUM(CASE WHEN gravity = 'Heinous' THEN 1 ELSE 0 END) as heinous,
          SUM(CASE WHEN status = 'Under Investigation' THEN 1 ELSE 0 END) as pending,
          SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved
        FROM FIRs
        WHERE district IS NOT NULL AND date_reported > date(:anchor, '-90 days')
        GROUP BY district
    """, {"anchor": anchor})
    if not rows:
        return []

    top_cats = await execute_query("""
        SELECT district, crime_minor_head as minor, COUNT(*) as cnt
        FROM FIRs
        WHERE district IS NOT NULL AND crime_minor_head IS NOT NULL
          AND date_reported > date(:anchor, '-90 days')
        GROUP BY district, crime_minor_head
    """, {"anchor": anchor})
    top_by_district = {}
    for tc in top_cats:
        cur = top_by_district.get(tc["district"])
        if cur is None or tc["cnt"] > cur[1]:
            top_by_district[tc["district"]] = (tc["minor"], tc["cnt"])

    totals = sorted(r["total90"] for r in rows)
    n = len(totals)
    state_clearance = sum(r["solved"] or 0 for r in rows) / max(sum(r["total90"] for r in rows), 1)

    out = []
    for r in rows:
        total90 = r["total90"] or 0
        last30, prior30 = r["last30"] or 0, r["prior30"] or 0
        growth = (last30 - prior30) / max(prior30, 1)
        heinous_share = (r["heinous"] or 0) / max(total90, 1)
        pending_share = (r["pending"] or 0) / max(total90, 1)
        clearance = (r["solved"] or 0) / max(total90, 1)

        vol_pct = totals.index(r["total90"]) / max(n - 1, 1)
        g_norm = min(max((growth + 0.5) / 1.5, 0.0), 1.0)
        h_norm = min(max(heinous_share / 0.25, 0.0), 1.0)

        score = int(round(100 * (0.45 * vol_pct + 0.25 * g_norm + 0.20 * h_norm + 0.10 * pending_share)))

        trend = "rising" if growth > 0.15 else ("falling" if growth < -0.15 else "stable")
        top = top_by_district.get(r["district"], ("—", 0))

        drivers = []
        if abs(growth) >= 0.15:
            drivers.append(f"Case volume {'up' if growth > 0 else 'down'} {abs(growth) * 100:.0f}% MoM")
        if heinous_share >= 0.10:
            drivers.append(f"High heinous-crime share ({heinous_share * 100:.0f}%)")
        if clearance < state_clearance - 0.02:
            drivers.append("Clearance rate below state average")
        drivers.append(f"Top category: {top[0]} ({top[1]} cases in 90 days)")
        if len(drivers) < 2:
            drivers.append(f"{total90} cases reported in the last 90 days")

        out.append({
            "district": r["district"],
            "score": score,
            "level": _risk_level(score),
            "trend": trend,
            "total_cases_90d": total90,
            "top_category": top[0],
            "drivers": drivers[:4],
        })

    out.sort(key=lambda d: d["score"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Time-of-day / day-of-week patterns
# ---------------------------------------------------------------------------

async def get_time_patterns(district: Optional[str] = None) -> dict:
    where = "WHERE incident_from_date IS NOT NULL"
    params = {}
    if district:
        where += " AND district = :district"
        params["district"] = district

    rows = await execute_query(f"""
        SELECT CAST(strftime('%w', incident_from_date) AS INTEGER) as w,
               CAST(strftime('%H', incident_from_date) AS INTEGER) as hour,
               COUNT(*) as count
        FROM FIRs {where}
        GROUP BY w, hour
    """, params)

    matrix = []
    peak = None
    for r in rows:
        if r["w"] is None or r["hour"] is None:
            continue
        dow = (r["w"] + 6) % 7  # strftime %w: 0=Sunday -> ours: 0=Monday
        cell = {"dow": dow, "hour": r["hour"], "count": r["count"]}
        matrix.append(cell)
        if peak is None or r["count"] > peak["count"]:
            peak = cell
    matrix.sort(key=lambda c: (c["dow"], c["hour"]))

    cat_rows = await execute_query(f"""
        SELECT crime_minor_head as category,
               CAST(strftime('%H', incident_from_date) AS INTEGER) as hour,
               COUNT(*) as count
        FROM FIRs {where} AND crime_minor_head IS NOT NULL
        GROUP BY crime_minor_head, hour
    """, params)
    agg = {}
    for r in cat_rows:
        c = agg.setdefault(r["category"], {"count": 0, "peak_hour": 0, "peak_n": -1})
        c["count"] += r["count"]
        if r["count"] > c["peak_n"]:
            c["peak_n"] = r["count"]
            c["peak_hour"] = r["hour"]
    by_category = sorted(
        [{"category": k, "peak_hour": v["peak_hour"], "count": v["count"]} for k, v in agg.items()],
        key=lambda x: x["count"], reverse=True,
    )[:6]

    return {
        "matrix": matrix,
        "peak": peak or {"dow": 0, "hour": 0, "count": 0},
        "by_category": by_category,
    }


# ---------------------------------------------------------------------------
# Category breakdown
# ---------------------------------------------------------------------------

async def get_categories() -> List[dict]:
    rows = await execute_query("""
        SELECT crime_major_head as category, COUNT(*) as count,
          SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved
        FROM FIRs
        WHERE crime_major_head IS NOT NULL
        GROUP BY crime_major_head
        ORDER BY count DESC
    """)
    return [{"category": r["category"], "count": r["count"], "solved": r["solved"] or 0}
            for r in rows]
