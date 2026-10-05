"""Check tracked document links and obvious accidental private artifacts."""
import re
import shutil
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
git=shutil.which('git') or r'C:\Users\LENOVO\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
tracked=subprocess.check_output([git,'-c',f'safe.directory={root}','ls-files','-z'],cwd=root).decode().split('\0')
failures=[];checked=0
for name in filter(None,tracked):
    path=root/name
    if name.startswith(('output/','logs/','.cache/','cookies/','credentials/','sessions/')) or (name.startswith('.env') and name!='.env.example'):
        failures.append('Private artifact tracked: '+name)
    if not path.is_file() or path.suffix not in {'.md','.py','.js','.html','.yml','.toml','.txt','.json'}:
        continue
    text=path.read_text(encoding='utf-8')
    if re.search(r'gh[opsur]_[A-Za-z0-9]{30,}',text):
        failures.append('Possible GitHub credential: '+name)
    if re.search(r'(?:MUSIC_U|qm_keyst|qqmusic_key)\s*[:=]\s*[\"\']?[A-Za-z0-9_-]{24,}',text):
        failures.append('Possible platform credential: '+name)
    if path.suffix=='.md' and 'legacy/' not in name:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            target=target.split(' ')[0].split('#')[0]
            if not target or '://' in target or target.startswith(('mailto:','#')):
                continue
            checked+=1
            if not (path.parent/target).exists():
                failures.append('Missing link: '+name+' → '+target)
if failures:
    print('\n'.join(failures));raise SystemExit(1)
print(f'Repository links and tracked privacy checks OK ({checked} local links)')
