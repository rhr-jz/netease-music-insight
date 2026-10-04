"""Repository CI helper. Git credentials stay in memory and are never printed."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
import requests

root=Path(__file__).resolve().parents[1]
git=shutil.which('git') or r'C:\Users\LENOVO\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
repo='rhr-jz/netease-music-insight'
branch='codex/online-web'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['runs','logs','pr','push'])
    parser.add_argument('--run',default='')
    args=parser.parse_args()
    value=subprocess.run([git,'-c',f'safe.directory={root}','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True,timeout=30)
    credential=dict(line.split('=',1) for line in value.stdout.splitlines() if '=' in line)
    token=credential.get('password')
    if not token:
        gh=root/'.runtime/gh/bin/gh.exe'
        if gh.is_file():
            auth=subprocess.run([str(gh),'auth','token'],text=True,capture_output=True,timeout=30)
            if auth.returncode==0:
                token=auth.stdout.strip()
    if not token:
        raise SystemExit('GitHub credential unavailable')
    client=requests.Session()
    client.headers.update({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    base='https://api.github.com/repos/'+repo
    def call(method,path,**kw):
        r=client.request(method,base+path,timeout=60,**kw)
        if not r.ok:
            raise SystemExit('GitHub API status '+str(r.status_code))
        return r
    if args.action=='push':
        env=os.environ.copy();env['GH_TOKEN']=token
        subprocess.run([git,'-c',f'safe.directory={root}','-c','credential.helper=',
                        '-c','credential.helper=!.runtime/gh/bin/gh.exe auth git-credential',
                        'push','-u','origin',branch],cwd=root,env=env,check=True,timeout=120)
    elif args.action=='runs':
        data=call('GET','/actions/runs',params={'branch':branch,'per_page':10}).json()
        print(json.dumps([{'id':r['id'],'name':r['name'],'status':r['status'],'conclusion':r['conclusion'],'url':r['html_url'],'sha':r['head_sha'][:12]} for r in data['workflow_runs']],ensure_ascii=False,indent=2))
    elif args.action=='logs':
        data=call('GET','/actions/runs/'+args.run+'/jobs').json()
        print(json.dumps([{'id':j['id'],'name':j['name'],'conclusion':j['conclusion'],'steps':[{'name':s['name'],'conclusion':s['conclusion']} for s in j.get('steps',[])]} for j in data['jobs']],indent=2))
        for job in data['jobs']:
            if job['conclusion']=='failure':
                r=call('GET','/actions/jobs/'+str(job['id'])+'/logs')
                folder=root/'build/ci';folder.mkdir(parents=True,exist_ok=True)
                (folder/(str(job['id'])+'.log')).write_text(r.text,encoding='utf-8')
                print('Saved CI diagnostic log:',job['id'])
    else:
        existing=call('GET','/pulls',params={'head':'rhr-jz:'+branch,'state':'open'}).json()
        if existing:
            print(existing[0]['html_url']);return
        text=(root/'build/online-pr.md').read_text(encoding='utf-8')
        r=call('POST','/pulls',json={'title':'feat: Music Insight v3 shared Online Web edition','head':branch,'base':'main','body':text})
        print(r.json()['html_url'])

if __name__=='__main__':
    main()
