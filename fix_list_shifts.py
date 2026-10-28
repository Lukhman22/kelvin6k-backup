import re

with open('api/server.py', 'r') as f:
    content = f.read()

content = content.replace(
    '''@app.get("/api/shifts")
def list_shifts(
    shift_date: Optional[str] = None,
    shift_type: Optional[str] = None,
    operator_id: str,
    status: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:''',
    '''@app.get("/api/shifts")
def list_shifts(
    shift_date: Optional[str] = None,
    shift_type: Optional[str] = None,
    operator_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:'''
)

with open('api/server.py', 'w') as f:
    f.write(content)
