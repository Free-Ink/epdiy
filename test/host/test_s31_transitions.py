#!/usr/bin/env python3
"""Check production S31 packing and pair lookup against the raw GC16 waveform."""
from pathlib import Path
import re
import subprocess
import tempfile
root = Path(__file__).resolve().parents[2]
def function(path, name, declaration):
    source = (root/path).read_text()
    start = re.search(r'\b'+name+r'\s*\(', source).start()
    opening = source.index('{',start)
    depth = 1
    end = opening+1
    while depth:
        depth += (source[end]=='{')-(source[end]=='}')
        end += 1
    return declaration+' '+source[start:end]+'\n'
code = '#include <assert.h>\n#include <stdbool.h>\n#include <stdint.h>\n#include <stdio.h>\n#include <string.h>\n#include "my_waveform_gc.h"\n'
for name in ['build_1ppB_lut_S3_VE_1k','expand_1k_to_pairs_s31','calc_epd_input_1ppB_pairs_s31','changed_only_phase']:
    code += function('src/output_common/lut.c',name,'static void')
code += function('src/output_common/riscv_ve.c','epd_interlace_4bpp_line_VE','static uint32_t')
code += r'''
static uint8_t raw_action(int frame,int pair) {
 int to=pair>>4,from=pair&15;
 return (my_gc_25_0_data[frame][to][from/4]>>(6-2*(from%4)))&3;
}
int main(void) {
 static uint32_t storage[65536/4]; uint8_t *lut=(uint8_t*)storage;
 // Every possible pair of packed old/new bytes; each pixel must keep its own history.
 for(int to=0;to<256;to++) for(int from=0;from<256;from++) {
  uint8_t t=to,f=from,out[2],dirty=0;
  uint32_t changed=epd_interlace_4bpp_line_VE(&t,&f,out,&dirty,2);
  assert(out[0]==(((to&15)<<4)|(from&15)));
  assert(out[1]==((to&240)|(from>>4)));
  assert(dirty==(uint8_t)(to^from));assert(!!changed==(to!=from));
 }
 for(int frame=0;frame<48;frame++) for(int skip=0;skip<2;skip++) {
  uint8_t data[16][4]; EpdWaveformPhases phase=my_gc_25_0;
  if(skip) { changed_only_phase(data,&my_gc_25_0,frame,false);phase.luts=(uint8_t*)data; }
  build_1ppB_lut_S3_VE_1k(lut,&phase,skip?0:frame);
  expand_1k_to_pairs_s31(lut);
  for(int a=0;a<256;a++) for(int b=0;b<256;b++) {
   int va=skip && (a>>4)==(a&15)?0:raw_action(frame,a);
   int vb=skip && (b>>4)==(b&15)?0:raw_action(frame,b);
   assert(lut[(b<<8)|a]==((va<<2)|vb));
   // Also exercise output order, with a,b,b,a in successive pixel positions.
   uint32_t pixels=(uint32_t)a|((uint32_t)b<<8)|((uint32_t)b<<16)|((uint32_t)a<<24);
   uint8_t out;
   calc_epd_input_1ppB_pairs_s31(&pixels,&out,lut,4);
   assert(out==((va<<6)|(vb<<4)|(vb<<2)|va));
  }
 }
 puts("S31 old/new packing and pair lookup match all GC16 phases, with and without unchanged suppression");
}
'''
with tempfile.TemporaryDirectory(prefix='epdiy-transition-') as tmp:
    path=Path(tmp)
    (path/'test.c').write_text(code)
    subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'src'),'-I'+str(root/'src/waveforms'),str(path/'test.c'),'-o',str(path/'test')],check=True)
    subprocess.run([str(path/'test')],check=True)
