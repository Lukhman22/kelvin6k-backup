import re

with open("ui/src/components/VoiceAssistant.tsx", "r") as f:
    content = f.read()

target = """        <div className="va-controls">
          <button 
            type="button"
            className={`va-btn ${listening || confirming ? "va-btn-recording" : "va-btn-idle"}`}
            onClick={toggleListening}
            disabled={speaking || transcribing || busy}
          >
            {listening || confirming ? "Stop Listening" : speaking ? "Kelvin is speaking..." : transcribing || busy ? "Processing..." : "Enable Voice"}
          </button>"""

replacement = """        <div className="va-controls">
          <button 
            type="button"
            className={`va-btn ${listening || confirming ? "va-btn-recording" : "va-btn-idle"}`}
            onClick={toggleListening}
            disabled={speaking || transcribing || busy}
          >
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
            {listening || confirming ? "Listening…" : speaking ? "Kelvin is speaking…" : transcribing || busy ? "Processing…" : "Enable Voice"}
          </button>"""

new_content = content.replace(target, replacement)

with open("ui/src/components/VoiceAssistant.tsx", "w") as f:
    f.write(new_content)

print("UI labels patched.")
