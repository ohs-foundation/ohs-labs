# Lists the on-screen elements of the current app: "x,y C text desc class". C marks clickable. Tap with input.sh.
import re,subprocess,os
adb=os.path.expanduser('~/Library/Android/sdk/platform-tools/adb')
subprocess.run([adb,'shell','uiautomator','dump','/sdcard/u.xml'],capture_output=True)
x=subprocess.run([adb,'shell','cat','/sdcard/u.xml'],capture_output=True,text=True).stdout
for m in re.finditer(r'<node [^>]*>',x):
    n=m.group(0); g=lambda k:(re.search(k+r'="([^"]*)"',n) or [None,''])[1]
    t,d,c=g('text'),g('content-desc'),g('clickable')
    b=re.findall(r'\d+',g('bounds'))
    if (t or d or c=='true') and b:
        x1,y1,x2,y2=map(int,b); print(f"{(x1+x2)//2},{(y1+y2)//2} {'C' if c=='true' else ' '} {t!r} {d!r} {g('class').split('.')[-1]}")
