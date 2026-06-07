import speech_recognition as sr
import pyaudio

# List devices
p = pyaudio.PyAudio()
print("Input devices:")
for i in range(p.get_device_count()):
    d = p.get_device_info_by_index(i)
    if d['maxInputChannels'] > 0:
        print(f"  [{i}] {d['name']} ch:{d['maxInputChannels']} rate:{int(d['defaultSampleRate'])}")
p.terminate()

# Try opening each input device
print("\nTesting each device:")
for idx in [None, 5, 6]:
    try:
        mic = sr.Microphone(device_index=idx)
        with mic as src:
            print(f"  [{idx}] OPENED OK — sample_rate:{src.SAMPLE_RATE}")
    except Exception as e:
        print(f"  [{idx}] FAILED: {e}")
