#!/usr/bin/env python3
"""
GreetBot Audio Debugger
=========================
Run this script on the Raspberry Pi to test speakers and microphone.
"""

import os
import sys
import time

def run_tests():
    print("\n" + "="*50)
    print(" 🛠️  GREETBOT AUDIO DIAGNOSTICS")
    print("="*50)
    
    print("\n[1/4] Listing Audio Output Devices (ALSA)...")
    os.system("aplay -l")
    
    print("\n[2/4] Listing Audio Input Devices (ALSA)...")
    os.system("arecord -l")
    
    print("\n[3/4] Testing Pygame Audio Output...")
    try:
        import pygame
        pygame.mixer.init()
        print("✅ Pygame mixer initialized successfully.")
        
        # Create a simple beep sound in memory instead of requiring a file
        import numpy as np
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(frequency * t * 2 * np.pi)
        audio = np.zeros((len(wave), 2), dtype=np.int16)
        audio[:, 0] = (wave * 32767).astype(np.int16)
        audio[:, 1] = (wave * 32767).astype(np.int16)
        
        sound = pygame.sndarray.make_sound(audio)
        print("🔊 Playing a 1-second beep... Do you hear it?")
        sound.play()
        time.sleep(1.5)
        pygame.mixer.quit()
    except Exception as e:
        print(f"❌ Pygame audio test failed: {e}")
        
    print("\n[4/4] Testing Microphone Recording (5 seconds)...")
    try:
        import sounddevice as sd
        import soundfile as sf
        fs = 16000
        seconds = 5
        print("🎤 Please speak into the microphone now...")
        myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        
        # Calculate volume level
        rms = np.sqrt(np.mean(myrecording.astype(np.float32)**2))
        print(f"✅ Recording finished! Average volume level: {rms:.2f}")
        
        if rms < 10:
            print("⚠️ Volume is VERY LOW. Your microphone might be muted or too far away.")
        else:
            print("✅ Microphone picked up sound successfully.")
            
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")

    print("\n" + "="*50)
    print(" DIAGNOSTICS COMPLETE")
    print("="*50 + "\n")
    print("If you heard no sound, ensure your Pi is sending audio to the correct port:")
    print("Run 'sudo raspi-config' -> System Options -> Audio")
    print("And select either Headphones or HDMI depending on your setup.")

if __name__ == "__main__":
    run_tests()
