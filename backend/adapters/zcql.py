"""
Zoho Catalyst ZCQL Database Adapter

This file provides the production implementations for Catalyst Serverless.
When ENVIRONMENT == 'production', the application should use these methods
instead of the local SQLite ones.
"""
from typing import List, Dict, Any
from config import settings

async def execute_zcql_query(query: str, params: dict = {}) -> List[Dict[str, Any]]:
    """
    Executes a ZCQL query against Zoho Catalyst Data Store.
    
    In a real Catalyst AppSail environment, we would use the zcatalyst_sdk:
    import zcatalyst_sdk
    app = zcatalyst_sdk.initialize()
    datastore = app.datastore()
    result = datastore.execute_zcql(formatted_query)
    """
    if settings.ENVIRONMENT == "local":
        print("Warning: execute_zcql_query called in local environment.")
        return []
        
    # Replace bound parameters with actual values (ZCQL doesn't support named bindings the same way)
    # This is a naive replacement for demonstration.
    for k, v in params.items():
        if isinstance(v, str):
            query = query.replace(f":{k}", f"'{v}'")
        else:
            query = query.replace(f":{k}", str(v))
            
    try:
        import zcatalyst_sdk
        app = zcatalyst_sdk.initialize()
        datastore = app.datastore()
        
        # ZCQL returns results wrapped in table names, e.g. [{"CaseMaster": {"CaseMasterID": 1}}]
        # We need to flatten it to match our sqlite output
        raw_results = datastore.execute_zcql(query)
        
        flattened = []
        for row in raw_results:
            flat_row = {}
            for table_name, columns in row.items():
                flat_row.update(columns)
            flattened.append(flat_row)
            
        return flattened
    except Exception as e:
        print(f"ZCQL Error: {str(e)}")
        return []
