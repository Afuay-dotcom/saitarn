import json
from shapely.geometry import shape

data = json.load(open("sakon_only.geojson", encoding="utf-8"))

for i, f in enumerate(data["features"][:10], start=1):
    p = shape(f["geometry"]).representative_point()  # จุดที่อยู่ภายใน polygon จริง
    print(f"{i}. lat={p.y:.6f}, lng={p.x:.6f}")
    print(f"   https://www.google.com/maps?q={p.y},{p.x}")