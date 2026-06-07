import pyaudio
p = pyaudio.PyAudio()
print("Input devices:")
for i in range(p.get_device_count()):
    d = p.get_device_info_by_index(i)
    if d['maxInputChannels'] > 0:
        print(f"  [{i}] {d['name']} (inputs:{d['maxInputChannels']}, rate:{int(d['defaultSampleRate'])})")
p.terminate()
