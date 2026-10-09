import json, glob, collections

path = sorted(glob.glob("gistda_features_flood_30days_*.geojson"))[-1]
data = json.load(open(path, encoding="utf-8"))
feats = data["features"]

cnt = collections.Counter(f["properties"].get("pv_tn") for f in feats)
print(path, "| รวมทั้งหมด:", len(feats))
for k, v in cnt.most_common():
    print(k, v)

sakon = [f for f in feats if "สกลนคร" in (f["properties"].get("pv_tn") or "")]
print("\nเฉพาะสกลนคร:", len(sakon))

with open("sakon_only.geojson", "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": sakon}, f, ensure_ascii=False)
print("บันทึก sakon_only.geojson แล้ว")