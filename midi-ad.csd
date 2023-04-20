<CsoundSynthesizer>
<CsOptions>
; -L stdin -odac           -iadc     -dm6    ;;;RT audio I/O
-L stdin -odac           -iadc -+rtmidi=virtual -M0    -dm6  -+rtaudio=jack -+jack_client=csoundMidi  -b 1024 -B 2048   ;;;RT audio I/O
; For Non-realtime ouput leave only the line below:
; -o grain3.wav -W ;;; for file output any platform
</CsOptions>
<CsInstruments>

sr	=  48000
;kr      =  100
ksmps   =  16
nchnls	=  4
gibase init nchnls
0dbfs = 1
gisine init 1

itmp	ftgen gisine, 0, 1024, 10, 1

gkrelease init 0.5
gksustain init 1
gkdecay init 0
gkattack init 0.5

instr 1
  iattack = i(gkattack)
  idecay = i(gkdecay)
  isustain = i(gksustain)
  irelease = i(gkrelease)
  ival notnum
  ain  inch (ival % gibase) + 1
  aenv madsr iattack, idecay, isustain, irelease
  out ain*aenv
endin

</CsInstruments>
<CsScore>
t 0 60

f 0 36000

e
</CsScore>
</CsoundSynthesizer>
