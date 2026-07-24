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

    # 2. Fetch Accused
    acc_query = "SELECT * FROM Accused WHERE fir_rowid = :fir_id"
    accused_list = await execute_query(acc_query, {"fir_id": fir_id})
    
    for acc in accused_list:
        acc_node_id = f"accused_{acc['ROWID']}"
        builder.add_node(acc_node_id, label=acc["name"], node_type="Accused", properties={"age": acc.get("age")})
        builder.add_edge(acc_node_id, fir_node_id, "ACCUSED_IN")
        
        # Look for other cases this accused is in
        other_cases_query = """
            SELECT c.ROWID as CaseMasterID, c.fir_number
            FROM Accused a
            JOIN FIRs c ON a.fir_rowid = c.ROWID
            WHERE a.name = :name AND c.ROWID != :fir_id
        """
        other_cases = await execute_query(other_cases_query, {"name": acc["name"], "fir_id": fir_id})
        for oc in other_cases:
            oc_node_id = f"fir_{oc['CaseMasterID']}"
            builder.add_node(
                oc_node_id, 
                label=oc.get("fir_number") or f"Case #{oc['CaseMasterID']}", 
                node_type="Case", 
                properties={}
            )
            builder.add_edge(acc_node_id, oc_node_id, "ACCUSED_IN")

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
    primary_node_id = f"accused_{primary_acc['ROWID']}"
    builder.add_node(primary_node_id, label=primary_acc["name"], node_type="Accused", properties={"age": primary_acc.get("age")})
    
    # 2. Fetch all FIRs for this accused by Name (to link across cases)
    firs_query = """
        SELECT c.*
        FROM Accused a
        JOIN FIRs c ON a.fir_rowid = c.ROWID
        WHERE a.name = :name
    """
    firs = await execute_query(firs_query, {"name": primary_acc["name"]})
    
    for fir in firs:
        fir_node_id = f"fir_{fir['ROWID']}"
        builder.add_node(fir_node_id, label=fir.get("fir_number") or f"Case #{fir['ROWID']}", node_type="Case", properties={"category": fir.get("crime_major_head")})
        builder.add_edge(primary_node_id, fir_node_id, "ACCUSED_IN")
        
        # 3. For each FIR, get Co-Accused
        co_acc_query = "SELECT * FROM Accused WHERE fir_rowid = :fir_id AND name != :name"
        co_accused = await execute_query(co_acc_query, {"fir_id": fir["ROWID"], "name": primary_acc["name"]})
        
        for co in co_accused:
            co_node_id = f"accused_{co['ROWID']}"
            builder.add_node(co_node_id, label=co["name"], node_type="Accused", properties={"age": co.get("age")})
            builder.add_edge(co_node_id, fir_node_id, "ACCUSED_IN")
            
    return builder.build()

async def get_network_by_name(name: str) -> GraphData:
    query = "SELECT ROWID as AccusedMasterID FROM Accused WHERE name LIKE :name LIMIT 1"
    res = await execute_query(query, {"name": f"%{name}%"})
    if res:
        return await get_accused_network(res[0]["AccusedMasterID"])
    return GraphData(nodes=[], edges=[])

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
