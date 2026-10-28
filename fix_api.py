import re

with open('api/server.py', 'r') as f:
    content = f.read()

content = content.replace(
    '''class CreateOperatorRequest(BaseModel):
    operator_id: str''',
    '''class CreateOperatorRequest(BaseModel):
    operator_id: Optional[str] = None'''
)

with open('api/server.py', 'w') as f:
    f.write(content)
