import json

data = {"name": "robot", "age": 2, "skills": ["piano", "vision"]}
json_data = json.dumps(data, ensure_ascii=False)
print(json_data)

json_data = json.loads(json_data)
print(json_data)