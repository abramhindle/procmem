<CsoundSynthesizer>
<CsOptions>
; -L stdin -odac           -iadc     -dm6    ;;;RT audio I/O
-L stdin -odac           -iadc     -dm6  -+rtaudio=jack -+jack_client=csVF  -b 1024 -B 2048   ;;;RT audio I/O
; For Non-realtime ouput leave only the line below:
; -o grain3.wav -W ;;; for file output any platform
</CsOptions>
<CsInstruments>

sr	=  48000
;kr      =  100
ksmps   =  16
nchnls	=  4
0dbfs = 1

gikvgain init 4
gkvgain init gikvgain
gikcarrier init 120
gkcarrier init gikcarrier
gisine init 1
gikharmonics init 16
gkharmonics init gikharmonics
gikdelmix init 0.1
gkdelmix init gikdelmix

itmp	ftgen gisine, 0, 1024, 10, 1

FLpanel "VoiceFilter",900,900, -1, -1, 5, 1, 1
        itype = 5
        ih = 900/6
        iw = 800
        ixoff = 50
        ioff= ih + 50
        imoff = 20
        iexp = 0
   gkvgain, gigkvgain FLslider              "GAIN",        0,   10, iexp,  itype, -1, iw, ih, ixoff, imoff + ioff*0
   gkcarrier, gigkcarrier FLslider      "CarrierF",       10,  440, iexp,  itype, -1, iw, ih, ixoff, imoff + ioff*1
   gkharmonics, gigkharmonics FLslider "Harmonics",        1,   32, iexp,  itype, -1, iw, ih, ixoff, imoff + ioff*2
   gkdelmix,    gigkdelmix    FLslider   "Del Mix",        0,    2, iexp,  itype, -1, iw, ih, ixoff, imoff + ioff*3
FLpanelEnd	;***** end of container   
FLrun		;***** runs the widget thread 

FLsetVal_i gikvgain, gigkvgain
FLsetVal_i gikcarrier, gigkcarrier
FLsetVal_i gikharmonics, gigkharmonics
FLsetVal_i gikdelmix, gigkdelmix


instr 1
ain0    inch 1
ain1    = gkvgain * ain0
acarr   oscili 1.0, gkcarrier, gisine
adelay1 delay acarr, 0.05
adelay2 delay acarr, 0.1
adelay3 delay acarr, 0.01
acarrdelay = (1.0 - gkdelmix)*acarr + 0.3*gkdelmix*(adelay1 + adelay2 + adelay3)
acarr     buzz 1, gkcarrier, gkharmonics, gisine
aring  =  0.8 * acarrdelay * ain1 + 0.2*acarr*ain1
          outs aring, -aring
endin

// This one is supposed to de-DC the output
instr 2
ain2    inch 2
ahp     butterhp ain2, 20
alp     butterlp ahp, 20000
adc     dcblock alp
ares    clip adc, 0, 1.0
alow     butterlp ares, 440
alow1     butterlp alow, 330
alow2     butterlp alow1, 220
alow3     butterlp alow2, 330
alower = alow + alow1 + alow2 + alow3
        outs ares-alower,-ares+alower
endin
</CsInstruments>
<CsScore>
t 0 60

f 0 36000

i 1 0 36000
i 2 0 36000

e
</CsScore>
</CsoundSynthesizer>
