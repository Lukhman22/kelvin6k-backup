import re

with open("ui/src/components/VoiceAssistant.tsx", "r") as f:
    content = f.read()

target = """        {needsPermissionGesture ? (
          <button className="va-enable" onClick={voice.toggleWakeWord}>
            TAP ONCE TO ENABLE HANDS-FREE
          </button>
        ) : null}"""

replacement = """        <div className="va-controls">
          <button 
            type="button"
            className={`va-btn ${listening || confirming ? "va-btn-recording" : "va-btn-idle"}`}
            onClick={toggleListening}
            disabled={speaking || transcribing || busy}
          >
            {listening || confirming ? "Stop Listening" : speaking ? "Kelvin is speaking..." : transcribing || busy ? "Processing..." : "Enable Voice"}
          </button>

          <label className="va-ww-toggle">
            <input 
              type="checkbox" 
              checked={voice.wakeWordEnabled} 
              onChange={voice.toggleWakeWord} 
            />
            <span>Wake Word On</span>
          </label>
        </div>"""

new_content = content.replace(target, replacement)

with open("ui/src/components/VoiceAssistant.tsx", "w") as f:
    f.write(new_content)

print("Patch applied.")
