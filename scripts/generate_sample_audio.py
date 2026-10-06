import math, wave, array
with wave.open('/tmp/welcome.wav','wb') as f:
 f.setparams((1,2,8000,0,'NONE','not compressed'))
 for second in range(1400):
  frequency=[220,261.63,329.63,293.66][(second//8)%4]
  samples=array.array('h',(int(900*math.sin(2*math.pi*frequency*(second+i/8000))*min(1,i/800)*min(1,(8000-i)/800)) for i in range(8000)))
  f.writeframes(samples.tobytes())
