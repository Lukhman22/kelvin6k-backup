import re

with open("ui/src/components/VoiceAssistant.tsx", "r") as f:
    content = f.read()

content = re.sub(r'  const needsPermissionGesture = voice\.supported && \(\!voice\.wakeWordEnabled \|\| \!\!voice\.error\);\n', '', content)

with open("ui/src/components/VoiceAssistant.tsx", "w") as f:
    f.write(content)

with open("ui/src/hooks/__tests__/useVoiceStateMachine.test.ts", "r") as f:
    test_content = f.read()

test_content = test_content.replace("import { describe, it, expect, vi } from 'vitest';", "import { describe, it, expect } from 'vitest';")

with open("ui/src/hooks/__tests__/useVoiceStateMachine.test.ts", "w") as f:
    f.write(test_content)

print("TS errors fixed.")
