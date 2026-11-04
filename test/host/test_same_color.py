#!/usr/bin/env python3
"""Verify endpoint reinforcement preserves every changed-pixel waveform action."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/waveforms/my_waveform.c').read_text()
def function(name):
    start=source.index('static void '+name+'(')
    opening=source.index('{',start)
    depth=1
    end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}')
        end+=1
    return source[start:end]
# lut_or is inline; compile its production body too.
start=source.index('static inline void lut_or(')
end=source.index('\n}',start)+2
code='''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "my_waveform_gc.h"
#include "my_waveform_trim.h"
'''+source[start:end]+function('gc16_reinforce_same_color')+r'''
static unsigned char original[48][16][4], reinforced[48][16][4];
static int get(unsigned char table[48][16][4],int f,int to,int from) {
 return (table[f][to][from/4]>>(6-2*(from%4)))&3;
}
int main(void) {
 const my_waveform_trim_t trim={11,5,0,3};
 int n=my_waveform_trim(&my_gc_25_0,&trim,original);
 assert(n==36);
 assert(my_waveform_trim(&my_gc_25_0,&trim,reinforced)==n);
 gc16_reinforce_same_color(reinforced,n);
 for(int f=0;f<n;f++) for(int to=0;to<16;to++) for(int from=0;from<16;from++) {
  int actual=get(reinforced,f,to,from);
  if(to!=from) assert(actual==get(original,f,to,from));
  else assert(actual==(f==n-2 ? (to==0?1:to==15?2:0) : 0));
 }
 puts("All changed-pixel actions preserved; exactly one same-color endpoint pulse; final hold intact");
}
'''
with tempfile.TemporaryDirectory(prefix='epdiy-same-color-') as tmp:
    p=Path(tmp)
    (p/'test.c').write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'src'),'-I'+str(root/'src/waveforms'),str(p/'test.c'),str(root/'src/waveforms/my_waveform_trim.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
