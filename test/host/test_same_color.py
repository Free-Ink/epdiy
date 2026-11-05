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
get_start=source.index('static inline int lut_get(')
get_end=source.index('\n}',get_start)+2
code='''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "my_waveform_gc.h"
#include "my_waveform_trim.h"
'''+source[start:end]+source[get_start:get_end]+function('gc16_reinforce_same_color')+function('gc16_adjust_endpoint_transitions')+'\nstatic uint8_t s_black_settle_data[3][16][4];\n'+function('black_settle_build')+r'''
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
  else {
   int expected=to==0 && (f==n-3 || f==n-2) ? 1 : to==15 && (f==n-3 || f==n-2) ? 2 : 0;
   assert(actual==expected);
  }
 }
 for(int profile=0;profile<2;profile++) {
  int frames=n;
  if(profile==1) {
   frames=48;
   memcpy(reinforced,my_gc_25_0_data,sizeof(reinforced));
  }
  memcpy(original,reinforced,sizeof(original));
  gc16_adjust_endpoint_transitions(reinforced,frames);
  int changes=0;
  for(int f=0;f<frames;f++) for(int to=0;to<16;to++) for(int from=0;from<16;from++) {
   int before=get(original,f,to,from),after=get(reinforced,f,to,from);
   if(before!=after) {
    assert(((to==15 && from==0) || (to==0 && from==15)) && f<frames-1 && f>0);
    if(to==0) {
     assert(before==1 && after==0);
     for(int later=f+1;later<frames;later++) assert(get(original,later,0,15)!=1);
    } else assert(before==0 && after==2 && get(original,f-1,to,from)==2);
    changes++;
   }
  }
  assert(changes==2);
 }
 black_settle_build();
 for(int f=0;f<3;f++) for(int to=0;to<16;to++) for(int from=0;from<16;from++) {
  int action=(s_black_settle_data[f][to][from/4]>>(6-2*(from%4)))&3;
  assert(action==((f<2 && to==0)?1:0));
 }
 puts("Trimmed GC16: two white and two black reinforcement pulses, final hold intact; white-to-black shortened, black-to-white extension preserved in full and trimmed tables");
}
'''
with tempfile.TemporaryDirectory(prefix='epdiy-same-color-') as tmp:
    p=Path(tmp)
    (p/'test.c').write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'src'),'-I'+str(root/'src/waveforms'),str(p/'test.c'),str(root/'src/waveforms/my_waveform_trim.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
