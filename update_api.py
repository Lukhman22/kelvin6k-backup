import re

with open('api/server.py', 'r') as f:
    content = f.read()

new_create = """@app.post("/api/operators")
def create_operator(req: CreateOperatorRequest) -> Dict[str, Any]:
    \"\"\"Creates a new operator.\"\"\"
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Employee name is required.")
        
    op_id = req.operator_id
    if not op_id:
        clean_name = req.name.strip().upper().replace(" ", "_")
        import uuid
        short_id = str(uuid.uuid4())[:6].upper()
        op_id = f"OP_{clean_name}_{short_id}"

    try:
        op_id = shift_store.create_operator(
            operator_id=op_id,
            name=req.name,
            employee_code=req.employee_code,
            role=req.role,
            active=req.active,
        )
        return {
            "operator_id": op_id,
            "name": req.name,
            "employee_code": req.employee_code,
            "role": req.role,
            "active": True if req.active == 1 else False
        }
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Employee code already exists.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))"""

old_create = re.search(r'@app\.post\("/api/operators"\)\ndef create_operator\(req: CreateOperatorRequest\) -> Dict\[str, Any\]:.*?(?=\n\n@app\.get\("/api/shifts/active"\))', content, re.DOTALL).group(0)

content = content.replace(old_create, new_create)

with open('api/server.py', 'w') as f:
    f.write(content)
