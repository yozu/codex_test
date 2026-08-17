from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path('te2do-out')
OUT.mkdir(exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/136 Safari/537.36'})

URLS = {
    'home':'https://www.te2do.jp/',
    'search':'https://www.te2do.jp/contents/?attr=1&xid=1',
    'known_download':'https://www.te2do.jp/download/?attr=1&line_cd=11313&sid=250&station_cd=1131320&xid=',
    'seibu_hanno':'https://www.te2do.jp/cntsearch/station/detail/?line_cd=22001&station_cd=2200125&xid=',
    'seibu_line':'https://www.te2do.jp/cntsearch/station/?line_cd=22001&xid=',
    'seibu_cd':'https://www.te2do.jp/contents/category-n3/?attr=1&cid1=28&cid2=78&cid3=25&xid=%2F1000',
}

report = {}
for key,url in URLS.items():
    r=SESSION.get(url,timeout=60)
    html=r.text
    (OUT/f'{key}.html').write_text(html,encoding='utf-8')
    soup=BeautifulSoup(html,'html.parser')
    forms=[]
    for form in soup.find_all('form'):
        forms.append({
            'action':urllib.parse.urljoin(url,form.get('action','')),
            'method':form.get('method','get'),
            'inputs':[{'name':x.get('name'),'value':x.get('value'),'type':x.get('type')} for x in form.find_all(['input','select','textarea'])],
        })
    media=[]
    for tag in soup.find_all(['audio','source','video','embed','iframe']):
        for attr in ['src','data-src','href']:
            if tag.get(attr): media.append(urllib.parse.urljoin(url,tag.get(attr)))
    links=[]
    for a in soup.find_all('a',href=True):
        href=urllib.parse.urljoin(url,a['href'])
        text=' '.join(a.get_text(' ',strip=True).split())
        if any(term in href.lower() for term in ['download','preview','sound','audio','mp3','m4a','wav']) or any(term in text for term in ['試聴','西武','メロディ']):
            links.append({'text':text,'href':href})
    scripts=[]
    for s in soup.find_all('script',src=True): scripts.append(urllib.parse.urljoin(url,s['src']))
    report[key]={'url':url,'status':r.status_code,'bytes':len(r.content),'forms':forms,'media':media,'links':links[:500],'scripts':scripts}

# Use site's GET search form candidates discovered above, plus common query names.
queries=['西武メロディ1','西武メロディ6','おれは怪物くんだ','銀河鉄道999','旅立ちの日に','地平を駈ける獅子を見た','茶摘み','きれいな川','たのしい場所']
search_results=[]
for q in queries:
    tried=[]
    for endpoint, params in [
        ('https://www.te2do.jp/contents/', {'attr':'1','keyword':q}),
        ('https://www.te2do.jp/contents/', {'attr':'1','word':q}),
        ('https://www.te2do.jp/cntsearch/', {'keyword':q}),
        ('https://www.te2do.jp/contents/detail/', {'keyword':q}),
    ]:
        r=SESSION.get(endpoint,params=params,timeout=60)
        soup=BeautifulSoup(r.text,'html.parser')
        items=[]
        for a in soup.find_all('a',href=True):
            text=' '.join(a.get_text(' ',strip=True).split())
            if q.replace(' ','') in text.replace(' ','') or any(x in text for x in q.split() if len(x)>1):
                items.append({'text':text,'href':urllib.parse.urljoin(r.url,a['href'])})
        tried.append({'url':r.url,'status':r.status_code,'bytes':len(r.content),'items':items[:100]})
    search_results.append({'query':q,'tried':tried})

(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'search-results.json').write_text(json.dumps(search_results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:{'status':v['status'],'forms':len(v['forms']),'media':len(v['media']),'links':len(v['links']),'scripts':len(v['scripts'])} for k,v in report.items()},ensure_ascii=False,indent=2))
