"""
Offline template-based NLG for the DRISHTI copilot.

Composes short markdown analyst answers with real numbers pulled from the
tool results — no LLM required in local mode.
"""

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_period(period: str) -> str:
    try:
        y, m = period.split("-")
        return f"{_MONTHS[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return period


def _scope_phrase(params: dict) -> str:
    parts = []
    if params.get("crime_category"):
        parts.append(params["crime_category"])
    if params.get("district"):
        parts.append(f"in {params['district']}")
    return " ".join(parts) if parts else "across Karnataka"


def _first(tool_results, key):
    for res in tool_results or []:
        if key in res:
            return res
    return None


def compose_answer(question: str, intent: str, params: dict, tool_results: list) -> str:
    composer = _COMPOSERS.get(intent, _compose_general)
    try:
        return composer(question, params, tool_results)
    except Exception:
        return _compose_general(question, params, tool_results)


# ---------------------------------------------------------------------------

def _compose_trends(question, params, tool_results):
    res = _first(tool_results, "data")
    data = (res or {}).get("data") or []
    scope = _scope_phrase(params)
    if not data:
        return (f"I found no reported cases for {scope} in the selected window. "
                f"Recommendation: widen the time range or drop a filter.")

    total = sum(d["count"] for d in data)
    peak = max(data, key=lambda d: d["count"])
    half = max(1, len(data) // 2)
    first_avg = sum(d["count"] for d in data[:half]) / half
    second_avg = sum(d["count"] for d in data[half:]) / max(len(data) - half, 1)
    change = (second_avg - first_avg) / max(first_avg, 1) * 100
    direction = "rising" if change > 8 else ("falling" if change < -8 else "broadly stable")

    mover, mover_delta = None, 0
    for prev, cur in zip(data, data[1:]):
        delta = cur["count"] - prev["count"]
        if abs(delta) > abs(mover_delta):
            mover, mover_delta = cur, delta

    ans = (f"**{total} cases** were reported for {scope} over the last {len(data)} months, "
           f"and the trend is **{direction}** ({change:+.0f}% comparing the first and second half "
           f"of the window). The peak month was **{_fmt_period(peak['period'])}** with "
           f"{peak['count']} cases.")
    if mover and mover_delta:
        ans += (f" The sharpest month-on-month move was in {_fmt_period(mover['period'])} "
                f"({mover_delta:+d} cases).")
    tail = ("Recommendation: increase beat presence and review deployment in the peak window."
            if change > 8 else
            "Recommendation: maintain current deployment and monitor monthly for reversals.")
    return f"{ans}\n\n{tail}"


def _compose_network(question, params, tool_results):
    res = _first(tool_results, "summary")
    if not res or not res["summary"]["case_count"]:
        name = params.get("person_name", "that person")
        return (f"No network could be built — I found no accused matching **{name}** in the records. "
                f"Recommendation: verify the spelling or search the repeat-offender registry.")
    s = res["summary"]
    assoc = s["associates"]
    assoc_str = ", ".join(assoc[:4]) + (f" and {len(assoc) - 4} more" if len(assoc) > 4 else "")
    ans = (f"**{s['person']}** is linked to **{s['case_count']} FIRs** spanning "
           f"{len(s['districts'])} district(s) ({', '.join(s['districts'])}), "
           f"with a signature in {', '.join(s['categories'][:3])}.")
    if assoc:
        ans += (f" The network includes **{len(assoc)} known associates** — {assoc_str} — "
                f"co-accused across shared cases, indicating an organised group rather than a lone operator.")
    else:
        ans += " No co-accused appear on record, suggesting a solo operator."
    tail = "Recommendation: map shared cases with the network graph and cross-check arrest records of associates."
    return f"{ans}\n\n{tail}"


def _compose_history(question, params, tool_results):
    res = _first(tool_results, "data")
    rows = (res or {}).get("data") or []
    name = params.get("person_name", "the person")
    if not rows:
        return (f"No criminal history found for **{name}** in the FIR database. "
                f"Recommendation: verify the name against the repeat-offender registry.")
    dists = sorted({r["district"] for r in rows if r.get("district")})
    cats = sorted({r["crime_minor_head"] for r in rows if r.get("crime_minor_head")})
    statuses = {}
    for r in rows:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    status_str = ", ".join(f"{v} {k.lower()}" for k, v in statuses.items())
    latest = rows[0]
    ans = (f"**{name}** appears in **{len(rows)} FIRs** between {rows[-1]['date_reported']} and "
           f"{latest['date_reported']}, across {', '.join(dists)}. Modus operandi centres on "
           f"{', '.join(cats[:3])}. Case status: {status_str}. Most recent: "
           f"**{latest['fir_number']}** ({latest['crime_minor_head']}, {latest['status']}).")
    tail = "Recommendation: review pending cases together — a consistent MO strengthens linked-case prosecution."
    return f"{ans}\n\n{tail}"


def _compose_comparison(question, params, tool_results):
    res = _first(tool_results, "data")
    rows = (res or {}).get("data") or []
    if not rows:
        return "No district data available. Recommendation: regenerate the dataset."
    top = rows[:3]
    parts = []
    for r in top:
        clr = (r["solved"] / max(r["total_cases"], 1)) * 100
        parts.append(f"**{r['district']}** ({r['total_cases']} cases, {clr:.0f}% clearance)")
    total = sum(r["total_cases"] for r in rows)
    best_clr = max(rows, key=lambda r: r["solved"] / max(r["total_cases"], 1))
    ans = (f"Across **{len(rows)} districts** and {total} recorded cases, the highest caseloads are "
           f"{', '.join(parts)}. {top[0]['district']} alone accounts for "
           f"{top[0]['total_cases'] / max(total, 1) * 100:.0f}% of the state's volume. The best clearance "
           f"rate is in **{best_clr['district']}** "
           f"({best_clr['solved'] / max(best_clr['total_cases'], 1) * 100:.0f}%).")
    tail = "Recommendation: study high-clearance districts' investigation practices for replication in high-volume zones."
    return f"{ans}\n\n{tail}"


def _compose_station(question, params, tool_results):
    res = _first(tool_results, "data")
    rows = (res or {}).get("data") or []
    scope = f"in {params['district']}" if params.get("district") else "statewide"
    if not rows:
        return f"No station data found {scope}."
    top = rows[0]
    pending_sorted = sorted(rows, key=lambda r: r["total_cases"] - r["solved"], reverse=True)
    worst = pending_sorted[0]
    ans = (f"Of **{len(rows)} police stations** {scope}, **{top['station_name']}** ({top['district']}) "
           f"carries the heaviest load with {top['total_cases']} cases "
           f"({top['solved']} solved). The largest pending pile-up is at **{worst['station_name']}** "
           f"with {worst['total_cases'] - worst['solved']} open cases.")
    tail = "Recommendation: rebalance investigating officers toward stations with the largest open-case backlog."
    return f"{ans}\n\n{tail}"


def _compose_ipc(question, params, tool_results):
    res = _first(tool_results, "data")
    rows = (res or {}).get("data") or []
    if not rows:
        return "No IPC section data found."
    top = rows[:3]
    parts = [f"**Sec {r['section']}** ({r['description']}, {r['count']} FIRs)" for r in top]
    ans = (f"The most invoked sections are {'; '.join(parts)}. "
           f"Together the top {len(top)} sections cover {sum(r['count'] for r in top)} charges "
           f"across registered FIRs.")
    tail = "Recommendation: align chargesheet quality reviews with the highest-volume sections."
    return f"{ans}\n\n{tail}"


def _compose_hotspots(question, params, tool_results):
    res = _first(tool_results, "hotspots")
    spots = (res or {}).get("hotspots") or []
    scope = _scope_phrase(params)
    if not spots:
        return (f"No hotspot concentration found for {scope} in the last 90 days. "
                f"Recommendation: broaden the filter.")
    parts = [f"**{s['locality']}** ({s['district']}, {s['count']} cases, led by {s['top_category']})"
             for s in spots[:3]]
    ans = (f"Over the last 90 days the sharpest concentrations for {scope} are "
           f"{'; '.join(parts)}. The top beat alone logged {spots[0]['count']} cases.")
    tail = "Recommendation: deploy targeted patrols in these beats during their peak hours (see time-pattern analysis)."
    return f"{ans}\n\n{tail}"


def _compose_similar(question, params, tool_results):
    res = _first(tool_results, "similar_firs")
    sims = (res or {}).get("similar_firs") or []
    if not sims:
        if res and not res.get("total_indexed"):
            return ("Semantic search is not available — the FAISS index has not been built yet. "
                    "Run scripts/build_embeddings.py. Recommendation: use category filters meanwhile.")
        return "No sufficiently similar cases found. Recommendation: rephrase with more incident detail."
    top = sims[0]
    dists = sorted({s["fir"]["district"] for s in sims if s["fir"].get("district")})
    ans = (f"I found **{len(sims)} similar cases**. The closest match is "
           f"**{top['fir']['fir_number']}** ({top['fir'].get('crime_minor_head')}, "
           f"{top['fir'].get('district')}) with {top['similarity_score'] * 100:.0f}% semantic similarity. "
           f"Matches span {', '.join(dists[:4])}, pointing to a recurring modus operandi.")
    tail = "Recommendation: review the top matches for common suspects or vehicle descriptions."
    return f"{ans}\n\n{tail}"


def _compose_case(question, params, tool_results):
    res = _first(tool_results, "data")
    rows = (res or {}).get("data") or []
    if not rows:
        return (f"No FIR matching {params.get('fir_number', 'that number')} was found. "
                f"Recommendation: verify the FIR number format (e.g. CBPK-0042/2026).")
    f = rows[0]
    ans = (f"**{f['fir_number']}** — {f['crime_minor_head']} ({f['crime_major_head']}), registered at "
           f"{f['police_station']}, {f['district']} on {f['date_reported']}. Status: **{f['status']}**, "
           f"gravity {f['gravity']}. Facts: {(f.get('brief_facts') or '')[:220]}...")
    tail = "Recommendation: open the case graph to view accused, victims and charged sections."
    return f"{ans}\n\n{tail}"


def _compose_general(question, params, tool_results):
    return ("I can analyse the live FIR database for you — try asking about **crime trends** "
            "(\"chain snatching trends in Bengaluru, last 6 months\"), **hotspots**, "
            "**criminal networks** of a named accused, **district comparisons**, "
            "**station workloads**, or **IPC section usage**.\n\n"
            "Recommendation: include a district, category or person name for a sharper answer.")


_COMPOSERS = {
    "crime_trends": _compose_trends,
    "criminal_network": _compose_network,
    "accused_history": _compose_history,
    "district_comparison": _compose_comparison,
    "station_analysis": _compose_station,
    "ipc_analysis": _compose_ipc,
    "hotspot_analysis": _compose_hotspots,
    "similar_cases": _compose_similar,
    "case_details": _compose_case,
    "general_question": _compose_general,
}
