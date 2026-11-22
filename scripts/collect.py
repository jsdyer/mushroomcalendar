#!/usr/bin/env python3
"""Collect bounded, public iNaturalist observations; never request private data."""
from pathlib import Path
from datetime import datetime,timezone,date
import gzip,hashlib,json,math,time,urllib.request,urllib.parse,urllib.error
ROOT=Path(__file__).resolve().parents[1]
AREAS={
 'langley':{'name':'Langley, BC','bounds':[49.02,-122.80,49.20,-122.52],'centre':[49.1044,-122.6608]},
 'halifax':{'name':'Halifax, NS','bounds':[44.56,-63.70,44.74,-63.45],'centre':[44.6488,-63.5752]}}
LICENSES={'cc0','cc-by','cc-by-nc'}
START='2023-01-01';END='2025-12-31';MAX_PAGES=50
LAST_REQUEST=0

def fetch(url):
 global LAST_REQUEST
 for attempt in range(4):
  time.sleep(max(0,1.1-(time.monotonic()-LAST_REQUEST)));LAST_REQUEST=time.monotonic()
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'CoolCode MushroomCalendar/1.0 (+https://coolcode.ca/mushroomcalendar/)','Accept':'application/json'})
   with urllib.request.urlopen(request,timeout=75) as r:raw=r.read(20_000_001)
   if len(raw)>20_000_000:raise ValueError('Response exceeds 20 MB limit')
   result=json.loads(raw)
   if not isinstance(result.get('results'),list) or not isinstance(result.get('total_results'),int):raise ValueError('Unexpected API schema')
   return result,hashlib.sha256(raw).hexdigest()
  except (OSError,TimeoutError):
   if attempt==3:raise
   time.sleep(2**attempt)

def normalize(r,area):
 taxon=r.get('taxon') or {};dt=r.get('observed_on')
 if not isinstance(r.get('id'),int) or not taxon.get('id') or not dt:return None
 try:date.fromisoformat(dt)
 except ValueError:return None
 if not START<=dt<=END:return None
 license=r.get('license_code')
 if license not in LICENSES:return None
 protected=bool(r.get('obscured') or r.get('coordinates_obscured') or r.get('geoprivacy') in ('obscured','private') or r.get('taxon_geoprivacy') in ('obscured','private'))
 coordinates=(r.get('geojson') or {}).get('coordinates');lat=lon=None
 if not protected and isinstance(coordinates,list) and len(coordinates)==2:
  x,y=coordinates
  if isinstance(x,(float,int)) and isinstance(y,(float,int)) and math.isfinite(x) and math.isfinite(y) and -90<=y<=90 and -180<=x<=180:
   lat=round(round(y/.02)*.02,2);lon=round(round(x/.02)*.02,2)
 accuracy=r.get('public_positional_accuracy')
 if not isinstance(accuracy,(int,float)) or accuracy<0 or not math.isfinite(accuracy):accuracy=None
 return {'id':str(r['id']),'area':area,'date':dt[:7] if protected else dt,'month':int(dt[5:7]),'year':int(dt[:4]),'week':None if protected else date.fromisoformat(dt).isocalendar().week,'taxon_id':taxon['id'],'name':taxon.get('name','Fungi'),'common':taxon.get('preferred_common_name',''),'rank':taxon.get('rank','unknown'),'quality':r.get('quality_grade','casual'),'captive':bool(r.get('captive')),'license':license,'observer':(r.get('user') or {}).get('login','unknown'),'privacy':'obscured' if protected else 'open','latitude':lat,'longitude':lon,'accuracy':accuracy}

def validate(payload):
 rows=payload.get('records')
 if payload.get('schema')!=1 or not isinstance(rows,list) or not rows:raise ValueError('Dataset must contain real observations')
 if {r.get('area') for r in rows}!=set(AREAS):raise ValueError('Both regions required')
 if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate observations')
 for r in rows:
  if r['license'] not in LICENSES or r['quality'] not in ('research','needs_id','casual') or not 1<=r['month']<=12:raise ValueError('Invalid source fields')
  if r['privacy']!='open' and (len(r['date'])!=7 or r['latitude'] is not None or r['longitude'] is not None or r['week'] is not None):raise ValueError('Protected record exposed')
  for coordinate in ('latitude','longitude'):
   if r[coordinate] is not None and abs(r[coordinate]/.02-round(r[coordinate]/.02))>1e-7:raise ValueError('Coordinates must be coarse')
 if not payload.get('queries') or not all(q.get('complete') for q in payload['queries']):raise ValueError('Incomplete acquisition must not replace last good snapshot')
 for q in payload['queries']:
  if q['retrieved'] != q['source_total'] or q['included']+q['skipped_invalid'] != q['retrieved']:raise ValueError('Source counts changed during collection; retry')
  if sum(p['returned'] for p in q['pages']) != q['retrieved']:raise ValueError('Page receipts do not reconcile')
  if q['included'] != sum(r['area']==q['area'] for r in rows):raise ValueError('Area coverage does not reconcile')
 json.dumps(payload,allow_nan=False)
 return payload

def collect():
 records=[];queries=[]
 for key,area in AREAS.items():
  s,w,n,e=area['bounds'];params={'taxon_id':47170,'d1':START,'d2':END,'swlat':s,'swlng':w,'nelat':n,'nelng':e,'per_page':200,'order_by':'id','order':'asc','license':','.join(sorted(LICENSES))}
  base='https://api.inaturalist.org/v1/observations?'+urllib.parse.urlencode(params)
  cursor=0;seen=set();total=None;receipts=[];complete=False;skipped=0
  for page in range(MAX_PAGES):
   url=base+('&id_above='+str(cursor) if cursor else '')
   data,digest=fetch(url);batch=data['results']
   if total is None:
    total=data['total_results']
    if not 0<total<=MAX_PAGES*200:raise ValueError(f'{key}: {total} results exceeds collection budget; narrow observation years before refreshing')
   ids=[r.get('id') for r in batch]
   if any(not isinstance(i,int) or i<=cursor or i in seen for i in ids) or ids!=sorted(ids):raise ValueError('Pagination did not advance monotonically')
   receipts.append({'page':page+1,'url':url,'sha256':digest,'returned':len(batch)})
   seen.update(ids)
   for row in batch:
    normalized=normalize(row,key)
    if normalized:records.append(normalized)
    else:skipped+=1
   print(f'{key}: {len(seen)}/{total}',flush=True)
   if len(batch)<200 or len(seen)>=total:complete=True;break
   cursor=ids[-1]
  if not complete:raise ValueError(f'{key}: exhausted pagination budget')
  queries.append({'area':key,'url':base,'source_total':total,'retrieved':len(seen),'included':len(seen)-skipped,'skipped_invalid':skipped,'complete':True,'pages':receipts})
 stamp=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
 return validate({'schema':1,'captured_at':stamp,'period':{'start':START,'end':END},'areas':AREAS,'queries':queries,'records':sorted(records,key=lambda r:int(r['id']))})

def save(payload):
 validate(payload);folder=ROOT/'data';folder.mkdir(exist_ok=True)
 current=folder/'current.json';old=json.loads(current.read_text()) if current.exists() else {'records':[]}
 digest=hashlib.sha256(json.dumps(payload['records'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
 payload['records_sha256']=digest
 history=json.loads((folder/'history.json').read_text()) if (folder/'history.json').exists() else []
 oldrows={r['id']:r for r in old['records']};newrows={r['id']:r for r in payload['records']}
 delta={'added':len(newrows.keys()-oldrows.keys()),'removed':len(oldrows.keys()-newrows.keys()),'changed':sum(oldrows[k]!=newrows[k] for k in oldrows.keys()&newrows.keys())}
 payload['changes']=delta
 if digest!=old.get('records_sha256'):
  path='archive/'+payload['captured_at'][:7]+'/'+payload['captured_at'].replace(':','').replace('-','')+'-'+digest[:10]+'.json.gz';target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True)
  raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
  with target.open('xb') as f:f.write(gzip.compress(raw,mtime=0))
  history.append({'captured_at':payload['captured_at'],'file':path,'sha256':hashlib.sha256(raw).hexdigest(),'count':len(payload['records']),'initial':not bool(oldrows),**delta})
 payload['checked_at']=payload['captured_at']
 if digest==old.get('records_sha256'):payload['captured_at']=old['captured_at'];payload['changes']=old['changes']
 index={'schema':1,'id':'mushroomcalendar','captured_at':payload['captured_at'],'checked_at':payload['checked_at'],'records':len(payload['records']),'snapshots':len(history),'period':payload['period'],'source':'iNaturalist public API','coverage':'Complete licensed public API query results in two fixed regional bounding boxes; 2023–2025 observations.','status':'ok'}
 for name,obj in [('current.json',payload),('history.json',history),('index.json',index)]:
  temp=folder/(name+'.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n');temp.replace(folder/name)
 print(f'Saved {len(newrows)} observations and {len(history)} retained versions')
if __name__=='__main__':save(collect())
