#!/usr/bin/env python3
"""Fix province classification using title-based extraction only."""
import os, re, json
from collections import Counter

out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "shenlun_zhenti")
manifest_path = os.path.join(out_dir, "_manifest.json")

with open(manifest_path) as f:
    manifest = json.load(f)

PROVINCES = ['北京','天津','上海','重庆','河北','山西','辽宁','吉林','黑龙江',
             '江苏','浙江','安徽','福建','江西','山东','河南','湖北','湖南',
             '广东','深圳','海南','四川','贵州','云南','陕西','甘肃','青海',
             '内蒙古','广西','西藏','宁夏','新疆','联考']

updated = 0
renamed = 0
for entry in manifest:
    title = entry.get('title', '')
    province = '国考'
    
    # Check title for province name
    for p in PROVINCES:
        if p in title:
            province = p if p != '深圳' else '广东'
            break
    
    # Also check if title mentions 国家公务员 or 国考
    if '国考' in title or '国家公务员' in title:
        province = '国考'
    
    old_prov = entry.get('province', '国考')
    if province != old_prov:
        entry['province'] = province
        entry['exam_type'] = '国考' if province == '国考' else '省考'
        updated += 1
    
    # Rename file
    old_file = entry.get('file', '')
    if not old_file:
        continue
    old_path = os.path.join(out_dir, old_file)
    if not os.path.exists(old_path):
        continue
    
    safe_title = re.sub(r'[^\w\u4e00-\u9fff（）]', '_', entry['title'])[:60]
    new_file = f"{province}_{entry['year']}_{safe_title}.md"
    new_path = os.path.join(out_dir, new_file)
    
    if old_file != new_file and not os.path.exists(new_path):
        os.rename(old_path, new_path)
        entry['file'] = new_file
        renamed += 1

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

provinces = Counter(e['province'] for e in manifest)
print(f"修正: {updated}条, 重命名: {renamed}个文件")
print(f"总计: {len(manifest)} 份真题, 总字数: {sum(e['chars'] for e in manifest):,}")
print("\n按省份:")
for p, c in provinces.most_common():
    print(f"  {p}: {c}份")
