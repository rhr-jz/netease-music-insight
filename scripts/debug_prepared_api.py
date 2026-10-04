"""Startup-only probe: no provider request or account credentials are used."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
api=root/'build/online-api'
print('Node found:',bool(shutil.which('node')))
print('Prepared Express found:',(api/'node_modules/express').is_dir())
with tempfile.TemporaryDirectory() as temp:
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','LANG'}}
    env.update(TEMP=temp,TMP=temp,TMPDIR=temp,NODE_ENV='production')
    Path(temp,'anonymous_token').write_text('')
    script=Path(temp,'probe.cjs')
    script.write_text('require('+json.dumps(str(api/'server.js'))+
                      ').serveNcmApi({host:"127.0.0.1",port:58005,checkVersion:false}).then(app=>app.server.close()).catch(e=>{console.error(e);process.exit(1)});',encoding='utf-8')
    run=subprocess.run([shutil.which('node'),str(script)],env=env,cwd=temp,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20)
    print('Startup return code:',run.returncode)
    print(run.stdout[-1000:].encode('ascii','backslashreplace').decode())
    print(run.stderr[-2000:].encode('ascii','backslashreplace').decode())
