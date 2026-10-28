# QtDragon migration — Phase 0 & 1 validation checklist

This is the **go/no-go** test before investing in the PyVCP→QtVCP panel port.
The original Axis config in the parent directory is untouched; if anything
here misbehaves, abandon this dir and keep using the parent.

---

## Pre-launch sanity checks (already done)

- [x] LinuxCNC version: **2.9.8** — QtDragon supported
- [x] QtDragon installed at `/usr/share/qtvcp/screens/qtdragon/`
- [x] All HAL/python/kins files copied into `qtdragon_test/`
- [x] INI: `DISPLAY = qtvcp qtdragon`, `PYVCP` commented, `PREFERENCE_FILE_PATH` set
- [x] `postgui.hal`: all 28 `pyvcp.*` refs removed; override AND-gates forced
      `in1=1` so axes still enable; aux motors forced OFF
- [x] Main `cylindrical_robot.hal`: no `pyvcp.*` refs — no changes needed

---

## How to launch (Phase 0)

**Do NOT use `start_linuxcnc.sh` for Phase 0/1** — its `sed` patches assume
`PYVCP = ...` is uncommented and may not behave as expected. Launch directly:

```bash
cd ~/linuxcnc/configs/cylindrical_robot/qtdragon_test
linuxcnc cylindrical_robot.ini
```

If QtDragon's window paints and the bottom status bar is not stuck on
"Loading…", Phase 0 is green. If it errors out, capture:

```bash
linuxcnc cylindrical_robot.ini 2>&1 | tee /tmp/qtdragon-launch.log
```

Common Phase 0 failures and what they mean:
- **"unknown pin/signal pyvcp.X"** → a `pyvcp.*` ref slipped through; grep
  `postgui.hal` again.
- **"Cannot find PYVCP_FILE"** → INI `PYVCP=` line wasn't commented out.
- **EtherCAT/lcec timeout** → drives not powered or network down; unrelated
  to QtDragon, would fail under Axis too.

---

## Phase 1 — joint-mode UX validation (the critical test)

QtDragon is Cartesian-XYZ-centric. For your absolute-encoder + per-joint
override workflow you MUST confirm joint-mode works. Run each item below
and tick it. If any fails, stop and report back before Phase 2.

### 1.1 Startup & home
- [ ] Clear E-stop (F1). QtDragon "Machine On" button (or F2) enables.
- [ ] **F2 triggers auto-home**: J0, J1, J2 all report "homed" within ~1 s.
      This proves `halui.machine.is-on` → `abs-home.machine-on` →
      `halui.home-all` still works under QtDragon.
- [ ] DRO shows X/Y/Z derived from polarkins3d (not raw joint values).

  Verify joint vs world separation from a terminal:
  ```bash
  halcmd show pin joint.0.pos-fb
  halcmd show pin axis.x.pos-fb
  ```
  Joint 0 should read degrees, axis.x should read mm.

### 1.2 Joint-mode jog (the hard part)
QtDragon's default jog UI is X/Y/Z. To jog J0/J1/J2 individually you'll
need joint-mode. Try in this order, stop at the first that works:

- [ ] **Keyboard**: press `$` to toggle joint mode (LinuxCNC convention).
      Then keys `1`/`2`/`3` (or `,`/`.`) jog J0/J1/J2. Check QtDragon
      hasn't rebound these.
- [ ] **DRO click**: tap the DRO row in QtDragon to switch the active
      jog target — see if joint readouts appear in joint mode.
- [ ] **MDI fallback**: `G38.3` / direct halui pins:
      ```bash
      halcmd setp halui.joint.0.select 1
      halcmd setp halui.joint.0.plus 1   # release with 0
      ```
      If this works but UI doesn't, we'd add joint-jog buttons in Phase 2.

**Decision point:** if NONE of the above gives smooth joint jog, QtDragon
needs a custom handler.py or an embedded jog panel — add 4–6 h to the
estimate. Report which methods worked.

### 1.3 Override checkboxes (forced-on in this phase)
- [ ] In another terminal: `halcmd show pin and2.0.out and2.1.out and2.2.out`
      All should be TRUE after machine-on (because in1 is `setp`'d to 1
      and in0 follows `joint.N.amp-enable-out`).
- [ ] Disable a joint via halcmd to simulate the override:
      `halcmd setp and2.0.in1 0` → joint 0 should drop (cia402.enable0 = 0).
      Restore with `setp and2.0.in1 1`.

### 1.4 Resume mode
- [ ] Close LinuxCNC. Edit `qtdragon_test/start_linuxcnc.sh` line 33 to
      tolerate the commented `# PYVCP` line, OR just relaunch with
      `linuxcnc cylindrical_robot.ini` and confirm `saved_positions.json`
      still tracks position (pos-saver runs regardless of GUI).
- [ ] Run a tiny G-code program (e.g. `G0 X100 Y100 Z10`). Pause, close,
      relaunch. Position should be preserved in `saved_positions.json`.

### 1.5 Clean shutdown
- [ ] Machine-off, E-stop, close window. No tracebacks on stdout.

---

---

## Phase 1.5 — joint-jog handler + first declutter pass

A local handler override now lives at
`qtdragon_test/qtvcp/screens/qtdragon/qtdragon_handler.py` (qtvcp resolves
this before the system default). It adds joint-mode jog keybinds and hides
unused widgets in `initialized__`.

### 1.5.1 Joint-mode jog via keyboard
After F1 (E-stop clear) + F2 (machine on + auto-home):

- [ ] Press `$` — status bar should read "Jog mode: Joint" (toggles
      Cartesian↔joint). Press again to return.
- [ ] Press and hold `1` → J0 rotates positive. Release → stops.
- [ ] Press `Q` → J0 rotates negative.
- [ ] Press `2` / `W` → J1 (radius) extends / retracts.
- [ ] Press `3` / `E` → J2 (Z) up / down.
- [ ] Shift + any of the above → fast jog (rate × 2).
- [ ] After jogging joints, press `$` to return to Cartesian, then verify
      X/Y/Z keys still jog through polarkins as before.

Sanity from a terminal while a jog is held:
```bash
halcmd show pin joint.0.vel-cmd   # should be non-zero during J0 jog
```

If a key does nothing, paste back: which key + the status bar text +
any stderr from the launch log.

### 1.5.2 First-pass declutter
On launch, these should be **gone** from the screen (handler hides them
in `_phase15_declutter()` at end of file):

- [ ] Spindle pause button
- [ ] Laser on + ref-laser buttons
- [ ] Camera + ref-camera buttons + camera controls widget
- [ ] Touchplate / touch-sensor / goto-sensor buttons
- [ ] Probe button

What's still visible after this pass is the *base* of QtDragon — main
nav (File/Offsets/Tool/Status/Gcodes/Setup/Settings/Utils), DRO,
jog frame, feed/spindle overrides, gcode viewer. Phase 5 will trim
further (e.g. spindle override widget, unused tabs) once the custom
panel exists.

Decide if Phase 2 is worth doing:
- [ ] Does the *remaining* screen look approximately usable?
- [ ] Are the operations you'd actually do daily reachable without
      excessive clicking?

---

## Reporting back

After running through, paste back:
1. Phase 1: which jog method(s) worked / didn't.
2. Phase 1.5: did joint keybinds work? Did the declutter hide everything
   on the list? Anything else still feels noisy?
3. Any error/traceback text from launch or shutdown.
4. Subjective: does the operator screen feel usable for daily work?

That tells us whether to commit to Phase 2 (PyVCP→QtVCP port) or fall
back to Axis.
