from adapters.database import execute_query
from models.schemas import GraphData, GraphNode, GraphEdge, AccusedPerson
from typing import List, Dict, Any

class GraphBuilder:
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._edge_set = set()

    def add_node(self, node_id: str, label: str, node_type: str, properties: Dict[str, Any]):
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(id=node_id, label=label, type=node_type, properties=properties)

    def add_edge(self, source: str, target: str, relationship: str):
        edge_id = f"{source}-{relationship}-{target}"
        if edge_id not in self._edge_set:
            self.edges.append(GraphEdge(source=source, target=target, relationship=relationship))
            self._edge_set.add(edge_id)

    def build(self) -> GraphData:
        return GraphData(nodes=list(self.nodes.values()), edges=self.edges)


async def _canonical_accused_ids(person_ids: List[str]) -> Dict[str, int]:
    """
    The Accused table stores one row per FIR appearance, so the same person
    owns many ROWIDs. Link analysis needs one node per *person*, otherwise a
    repeat offender fragments into unconnected duplicates and the shared-case
    links he exists to reveal never appear. Collapse each person onto their
    lowest ROWID — still a valid /graph/accused/{id} handle for drill-down.
    """
    ids = [p for p in dict.fromkeys(person_ids) if p]
    if not ids:
        return {}
    placeholders = ", ".join(f":p{i}" for i in range(len(ids)))
    params = {f"p{i}": pid for i, pid in enumerate(ids)}
    rows = await execute_query(
        f"SELECT person_id, MIN(ROWID) as rid FROM Accused "
        f"WHERE person_id IN ({placeholders}) GROUP BY person_id",
        params,
    )
    return {r["person_id"]: r["rid"] for r in rows}


def _accused_node_id(acc: Dict[str, Any], canonical: Dict[str, int]) -> str:
    pid = acc.get("person_id")
    rid = canonical.get(pid, acc["ROWID"]) if pid else acc["ROWID"]
    return f"accused_{rid}"


async def get_case_graph(fir_id: int) -> GraphData:
    builder = GraphBuilder()
    
    # 1. Fetch FIR details
    fir_query = "SELECT * FROM FIRs WHERE ROWID = :fir_id"
    fir_res = await execute_query(fir_query, {"fir_id": fir_id})
    if not fir_res:
        return builder.build()
        
    fir = fir_res[0]
    fir_node_id = f"fir_{fir['ROWID']}"
    builder.add_node(
        fir_node_id, 
        label=fir.get("fir_number") or f"Case #{fir['ROWID']}", 
        node_type="Case",
        properties={"status": fir.get("status"), "date": fir.get("date_reported")}
    )
    
    if fir.get("police_station"):
        unit_node_id = f"station_{fir['police_station'].replace(' ', '_')}"
        builder.add_node(unit_node_id, label=fir["police_station"], node_type="PoliceStation", properties={"district": fir.get("district")})
        builder.add_edge(fir_node_id, unit_node_id, "REGISTERED_AT")
        
    if fir.get("crime_major_head"):
        cat_node_id = f"cat_{fir['crime_major_head'].replace(' ', '_')}"
        builder.add_node(cat_node_id, label=fir["crime_major_head"], node_type="CrimeCategory", properties={})
        builder.add_edge(fir_node_id, cat_node_id, "CATEGORIZED_AS")

    # 2. Fetch Accused, collapsed to one node per person
    acc_query = "SELECT * FROM Accused WHERE fir_rowid = :fir_id"
    accused_list = await execute_query(acc_query, {"fir_id": fir_id})
    person_ids = [a["person_id"] for a in accused_list if a.get("person_id")]
    canonical = await _canonical_accused_ids(person_ids)

    for acc in accused_list:
        acc_node_id = _accused_node_id(acc, canonical)
        builder.add_node(
            acc_node_id, label=acc["name"], node_type="Accused",
            properties={"age": acc.get("age"), "person_id": acc.get("person_id")},
        )
        builder.add_edge(acc_node_id, fir_node_id, "ACCUSED_IN")

    # Prior cases for the same people — one query, not one per accused
    if person_ids:
        placeholders = ", ".join(f":q{i}" for i in range(len(person_ids)))
        params = {f"q{i}": pid for i, pid in enumerate(person_ids)}
        params["fir_id"] = fir_id
        other_cases = await execute_query(
            f"""
            SELECT a.person_id, c.ROWID as rid, c.fir_number, c.crime_major_head
            FROM Accused a
            JOIN FIRs c ON a.fir_rowid = c.ROWID
            WHERE a.person_id IN ({placeholders}) AND c.ROWID != :fir_id
            """,
            params,
        )
        for oc in other_cases:
            oc_node_id = f"fir_{oc['rid']}"
            builder.add_node(
                oc_node_id,
                label=oc.get("fir_number") or f"Case #{oc['rid']}",
                node_type="Case",
                properties={"category": oc.get("crime_major_head")},
            )
            builder.add_edge(f"accused_{canonical[oc['person_id']]}", oc_node_id, "ACCUSED_IN")

    # 3. Fetch Victims
    vic_query = "SELECT * FROM Victims WHERE fir_rowid = :fir_id"
    victims_list = await execute_query(vic_query, {"fir_id": fir_id})
    
    for vic in victims_list:
        vic_node_id = f"victim_{vic['ROWID']}"
        builder.add_node(vic_node_id, label=vic["name"], node_type="Victim", properties={"age": vic.get("age")})
        builder.add_edge(vic_node_id, fir_node_id, "VICTIM_IN")

    # 4. Fetch IPC Sections
    ipc_query = """
        SELECT i.section_number as SectionCode, i.description as SectionDescription 
        FROM FIR_IPC_Map m
        JOIN IPCSections i ON m.ipc_rowid = i.ROWID
        WHERE m.fir_rowid = :fir_id
    """
    ipc_list = await execute_query(ipc_query, {"fir_id": fir_id})
    for ipc in ipc_list:
        ipc_node_id = f"ipc_{ipc['SectionCode']}"
        builder.add_node(ipc_node_id, label=f"Section {ipc['SectionCode']}", node_type="IPCSection", properties={"desc": ipc.get("SectionDescription")})
        builder.add_edge(fir_node_id, ipc_node_id, "CHARGED_UNDER")
        
    return builder.build()

async def get_accused_network(accused_id: int) -> GraphData:
    builder = GraphBuilder()
    
    # 1. Fetch Accused
    acc_query = "SELECT * FROM Accused WHERE ROWID = :id"
    acc_res = await execute_query(acc_query, {"id": accused_id})
    if not acc_res:
        return builder.build()
        
    primary_acc = acc_res[0]
    pid = primary_acc.get("person_id")

    # 2. Every FIR this person appears in — matched on person_id so two
    #    officers sharing a common name never merge into one subject.
    if pid:
        firs = await execute_query(
            "SELECT c.* FROM Accused a JOIN FIRs c ON a.fir_rowid = c.ROWID WHERE a.person_id = :pid",
            {"pid": pid},
        )
        canonical = await _canonical_accused_ids([pid])
    else:
        firs = await execute_query(
            "SELECT c.* FROM Accused a JOIN FIRs c ON a.fir_rowid = c.ROWID WHERE a.name = :name",
            {"name": primary_acc["name"]},
        )
        canonical = {}

    primary_node_id = _accused_node_id(primary_acc, canonical)
    builder.add_node(
        primary_node_id, label=primary_acc["name"], node_type="Accused",
        properties={"age": primary_acc.get("age"), "person_id": pid},
    )

    for fir in firs:
        fir_node_id = f"fir_{fir['ROWID']}"
        builder.add_node(fir_node_id, label=fir.get("fir_number") or f"Case #{fir['ROWID']}", node_type="Case", properties={"category": fir.get("crime_major_head")})
        builder.add_edge(primary_node_id, fir_node_id, "ACCUSED_IN")

    # 3. Co-accused across those FIRs, also collapsed one-node-per-person, so a
    #    shared associate visibly bridges every case he took part in.
    fir_ids = [fir["ROWID"] for fir in firs]
    if fir_ids:
        placeholders = ", ".join(f":fid{i}" for i in range(len(fir_ids)))
        params = {f"fid{i}": fid for i, fid in enumerate(fir_ids)}
        co_accused = await execute_query(
            f"SELECT * FROM Accused WHERE fir_rowid IN ({placeholders})", params
        )
        if pid:
            co_accused = [c for c in co_accused if c.get("person_id") != pid]
        else:
            co_accused = [c for c in co_accused if c["name"] != primary_acc["name"]]
        co_canonical = await _canonical_accused_ids([c["person_id"] for c in co_accused if c.get("person_id")])

        for co in co_accused:
            co_node_id = _accused_node_id(co, co_canonical)
            builder.add_node(
                co_node_id, label=co["name"], node_type="Accused",
                properties={"age": co.get("age"), "person_id": co.get("person_id")},
            )
            builder.add_edge(co_node_id, f"fir_{co['fir_rowid']}", "ACCUSED_IN")

    return builder.build()

async def get_network_by_name(name: str) -> GraphData:
    query = "SELECT ROWID as AccusedMasterID FROM Accused WHERE LOWER(name) LIKE LOWER(:name) LIMIT 1"
    res = await execute_query(query, {"name": f"%{name}%"})
    if res:
        return await get_accused_network(res[0]["AccusedMasterID"])
    return GraphData(nodes=[], edges=[])


async def get_repeat_offenders(limit: int = 20) -> List[dict]:
    query = """
        SELECT a.person_id,
               MAX(a.name) as name,
               MAX(a.age) as age,
               MAX(a.gender) as gender,
               COUNT(DISTINCT a.fir_rowid) as case_count,
               GROUP_CONCAT(DISTINCT c.district) as districts,
               GROUP_CONCAT(DISTINCT c.crime_minor_head) as categories,
               MIN(c.date_reported) as first_seen,
               MAX(c.date_reported) as last_seen,
               MIN(a.ROWID) as any_accused_rowid
        FROM Accused a
        JOIN FIRs c ON a.fir_rowid = c.ROWID
        WHERE a.person_id IS NOT NULL
        GROUP BY a.person_id
        HAVING COUNT(DISTINCT a.fir_rowid) >= 2
        ORDER BY case_count DESC, last_seen DESC
        LIMIT :limit
    """
    rows = await execute_query(query, {"limit": limit})
    return [{
        "person_id": r["person_id"],
        "name": r["name"],
        "age": r["age"],
        "gender": r["gender"],
        "case_count": r["case_count"],
        "districts": sorted(set((r["districts"] or "").split(","))) if r["districts"] else [],
        "categories": sorted(set((r["categories"] or "").split(","))) if r["categories"] else [],
        "first_seen": r["first_seen"],
        "last_seen": r["last_seen"],
        "any_accused_rowid": r["any_accused_rowid"],
    } for r in rows]

async def get_all_accused(limit: int = 100) -> List[AccusedPerson]:
    query = "SELECT * FROM Accused LIMIT :limit"
    results = await execute_query(query, {"limit": limit})
    return [AccusedPerson(**row) for row in results]

async def get_co_accused(accused_id: int) -> List[AccusedPerson]:
    query = """
        SELECT DISTINCT a2.*
        FROM Accused a1
        JOIN Accused a2 ON a1.fir_rowid = a2.fir_rowid
        WHERE a1.ROWID = :id AND a2.name != a1.name
    """
    results = await execute_query(query, {"id": accused_id})
    return [AccusedPerson(**row) for row in results]
