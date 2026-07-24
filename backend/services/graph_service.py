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
    fir_query = """
        SELECT c.*, ch.CrimeGroupName, u.UnitName, d.DistrictName, s.CaseStatusName
        FROM CaseMaster c
        LEFT JOIN CrimeHead ch ON c.CrimeMajorHeadID = ch.CrimeHeadID
        LEFT JOIN Unit u ON c.PoliceStationID = u.UnitID
        LEFT JOIN District d ON u.DistrictID = d.DistrictID
        LEFT JOIN CaseStatusMaster s ON c.CaseStatusID = s.CaseStatusID
        WHERE c.CaseMasterID = :fir_id
    """
    fir_res = await execute_query(fir_query, {"fir_id": fir_id})
    if not fir_res:
        return builder.build()
        
    fir = fir_res[0]
    fir_node_id = f"fir_{fir['CaseMasterID']}"
    builder.add_node(
        fir_node_id, 
        label=fir.get("CrimeNo") or f"Case #{fir['CaseNo']}", 
        node_type="Case",
        properties={"status": fir.get("CaseStatusName"), "date": fir.get("CrimeRegisteredDate")}
    )
    
    if fir.get("UnitName"):
        unit_node_id = f"station_{fir['PoliceStationID']}"
        builder.add_node(unit_node_id, label=fir["UnitName"], node_type="PoliceStation", properties={"district": fir.get("DistrictName")})
        builder.add_edge(fir_node_id, unit_node_id, "REGISTERED_AT")
        
    if fir.get("CrimeGroupName"):
        cat_node_id = f"cat_{fir['CrimeMajorHeadID']}"
        builder.add_node(cat_node_id, label=fir["CrimeGroupName"], node_type="CrimeCategory", properties={})
        builder.add_edge(fir_node_id, cat_node_id, "CATEGORIZED_AS")

    # 2. Fetch Accused
    acc_query = "SELECT * FROM Accused WHERE CaseMasterID = :fir_id"
    accused_list = await execute_query(acc_query, {"fir_id": fir_id})
    
    for acc in accused_list:
        acc_node_id = f"accused_{acc['AccusedMasterID']}"
        builder.add_node(acc_node_id, label=acc["AccusedName"], node_type="Accused", properties={"age": acc.get("AgeYear")})
        builder.add_edge(acc_node_id, fir_node_id, "ACCUSED_IN")
        
        # Look for other cases this accused is in
        other_cases_query = """
            SELECT c.CaseMasterID, c.CrimeNo, c.CaseNo
            FROM Accused a
            JOIN CaseMaster c ON a.CaseMasterID = c.CaseMasterID
            WHERE a.AccusedName = :name AND c.CaseMasterID != :fir_id
        """
        other_cases = await execute_query(other_cases_query, {"name": acc["AccusedName"], "fir_id": fir_id})
        for oc in other_cases:
            oc_node_id = f"fir_{oc['CaseMasterID']}"
            builder.add_node(
                oc_node_id, 
                label=oc.get("CrimeNo") or f"Case #{oc['CaseNo']}", 
                node_type="Case", 
                properties={}
            )
            builder.add_edge(acc_node_id, oc_node_id, "ACCUSED_IN")

    # 3. Fetch Victims
    vic_query = "SELECT * FROM Victim WHERE CaseMasterID = :fir_id"
    victims_list = await execute_query(vic_query, {"fir_id": fir_id})
    
    for vic in victims_list:
        vic_node_id = f"victim_{vic['VictimMasterID']}"
        builder.add_node(vic_node_id, label=vic["VictimName"], node_type="Victim", properties={"age": vic.get("AgeYear")})
        builder.add_edge(vic_node_id, fir_node_id, "VICTIM_IN")

    # 4. Fetch IPC Sections
    ipc_query = """
        SELECT s.SectionCode, s.SectionDescription 
        FROM ActSectionAssociation asa
        JOIN Section s ON asa.SectionID = s.SectionCode
        WHERE asa.CaseMasterID = :fir_id
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
    acc_query = "SELECT * FROM Accused WHERE AccusedMasterID = :id"
    acc_res = await execute_query(acc_query, {"id": accused_id})
    if not acc_res:
        return builder.build()
        
    primary_acc = acc_res[0]
    primary_node_id = f"accused_{primary_acc['AccusedMasterID']}"
    builder.add_node(primary_node_id, label=primary_acc["AccusedName"], node_type="Accused", properties={"age": primary_acc.get("AgeYear")})
    
    # 2. Fetch all FIRs for this accused by Name (to link across cases)
    firs_query = """
        SELECT c.*, ch.CrimeGroupName
        FROM Accused a
        JOIN CaseMaster c ON a.CaseMasterID = c.CaseMasterID
        LEFT JOIN CrimeHead ch ON c.CrimeMajorHeadID = ch.CrimeHeadID
        WHERE a.AccusedName = :name
    """
    firs = await execute_query(firs_query, {"name": primary_acc["AccusedName"]})
    
    for fir in firs:
        fir_node_id = f"fir_{fir['CaseMasterID']}"
        builder.add_node(fir_node_id, label=fir.get("CrimeNo") or f"Case #{fir['CaseNo']}", node_type="Case", properties={"category": fir.get("CrimeGroupName")})
        builder.add_edge(primary_node_id, fir_node_id, "ACCUSED_IN")
        
        # 3. For each FIR, get Co-Accused
        co_acc_query = "SELECT * FROM Accused WHERE CaseMasterID = :fir_id AND AccusedName != :name"
        co_accused = await execute_query(co_acc_query, {"fir_id": fir["CaseMasterID"], "name": primary_acc["AccusedName"]})
        
        for co in co_accused:
            co_node_id = f"accused_{co['AccusedMasterID']}"
            builder.add_node(co_node_id, label=co["AccusedName"], node_type="Accused", properties={"age": co.get("AgeYear")})
            builder.add_edge(co_node_id, fir_node_id, "ACCUSED_IN")
            
    return builder.build()

async def get_network_by_name(name: str) -> GraphData:
    # Find the best matching accused and build network
    query = "SELECT AccusedMasterID FROM Accused WHERE AccusedName LIKE :name LIMIT 1"
    res = await execute_query(query, {"name": f"%{name}%"})
    if res:
        return await get_accused_network(res[0]["AccusedMasterID"])
    return GraphData(nodes=[], edges=[])

async def get_co_accused(accused_id: int) -> List[AccusedPerson]:
    query = """
        SELECT DISTINCT a2.*
        FROM Accused a1
        JOIN Accused a2 ON a1.CaseMasterID = a2.CaseMasterID
        WHERE a1.AccusedMasterID = :id AND a2.AccusedName != a1.AccusedName
    """
    results = await execute_query(query, {"id": accused_id})
    return [AccusedPerson(**row) for row in results]
