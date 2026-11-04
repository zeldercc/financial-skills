#!/usr/bin/env python3
"""Standard-library structural and integrity check for the Mi-Sky Agent Skill."""
from pathlib import Path
import re,sys,csv,ast

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[2]
errors=[]
main=HERE/'SKILL.md'
if not main.is_file(): errors.append('missing SKILL.md')
else:
  t=main.read_text(encoding='utf-8')
  if not t.startswith('---\n'):errors.append('missing YAML frontmatter')
  else:
    parts=t.split('---\n',2)
    fm=parts[1] if len(parts)>=3 else ''
    name=re.search(r'^name:\s*(\S+)\s*$',fm,re.M)
    desc=re.search(r'^description:\s*(.+)$',fm,re.M)
    if not name or name.group(1)!=HERE.name:errors.append('name must match folder')
    if name and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name.group(1)):errors.append('invalid name format')
    if not desc or not desc.group(1).strip():errors.append('missing description')
    if desc and len(desc.group(1))>1024:errors.append('description too long')
  refs=re.findall(r'`((?:references|templates)/[^`]+\.(?:md|csv))`',t)
  for rel in refs:
    if not (HERE/rel).is_file():errors.append('unresolved reference: '+rel)
  if len(t.splitlines())>500:errors.append('SKILL.md over 500 lines')
for fn in ('core-methodology.md','source-index.md','evidence-protocol.md','decision-process.md','historical-notes.md','technical-playbook.md','stock-selection.md','price-action-and-exits.md','multi-timeframe-and-chips.md','chanlun-framework.md','unified-decision-framework.md'):
  if not (HERE/'references'/fn).exists():errors.append('missing '+fn)
for scriptname in ('analyze_ohlcv.py','screen_watchlist.py','analyze_multitimeframe.py','chan_segment_check.py'):
  script=HERE/'scripts'/scriptname
  if not script.is_file():errors.append('missing analyzer '+scriptname)
  else:
    try:ast.parse(script.read_text(encoding='utf-8'),filename=str(script))
    except SyntaxError as ex:errors.append(scriptname+' syntax error: '+str(ex))
with (HERE/'templates/opinion-ledger.csv').open(encoding='utf-8',newline='') as f:
  cols=next(csv.reader(f))
  for req in ('claim_id','claimed_at','source_key','falsifier','status'):
    if req not in cols:errors.append('missing ledger column '+req)
source=(HERE/'references/source-index.md').read_text(encoding='utf-8')
for key in ('M01','M08','T00','T08','A01','A02','W01','W02','K01','P01','P03','B01','B02','C01','C02'):
  if f'`{key}`' not in source:errors.append('missing source code '+key)
if '目录中共34个文件' not in source:errors.append('source inventory must reflect 34 Drive items')
if errors:
  print('FAILED:')
  for e in errors:print(' - '+e)
  sys.exit(1)
print('PASS: Skill structure, 34-item index, original-source boundaries, 4 script syntax and ledger schema valid')
