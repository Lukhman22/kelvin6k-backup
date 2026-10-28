import re

with open("ui/src/components/VoiceAssistant.tsx", "r") as f:
    content = f.read()

target = """  const toggleListening = useCallback(async () => {
    if (recorder.status === "recording") {
      recorder.stop();
      return;
    }
    await startRecording();
  }, [recorder, startRecording]);"""

replacement = """  const toggleListening = useCallback(async () => {
    if (recorder.status === "recording") {
      recorder.stop();
      return;
    }
    handsFreeRef.current = true;
    voiceRef.current?.pauseWakeWord();
    playWakeChime();
    await startRecording({ autoStopOnSilence: true });
  }, [recorder, startRecording]);"""

new_content = content.replace(target, replacement)

with open("ui/src/components/VoiceAssistant.tsx", "w") as f:
    f.write(new_content)

print("Patch applied.")
