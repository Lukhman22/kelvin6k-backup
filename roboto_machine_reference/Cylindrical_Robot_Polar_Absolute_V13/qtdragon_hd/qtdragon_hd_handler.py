import os, re, time, bisect
from PyQt5 import QtCore, QtWidgets, QtGui
from qtvcp.widgets.gcode_editor import GcodeEditor as GCODE
from qtvcp.widgets.mdi_line import MDILine as MDI_WIDGET
from qtvcp.widgets.status_label import StatusLabel
from qtvcp.widgets.tool_offsetview import ToolOffsetView as TOOL_TABLE
from qtvcp.widgets.origin_offsetview import OriginOffsetView as OFFSET_VIEW
from qtvcp.widgets.stylesheeteditor import StyleSheetEditor as SSE
from qtvcp.widgets.file_manager import FileManager as FM
from qtvcp.lib.qt_ngcgui.ngcgui import NgcGui
from qtvcp.lib.auto_height.auto_height import Auto_Measure
from qtvcp.lib.writer import writer
from qtvcp.lib.keybindings import Keylookup
from qtvcp.lib.gcodes import GCodes
from qtvcp.lib.qt_pdf import PDFViewer
from qtvcp.lib.aux_program_loader import Aux_program_loader
from qtvcp.core import Status, Action, Info, Path, Qhal
from qtvcp import logger
from shutil import copyfile
from math import sqrt, ceil

LOG = logger.getLogger(__name__)
KEYBIND = Keylookup()
AUX_PRGM = Aux_program_loader()
STATUS = Status()
INFO = Info()
ACTION = Action()
PATH = Path()
STYLEEDITOR = SSE()
WRITER = writer.Main()
QHAL = Qhal()

try:
    from PyQt5.QtWebEngineWidgets import QWebEnginePage
except:
    LOG.warning('QtDragon warning with loading QtWebEngineWidget - is python3-pyqt5.qtwebengine installed?')

# constants for tab pages
# probe is not actually a separate tab now
# but there is a button for showing it in stack
TAB_PROBE = -1
TAB_MAIN = 0
TAB_FILE = 1
TAB_OFFSETS = 2
TAB_TOOL = 3
TAB_STATUS = 4
TAB_CAMVIEW = 5
TAB_GCODES = 6
TAB_SETUP = 7
TAB_SETTINGS = 8
TAB_UTILS = 9
TAB_USER = 10
TAB_PRINT_CAL = 12
# Dynamic MDI history tab — page index assigned at runtime (see _setup_mdi_tab).
TAB_MDI = None

# constants for (left side) stacked widget
PAGE_UNCHANGED = -1
PAGE_GCODE = 0
PAGE_NGCGUI = 1
MACRO = True
NO_MACRO = False

DEFAULT = 0
WARNING = 1
CRITICAL = 2

VERSION ='1.5'

class _MDIPanelSync(QtCore.QObject):
    # Broadcast bus so multiple ManualMDIPanel instances stay in sync.
    # _submit emits command_added -> every instance appends to its list.
    # _clear_history emits history_cleared -> every instance wipes its list.
    command_added = QtCore.pyqtSignal(str)
    history_cleared = QtCore.pyqtSignal()


class ManualMDIPanel(QtWidgets.QWidget):
    """MDI command panel that logs ONLY commands the operator types here.

    LinuxCNC's MDI_HISTORY_FILE (used by qtvcp.MDIHistory) records every
    command sent through MDI, including programmatic ones (tool changes,
    run-from-line, etc.). This panel maintains its own log so the history
    contains only commands actually typed and submitted in this panel.

    Multiple instances (e.g. the MDI top tab and the gcode-side panel)
    share state through a class-level _MDIPanelSync signal bus.
    """

    HISTORY_FILE = 'manual_mdi_history.txt'
    _sync = _MDIPanelSync()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(4)

        self.list = QtWidgets.QListWidget()
        self.list.setFont(QtGui.QFont('Monospace', 11))
        self.list.itemClicked.connect(self._on_item_click)
        self.list.itemDoubleClicked.connect(self._on_item_doubleclick)
        v.addWidget(self.list, 1)

        row = QtWidgets.QHBoxLayout()
        self.entry = QtWidgets.QLineEdit()
        self.entry.setFont(QtGui.QFont('Monospace', 13))
        self.entry.setPlaceholderText('Type MDI command, press Enter to run')
        self.entry.setMinimumHeight(34)
        # Match the original MDILine look: light field on the dark UI so it
        # reads as a clearly clickable input.
        self.entry.setStyleSheet(
            'QLineEdit {'
            ' background: rgb(250,250,250);'
            ' color: black;'
            ' border: 1px solid #888;'
            ' border-radius: 4px;'
            ' padding: 2px 6px;'
            '}')
        self.entry.returnPressed.connect(self._submit)
        self.entry.installEventFilter(self)

        self.btn_run = QtWidgets.QPushButton('RUN')
        self.btn_run.clicked.connect(self._submit)
        self.btn_clear = QtWidgets.QPushButton('CLEAR')
        self.btn_clear.clicked.connect(self._clear_history)
        # Match the entry's minimum height so the row reads as a single bar.
        for _b in (self.btn_run, self.btn_clear):
            _b.setMinimumHeight(34)

        row.addWidget(self.entry, 1)
        row.addWidget(self.btn_run)
        row.addWidget(self.btn_clear)
        v.addLayout(row)

        self._fp = self._resolve_path()
        self._recall_row = -1
        self._load()

        type(self)._sync.command_added.connect(self._on_remote_add)
        type(self)._sync.history_cleared.connect(self._on_remote_clear)

    def _resolve_path(self):
        # Save next to the running ini if PATH gives us its directory,
        # otherwise fall back to the current working directory.
        try:
            d = PATH.CONFIGPATH
        except AttributeError:
            d = None
        if not d:
            d = os.getcwd()
        return os.path.join(d, self.HISTORY_FILE)

    def _load(self):
        if not os.path.exists(self._fp):
            return
        try:
            with open(self._fp, 'r') as f:
                for line in f:
                    s = line.rstrip('\n')
                    if s:
                        self.list.addItem(s)
        except OSError:
            pass
        self.list.scrollToBottom()
        self._recall_row = self.list.count()

    def _append_to_file(self, cmd):
        try:
            with open(self._fp, 'a') as f:
                f.write(cmd + '\n')
        except OSError:
            pass

    def _submit(self):
        cmd = self.entry.text().strip()
        if not cmd:
            return
        # Run via the same path the standard MDI widget uses.
        ACTION.CALL_MDI(cmd)
        # Log to our own history (independent of LinuxCNC's MDI_HISTORY_FILE).
        self._append_to_file(cmd)
        self.entry.clear()
        # Broadcast: every instance (including self) appends to its list.
        type(self)._sync.command_added.emit(cmd)

    def _on_remote_add(self, cmd):
        self.list.addItem(cmd)
        self.list.scrollToBottom()
        self._recall_row = self.list.count()

    def _on_item_click(self, item):
        self.entry.setText(item.text())
        self.entry.setFocus()
        self._recall_row = self.list.row(item)

    def _on_item_doubleclick(self, item):
        self.entry.setText(item.text())
        self._submit()

    def _clear_history(self):
        ret = QtWidgets.QMessageBox.question(
            self, 'Clear history',
            'Clear all manual MDI command history?\n\n'
            'This only affects the manual log, not LinuxCNC.',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        if ret != QtWidgets.QMessageBox.Yes:
            return
        try:
            os.remove(self._fp)
        except OSError:
            pass
        # Broadcast: every instance wipes its list.
        type(self)._sync.history_cleared.emit()

    def _on_remote_clear(self):
        self.list.clear()
        self._recall_row = -1

    def eventFilter(self, obj, event):
        if obj is self.entry:
            et = event.type()
            # Placeholder turns theme-green while focused, dim grey otherwise
            # (matches the qtdragon dark-grey accent #9ad58d).
            if et == QtCore.QEvent.FocusIn:
                self._set_placeholder_color('#9ad58d')
            elif et == QtCore.QEvent.FocusOut:
                self._set_placeholder_color('#888888')
            # Up/Down in the entry box scroll through past commands.
            elif et == QtCore.QEvent.KeyPress:
                n = self.list.count()
                if n == 0:
                    return False
                key = event.key()
                if key == QtCore.Qt.Key_Up:
                    self._recall_row = max(0, (self._recall_row if self._recall_row >= 0 else n) - 1)
                    self.entry.setText(self.list.item(self._recall_row).text())
                    return True
                if key == QtCore.Qt.Key_Down:
                    if self._recall_row < 0 or self._recall_row >= n - 1:
                        self._recall_row = n
                        self.entry.clear()
                    else:
                        self._recall_row += 1
                        self.entry.setText(self.list.item(self._recall_row).text())
                    return True
        return False

    def _set_placeholder_color(self, color):
        p = self.entry.palette()
        p.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(color))
        self.entry.setPalette(p)


class HandlerClass:
    def __init__(self, halcomp, widgets, paths):
        self.h = halcomp
        self.w = widgets
        self.gcodes = GCodes(widgets)
        # This validator precludes using comma as a decimal
        self.valid = QtGui.QRegExpValidator(QtCore.QRegExp('-?[0-9]{0,6}[.][0-9]{0,3}'))
        self.styleeditor = SSE(widgets, paths)
        self.KEYBIND = KEYBIND
        KEYBIND.add_call('Key_F4', 'on_keycall_F4')
        KEYBIND.add_call('Key_F12','on_keycall_F12')
        KEYBIND.add_call('Key_Pause', 'on_keycall_PAUSE')
        KEYBIND.add_call('Key_Any', 'on_keycall_PAUSE')
        KEYBIND.add_call('Key_Period','on_keycall_jograte',1)
        KEYBIND.add_call('Key_Comma','on_keycall_jograte',0)
        KEYBIND.add_call('Key_Greater','on_keycall_angular_jograte',1)
        KEYBIND.add_call('Key_Less','on_keycall_angular_jograte',0)

        # some global variables
        self.factor = 1.0
        self._spindle_wait = False
        self.probe = None
        self.default_setup = os.path.join(PATH.CONFIGPATH, "default_setup.html")
        self.docs = os.path.join(PATH.SCREENDIR, PATH.BASEPATH,'docs/getting_started.html')
        self.start_line = 0
        self.run_time = 0
        self.time_tenths = 0
        self.timer_on = False
        self.home_all = False
        self.min_spindle_rpm = INFO.MIN_SPINDLE_SPEED
        self.max_spindle_rpm = INFO.MAX_SPINDLE_SPEED
        self.max_spindle_power = INFO.get_error_safe_setting('DISPLAY', 'MAX_SPINDLE_POWER',"1500")
        self.max_linear_velocity = INFO.MAX_TRAJ_VELOCITY
        self.system_list = ["G54","G55","G56","G57","G58","G59","G59.1","G59.2","G59.3"]
        self.slow_jog_factor = 10
        self.reload_tool = 0
        self.last_loaded_program = ""
        self.first_turnon = True
        self.unit_label_list = ["ts_height", "tp_height", "zoffset_units", "max_probe_units", "retract_dist_units", "z_safe_travel_units"]
        self.lineedit_list = ["work_height", "touch_height", "sensor_height", "laser_x", "laser_y",
                              "sensor_x", "sensor_y", "camera_x", "camera_y",
                              "search_vel", "probe_vel", "max_probe", "eoffset_count"]
        self.onoff_list = ["frame_program", "frame_tool", "frame_offsets", "frame_dro", "frame_override"]
        self.axis_4_list = ["label_axis_4", "dro_axis_4", "action_zero_4", "axistoolbutton_4",
                            "dro_button_stack_4",  "plus_jogbutton_4", "minus_jogbutton_4",
                            "widget_home_4"]
        self.axis_5_list = ["label_axis_5", "dro_axis_5", "action_zero_5", "axistoolbutton_5",
                            "dro_button_stack_5","plus_jogbutton_5", "minus_jogbutton_5",
                            "widget_home_5"]
        self.statusbar_reset_time = 10000 # ten seconds
        # LAYERS box state: list of 1-based ngc line numbers where each
        # layer (Z-change > 0.01) begins, populated on file_loaded.
        self._layer_starts = []
        self._total_layers = 0

        STATUS.connect('general', self.dialog_return)
        STATUS.connect('state-on', lambda w: self.enable_onoff(True))
        STATUS.connect('state-off', lambda w: self.enable_onoff(False))
        STATUS.connect('mode-auto', lambda w: self.enable_auto(True))
        STATUS.connect('mode-auto', lambda w: self.w.lineEdit_eoffset_count.setEnabled(False))
        STATUS.connect('mode-mdi', lambda w: self.w.lineEdit_eoffset_count.setEnabled(True))
        STATUS.connect('mode-manual', lambda w: self.w.lineEdit_eoffset_count.setEnabled(True))
        STATUS.connect('gcode-line-selected', lambda w, line: self.set_start_line(line))
        STATUS.connect('hard-limits-tripped', self.hard_limit_tripped)
        STATUS.connect('program-pause-changed', lambda w, state: self.w.btn_pause_spindle.setEnabled(state))
        STATUS.connect('user-system-changed', lambda w, data: self.user_system_changed(data))
        STATUS.connect('metric-mode-changed', lambda w, mode: self.metric_mode_changed(mode))
        STATUS.connect('file-loaded', self.file_loaded)
        STATUS.connect('all-homed', self.all_homed)
        STATUS.connect('not-all-homed', self.not_all_homed)
        STATUS.connect('periodic', lambda w: self.periodic_update())
        STATUS.connect('interp-idle', lambda w: self.stop_timer())
        STATUS.connect('actual-spindle-speed-changed',self.update_spindle)
        STATUS.connect('requested-spindle-speed-changed',self.update_spindle_requested)
        STATUS.connect('override-limits-changed', lambda w, state, data: self._check_override_limits(state, data))
        STATUS.connect('graphics-gcode-properties', lambda w, d: self.update_gcode_properties(d))

        self.html = """<html>
<head>
<title>Test page for the download:// scheme</title>
</head>
<body>
<h1>Setup Tab</h1>
<p>If you select a file with .html as a file ending, it will be shown here..</p>
<li><a href="http://linuxcnc.org/docs/devel/html/">Documents online</a></li>
<li><a href="http://linuxcnc.org/docs/2.9/html/gui/qtdragon.html">QtDragon online</a></li>
<li><a href="file://%s">Local files</a></li>
<img src="file://%s" alt="lcnc_swoop" />
<hr />
</body>
</html>
"""%(  os.path.expanduser('~/linuxcnc'),
        os.path.join(paths.IMAGEDIR,'lcnc_swoop.png'))


    def class_patch__(self):
        # override file manager load button
        self.old_fman = FM.load
        FM.load = self.load_code

        # override NGCGui path check
        NgcGui.check_linuxcnc_paths_fail = self.check_linuxcnc_paths_fail_override

    def initialized__(self):
        self.init_pins()
        self.init_preferences()
        self.init_widgets()
        self.init_probe()
        self.init_utils()
        self._setup_mdi_tab()
        self._setup_mdi_side_panel()
        self._move_speeds_to_status()
        self._restructure_dro_and_modes()
        self._move_op_mode_to_calibrate_tab()
        self._install_print_cal_tab()
        self._move_jog_mode_to_jogging()
        self._polish_bottom_row()
        self._fix_machine_state_label()
        self._tidy_jogging_section()
        self._apply_j1_j2_jog_labels()
        self._configure_jog_sliders()
        self._align_j2_column()
        self._style_section_titles()
        self._add_aux_quick_buttons()
        self._compact_overrides()
        self._move_increments_under_sliders()
        self._move_settings_tab_to_end()
        self._hide_home_axis_labels()
        self._tighten_bottom_row_gaps()
        self._add_y_jog_slider()
        self.w.stackedWidget_log.setCurrentIndex(0)
        self.w.stackedWidget_dro.setCurrentIndex(0)
        if self.probe is not None:
            self.probe.hide()
        self.w.btn_pause_spindle.setEnabled(False)
        self.w.btn_dimensions.setChecked(True)
        self.w.page_buttonGroup.buttonClicked.connect(self.main_tab_changed)
        # PROGRAM panel — wire RELOAD FILE explicitly. The .ui has a
        # designer-defined clicked->btn_reload_file_clicked() connection
        # routed through MainWindow, but qtvcp's connectSlotsByName does
        # not always resolve handler-class slots through the screen
        # wrapper. An explicit connect makes the button work reliably.
        try:
            self.w.btn_reload_file.clicked.connect(self.btn_reload_file_clicked)
            # Size to match RUN (btn_cycle_start): 188 min width, height 48,
            # horizontally expanding to fill its column.
            self.w.btn_reload_file.setMinimumSize(188, 48)
            self.w.btn_reload_file.setMaximumSize(16777215, 48)
        except AttributeError:
            pass
        self.w.filemanager_usb.showMediaDir(quiet = True)

    # hide or initiate 4th/5th AXIS dro/jog
        flag = False
        flag4 = True
        num = 4
        for temp in ('A','B','C','U','V','W'):
            if temp in INFO.AVAILABLE_AXES:
                if temp in ('A','B','C'):
                    flag = True
                self.initiate_axis_dro(num,temp)
                num +=1
                if num ==6:
                    break
        # no 5th axis
        if num < 6:
            for i in self.axis_5_list:
                self.w[i].hide()
        # no 4th axis
        if num < 5 :
            for i in self.axis_4_list:
                self.w[i].hide()
        # angular increment controls
        if flag:
           self.w.lbl_increments_linear.setText("INCREMENTS")
        else:
            self.w.widget_jog_angular.hide()
            self.w.widget_increments_angular.hide()
    # set validators for lineEdit widgets
        for val in self.lineedit_list:
            _name = 'lineEdit_' + val
            if hasattr(self.w, _name):
                self.w[_name].setValidator(self.valid)
        self.w.lineEdit_eoffset_count.setValidator(QtGui.QIntValidator(0,100))
    # set unit labels according to machine mode
        unit = "MM" if INFO.MACHINE_IS_METRIC else "IN"
        for i in self.unit_label_list:
            self.w['lbl_' + i].setText(unit)
        unit = "MM/MIN" if INFO.MACHINE_IS_METRIC else "IN/MIN"
        for i in ["search_vel_units", "probe_vel_units", "jog_linear"]:
            self.w['lbl_' + i].setText(unit)
        self.w.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        # Show assigned macrobuttons define in INI under [MDI_COMMAND_LIST]
        flag = True
        macro_button_list = [self.w.macrobutton0, 
                             self.w.macrobutton1, 
                             self.w.macrobutton2, 
                             self.w.macrobutton3, 
                             self.w.macrobutton4, 
                             self.w.macrobutton5, 
                             self.w.macrobutton6, 
                             self.w.macrobutton7, 
                             self.w.macrobutton8,
                             self.w.macrobutton9
                             ]
        for button in (macro_button_list):
            num = button.property('ini_mdi_number')
            try:
                code = INFO.MDI_COMMAND_LIST[num]
                flag = False
            except:
                button.hide()
        # no buttons hide frame
        if flag:
            self.w.frame_macro_buttons.hide()

        message = "--- QtDragon_hd Version {} on Linuxcnc {} ---".format(
            VERSION, STATUS.get_linuxcnc_version())
        STATUS.emit('update-machine-log', message, None)

        # === CYLINDRICAL ROBOT — Auxiliary motor controls (TOOLS tab).
        # DIRECT CONTROL: checkbox ON -> motor runs at slider %; OFF -> stops.
        # No M64/M65 master gate (see postgui_qtdragon.hal aux block).
        # Handler exports the two OUT pins per channel:
        #   qtvcp.aux-<ch>-on       (BIT)   — checkbox state -> mux2.N.sel + LED
        #   qtvcp.aux-<ch>-speed-f  (FLOAT) — slider 0..100 (%) -> scale.N + display
        # The matching IN pins (aux-<ch>-led, aux-<ch>-display) are
        # auto-created by the LED + HALLabel widgets in the .ui.
        self._aux_speed_pins = {}
        self._aux_on_pins = {}
        for _ch in ('ext', 'pump', 'fluid'):
            try:
                _sld = getattr(self.w, 'sld_aux_{}_speed'.format(_ch))
                _chk = getattr(self.w, 'chk_aux_{}_on'.format(_ch))
            except AttributeError:
                continue
            _speed_pin = QHAL.newpin('aux-{}-speed-f'.format(_ch),
                                      QHAL.HAL_FLOAT, QHAL.HAL_OUT)
            _on_pin = QHAL.newpin('aux-{}-on'.format(_ch),
                                   QHAL.HAL_BIT, QHAL.HAL_OUT)
            self._aux_speed_pins[_ch] = _speed_pin
            self._aux_on_pins[_ch] = _on_pin
            # Speed control: the integer slider (coarse) and the editable
            # QLineEdit (fine, decimals — built in _add_aux_quick_buttons)
            # are two views of ONE value: the HAL float pin aux-<ch>-speed-f.
            # Each updates the pin and mirrors the other, with the mirror
            # guarded so there is no feedback loop. Decimals live in the
            # field + pin; the slider just snaps to the nearest whole % as a
            # visual cue.
            _field = self._aux_value_fields.get(_ch) \
                if hasattr(self, '_aux_value_fields') else None

            def _on_slider(v, pin=_speed_pin, fld=_field):
                pin.set(float(v))
                # Don't clobber the box while the operator is typing into it.
                if fld is not None and not fld.hasFocus():
                    fld.setText('{:.1f} %'.format(float(v)))
            _sld.valueChanged.connect(_on_slider)

            if _field is not None:
                def _commit_field(pin=_speed_pin, sld=_sld, fld=_field):
                    # Lenient parse: tolerate a trailing '%' and stray spaces;
                    # revert to the slider value on unparseable input.
                    _txt = fld.text().replace('%', '').strip()
                    try:
                        _val = max(0.0, min(100.0, float(_txt)))
                    except ValueError:
                        _val = float(sld.value())
                    pin.set(_val)
                    # Snap the slider (integer) WITHOUT re-driving the pin.
                    sld.blockSignals(True)
                    sld.setValue(int(round(_val)))
                    sld.blockSignals(False)
                    fld.setText('{:.1f} %'.format(_val))
                _field.editingFinished.connect(_commit_field)

            # Checkbox -> HAL bit pin
            _chk.stateChanged.connect(
                lambda state, pin=_on_pin: pin.set(bool(state)))

            # Restore the last-used speed from the preference file (decimals
            # preserved) so the operator doesn't re-dial it every boot (saved
            # in closing_cleanup__). The on-state is deliberately NOT restored
            # — an aux motor must never auto-start on boot.
            _restored = float(_sld.value())
            if self.w.PREFS_:
                _restored = max(0.0, min(100.0, float(self.w.PREFS_.getpref(
                    'Aux {} speed'.format(_ch), float(_sld.value()),
                    float, 'CUSTOM_FORM_ENTRIES'))))
                _sld.blockSignals(True)
                _sld.setValue(int(round(_restored)))
                _sld.blockSignals(False)
                if _field is not None:
                    _field.setText('{:.1f} %'.format(_restored))
            # Seed both pins from the restored state. valueChanged /
            # stateChanged only fire on a *change*, so without this the speed
            # pin stays 0.0 at startup even though the box shows a non-zero %.
            _speed_pin.set(_restored)
            _on_pin.set(bool(_chk.isChecked()))

        # Auto-gate Aux off around the print cycle. Slider values are NEVER
        # touched — only the on-checkboxes flip, which then drive the HAL
        # on-pins via the stateChanged connection above. Turning Aux ON
        # initially is the operator's job; we only handle the off/restore.
        #   pause            -> snapshot current state, all OFF
        #   resume           -> restore snapshot (back ON if it was on)
        #   stop / complete  -> all OFF, clear snapshot
        self._aux_pause_snapshot = None
        _aux_channels = tuple(self._aux_on_pins.keys())

        def _aux_set_all(on):
            for _c in _aux_channels:
                _b = getattr(self.w, 'chk_aux_{}_on'.format(_c), None)
                if _b is not None:
                    _b.setChecked(bool(on))

        def _aux_snapshot():
            snap = {}
            for _c in _aux_channels:
                _b = getattr(self.w, 'chk_aux_{}_on'.format(_c), None)
                if _b is not None:
                    snap[_c] = _b.isChecked()
            return snap

        def _aux_restore(snap):
            if not snap:
                return
            for _c, _v in snap.items():
                _b = getattr(self.w, 'chk_aux_{}_on'.format(_c), None)
                if _b is not None:
                    _b.setChecked(bool(_v))

        def _aux_on_pause_changed(_w, state):
            if state:
                self._aux_pause_snapshot = _aux_snapshot()
                _aux_set_all(False)
            else:
                if self._aux_pause_snapshot is not None:
                    _aux_restore(self._aux_pause_snapshot)
                    self._aux_pause_snapshot = None

        def _aux_on_idle(_w=None):
            self._aux_pause_snapshot = None
            _aux_set_all(False)

        STATUS.connect('program-pause-changed', _aux_on_pause_changed)
        STATUS.connect('interp-idle', _aux_on_idle)
        STATUS.connect('state-off', _aux_on_idle)

        # === CYLINDRICAL ROBOT — "Material auto-start on run" arm toggle ===
        # A checkable button pinned to the TOP of the AUX MOTORS panel. It
        # arms the INITIAL turn-on only:
        #   ARMED  + Run-from-start -> all material controls switch on
        #                              automatically (real print).
        #   OFF    + Run-from-start -> material stays off (air print, used
        #                              to check the print area first).
        # The auto-off/restore-on around pause/resume and the turn-all-off
        # on idle/complete above are deliberately NOT touched. This hooks
        # 'interp-run', which GStat emits ONLY on a genuine idle->running
        # transition (never on resume — see hal_glib), and it is gated to
        # AUTO mode so an MDI move never dispenses material. Defaults OFF on
        # every boot so material can never auto-arm unattended.
        _aux_arm_btn = QtWidgets.QPushButton()
        _aux_arm_btn.setObjectName('btn_aux_arm')
        _aux_arm_btn.setCheckable(True)
        _aux_arm_btn.setChecked(False)
        # Height matches the RUN button (btn_cycle_start = 48 px tall).
        _aux_arm_btn.setMinimumHeight(48)
        _aux_arm_btn.setMaximumHeight(48)
        _arm_sp = _aux_arm_btn.sizePolicy()
        _arm_sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        _aux_arm_btn.setSizePolicy(_arm_sp)
        _aux_arm_btn.setToolTip(
            'ARMED: material controls (Extruder, Pump, Fluid Pump) switch\n'
            'on automatically when a print is started from the beginning.\n'
            'OFF: Run leaves material off (air print).')

        def _aux_arm_text(checked):
            _aux_arm_btn.setText(
                'MATERIAL AUTO-START: ON' if checked
                else 'MATERIAL AUTO-START: OFF')
        _aux_arm_text(False)
        _aux_arm_btn.toggled.connect(_aux_arm_text)

        # Insert at the very top of the AUX MOTORS panel (vlay_aux_panel);
        # the three existing motor rows flow down. Fetch the layout via the
        # extruder groupbox's parent — same tactic as _add_aux_quick_buttons.
        try:
            _aux_panel_layout = self.w.groupBox_aux_extruder.parentWidget().layout()
        except AttributeError:
            _aux_panel_layout = None
        if _aux_panel_layout is not None:
            _aux_panel_layout.insertWidget(0, _aux_arm_btn)
        # Force the app QSS to apply now that the button exists (Qt's initial
        # polish ran before it did) so it matches the theme, incl. :checked.
        _aux_arm_btn.style().unpolish(_aux_arm_btn)
        _aux_arm_btn.style().polish(_aux_arm_btn)
        self.w.btn_aux_arm = _aux_arm_btn

        def _aux_on_run_start(_w=None):
            # Fires ONLY on idle->running (fresh Run), never on resume.
            # Gate to AUTO so an MDI move never turns material on. When
            # armed, switch every material control on via the same checkbox
            # path the operator would use by hand.
            if not _aux_arm_btn.isChecked():
                return
            if not STATUS.is_auto_mode():
                return
            _aux_set_all(True)

        STATUS.connect('interp-run', _aux_on_run_start)

        # === CYLINDRICAL ROBOT — Drives override checkboxes (in OFFSETS panel).
        # Replaces 'setp and2.0/1/2.in1 1' from postgui_qtdragon.hal. Each
        # pin defaults True (matches checkbox checked=true), so boot
        # behaviour is identical to the previous force-on.
        # Per-joint Home/Unhome are NOT here — the DRO has built-in
        # btn_home_x/y/z toggle buttons (see btn_home_clicked at line ~1068).
        self._drv_override_pins = {}
        for _j in ('0', '1', '2'):
            try:
                _chk = getattr(self.w, 'chk_j{}_override'.format(_j))
            except AttributeError:
                continue
            _ovr_pin = QHAL.newpin('j{}-override'.format(_j),
                                    QHAL.HAL_BIT, QHAL.HAL_OUT)
            _ovr_pin.set(True)  # default: drive enabled
            self._drv_override_pins[_j] = _ovr_pin
            _chk.stateChanged.connect(
                lambda s, pin=_ovr_pin: pin.set(bool(s)))

        # Home All / Unhome All are NOT here — the DRO's btn_home_all
        # toggle (text flips HOME ALL ↔ ALL HOMED) handles both, with a
        # confirmation dialog for unhome. See btn_home_all_clicked.

        # === CYLINDRICAL ROBOT — JOG CARTESIAN/JOINT toggle (in JOGGING panel).
        # Equivalent to '$' key in classic AXIS GUI. Cartesian (a.k.a. world)
        # jog moves X/Y/Z via polarkins3d -> joints; joint jog moves J0/J1/J2
        # directly — needed to use the angular jog slider for J0.
        def _jog_mode_text():
            self.w.btn_jog_mode_toggle.setText(
                'JOG: CARTESIAN' if STATUS.is_world_mode() else 'JOG: JOINT')
        try:
            self.w.btn_jog_mode_toggle.clicked.connect(
                lambda: ACTION.TOGGLE_TELEOP_MODE())
            STATUS.connect('motion-mode-changed',
                           lambda w, mode: _jog_mode_text())
            _jog_mode_text()  # initial state
        except AttributeError:
            pass
        # Keyboard shortcut '$' (Shift+4) — same as AXIS GUI.
        KEYBIND.add_call('Key_Dollar', 'on_keycall_jog_mode_toggle')

        # === CYLINDRICAL ROBOT — ZERO Z touch-off + Z-jog lock.
        # Z=0     : sets current Z as WCS Z=0 AND locks manual Z jog.
        #           Once locked, pressing z_plus_jogbutton or z_minus_jogbutton
        #           pops a confirmation dialog ("Allow this Z jog?"). OK
        #           clears the lock but ALWAYS swallows this press — the
        #           operator must release and tap again to jog. If we let
        #           the original press through, the modal dialog has
        #           already consumed the matching MouseRelease (released
        #           on the dialog's OK button), and the hold-to-jog button
        #           would get a press with no release → continuous jog
        #           until limit. That can crash the nozzle into the bed.
        # Lock applies to MANUAL JOG ONLY — G-code Z moves are unaffected.
        from PyQt5.QtCore import QObject as _QObject, QEvent as _QEvent
        from PyQt5.QtWidgets import QMessageBox as _QMessageBox

        self._z_locked = False

        class _ZJogGuard(_QObject):
            def __init__(_self, handler):
                super().__init__()
                _self.handler = handler

            def eventFilter(_self, obj, event):
                if (event.type() == _QEvent.MouseButtonPress
                        and _self.handler._z_locked):
                    _ret = _QMessageBox.question(
                        obj, "Z Locked",
                        "Z is locked at the zero reference.\n"
                        "Allow Z jog?\n\n"
                        "OK     = unlock (tap Z+/Z− again to jog)\n"
                        "Cancel = keep locked",
                        _QMessageBox.Ok | _QMessageBox.Cancel,
                        _QMessageBox.Cancel)
                    if _ret == _QMessageBox.Ok:
                        _self.handler._z_locked = False
                        _self.handler.w.btn_zero_z.setChecked(False)
                        STATUS.emit('update-machine-log',
                            'Z jog unlocked — tap Z+/Z− again to jog.',
                            None)
                    # Swallow this press in both cases. Letting it through
                    # would deliver a MousePress with no matching Release,
                    # causing a continuous jog.
                    return True
                return False

        self._z_jog_guard = _ZJogGuard(self)

        def _on_zero_z():
            ACTION.SET_AXIS_ORIGIN('Z', 0)
            self._z_locked = True
            self.w.btn_zero_z.setChecked(True)
            STATUS.emit('update-machine-log',
                'Z=0 set at current Z. Manual Z jog locked.', None)

        try:
            self.w.btn_zero_z.clicked.connect(_on_zero_z)
            self.w.z_plus_jogbutton.installEventFilter(self._z_jog_guard)
            self.w.z_minus_jogbutton.installEventFilter(self._z_jog_guard)
        except AttributeError:
            pass

        # === CYLINDRICAL ROBOT — Operating mode (CALIBRATE / ABSOLUTE).
        # Phase 1 auto-resume: in ABSOLUTE mode, when machine turns on
        # the last-running G-code file and line are loaded into RUN. The
        # operator still presses RUN to actually start (one-click resume).
        # In CALIBRATE mode no auto-anything — operator drives everything.
        # Mode persisted in mode.json next to the INI.
        import json as _json
        self._op_mode_path = os.path.join(
            self.PATHS.CONFIGPATH if hasattr(self, 'PATHS') else os.getcwd(),
            'mode.json')
        self._saved_pos_path = os.path.join(
            os.path.dirname(self._op_mode_path), 'saved_positions.json')
        # Durable record of the original .ngc path (written on file-load,
        # not on close) so a power-cut still has the path for auto-resume.
        self._last_gcode_path = os.path.join(
            os.path.dirname(self._op_mode_path), 'last_gcode.txt')

        def _load_op_mode():
            try:
                with open(self._op_mode_path) as _f:
                    return _json.load(_f).get('mode', 'absolute')
            except (FileNotFoundError, ValueError):
                return 'absolute'

        def _save_op_mode(mode):
            try:
                with open(self._op_mode_path, 'w') as _f:
                    _json.dump({'mode': mode}, _f)
            except OSError:
                pass

        def _refresh_mode_btn(mode):
            self.w.btn_op_mode.setText('MODE: {}'.format(mode.upper()))
            self.w.btn_op_mode.setChecked(mode == 'absolute')

        def _toggle_op_mode():
            new_mode = 'absolute' if self.w.btn_op_mode.isChecked() else 'calibrate'
            # Confirm before turning OFF auto-resume — easy to hit by accident
            # and the consequence (no auto-resume on next power-cut) is silent.
            if new_mode == 'calibrate':
                _ret = _QMessageBox.question(
                    self.w, "Switch to CALIBRATE?",
                    "Switching to CALIBRATE mode will DISABLE auto-resume.\n\n"
                    "On the next launch, no G-code file will be auto-loaded "
                    "and you will have to load files manually.\n\n"
                    "Use CALIBRATE only for jogging, homing checks, or "
                    "J0/J1/J2 calibration.\n\n"
                    "Continue?",
                    _QMessageBox.Yes | _QMessageBox.No,
                    _QMessageBox.No)
                if _ret != _QMessageBox.Yes:
                    # Revert the button state — user cancelled.
                    self.w.btn_op_mode.setChecked(True)
                    _refresh_mode_btn('absolute')
                    return
            _save_op_mode(new_mode)
            _refresh_mode_btn(new_mode)
            STATUS.emit('update-machine-log',
                        '*** Operating mode → {} ***'.format(new_mode.upper()),
                        None)

        self._auto_resume_done = False

        def _resolve_resume():
            # Resolve the (file, line) to auto-resume in ABSOLUTE mode, or
            # (None, line) if there's nothing resumable. Shared by the
            # auto-resume itself AND the G92-preserve check below, so both
            # agree on whether a power-cut resume is in progress regardless
            # of which STATUS signal fires first.
            if _load_op_mode() != 'absolute':
                return None, 0
            try:
                with open(self._saved_pos_path) as _f:
                    saved = _json.load(_f)
            except (FileNotFoundError, ValueError):
                saved = {}
            fname = saved.get('gcode_file')
            line = int(saved.get('gcode_line', 0) or 0)
            # The position_saver records lcnc_stat.file, which is the
            # [FILTER] temp path (/tmp/emcflt-*). That path is deleted on
            # LinuxCNC shutdown — so on next launch fall back to the
            # original path persisted on every file-load (survives power
            # cuts), then to PREFS_ (clean-shutdown-only) as last resort.
            if (not fname or fname.startswith('/tmp/emcflt-') or
                    not os.path.isfile(fname)):
                try:
                    with open(self._last_gcode_path) as _lf:
                        fname = _lf.read().strip()
                except (FileNotFoundError, OSError):
                    fname = None
            if not fname or not os.path.isfile(fname):
                fname = self.w.PREFS_.getpref('last_loaded_file', None, str, 'BOOK_KEEPING')
            if not fname or not os.path.isfile(fname):
                return None, line
            return fname, line

        def _auto_resume_if_absolute(_w=None):
            # Only fire ONCE per process — otherwise cycling the machine
            # after a manual file-load would clobber the operator's choice.
            if self._auto_resume_done:
                return
            if _load_op_mode() != 'absolute':
                STATUS.emit('update-machine-log',
                            'AUTO-RESUME: skipped (mode is CALIBRATE).', None)
                return
            fname, line = _resolve_resume()
            if not fname:
                STATUS.emit('update-machine-log',
                            'AUTO-RESUME: no saved file.', None)
                return
            self._auto_resume_done = True
            STATUS.emit('update-machine-log',
                        'AUTO-RESUME: loading {} @ line {}'.format(fname, line),
                        None)
            # Seed _original_loaded_file so file_loaded() can recover the
            # real path when LinuxCNC hands it the [FILTER] /tmp temp.
            # Without this, last_gcode.txt would get overwritten with the
            # /tmp/emcflt-* path and the NEXT launch's auto-resume fails.
            self._original_loaded_file = fname
            ACTION.OPEN_PROGRAM(fname)
            if line > 1:
                # Engage Run-from-line so set_start_line keeps the value
                # and btn_cycle_start text shows "RUN\nLINE N".
                self.w.chk_run_from_line.setChecked(True)
                self.start_line = line
                self.w.btn_cycle_start.setText("RUN\nLINE {}".format(line))

        # Clear saved_positions.json when a print COMPLETES naturally so
        # the next launch in ABSOLUTE mode doesn't try to "resume" a
        # finished file (which would replay just the trailing M-codes).
        # 'reached 100' flag is set in percent_done_changed; reset when
        # a fresh program starts.
        self._reached_100 = False

        def _clear_saved_pos_on_completion(_w=None):
            if not self._reached_100:
                return  # operator abort / stop / error → keep saved for resume
            self._reached_100 = False
            # Clear BOTH state files so the next launch starts fresh — no
            # ghost file is auto-loaded from a finished print.
            for _p in (self._saved_pos_path, self._last_gcode_path):
                try:
                    os.remove(_p)
                except (OSError, AttributeError):
                    pass
            STATUS.emit('update-machine-log',
                'Print completed — resume state cleared.', None)

        def _reset_completion_flag(_w=None):
            self._reached_100 = False

        # Clear any G92 offsets persisted in linuxcnc.var across sessions.
        # LinuxCNC auto-loads G92 from params 5210..5219 at start, and the
        # offset survives across restarts. If a previous session ever set
        # one (intentionally or by mistake), every subsequent print would
        # be shifted until G92.1 is sent. Auto-issue once per machine-on.
        # Must wait for all-homed: MDI is blocked pre-homing on this
        # kinematic config. Use CALL_MDI_WAIT so the mode switch to MDI
        # is handled (plain CALL_MDI errors with "Must be in MDI mode").
        #
        # EXCEPTION: if a power-cut resume is pending, the saved positions
        # were recorded WITH the operator's G92 offset active (e.g. they
        # jogged to a second spot, set G92 to relocate the print, and were
        # printing there). LinuxCNC restores that G92 from linuxcnc.var on
        # restart — clearing it would send the resumed print back to the
        # original, un-offset coordinates. So preserve G92 while resuming;
        # it's cleared on the next machine-on once the print completes and
        # the resume state is removed.
        self._g92_cleared = False

        def _clear_g92_after_homing(_w=None):
            if self._g92_cleared:
                return
            resume_fname, _ = _resolve_resume()
            if resume_fname:
                # Don't retry on later homings this session, and don't wipe
                # the offset the resumed print depends on.
                self._g92_cleared = True
                STATUS.emit('update-machine-log',
                    'G92 preserved for auto-resume of {}.'.format(
                        os.path.basename(resume_fname)), None)
                return
            try:
                ACTION.CALL_MDI_WAIT("G92.1", 3)
                ACTION.SET_MANUAL_MODE()
                self._g92_cleared = True
                STATUS.emit('update-machine-log',
                    'Auto-issued G92.1 — G92 offsets cleared.', None)
            except Exception:
                pass

        def _reset_g92_flag(_w=None):
            self._g92_cleared = False

        try:
            self.w.btn_op_mode.clicked.connect(_toggle_op_mode)
            _refresh_mode_btn(_load_op_mode())
            STATUS.connect('state-on', _auto_resume_if_absolute)
            STATUS.connect('all-homed', _clear_g92_after_homing)
            STATUS.connect('state-off', _reset_g92_flag)
            STATUS.connect('interp-run', _reset_completion_flag)
            STATUS.connect('interp-idle', _clear_saved_pos_on_completion)
        except AttributeError:
            pass

        # === CYLINDRICAL ROBOT — CALIBRATE tab buttons.
        # Buttons fire a 200 ms momentary pulse on qtvcp.cal-jN which
        # postgui_qtdragon.hal nets to jN-cal.calibrate (BIT IN pins on the
        # userspace helpers: j0_calibrate.py, j1_calibrate.py, j2_calibrate.py).
        from PyQt5.QtCore import QTimer as _QTimer
        def _make_pulse(pin):
            def _click():
                pin.set(True)
                _QTimer.singleShot(200, lambda: pin.set(False))
            return _click
        for _j in ('0', '1', '2'):
            try:
                _btn = getattr(self.w, 'btn_cal_j{}'.format(_j))
            except AttributeError:
                continue
            _pin = QHAL.newpin('cal-j{}'.format(_j),
                                QHAL.HAL_BIT, QHAL.HAL_OUT)
            _btn.clicked.connect(_make_pulse(_pin))

        # === CYLINDRICAL ROBOT — force-show the angular jog widget.
        # QtDragon hides widget_jog_angular when no A/B/C axis is exposed at
        # the trajectory level. Our machine has no angular AXIS (X Y Z only)
        # but J0 is an angular JOINT, so the slider is meaningful for
        # joint-mode jogging. Override the earlier .hide() above.
        try:
            self.w.widget_jog_angular.show()
            # widget_increments_angular and the LINEAR/ANGULAR INCREMENT
            # labels are hidden via _move_increments_under_sliders() —
            # the JogIncrements combos now live inline under each slider.
        except (AttributeError, RuntimeError):
            pass

        # === CYLINDRICAL ROBOT — hide widgets the polar plotter doesn't use.
        # Spindle widgets are intentionally KEPT (the gauge will be repurposed
        # to show TCP velocity / print speed). Restoration: delete this block,
        # or restore qtdragon_hd.bak/ over qtdragon_hd/.
        _hide = [
            # MODBUS panel (no VFD over Modbus)
            'frame_modbus', 'widget_modbus_fault',
            # Coolant (no mist/flood on a plotter)
            'action_mist', 'action_flood', 'widget_mist_flood',
            # Laser crosshair
            'btn_laser_on', 'btn_ref_laser',
            'widget_laser_offset', 'lineEdit_laser_x', 'lineEdit_laser_y',
            # Camera + CAMVIEW button
            'btn_camera', 'btn_ref_camera', 'chk_use_camera',
            'widget_camera_offset', 'widget_cam_controls',
            'lineEdit_camera_x', 'lineEdit_camera_y',
            # Tool sensor / touchplate
            'btn_tool_sensor', 'btn_touchplate', 'btn_goto_sensor',
            'chk_use_tool_sensor', 'chk_use_touchplate',
            'widget_sensor_location', 'widget_sensor_height', 'widget_touch_height',
            'lineEdit_sensor_x', 'lineEdit_sensor_y',
            'lineEdit_sensor_height', 'lineEdit_touch_height',
            # Probe button + probe parameters in SETUP
            'btn_probe', 'groupBox_probe_parameters',
            'widget_probe_vel', 'widget_max_probe',
            'lineEdit_probe_vel', 'lineEdit_max_probe',
            'lbl_probe_vel_units', 'lbl_max_probe_units',
            # G30 secondary park
            'action_g30',
            # External offsets / Z compensation
            'chk_eoffsets', 'widget_eoffset', 'lineEdit_eoffset_count',
            'btn_enable_comp',
            # OFFSETS panel (bottom strip) — WORKPIECE HEIGHT is for laser /
            # touchplate workflows, not relevant to a polar plotter.
            'chk_lock_wph', 'lineEdit_work_height',
            # STATUS panel — UNITS row is fixed at MM for this machine
            # (LINEAR_UNITS = mm in INI). Hiding the whole widget hides
            # both the label and the value cleanly.
            'widget_units',
            # DRO G54 button — redundant on a single-fixture plotter
            # (WCS already shows G54 since G54 is the only WCS used).
            'actionbutton_rel',
            # OFFSETS panel — GO HOME (G53 G0 to a saved XY) is for mill
            # parking workflows. Polar plotter has no parking concept and
            # cartesian X=0,Y=0 is outside the reachable annulus anyway.
            'btn_go_home',
            # All manual Home buttons + their homed-LED indicators + HOME-value
            # labels. AXIS custompanel.xml has no Home widgets at all — the
            # PyVCP dashboard is the visual reference and QtDragon should
            # match. Homing still works: F2 (machine-on) → abs_home.py
            # pulses halui.home-all in the backend. Operator never needs
            # to click a Home button.
            'btn_home_x', 'btn_home_y', 'btn_home_z', 'btn_home_all',
            'btn_home_4', 'btn_home_5',
            'action_home_6', 'action_home_7',
            'hal_led_home_x', 'hal_led_home_y', 'hal_led_home_z',
            'hal_led_home_4', 'hal_led_home_5',
            'widget_home_4', 'widget_home_5',
            'lbl_home_x', 'lbl_home_y',
            # DRO per-axis "REF X / Y / Z" reference buttons (AxisToolButton
            # widgets) — pop a menu of {Set Origin, Set to..., Home, Zero}
            # for that axis. Home is auto-handled via abs_home.py + F2;
            # zero is provided by the CTR XY / Z=0 buttons next to the
            # visualizer; Set-to/Set-Origin are mill workflows the polar
            # plotter doesn't use. Hide the per-axis button stacks too so
            # the empty column collapses cleanly.
            'axistoolbutton_x', 'axistoolbutton_y', 'axistoolbutton_z',
            'axistoolbutton_4', 'axistoolbutton_5',
            'dro_button_stack_x', 'dro_button_stack_y', 'dro_button_stack_z',
            'dro_button_stack_4', 'dro_button_stack_5',
            # PROGRAM panel — Z AXIS COMP + SPINDLE LIFT rows are mill /
            # plasma workflows. Inner widgets (eoffset value, btn_enable_comp)
            # are already hidden, but the parent QWidgets stay visible as
            # empty bars in the QVBoxLayout. Hide the parents so the rows
            # collapse completely.
            'widget_zaxis_offset', 'widget_zaxis_offset_2',
            # MODBUS frame — its only two children (widget_spindle_error +
            # widget_spindle_fault) are hidden. The empty "MODBUS" titled
            # groupbox just shows a header bar. Hide the whole frame.
            'frame_modbus',
            # OVERRIDES panel — SPINDLE row useless without a spindle.
            'widget_spindle_ovr',
            # USER tab placeholder — we have CALIBRATE / POLAR for our needs;
            # static page count is now > 10 so the count==10 auto-hide check
            # in init_widgets won't fire. Force-hide here.
            'btn_user',
            # PROGRAM panel — OPT STOP (M1 pause toggle), OPT BLOCK (skip
            # /-prefixed lines), and STEP (advance one G-code block at a
            # time) are mill / debugging features. Slicer-output G-code
            # never emits M1 or '/' lines, and single-stepping through
            # tens of thousands of print moves has no practical use —
            # all three are dead weight on this machine. Handler refs
            # (e.g. self.w.action_step.setEnabled in btn_pause_spindle_
            # clicked) stay valid because the widget still exists.
            'action_opt_stp', 'action_opt_blk', 'action_step',
            # PROGRAM panel — PAUSE SPINDLE button is for mill workflows
            # (pauses spindle + retracts on program-pause). No spindle on
            # this machine. Handler refs stay valid (widget exists hidden).
            'btn_pause_spindle', 'widget_pause_spindle',
            # PROGRAM panel — SPINDLE LIFT (Z-lift on pause via external
            # offsets) and Z AXIS COMP (probe-mesh-based Z compensation
            # for warped material) are mill / plasma features. No spindle,
            # no probe mesh on this machine.
            'label_46', 'spindle_eoffset_value',
            'label_25', 'z_comp_eoffset_value',
            # INPUTS panel (right column) — PROBE LED (no probe), AT SPEED
            # LED (no spindle), EOFFSET LTD (no external offsets) all dead
            # on this machine. Hide each label + LED pair.
            'label_13', 'hal_led_probe',
            'label_22', 'hal_led_atspeed',
            'label_43', 'stateled',
            # PRINT HEAD panel — no spindle, so M3/M4/M5 buttons, motor power
            # bar, and Modbus error/fault displays are dead UI. Gauge + PROGRESS
            # bar are kept (gauge repurposed for TCP velocity).
            'widget_spindle_controls',  # M3 reverse / M5 stop / M3 forward
            'spindle_power',            # POWER %p% bar
            'widget_spindle_error', 'widget_spindle_fault',
            # SPEEDS panel — SURFACE CUT SPEED (π × tool_dia × spindle_RPM)
            # is mill-specific cutting metric. No spindle, no tool diameter
            # on this machine. Other 3 rows (MAX VELOCITY / MAX RAPID /
            # CURRENT FEEDRATE) stay.
            'label_40', 'lbl_tool_scs',
            # DRO per-axis ZERO buttons — duplicate the new CTR XY (X+Y) and
            # Z=0 (with jog lock) buttons next to the visualizer. Single-axis
            # zero is still reachable via REF X/Y/Z popup → Zero menu entry.
            'action_zero_x', 'action_zero_y', 'action_zero_z',
            # STATUS panel (renamed from PRINT HEAD) — hide the round gauge
            # since the same TCP-velocity number is shown in SPEEDS panel
            # ("CURRENT FEEDRATE" row). PROGRESS bar stays visible. The
            # moved groupBox_status (MACHINE / RUN TIME) sits below.
            'gauge_spindle',
            # DRO mode toggles — operator wants AXIS-style simple jog DRO
            # without WCS/ABS/DTG mode confusion. WCS view (default) is
            # always shown; the others are hidden.
            'systemtoolbutton',          # WCS popup button
            'actionbutton_abs',          # ABS button
            'actionbutton_dtg',          # DTG button
            # Top tab row — hide SETUP / OFFSETS / TOOL / UTILS (rare for
            # daily polar-printing workflow; CALIBRATE + STATUS cover what
            # operator needs). Pages still exist in stack so handler logic
            # that references them keeps working.
            'btn_setup', 'btn_offsets', 'btn_tool', 'btn_utils',
        ]
        for _name in _hide:
            try:
                getattr(self.w, _name).hide()
            except (AttributeError, RuntimeError):
                pass

        # Hard-detach widgets that some qtvcp signal (state-on, mode-change,
        # periodic refresh) might otherwise re-show after a plain .hide().
        # setParent(None) yanks them out of every layout entirely so they
        # have no place to render, and retainSizeWhenHidden=False ensures
        # no reserved slot remains. The Python widget objects stay alive
        # so any setChecked()/setText() callbacks on them still no-op
        # safely instead of raising.
        #   btn_status    — top STATUS tab button (always-hidden top tab)
        #   action_zero_z — qtvcp per-axis Z zero button (DRO row)
        # btn_zero_z (Z=0 in widget_view_buttons next to GCodeGraphics)
        # has been deleted from qtdragon_hd.ui entirely. The Python
        # _on_zero_z connect + jog-filter installs in the ZERO Z block
        # above already AttributeError-out cleanly when self.w.btn_zero_z
        # is missing, so no additional cleanup is needed.
        _detach = ['btn_status', 'action_zero_z']
        for _name in _detach:
            w = getattr(self.w, _name, None)
            if w is None:
                continue
            try:
                w.hide()
                sp = w.sizePolicy()
                sp.setRetainSizeWhenHidden(False)
                w.setSizePolicy(sp)
                w.setParent(None)
            except (AttributeError, RuntimeError):
                pass

    #############################
    # SPECIAL FUNCTIONS SECTION #
    #############################
    def init_pins(self):
        # CYLINDRICAL ROBOT — PRINT HEAD gauge feedrate source.
        # Subscribe to STATUS 'current-feed-rate' which fires reliably whenever
        # LinuxCNC's reported feed rate changes (programmed F-word, override,
        # accel/decel ramps). Same source the SPEEDS panel's CURRENT FEEDRATE
        # widget uses, so the gauge needle and the SPEEDS number always match.
        # Replaces the older motion.current-vel HAL-pin approach which was
        # unreliable in sim because value_changed signals weren't firing.
        STATUS.connect('current-feed-rate', self.tcp_velocity_changed)

        # spindle control pins
        pin = QHAL.newpin("spindle-amps", QHAL.HAL_FLOAT, QHAL.HAL_IN)
        pin.value_changed.connect(self.spindle_pwr_changed)

        pin = QHAL.newpin("spindle-volts", QHAL.HAL_FLOAT, QHAL.HAL_IN)
        pin.value_changed.connect(self.spindle_pwr_changed)

        pin = QHAL.newpin("spindle-fault-u32", QHAL.HAL_U32, QHAL.HAL_IN)
        pin.value_changed.connect(self.spindle_fault_changed)
        pin = QHAL.newpin("spindle-fault", QHAL.HAL_S32, QHAL.HAL_IN)
        pin.value_changed.connect(self.spindle_fault_changed)

        pin = QHAL.newpin("spindle-modbus-errors-u32", QHAL.HAL_U32, QHAL.HAL_IN)
        pin.value_changed.connect(self.mb_errors_changed)
        pin = QHAL.newpin("spindle-modbus-errors", QHAL.HAL_S32, QHAL.HAL_IN)
        pin.value_changed.connect(self.mb_errors_changed)

        QHAL.newpin("spindle-inhibit", QHAL.HAL_BIT, QHAL.HAL_OUT)
        pin = QHAL.newpin("spindle-modbus-connection", QHAL.HAL_BIT, QHAL.HAL_IN)
        pin.value_changed.connect(self.mb_connection_changed)

        # external offset control pins
        QHAL.newpin("eoffset-enable", QHAL.HAL_BIT, QHAL.HAL_OUT)
        QHAL.newpin("eoffset-clear", QHAL.HAL_BIT, QHAL.HAL_OUT)
        self.h['eoffset-clear'] = True
        QHAL.newpin("eoffset-spindle-count", QHAL.HAL_S32, QHAL.HAL_OUT)
        QHAL.newpin("eoffset-count", QHAL.HAL_S32, QHAL.HAL_OUT)

        # total external offsets
        pin = QHAL.newpin("eoffset-value", QHAL.HAL_FLOAT, QHAL.HAL_IN)

        pin = QHAL.newpin("eoffset-zlevel-count", QHAL.HAL_S32, QHAL.HAL_IN)
        pin.value_changed.connect(self.comp_count_changed)
        QHAL.newpin("comp-on", Qhal.HAL_BIT, Qhal.HAL_OUT)
        QHAL.newpin("spindle-lift-on", Qhal.HAL_BIT, Qhal.HAL_OUT)

    def init_preferences(self):
        if not self.w.PREFS_:
            self.add_status("CRITICAL - no preference file found, enable preferences in screenoptions widget")
            return
        self.last_loaded_program = self.w.PREFS_.getpref('last_loaded_file', None, str,'BOOK_KEEPING')
        self.reload_tool = self.w.PREFS_.getpref('Tool to load', 0, int,'CUSTOM_FORM_ENTRIES')
        self.w.lineEdit_laser_x.setText(str(self.w.PREFS_.getpref('Laser X', 100, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_laser_y.setText(str(self.w.PREFS_.getpref('Laser Y', -20, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_sensor_x.setText(str(self.w.PREFS_.getpref('Sensor X', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_sensor_y.setText(str(self.w.PREFS_.getpref('Sensor Y', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_camera_x.setText(str(self.w.PREFS_.getpref('Camera X', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_camera_y.setText(str(self.w.PREFS_.getpref('Camera Y', 10, float, 'CUSTOM_FORM_ENTRIES')))
        if hasattr(self.w, 'lineEdit_work_height'):
            self.w.lineEdit_work_height.setText(str(self.w.PREFS_.getpref('Work Height', 20, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_touch_height.setText(str(self.w.PREFS_.getpref('Touch Height', 40, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_sensor_height.setText(str(self.w.PREFS_.getpref('Sensor Height', 40, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_search_vel.setText(str(self.w.PREFS_.getpref('Search Velocity', 40, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_probe_vel.setText(str(self.w.PREFS_.getpref('Probe Velocity', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_max_probe.setText(str(self.w.PREFS_.getpref('Max Probe', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_retract_distance.setText(str(self.w.PREFS_.getpref('Retract Distance', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_z_safe_travel.setText(str(self.w.PREFS_.getpref('Z Safe Travel', 10, float, 'CUSTOM_FORM_ENTRIES')))
        self.w.lineEdit_eoffset_count.setText(str(self.w.PREFS_.getpref('Eoffset count', 0, int, 'CUSTOM_FORM_ENTRIES')))
        self.w.chk_eoffsets.setChecked(self.w.PREFS_.getpref('External offsets', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_reload_program.setChecked(self.w.PREFS_.getpref('Reload program', False, bool,'CUSTOM_FORM_ENTRIES'))
        self.w.chk_reload_tool.setChecked(self.w.PREFS_.getpref('Reload tool', False, bool,'CUSTOM_FORM_ENTRIES'))
        self.w.chk_use_keyboard.setChecked(self.w.PREFS_.getpref('Use keyboard', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_use_tool_sensor.setChecked(self.w.PREFS_.getpref('Use tool sensor', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_use_touchplate.setChecked(self.w.PREFS_.getpref('Use tool touchplate', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_run_from_line.setChecked(self.w.PREFS_.getpref('Run from line', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_use_virtual.setChecked(self.w.PREFS_.getpref('Use virtual keyboard', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_use_camera.setChecked(self.w.PREFS_.getpref('Use camera', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_alpha_mode.setChecked(self.w.PREFS_.getpref('Use alpha display mode', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.w.chk_inhibit_selection.setChecked(self.w.PREFS_.getpref('Inhibit display mouse selection', False, bool, 'CUSTOM_FORM_ENTRIES'))
        self.cam_xscale_changed(self.w.PREFS_.getpref('Camview xscale', 100, int, 'CUSTOM_FORM_ENTRIES'))
        self.cam_yscale_changed(self.w.PREFS_.getpref('Camview yscale', 100, int, 'CUSTOM_FORM_ENTRIES'))
        self.w.camview._camNum = self.w.PREFS_.getpref('Camview cam number', 0, int, 'CUSTOM_FORM_ENTRIES')

    def closing_cleanup__(self):
        if not self.w.PREFS_: return
        # Persist the last-used aux motor speed % (restored in initialized__).
        # Prefer the editable field's value so a decimal % is preserved; fall
        # back to the (integer) slider if the field isn't present.
        _fields = getattr(self, '_aux_value_fields', {})
        for _ch in ('ext', 'pump', 'fluid'):
            _fld = _fields.get(_ch)
            if _fld is not None:
                try:
                    _val = float(_fld.text().replace('%', '').strip())
                except ValueError:
                    _val = 0.0
                self.w.PREFS_.putpref('Aux {} speed'.format(_ch),
                                      max(0.0, min(100.0, _val)), float,
                                      'CUSTOM_FORM_ENTRIES')
                continue
            _sld = getattr(self.w, 'sld_aux_{}_speed'.format(_ch), None)
            if _sld is not None:
                self.w.PREFS_.putpref('Aux {} speed'.format(_ch),
                                      _sld.value(), float,
                                      'CUSTOM_FORM_ENTRIES')
        if self.last_loaded_program is not None:
            self.w.PREFS_.putpref('last_loaded_directory', os.path.dirname(self.last_loaded_program), str, 'BOOK_KEEPING')
            self.w.PREFS_.putpref('last_loaded_file', self.last_loaded_program, str, 'BOOK_KEEPING')
        self.w.PREFS_.putpref('Tool to load', STATUS.get_current_tool(), int, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Laser X', self.w.lineEdit_laser_x.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Laser Y', self.w.lineEdit_laser_y.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Sensor X', self.w.lineEdit_sensor_x.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Sensor Y', self.w.lineEdit_sensor_y.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Camera X', self.w.lineEdit_camera_x.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Camera Y', self.w.lineEdit_camera_y.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        if hasattr(self.w, 'lineEdit_work_height'):
            self.w.PREFS_.putpref('Work Height', self.w.lineEdit_work_height.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Touch Height', self.w.lineEdit_touch_height.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Sensor Height', self.w.lineEdit_sensor_height.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Search Velocity', self.w.lineEdit_search_vel.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Probe Velocity', self.w.lineEdit_probe_vel.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Max Probe', self.w.lineEdit_max_probe.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Retract Distance', self.w.lineEdit_retract_distance.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Z Safe Travel', self.w.lineEdit_z_safe_travel.text().encode('utf-8'), float, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Eoffset count', self.w.lineEdit_eoffset_count.text().encode('utf-8'), int, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('External offsets', self.w.chk_eoffsets.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Reload program', self.w.chk_reload_program.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Reload tool', self.w.chk_reload_tool.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Use keyboard', self.w.chk_use_keyboard.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Use tool sensor', self.w.chk_use_tool_sensor.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Use tool touchplate', self.w.chk_use_touchplate.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Run from line', self.w.chk_run_from_line.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Use virtual keyboard', self.w.chk_use_virtual.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Use camera', self.w.chk_use_camera.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Use alpha display mode', self.w.chk_alpha_mode.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Inhibit display mouse selection', self.w.chk_inhibit_selection.isChecked(), bool, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Camview xscale', self.cam_xscale_percent(), int, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Camview yscale', self.cam_yscale_percent(), int, 'CUSTOM_FORM_ENTRIES')
        self.w.PREFS_.putpref('Camview cam number', self.w.camview._camNum, int, 'CUSTOM_FORM_ENTRIES')

    def init_widgets(self):
        self.w.stackedWidget_mainTab.setCurrentIndex(0)
        self.w.chk_override_limits.setChecked(False)
        self.w.chk_override_limits.setEnabled(False)
        self.w.lbl_maxv_percent.setText("100 %")
        self.w.lbl_max_rapid.setText(str(self.max_linear_velocity))
        self.w.lbl_home_x.setText(INFO.get_error_safe_setting('JOINT_0', 'HOME',"50"))
        self.w.lbl_home_y.setText(INFO.get_error_safe_setting('JOINT_1', 'HOME',"50"))
        self.w.cmb_gcode_history.addItem("No File Loaded")
        self.w.cmb_gcode_history.wheelEvent = lambda event: None
        self.w.jogincrements_linear.wheelEvent = lambda event: None
        self.w.jogincrements_angular.wheelEvent = lambda event: None
        self.w.gcode_editor.hide()
        self.w.filemanager.table.setShowGrid(False)
        self.w.filemanager_usb.table.setShowGrid(False)
        self.w.tooloffsetview.setShowGrid(False)
        self.w.offset_table.setShowGrid(False)
        self.w.divider_line.hide()

        #set up gcode list
        self.gcodes.setup_list()

        # check for default setup html file
        try:
            # web view widget for SETUP page
            if self.w.web_view:
                self.toolBar = QtWidgets.QToolBar(self.w)
                self.w.tabWidget_setup.setCornerWidget(self.toolBar)

                self.zoomBtn = QtWidgets.QPushButton(self.w)
                self.zoomBtn.setEnabled(True)
                self.zoomBtn.setMinimumSize(64, 40)
                self.zoomBtn.setIconSize(QtCore.QSize(38, 38))
                self.zoomBtn.setIcon(QtGui.QIcon(QtGui.QPixmap(':/buttons/images/zoom.png')))
                self.zoomBtn.clicked.connect(self.zoomWeb)
                self.toolBar.addWidget(self.zoomBtn)
    
                self.homeBtn = QtWidgets.QPushButton(self.w)
                self.homeBtn.setEnabled(True)
                self.homeBtn.setMinimumSize(64, 40)
                self.homeBtn.setIconSize(QtCore.QSize(38, 38))
                self.homeBtn.setIcon(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/up-32.png'))
                self.homeBtn.clicked.connect(self.homeWeb)
                self.toolBar.addWidget(self.homeBtn)

                self.backBtn = QtWidgets.QPushButton(self.w)
                self.backBtn.setEnabled(True)
                self.backBtn.setMinimumSize(64, 40)
                self.backBtn.setIconSize(QtCore.QSize(38, 38))
                self.backBtn.setIcon(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/left-32.png'))
                self.backBtn.clicked.connect(self.back)
                self.toolBar.addWidget(self.backBtn)

                self.forBtn = QtWidgets.QPushButton(self.w)
                self.forBtn.setEnabled(True)
                self.forBtn.setMinimumSize(64, 40)
                self.forBtn.setIconSize(QtCore.QSize(38, 38))
                self.forBtn.setIcon(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/right-32.png'))
                self.forBtn.clicked.connect(self.forward)
                self.toolBar.addWidget(self.forBtn)

                self.writeBtn = QtWidgets.QPushButton('SetUp\n Writer',self.w)
                self.writeBtn.setMinimumSize(64, 40)
                self.writeBtn.setEnabled(True)
                self.writeBtn.clicked.connect(self.writer)
                self.toolBar.addWidget(self.writeBtn)

                self.w.layout_HTML.addWidget(self.w.web_view)
                if os.path.exists(self.default_setup):
                    self.w.web_view.load(QtCore.QUrl.fromLocalFile(self.default_setup))
                else:
                    self.w.web_view.setHtml(self.html)
                self.w.web_view.page().urlChanged.connect(self.onLoadFinished)
        except Exception as e:
            print("No default setup file found - {}".format(e))

        # PDF setup page
        self.PDFView = PDFViewer.PDFView()
        self.w.layout_PDF.addWidget(self.PDFView)
        self.PDFView.loadSample('setup_tab')

        # === CYLINDRICAL ROBOT — repurpose the gauge as TCP VELOCITY display.
        # The PRINT HEAD panel's round gauge now shows the tool-center-point
        # speed (mm/min) instead of spindle RPM. Pulled from motion.current-vel
        # via qtvcp.tcp-velocity HAL pin (created in init_pins, netted in
        # postgui_qtdragon.hal). motion.current-vel reports mm/s — handler
        # multiplies by 60 in the value-changed callback.
        # Gauge scaled to INI [TRAJ] MAX_LINEAR_VELOCITY * 60 (12000 mm/min on
        # this machine). Dial shows 0..12 (×1000 mm/min) so the labels stay
        # readable at small font.
        try:
            _max_vel_mmpm = int(round(INFO.MAX_TRAJ_VELOCITY * 60))
        except Exception:
            _max_vel_mmpm = 12000
        self.w.gauge_spindle.set_max_value(_max_vel_mmpm)
        self.w.gauge_spindle.set_max_reading(max(1, _max_vel_mmpm // 1000))
        self.w.gauge_spindle.set_threshold(0)
        self.w.gauge_spindle.set_label("mm/min\nx1000")

        # hide user tab button if no user tabs
        if self.w.stackedWidget_mainTab.count() == 10:
            self.w.btn_user.hide()

    def init_probe(self):
        probe = INFO.get_error_safe_setting('PROBE', 'USE_PROBE', 'none').lower()
        if probe == 'versaprobe':
            LOG.info("Using Versa Probe")
            from qtvcp.widgets.versa_probe import VersaProbe
            self.probe = VersaProbe()
            self.probe.setObjectName('versaprobe')
        elif probe == 'basicprobe':
            LOG.info("Using Basic Probe")
            from qtvcp.widgets.basic_probe import BasicProbe
            self.probe = BasicProbe()
            self.probe.setObjectName('basicprobe')
        else:
            LOG.info("No valid probe widget specified")
            self.w.btn_probe.hide()
            return
        self.w.probe_layout.addWidget(self.probe)
        self.probe.hal_init()

    def init_utils(self):
        from qtvcp.lib.gcode_utility.facing import Facing
        self.facing = Facing()
        self.w.layout_facing.addWidget(self.facing)

        from qtvcp.lib.gcode_utility.hole_circle import Hole_Circle
        self.hole_circle = Hole_Circle()
        self.w.layout_hole_circle.addWidget(self.hole_circle)

        try:
            from qtvcp.lib.gcode_utility.hole_enlarge import Hole_Enlarge
            self.hole_enlarge = Hole_Enlarge()
            ACTION.ADD_WIDGET_TO_TAB(self.w.tabWidget_utilities,self.hole_enlarge, 'Hole Enlarge')
        except Exception as e:
            LOG.info("Utility hole enlarge unavailable: {}".format(e))

        LOG.info("Using NGCGUI utility")
        self.ngcgui = NgcGui()
        self.w.layout_ngcgui.addWidget(self.ngcgui)
        self.ngcgui.warp_info_frame(self.w.ngcGuiLeftLayout)

        self.auto_measure = Auto_Measure(self.w)
        self.w.layout_workpiece.addWidget(self.auto_measure)
        self.auto_measure._hal_init()

    def processed_focus_event__(self, receiver, event):
        if not self.w.chk_use_virtual.isChecked() or STATUS.is_auto_mode(): return
        if isinstance(receiver, QtWidgets.QLineEdit):
            if not receiver.isReadOnly():
                self.w.stackedWidget_dro.setCurrentIndex(1)
        elif isinstance(receiver, QtWidgets.QTableView):
            self.w.stackedWidget_dro.setCurrentIndex(1)
        elif isinstance(receiver, QtWidgets.QCommonStyle):
            return
    
    def processed_key_event__(self,receiver,event,is_pressed,key,code,shift,cntrl):
        # when typing in MDI, we don't want keybinding to call functions
        # so we catch and process the events directly.
        # We do want ESC, F1 and F2 to call keybinding functions though
        if code not in(QtCore.Qt.Key_Escape,QtCore.Qt.Key_F1 ,QtCore.Qt.Key_F2):
#                    QtCore.Qt.Key_F3,QtCore.Qt.Key_F4,QtCore.Qt.Key_F5):

            # search for the top widget of whatever widget received the event
            # then check if it's one we want the keypress events to go to
            flag = False
            receiver2 = receiver
            while receiver2 is not None and not flag:
                if isinstance(receiver2, QtWidgets.QDialog):
                    flag = True
                    break
                if isinstance(receiver2, QtWidgets.QLineEdit):
                    flag = True
                    break
                if isinstance(receiver2, MDI_WIDGET):
                    flag = True
                    break
                if isinstance(receiver2, GCODE):
                    flag = True
                    break
                if isinstance(receiver2, TOOL_TABLE):
                    flag = True
                    break
                if isinstance(receiver2, OFFSET_VIEW):
                    flag = True
                    break
                receiver2 = receiver2.parent()

            if flag:
                if isinstance(receiver2, GCODE):
                    # if in manual or in readonly mode do our keybindings - otherwise
                    # send events to gcode widget
                    if STATUS.is_man_mode() == False or not receiver2.isReadOnly():
                        if is_pressed:
                            receiver.keyPressEvent(event)
                            event.accept()
                        return True
                if is_pressed:
                    receiver.keyPressEvent(event)
                    event.accept()
                    return True
                else:
                    event.accept()
                    return True

        if event.isAutoRepeat():return True

        # ok if we got here then try keybindings function calls
        # KEYBINDING will call functions from handler file as
        # registered by KEYBIND.add_call(KEY,FUNCTION) above
        return KEYBIND.manage_function_calls(self,event,is_pressed,key,shift,cntrl)

    #########################
    # CALLBACKS FROM STATUS #
    #########################

    def update_spindle(self,w,data):
        # CYLINDRICAL ROBOT — gauge repurposed to TCP velocity (see
        # tcp_velocity_changed). Spindle speed updates ignored on this
        # machine. Kept as no-op so STATUS connections in __init__ don't
        # explode.
        pass

    def update_spindle_requested(self,w,data):
        pass

    def tcp_velocity_changed(self, w, data):
        # STATUS 'current-feed-rate' callback signature is (widget, data).
        # data is in user units / minute (mm/min on this machine) — same
        # source the SPEEDS panel's CURRENT FEEDRATE widget reads.
        try:
            self.w.gauge_spindle.update_value(abs(float(data)))
        except (AttributeError, ValueError, TypeError):
            pass

    def spindle_pwr_changed(self, data):
        # this calculation assumes the voltage is line to neutral
        # that the current reported by the VFD is total current for all 3 phases
        # and that the synchronous motor spindle has a power factor of 0.9
        try:
            power = float(self.h['spindle-volts'] * self.h['spindle-amps'] * 0.9) # Watts = V x I x PF
            pc_power = (power / float(self.max_spindle_power)) * 100
            if pc_power > 100:
                pc_power = 100
            self.w.spindle_power.setValue(int(pc_power))
        except Exception as e:
            #print(e)
            self.w.spindle_power.setValue(0)

    def spindle_fault_changed(self, data):
        fault = hex(data)
        self.w.lbl_spindle_fault.setText(fault)

    def mb_errors_changed(self, data):
        self.w.lbl_mb_errors.setText(str(data))

    def mb_connection_changed(self, data):
        if data:
            self.w.lbl_mb_errors.setStyleSheet('')
        else:
            self.w.lbl_mb_errors.setStyleSheet('''background-color:rgb(202, 0, 0);''')

    def comp_count_changed(self, data):
        self.w.z_comp_eoffset_value.setText(format(data*.001, '.3f'))

    def dialog_return(self, w, message):
        rtn = message.get('RETURN')
        name = message.get('NAME')
        plate_code = bool(message.get('ID') == '_touchplate_')
        sensor_code = bool(message.get('ID') == '_toolsensor_')
        wait_code = bool(message.get('ID') == '_wait_resume_')
        unhome_code = bool(message.get('ID') == '_unhome_')
        overwrite = bool(message.get('ID') == '_overwrite_')
        if plate_code and name == 'MESSAGE' and rtn is True:
            self.touchoff('touchplate')
        elif sensor_code and name == 'MESSAGE' and rtn is True:
            self.touchoff('sensor')
        elif wait_code and name == 'MESSAGE':
            self.h['spindle-lift-on'] = False
            self.h['eoffset-spindle-count'] = 0
            self.w.spindle_eoffset_value.setText('0')
            self.add_status('Spindle lowered')
        elif unhome_code and name == 'MESSAGE' and rtn is True:
            ACTION.SET_MACHINE_UNHOMED(-1)
        elif overwrite and name == 'MESSAGE':
            if rtn is True:
                self.do_file_copy()
            else:
                self.add_status("File not copied", CRITICAL)

    def user_system_changed(self, data):
        sys = self.system_list[int(data) - 1]
        self.w.offset_table.selectRow(int(data) + 3)
        self.w.actionbutton_rel.setText(sys)

    def metric_mode_changed(self, mode):
        unit = "MM" if mode else "IN"
        # lbl_jog_linear has been repurposed as the J2 slider title — don't
        # overwrite it with the unit string.
        if INFO.MACHINE_IS_METRIC == mode:
            self.factor = 1.0
            rapid = (float(self.w.slider_rapid_ovr.value()) / 100) * self.max_linear_velocity
        elif mode:
            self.factor = 25.4
            rapid = (float(self.w.slider_rapid_ovr.value()) / 100) * self.max_linear_velocity * 25.4
        else:
            self.factor = 1/25.4
            rapid = (float(self.w.slider_rapid_ovr.value()) / 100) * self.max_linear_velocity / 25.4
        self.w.lbl_max_rapid.setText("{:4.0f}".format(rapid))

    # === CYLINDRICAL ROBOT — Align angular column items under the slider ===
    # In the .ui the J2 column (widget_jog_angular / verticalLayout_11) has
    # AlignHCenter on the value box ABOVE the slider, but no alignment on
    # the slider's layout item, so the slider sits flush-left of the
    # column while the value box centers — they look misaligned. Force the
    # slider, value label, and slow/fast button items to AlignHCenter to
    # match (and mirror the linear column's behaviour).
    def _align_j2_column(self):
        try:
            container = self.w.widget_jog_angular
        except AttributeError:
            return
        lay = container.layout()
        if lay is None:
            return
        for child_name in ('status_jog_angular', 'slider_jog_angular',
                           'btn_jog_a_slow', 'lbl_jog_angular'):
            child = getattr(self.w, child_name, None)
            if child is None:
                continue
            idx = lay.indexOf(child)
            if idx >= 0:
                lay.setAlignment(child, QtCore.Qt.AlignHCenter)

    # === CYLINDRICAL ROBOT — Slider labelling (Z + X) ===
    # Rename the two original .ui slider columns to operator-friendly axis
    # names. The left (linear) column now reads "Z": it still sets the shared
    # LINEAR jog rate, but a dedicated independent "Y" slider (added by
    # _add_y_jog_slider) is inserted between it and the "X" column so Y can be
    # jogged at its own rate. See _jog_axis_explicit / kb_jog.
    #   LEFT  column (widget_jog_linear, slider-jogspeed-linear)
    #         drives the shared LINEAR jog rate -> used for Z (and default).
    #         Label: "Z".
    #   RIGHT column (widget_jog_angular, slider-jogspeed-angular)
    #         drives the ANGULAR jog rate -> affects J0 (X).
    #         Label: "X".
    # Only the text changes here; the widgets, HAL pins, and jog bindings are
    # untouched. Bold; re-asserted shortly after start to outlast deferred
    # qtvcp signals (state-on, metric-mode-changed) that may re-write labels.
    def _apply_j1_j2_jog_labels(self):
        def _bold(lbl):
            f = lbl.font()
            f.setBold(True)
            lbl.setFont(f)
        for nm, txt in (('lbl_jog_linear',  'Z'),
                        ('lbl_jog_angular', 'X')):
            lbl = getattr(self.w, nm, None)
            if lbl is None:
                continue
            lbl.setText(txt)
            _bold(lbl)
            QtCore.QTimer.singleShot(
                500, lambda _lbl=lbl, _txt=txt: (_lbl.setText(_txt), _bold(_lbl)))

    # === CYLINDRICAL ROBOT — Jog slider ranges + J0 default ===
    # qtvcp's StatusSlider with jograte_rate / jograte_angular_rate auto-
    # scales the slider max from [TRAJ] MAX_LINEAR_VELOCITY / MAX_ANGULAR_
    # VELOCITY (×60 → per-min). The resulting 12000 mm/min and 1080 deg/min
    # ranges are too wide for safe jogging on this machine — cap them at
    # 10000 mm/min (linear, Y/Z) and 720 deg/min (angular, X). Also set the
    # initial X (J0) jog rate to 150 deg/min so the operator starts with a
    # gentle angular jog.
    # Re-apply on a deferred QTimer so qtvcp's own startup ordering can't
    # silently overwrite the max after we set it.
    def _configure_jog_sliders(self):
        try:
            lin = self.w.slider_jog_linear
            ang = self.w.slider_jog_angular
        except AttributeError:
            return
        def _apply():
            lin.setMaximum(10000)
            ang.setMaximum(720)
        _apply()
        ang.setValue(150)     # X (angular) default jog rate
        lin.setValue(2000)    # Z (linear) default jog rate
        QtCore.QTimer.singleShot(500, _apply)

    # === CYLINDRICAL ROBOT — Dedicated independent "Y" jog-speed slider ===
    # LinuxCNC shares ONE linear jog rate across all linear axes, so the
    # original linear slider (now "Z") governs both Y and Z. To give Y its
    # own speed, we add a third slider column between "Z" and "X" that stores
    # a Y-only rate and apply it explicitly whenever Y is jogged — see
    # _jog_axis_explicit (on-screen X/Y/Z buttons) and kb_jog (keyboard).
    # The column mirrors the linear column exactly: bold title, sunken value
    # pill, vertical slider, FAST/SLOW range toggle. The slider is a plain
    # QSlider (NOT jograte-bound) so it never fights the global linear rate,
    # and jogging uses an explicit ACTION.JOG rate (no SET_JOG_RATE), so the
    # "Z" slider never flickers while Y jogs.
    # Return the layout that DIRECTLY contains `widget`. parentWidget().layout()
    # only gives the widget's TOP layout, which may hold `widget` indirectly
    # via a nested sub-layout (as the jog columns sit in horizontalLayout_25
    # inside frame_jogging's verticalLayout_8) — so search the sub-layouts too.
    def _managing_layout(self, widget):
        pw = widget.parentWidget()
        top = pw.layout() if pw is not None else None
        if top is None:
            return None
        stack = [top]
        while stack:
            lay = stack.pop()
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if item is None:
                    continue
                if item.widget() is widget:
                    return lay
                sub = item.layout()
                if sub is not None:
                    stack.append(sub)
        return None

    def _add_y_jog_slider(self):
        lin = getattr(self.w, 'widget_jog_linear', None)
        if lin is None:
            return
        parent = self._managing_layout(lin)
        if parent is None:
            return
        idx = parent.indexOf(lin)
        if idx < 0:
            return

        col = QtWidgets.QWidget()
        col.setObjectName('widget_jog_y')
        vbox = QtWidgets.QVBoxLayout(col)
        vbox.setSpacing(8)
        vbox.setContentsMargins(0, 0, 0, 5)

        # Bold "Y" title — mirror lbl_jog_linear EXACTLY, incl. its fixed 30px
        # height + (Preferred, Fixed) policy. A default QLabel is vertically
        # growable, which would let the title steal column space from the
        # slider and push the value/slider/FAST button down — misaligning the
        # FAST buttons and shrinking the slider vs the X/Z columns.
        title = QtWidgets.QLabel('Y')
        title.setMinimumSize(58, 30); title.setMaximumSize(58, 30)
        title.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                            QtWidgets.QSizePolicy.Fixed)
        _tf = title.font(); _tf.setPointSize(10); _tf.setBold(True)
        title.setFont(_tf)
        title.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(title, 0, QtCore.Qt.AlignHCenter)

        # Value pill — a StatusLabel with no binding keeps a manual setText
        # yet still gets the themed pill styling (black/green|white, sunken).
        val = StatusLabel()
        val.setObjectName('status_jog_y')
        val.setMinimumSize(58, 30); val.setMaximumSize(58, 30)
        val.setFrameShape(QtWidgets.QFrame.WinPanel)
        val.setFrameShadow(QtWidgets.QFrame.Sunken)
        val.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(val, 0, QtCore.Qt.AlignHCenter)

        # Slider — mirror slider_jog_linear geometry, but plain (independent).
        sld = QtWidgets.QSlider(QtCore.Qt.Vertical)
        sld.setObjectName('slider_jog_y')
        sld.setMinimumSize(58, 0); sld.setMaximumSize(58, 16777215)
        sld.setMinimum(0); sld.setMaximum(10000)
        sld.setSingleStep(1000); sld.setPageStep(1000)   # FAST step (SLOW=100)
        sld.setTickPosition(QtWidgets.QSlider.TicksBelow)
        sld.setTickInterval(200)
        sld.setToolTip('Adjust Y-axis jog rate (independent of Z)')
        # Match the existing sliders' size policy (Preferred/Preferred). A bare
        # vertical QSlider defaults to (Fixed, Expanding), which stretches it
        # to fill the column and makes it taller than the X/Z sliders.
        _ref = getattr(self.w, 'slider_jog_linear', None)
        if _ref is not None:
            sld.setSizePolicy(_ref.sizePolicy())
        else:
            sld.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                              QtWidgets.QSizePolicy.Preferred)
        vbox.addWidget(sld, 0, QtCore.Qt.AlignHCenter)

        # FAST/SLOW toggle — uses the exact same mechanism as the Z/X buttons
        # (slow_button_clicked -> _apply_slow_fast): SLOW divides the Y speed +
        # range by 10 (e.g. 5000 -> 500) and sets the step to slow_step; FAST
        # multiplies back and uses fast_step. Y steps are 1000 (fast) / 100
        # (slow), declared via button properties.
        rng = QtWidgets.QPushButton('FAST')
        rng.setObjectName('btn_jog_y_slow')
        rng.setCheckable(True)
        rng.setMinimumSize(58, 40); rng.setMaximumSize(58, 40)
        rng.setToolTip('Toggle Y jog speed range')
        rng.setProperty('slider', 'slider_jog_y')
        rng.setProperty('fast_step', 1000)
        rng.setProperty('slow_step', 100)
        rng.clicked.connect(
            lambda checked, _b=rng: self._apply_slow_fast(_b, checked))
        vbox.addWidget(rng, 0, QtCore.Qt.AlignHCenter)

        # No bottom padding needed: the jog-increment combos have been moved
        # out of the Z/X columns into their own full-width row below the
        # sliders (see _move_increments_under_sliders), so all three columns
        # are now [title, value, slider, FAST] and their FAST buttons line up
        # naturally.

        # Value pill tracks the slider.
        sld.valueChanged.connect(
            lambda v, _v=val: _v.setText('{:.1f}'.format(float(v))))

        # Default Y jog rate — fixed each boot, matching the X (150) and
        # Z (2000) defaults set in _configure_jog_sliders.
        sld.setValue(5000)
        val.setText('{:.1f}'.format(float(sld.value())))

        # Insert between the linear ("Z") and angular ("X") columns.
        parent.insertWidget(idx + 1, col)

        # Pin each slider column to the slider width (the combos below Z/X
        # would otherwise widen them and spread the sliders far apart).
        for _cw in (lin, col, getattr(self.w, 'widget_jog_angular', None)):
            if _cw is not None:
                _cw.setFixedWidth(60)
        # Give the sliders a little breathing room and spread the surrounding
        # empty space evenly: a small fixed gap BETWEEN the sliders, plus equal
        # stretches on the LEFT (before Z) and RIGHT (after X) so the group is
        # centred in the space beside the jog-button pad. The pad stays at
        # index 0 (untouched), so nothing above it shifts.
        parent.setSpacing(0)
        _ang = getattr(self.w, 'widget_jog_angular', None)
        _gap = lambda: QtWidgets.QSpacerItem(
            14, 0, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        if _ang is not None:
            parent.insertStretch(parent.indexOf(_ang) + 1, 1)      # right stretch
            parent.insertSpacerItem(parent.indexOf(_ang), _gap())  # Y|X gap
        parent.insertSpacerItem(parent.indexOf(col), _gap())       # Z|Y gap
        parent.insertStretch(parent.indexOf(lin), 1)               # left stretch

        self.w.widget_jog_y = col
        self.w.slider_jog_y = sld
        self.w.status_jog_y = val

        self._rewire_axis_jog_buttons()

    # Map an axis ('X'/'Y'/'Z') or joint index (0/1/2) to the slider that owns
    # that axis's independent jog rate:
    #   X -> slider_jog_angular (the "X"/J0 angular slider)
    #   Y -> slider_jog_y       (the dedicated independent Y slider)
    #   Z -> slider_jog_linear  (the "Z"/linear slider)
    def _jog_slider_for(self, key):
        name = {'X': 'slider_jog_angular', 'Y': 'slider_jog_y',
                'Z': 'slider_jog_linear',
                0: 'slider_jog_angular', 1: 'slider_jog_y',
                2: 'slider_jog_linear'}.get(key)
        return getattr(self.w, name, None) if name else None

    # Jog rate (units/sec) for an axis ('X'/'Y'/'Z') or joint index (0/1/2),
    # honoring the current jog mode. The on-screen "X" column is bound to the
    # ANGULAR jog rate because in JOINT mode it drives the rotary joint J0.
    # In CARTESIAN (world) mode, though, X is an ordinary LINEAR axis: feeding
    # it the angular rate produced a tiny degrees-scaled mm/min feed, so
    # cartesian X barely crept while Y/Z jogged normally — i.e. "X not moving".
    # In world mode we therefore jog cartesian X at the shared LINEAR jog rate
    # (like every other linear axis). Y keeps its own independent slider, Z the
    # linear slider, and JOINT-mode J0 still uses the angular slider.
    def _jog_rate_for(self, key):
        if STATUS.is_world_mode() and key in ('X', 0):
            return STATUS.get_jograte() / 60.0
        sld = self._jog_slider_for(key)
        if sld is not None:
            return float(sld.value()) / 60.0
        return STATUS.get_jograte() / 60.0

    # Re-route EVERY on-screen axis jog button (X/Y/Z +/-) through our
    # explicit-rate jogger so each axis uses ONLY its own slider's rate, in
    # both Cartesian and joint modes — no slider can affect another axis.
    # The ActionButtons' own pressed/released->jog_action connections are
    # dropped; their enable/disable STATUS connections (on other signals) stay
    # intact, and the Z-jog lock event filter is unaffected (it works at the
    # event level, before the pressed signal).
    def _rewire_axis_jog_buttons(self):
        specs = (('x_plus_jogbutton',  'X',  1), ('x_minus_jogbutton', 'X', -1),
                 ('y_plus_jogbutton',  'Y',  1), ('y_minus_jogbutton', 'Y', -1),
                 ('z_plus_jogbutton',  'Z',  1), ('z_minus_jogbutton', 'Z', -1))
        for name, axis, direction in specs:
            btn = getattr(self.w, name, None)
            if btn is None:
                continue
            for sig in (btn.pressed, btn.released):
                try:
                    sig.disconnect()
                except TypeError:
                    pass
            btn.pressed.connect(
                lambda a=axis, d=direction: self._jog_axis_explicit(a, d))
            btn.released.connect(
                lambda a=axis: self._jog_axis_explicit(a, 0))

    # Jog one axis at ITS OWN slider's rate. Mirrors ActionButton.jog_action()
    # + DO_JOG actuator/angular resolution (so Cartesian and joint modes both
    # behave correctly) but issues ACTION.JOG with an EXPLICIT per-axis rate
    # (like kb_jog). Because no SET_JOG_RATE is used, no slider affects any
    # other axis and none of the sliders flicker while another axis jogs.
    def _jog_axis_explicit(self, axis, direction):
        import linuxcnc
        ACTION.SET_MANUAL_MODE()
        if not STATUS.is_man_mode() or not STATUS.machine_is_on():
            if direction != 0:
                self.add_status('Machine must be ON and in Manual mode to jog',
                                WARNING)
            return
        # Actuator: axis letter in Cartesian/world mode, joint number in joint
        # mode (mirrors ActionButton.jog_action with joint_number == -1).
        if STATUS.is_world_mode():
            actuator = axis
        else:
            actuator = INFO.GET_JOG_FROM_NAME.get(
                axis, {'X': 0, 'Y': 1, 'Z': 2}.get(axis, 0))
        # Resolve jointnum + angular exactly like DO_JOG.
        if isinstance(actuator, int):
            try:
                angular = (STATUS.stat.joint[actuator]['jointType']
                           == linuxcnc.ANGULAR)
            except Exception:
                angular = False
            jointnum = actuator
        else:
            angular = actuator.upper() in ('A', 'B', 'C')
            jointnum = 'XYZABCUVW'.find(actuator)
        rate = self._jog_rate_for(axis)
        distance = (STATUS.get_jog_increment_angular() if angular
                    else STATUS.get_jog_increment())
        if direction == 0:
            # Increment jog is discrete — nothing to stop on release.
            if distance != 0:
                return
            ACTION.JOG(jointnum, 0, 0, 0)
            return
        ACTION.JOG(jointnum, direction, rate, distance)

    # === CYLINDRICAL ROBOT — Consistent gap between bottom-row sections ===
    # `widget_offsets_2` sits between AUX MOTORS and OVERRIDES in layout_lower
    # with an empty verticalLayout_35 — it adds asymmetric spacing because
    # the layout still reserves a slot for it. We pull it out of the layout
    # entirely so the visible sections (PROGRAM, AUX, OVERRIDES, JOGGING,
    # STATUS) sit with one uniform gap between each pair. Spacing is bumped
    # to 12 px and uniform margins applied.
    def _tighten_bottom_row_gaps(self):
        layout = getattr(self.w, 'layout_lower', None)
        if layout is None:
            return

        # Detach the empty offsets wrapper so it doesn't reserve a slot.
        offsets = getattr(self.w, 'widget_offsets_2', None)
        if offsets is not None and layout.indexOf(offsets) >= 0:
            layout.removeWidget(offsets)
            offsets.setParent(None)

        # Uniform spacing/margins. 12 px is a clean operator-visible gap.
        layout.setSpacing(12)
        layout.setContentsMargins(6, 4, 6, 4)

    # === CYLINDRICAL ROBOT — Blank HOME X/Y/Z + LIMIT rows in INPUTS panel ===
    # Operator wants the HOME X / HOME Y / HOME Z text gone, plus the
    # LIMIT row's label AND its LED hidden — but the slots must be PRESERVED
    # because new widgets will be placed there later. We clear text instead
    # of hiding labels (label remains visible & empty, slot keeps its size)
    # and use setRetainSizeWhenHidden on the LED so its column doesn't
    # collapse when hidden.
    def _hide_home_axis_labels(self):
        # HOME X/Y/Z text labels — clear text, keep widget visible so the
        # row height/space is preserved for future replacement content.
        for nm in ('label_10', 'label_11', 'label_12'):
            lbl = getattr(self.w, nm, None)
            if lbl is not None:
                lbl.setText('')

        # LIMIT text — same approach.
        lim_lbl = getattr(self.w, 'label_14', None)
        if lim_lbl is not None:
            lim_lbl.setText('')

        # LIMIT LED — hide but retain layout slot.
        lim_led = getattr(self.w, 'hal_led_limit', None)
        if lim_led is not None:
            sp = lim_led.sizePolicy()
            sp.setRetainSizeWhenHidden(True)
            lim_led.setSizePolicy(sp)
            lim_led.hide()

    # === CYLINDRICAL ROBOT — OVERRIDES-style quick buttons on aux rows ===
    # Each aux motor row (Extruder / Pump / Fluid Pump) gets a "50" button
    # immediately before its slider and a "100" button immediately after.
    # Buttons set the slider to that percentage. The LED indicator is hidden
    # and the % display is restyled to match the OVERRIDES status box
    # (60x30, WinPanel + sunken, centered) — see status_rapid_ovr for the
    # reference. Final row:
    #   [ON] [50] [-------- slider --------] [100] [ % display ]
    def _add_aux_quick_buttons(self):
        # Editable speed boxes, keyed by channel — populated below and wired
        # to the HAL speed pins in the aux block of initialized__().
        self._aux_value_fields = {}
        for ch in ('ext', 'pump', 'fluid'):
            try:
                slider = getattr(self.w, 'sld_aux_{}_speed'.format(ch))
            except AttributeError:
                continue
            layout = slider.parentWidget().layout()
            if layout is None:
                continue

            # 1. Hide the LED indicator beside the ON checkbox.
            led = getattr(self.w, 'led_aux_{}'.format(ch), None)
            if led is not None:
                led.hide()

            # 2. Build the 50/100 quick buttons.
            slider_idx = layout.indexOf(slider)
            if slider_idx < 0:
                continue
            btn50 = QtWidgets.QPushButton('50')
            btn100 = QtWidgets.QPushButton('100')
            # No per-widget stylesheet — let the application QSS rule for
            # QPushButton apply (identical to the OVERRIDES action buttons).
            for b in (btn50, btn100):
                b.setMinimumSize(42, 30)
                b.setMaximumSize(42, 30)
                sp = b.sizePolicy()
                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
                sp.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)
                b.setSizePolicy(sp)
            btn50.setObjectName('btn_aux_{}_50'.format(ch))
            btn100.setObjectName('btn_aux_{}_100'.format(ch))
            btn50.setToolTip('Set {} speed to 50%'.format(ch))
            btn100.setToolTip('Set {} speed to 100%'.format(ch))
            btn50.clicked.connect(lambda _=False, s=slider: s.setValue(50))
            btn100.clicked.connect(lambda _=False, s=slider: s.setValue(100))
            layout.insertWidget(slider_idx, btn50)
            layout.insertWidget(slider_idx + 2, btn100)

            # 3. Replace the read-only HALLabel % display with an EDITABLE
            # QLineEdit. It still shows the live speed (mirrors the slider),
            # but the operator can also click into it and type a decimal %
            # (finer than the integer slider) to set the speed directly.
            # A QLineEdit is used (not QDoubleSpinBox) because the app QSS
            # already styles QLineEdit in both the sim and production themes
            # (black pill, themed border/text) — so it matches automatically
            # with only a per-widget font override, exactly like the old
            # StatusLabel did. The slider<->field<->HAL-pin wiring lives in
            # the aux block of initialized__() (self._aux_value_fields).
            disp_old = getattr(self.w, 'lbl_aux_{}_value'.format(ch), None)
            if disp_old is not None:
                disp_idx = layout.indexOf(disp_old)
                field = QtWidgets.QLineEdit()
                field.setObjectName('field_aux_{}_value'.format(ch))
                # Same footprint as the old pill so the row layout is
                # unchanged.
                field.setMinimumSize(80, 40)
                field.setMaximumSize(80, 40)
                field.setAlignment(QtCore.Qt.AlignCenter)
                # Font only — background/border/colour come from the app QSS
                # QLineEdit rule so the box tracks whichever theme is active.
                field.setStyleSheet('font: bold 16pt "Lato Heavy";')
                field.setToolTip(
                    'Click and type a speed % to set it directly.\n'
                    'Decimals allowed (e.g. 42.5); range 0-100.')
                field.setText('{:.1f} %'.format(float(slider.value())))
                if disp_idx >= 0:
                    layout.insertWidget(disp_idx, field)
                disp_old.hide()
                setattr(self.w, 'field_aux_{}_value'.format(ch), field)
                self._aux_value_fields[ch] = field

            # Force the global QSS to apply to the new buttons (Qt's
            # initial polish ran before they existed).
            for b in (btn50, btn100):
                b.style().unpolish(b)
                b.style().polish(b)

            setattr(self.w, 'btn_aux_{}_50'.format(ch), btn50)
            setattr(self.w, 'btn_aux_{}_100'.format(ch), btn100)

    # === CYLINDRICAL ROBOT — Bold-white titles for bottom-row sections ===
    # The app QSS (dark_grey.qss) styles QGroupBox::Title with #e0e0e0 (light
    # grey) and "Lato Heavy" weight. Operator wants pure white + explicit
    # bold for the five bottom-row group titles. Setting a per-widget
    # stylesheet on each frame is the lightest touch — it adds an override
    # without disturbing the app QSS for everything else.
    def _style_section_titles(self):
        css = 'QGroupBox::title { color: #ffffff; font-weight: bold; }'
        for nm in ('frame_program', 'frame_tool', 'frame_override',
                   'frame_jogging', 'frame_spindle'):
            w = getattr(self.w, nm, None)
            if w is None:
                continue
            existing = w.styleSheet() or ''
            # Append our rule so any prior per-widget style is preserved.
            w.setStyleSheet(existing + ('\n' if existing else '') + css)

    # === CYLINDRICAL ROBOT — Tidy the JOGGING section internal layout ===
    # The .ui's gridLayout_jog_2 (inside widget_jog_buttons) was sized for a
    # narrow JOGGING frame. After we widened the section, the grid columns
    # stretched and Z+/Z- (col 0) drifted away from the X/Y cluster (col 1/2).
    # Cap the button cluster's width at its natural sizeHint and pin it to
    # the left so the cluster stays tight; let the sliders sit on the right
    # with the freed elastic space between them.
    def _tidy_jogging_section(self):
        row = getattr(self.w, 'horizontalLayout_25', None)
        buttons = getattr(self.w, 'widget_jog_buttons', None)
        if row is None or buttons is None:
            return

        # Lock the button cluster to its natural width — 3 columns x ~70 px
        # plus 3 px spacing + 2 px side margins ≈ 220 px.
        buttons.setMaximumWidth(220)
        sp = buttons.sizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
        buttons.setSizePolicy(sp)

        # Equalize the grid's columns so the three jog columns line up.
        grid = buttons.layout()
        if isinstance(grid, QtWidgets.QGridLayout):
            for c in range(grid.columnCount()):
                grid.setColumnStretch(c, 1)
                grid.setColumnMinimumWidth(c, 64)
            grid.setHorizontalSpacing(3)
            grid.setVerticalSpacing(3)

        # Stretch factors inside JOGGING: buttons stay fixed; the two
        # sliders share the remaining horizontal room equally.
        for name, factor in (
            ('widget_jog_buttons', 0),
            ('widget_jog_linear', 1),
            ('widget_jog_angular', 1),
        ):
            w = getattr(self.w, name, None)
            if w is None:
                continue
            idx = row.indexOf(w)
            if idx >= 0:
                row.setStretch(idx, factor)

    # === CYLINDRICAL ROBOT — Stabilize MACHINE status label ===
    # qtvcp's StatusLabel(machine_state_status=true) reflects the LinuxCNC
    # interpreter state. During AUTO execution the polar kins flushes the
    # motion queue often, so INTERP_READING and INTERP_WAITING fire many
    # times per second and the label flickers between Running / Reading /
    # Waiting. Operator misreads the transient text. Map both transient
    # states to "Running" so the label is stable while a program executes.
    # The visible states become: Estopped / Running / Stopped / Paused.
    def _fix_machine_state_label(self):
        w = getattr(self.w, 'status_machine_state', None)
        if w is None:
            return
        # Order matches qtvcp StatusLabel internals:
        #   [estop, interp-run, interp-idle, interp-paused,
        #    interp-waiting, interp-reading]
        w._state_label_list = [
            'Estopped', 'Running', 'Stopped', 'Paused', 'Running', 'Running'
        ]
        # Until the first interp signal arrives the QLabel is blank — show
        # 'Stopped' so the operator never sees an unexpected default.
        if not w.text():
            w.setText('Stopped')

    # === CYLINDRICAL ROBOT — Polish bottom row proportions + button sizing ===
    # Called last in initialized__ so it overrides any sizes set earlier.
    # 1. Equalize MODE group buttons: same uniform height, full-width stretch
    #    so MODE: CALIBRATE / HOME ALL / JOG: CARTESIAN line up visually.
    # 2. Tighten the OVERRIDES column (stackedWidget_dro) so OVERRIDES looks
    #    a bit smaller, and give JOGGING the freed horizontal space via
    #    a stretch factor in layout_lower.
    def _polish_bottom_row(self):
        # The legacy MODE group box (btn_op_mode + btn_home_all +
        # btn_jog_mode_toggle) no longer exists — every button moved
        # elsewhere or was hidden, so no per-button sizing is needed here.

        # --- proportions of the lower bar ---
        # OVERRIDES + MODE stays Expanding with stretch=1 (untouched).
        # PROGRAM and JOGGING get a matching fixed width that's a bit
        # smaller than before — equal to each other, slightly less than
        # what the equal-share trio yielded previously.
        sw = getattr(self.w, 'stackedWidget_dro', None)
        if sw is not None:
            sw.setMaximumWidth(16777215)

        layout_lower = getattr(self.w, 'layout_lower', None)
        if layout_lower is not None:
            # OVERRIDES stays elastic, min 360 px, stretch=1 (unchanged).
            ov = getattr(self.w, 'stackedWidget_dro', None)
            if ov is not None:
                ov.setMinimumWidth(360)
                sp = ov.sizePolicy()
                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                ov.setSizePolicy(sp)
                idx = layout_lower.indexOf(ov)
                if idx >= 0:
                    layout_lower.setStretch(idx, 1)

            # PROGRAM reduced to 8 cm; JOGGING stays at 14 cm.
            widths_px = {
                'frame_program': 265,   # 7 cm  @ 96 DPI (was 8 cm, -1 cm)
                'frame_jogging': 454,   # 12 cm @ 96 DPI (was 14 cm, -2 cm)
            }
            for name, px in widths_px.items():
                w = getattr(self.w, name, None)
                if w is None:
                    continue
                sp = w.sizePolicy()
                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
                w.setSizePolicy(sp)
                w.setFixedWidth(px)
                idx = layout_lower.indexOf(w)
                if idx >= 0:
                    layout_lower.setStretch(idx, 0)

            # AUX MOTORS: bump up by 3 cm from its natural ~7 cm sizeHint
            # → fixed at 10 cm. OVERRIDES auto-shrinks because it's the
            # only Expanding/stretch=1 section that absorbs layout deltas.
            tool = getattr(self.w, 'frame_tool', None)
            if tool is not None:
                sp = tool.sizePolicy()
                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
                tool.setSizePolicy(sp)
                tool.setFixedWidth(529)  # 14 cm @ 96 DPI (was 12 cm, +2 cm)
                idx = layout_lower.indexOf(tool)
                if idx >= 0:
                    layout_lower.setStretch(idx, 0)

            # STATUS untouched.

    # === CYLINDRICAL ROBOT — Empty out the DRO frame; hide empty panels ===
    # The X/Y/Z DRO rows and G/M code labels are hidden. The legacy "MODE"
    # group box under OVERRIDES held HOME ALL + jog/op-mode toggles, but
    # those have all moved: btn_op_mode -> CALIBRATE tab, btn_jog_mode_toggle
    # -> JOGGING grid, btn_home_all is hidden via _hide. Without any
    # content the MODE group is no longer built. The INPUTS panel under
    # MACHINE ON/OFF likewise lost its content (HOME X/Y/Z labels cleared,
    # LIMIT LED hidden) so it gets hidden here too. Finally frame_dro is
    # hidden so the bottom row redistributes evenly across the remaining
    # sections.
    def _restructure_dro_and_modes(self):
        # Hide the now-empty DRO group entirely so the bottom-row layout
        # redistributes the freed space across PROGRAM / AUX MOTORS /
        # OVERRIDES / JOGGING / STATUS evenly.
        for nm in ('frame_dro', 'groupBox_inputs'):
            w = getattr(self.w, nm, None)
            if w is None:
                continue
            sp = w.sizePolicy()
            sp.setRetainSizeWhenHidden(False)
            w.setSizePolicy(sp)
            w.hide()
        # Pin ESTOP / MACHINE ON-OFF to the top of the right column. The
        # column's QVBoxLayout (verticalLayout_24) used to have ESTOP on
        # top and groupBox_inputs below; with INPUTS hidden, ESTOP would
        # otherwise expand to fill the column and visually drift down.
        # An end-of-column stretch absorbs the freed space instead.
        try:
            vl = self.w.verticalLayout_24
            vl.addStretch(1)
        except AttributeError:
            pass

    # === CYLINDRICAL ROBOT — Move JOG: CARTESIAN/JOINT toggle into JOGGING ===
    # Operator wants the world/joint jog toggle in the jogging section right
    # next to Z+/Z-, not in the bottom MODE group. Reparent btn_jog_mode_toggle
    # into gridLayout_jog_2: spans rows 1-2 (same vertical extent as Z+/Z-)
    # and columns 1-2 (the slot vacated by the hidden A/C axis jog buttons).
    def _move_jog_mode_to_jogging(self):
        try:
            btn = self.w.btn_jog_mode_toggle
            grid = self.w.gridLayout_jog_2
        except AttributeError:
            return
        # Detach from current parent layout (handled implicitly by addWidget
        # on the new grid).
        # The grid columns 1-2 inherit their width from the (hidden) A/C
        # axis jog buttons which are 53 px each — about 110 px usable
        # for the spanned cell. With AlignHCenter, a button wider than
        # that cell overflows symmetrically and gets clipped on the
        # right edge of the JOGGING section. Cap max at 150 px and keep
        # min at 100 px so the button stays bigger than the original
        # 32 px row but never exceeds the cell's safe width.
        btn.setMinimumSize(120, 50)
        btn.setMaximumSize(160, 50)
        sp = btn.sizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)
        btn.setSizePolicy(sp)
        # row=1, col=1, rowspan=2, colspan=2; top-aligned so its top
        # edge sits flush with Z+ (row=1, col=0), horizontally centered
        # so margins on the left and right are equal.
        grid.addWidget(btn, 1, 1, 2, 2,
                       QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

    # === CYLINDRICAL ROBOT — Move MODE: CALIBRATE/ABSOLUTE to CALIBRATE tab ===
    # btn_op_mode toggles the operating mode the next-launch auto-resume
    # logic checks. Operators only flip it during setup, so it belongs on
    # the CALIBRATE tab next to the J0/J1/J2 calibration controls, not in
    # the always-visible bottom MODE group. The .ui adds cal_page_mode_holder
    # at the top of main_tab_Page_Calibrate; we reparent the button into it.
    def _move_op_mode_to_calibrate_tab(self):
        try:
            mode_btn = self.w.btn_op_mode
            holder_layout = self.w.cal_page_mode_holder.layout()
        except AttributeError:
            return
        holder_layout.addWidget(mode_btn)

    # === CYLINDRICAL ROBOT — Move SETTINGS tab to the end ===
    # Operator preference: SETTINGS lives at the very end of the top tab
    # row (just before the spacer / EXIT), after JOINTS. Reparent by
    # removing it from layout_buttonbar at its current position and
    # re-inserting it right before the trailing horizontalSpacer.
    def _move_settings_tab_to_end(self):
        try:
            bar = self.w.layout_buttonbar
            btn = self.w.btn_settings
            spacer_marker = self.w.horizontalSpacer
        except AttributeError:
            return
        # Find the spacer's position so we can insert btn_settings just
        # before it (i.e. after JOINTS and the other top-tab buttons).
        spacer_idx = -1
        for i in range(bar.count()):
            it = bar.itemAt(i)
            if it is not None and it.spacerItem() is spacer_marker:
                spacer_idx = i
                break
        bar.removeWidget(btn)
        if spacer_idx < 0:
            # Fallback: append at the end.
            bar.addWidget(btn)
        else:
            bar.insertWidget(spacer_idx, btn)

    # === CYLINDRICAL ROBOT — Compact OVERRIDES rows ===
    # The .ui stacks the section label (MAX VELOCITY / RAPID / FEEDRATE)
    # ABOVE each slider row, which makes the OVERRIDES section three
    # double-height rows that dominate the bottom bar. The AUX MOTORS
    # section uses an inline [label][50][slider][100][value] arrangement
    # — we apply the same here by moving each label into the start of
    # its row's inner QHBoxLayout so the rows become single-row tall.
    # Widgets, signals, and behavior are unchanged — only the parent
    # layout placement of three QLabels differs.
    # === CYLINDRICAL ROBOT — Move JogIncrements under each slider ===
    # The .ui places jogincrements_linear / jogincrements_angular
    # (combo boxes whose first entry is "Continuous") on a separate row
    # next to bulky LINEAR INCREMENT / ANGULAR INCREMENT labels. We
    # hide the labels and reparent each combo into its slider column
    # so the JOG mode (continuous vs increment) sits directly under
    # the slider that uses it.
    def _move_increments_under_sliders(self):
        # Put the two jog-increment combos ("Continuous" ...) in a single
        # FULL-WIDTH row directly below the three slider columns. They can't
        # live inside the columns: those are pinned narrow (60px) for the tight
        # sliders, which clips the ~100px combos. A centred row (stretch on
        # each side) lets both combos show at full width. This uses roughly the
        # same vertical budget the combos took at the column bottoms, so the
        # slider lengths are essentially unchanged (frame_jogging is fixed at
        # 400px tall).
        frame = getattr(self.w, 'frame_jogging', None)
        v8 = frame.layout() if frame is not None else None
        if v8 is None:
            return
        row = QtWidgets.QWidget()
        row.setObjectName('widget_jog_increments_row')
        hb = QtWidgets.QHBoxLayout(row)
        hb.setContentsMargins(6, 2, 6, 2)
        hb.setSpacing(10)
        hb.addStretch(1)
        for combo_name in ('jogincrements_linear', 'jogincrements_angular'):
            combo = getattr(self.w, combo_name, None)
            if combo is None:
                continue
            combo.setMinimumWidth(110)     # enough for "Continuous"
            combo.setMaximumWidth(220)
            hb.addWidget(combo)            # addWidget() auto-reparents
            hb.addStretch(1)
        # Insert just below the slider row (horizontalLayout_25 is the first
        # item of verticalLayout_8).
        v8.insertWidget(1, row)
        # Hide the old separate "LINEAR INCREMENT" / "ANGULAR INCREMENT"
        # label + container rows.
        for nm in ('lbl_increments_linear', 'lbl_increments_angular',
                   'widget_increments_linear', 'widget_increments_angular'):
            w = getattr(self.w, nm, None)
            if w is None:
                continue
            try:
                sp = w.sizePolicy()
                sp.setRetainSizeWhenHidden(False)
                w.setSizePolicy(sp)
                w.hide()
            except (AttributeError, RuntimeError):
                pass

    def _compact_overrides(self):
        # Each row becomes its own QGroupBox (title="Max Velocity" /
        # "Rapid" / "Feedrate") containing [50][slider][100][display] —
        # visually identical to AUX MOTORS' Extruder/Pump/Fluid Pump
        # boxes. The old standalone label is dropped (group-box title
        # replaces it). The original widget_max_ovr/widget_rapid_ovr/
        # widget_feed_ovr containers are removed in favour of the new
        # group boxes.
        ov = getattr(self.w, 'frame_override', None)
        if ov is None:
            return
        ov_layout = ov.layout()
        if ov_layout is None:
            return
        # Match AUX MOTORS panel spacing + margins exactly.
        ov_layout.setSpacing(8)
        ov_layout.setContentsMargins(8, 12, 8, 8)

        rows = [
            ('widget_max_ovr',   'label_28', 'Max Velocity', 'max'),
            ('widget_rapid_ovr', 'label_32', 'Rapid',        'rapid'),
            ('widget_feed_ovr',  'label_36', 'Feedrate',     'feed'),
        ]
        for outer_name, label_name, title, key in rows:
            outer = getattr(self.w, outer_name, None)
            label = getattr(self.w, label_name, None)
            if outer is None:
                continue
            # Gather every widget out of the original outer container
            # (label may be in the outer vbox; the slider/buttons/display
            # are in the inner hbox).
            children = []
            outer_layout_orig = outer.layout()
            if outer_layout_orig is not None:
                for i in range(outer_layout_orig.count()):
                    it = outer_layout_orig.itemAt(i)
                    if it is None:
                        continue
                    if it.widget() is not None and it.widget() is not label:
                        children.append(it.widget())
                    inner = it.layout()
                    if inner is not None:
                        for j in range(inner.count()):
                            sub = inner.itemAt(j)
                            if sub is None:
                                continue
                            w = sub.widget()
                            if w is not None and w is not label:
                                children.append(w)

            # Find where the old row sits inside the OVERRIDES group so
            # we can splice the new group box in at the same position.
            outer_idx = ov_layout.indexOf(outer)
            if outer_idx < 0:
                continue

            gb = QtWidgets.QGroupBox(title)
            gb.setObjectName('groupBox_ovr_' + key)
            gb_lay = QtWidgets.QHBoxLayout(gb)
            # Match AUX row spacing/margins exactly (hlay_aux_ext etc.):
            # spacing=6, margins=6/4/6/4. The slider's themed handle
            # extends ~6px past the slider rect at value extremes; with
            # spacing=6 the handle's outer edge touches — but does not
            # cover — the next button, matching the AUX visual.
            gb_lay.setSpacing(6)
            gb_lay.setContentsMargins(6, 4, 6, 4)
            for w in children:
                gb_lay.addWidget(w)
            # White, bold title to match other section group boxes
            # (_style_section_titles ran earlier — these new gbs need
            # the rule applied directly).
            gb.setStyleSheet(
                'QGroupBox::title { color: #ffffff; font-weight: bold; }')

            self.w['groupBox_ovr_' + key] = gb

            # Out with the old, in with the new.
            ov_layout.removeWidget(outer)
            outer.setParent(None)
            outer.deleteLater()
            if label is not None:
                label.setParent(None)
                label.deleteLater()
            ov_layout.insertWidget(outer_idx, gb)

        # Push the three group boxes to the top of OVERRIDES; freed
        # space goes to a trailing stretch instead of inflating rows.
        ov_layout.addStretch(1)

        # AUX sliders keep the wider 200px min so their long rows feel
        # balanced; OVERRIDES rows are narrower without the ON checkbox
        # in front, so shrink their sliders to 140px min for a more
        # compact look.
        for nm in ('sld_aux_ext_speed', 'sld_aux_pump_speed',
                   'sld_aux_fluid_speed'):
            s = getattr(self.w, nm, None)
            if s is None:
                continue
            s.setMinimumWidth(200)
            sp = s.sizePolicy()
            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
            s.setSizePolicy(sp)
        for nm in ('slider_maxv_ovr', 'slider_rapid_ovr', 'slider_feed_ovr'):
            s = getattr(self.w, nm, None)
            if s is None:
                continue
            s.setMinimumWidth(140)
            s.setMaximumWidth(180)
            sp = s.sizePolicy()
            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
            s.setSizePolicy(sp)

        # Match AUX row structure: the slider's groove fills its full
        # widget rect (no per-widget QSS inset) and the row spacing alone
        # keeps the handle from overlapping the "100" button. Override
        # sliders default to value=max (handle at right edge), so this
        # is more visible than on AUX where the handle starts at 0.
        # The handle's 6px overhang at max sits inside the row spacing,
        # not on top of the next widget.

    # === CYLINDRICAL ROBOT — PRINT CAL embedded tab ===
    # The PRINT CAL top tab page (main_tab_Page_PrintCal) hosts a
    # PrintCalWidget — a fully Qt-native G-code offset tool ported
    # from the legacy standalone Tkinter gcode_viewer.py. The panel is
    # given over to the graph: it mirrors the currently-loaded program
    # (fed in via set_source_file from file_loaded) and offers only the
    # PLACE START HERE placement plus two buttons — EXPORT (save the
    # positioned file to disk) and LOAD (push that file into LinuxCNC to
    # run, via the widget's request_load signal -> ACTION.OPEN_PROGRAM).
    def _install_print_cal_tab(self):
        try:
            page = self.w.main_tab_Page_PrintCal
        except AttributeError:
            return
        # Resolve the auto-save directory. Root launches put us in the
        # project root; sim launches cd into Trial/ so the folder sits
        # one level up. Either candidate's parent dir must already
        # exist (the "Print Calibrate" folder); we'll create output/
        # under it on demand.
        cfg_dir = PATH.CONFIGPATH if hasattr(PATH, 'CONFIGPATH') else os.getcwd()
        candidates = [
            os.path.join(cfg_dir, 'Print Calibrate', 'output'),
            os.path.join(cfg_dir, '..', 'Print Calibrate', 'output'),
        ]
        parent_exists = lambda p: os.path.isdir(os.path.dirname(p))
        out_dir = next((p for p in candidates if parent_exists(p)), None)
        if out_dir is None:
            out_dir = candidates[0]
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError:
            pass

        # Clear any placeholder children the .ui left in the page.
        layout = page.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(page)
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        from qtdragon_hd.printcal_widget import PrintCalWidget
        widget = PrintCalWidget(out_dir, page)
        self.w.printcal_widget = widget
        layout.addWidget(widget)
        widget.request_load.connect(self._on_printcal_load)

    def _on_printcal_load(self, save_path):
        # LOAD wrote the positioned file (no separate EXPORT needed) and
        # emitted its path. Push it through LinuxCNC's program-load
        # action so QtDragon's main gcode viewer picks it up immediately.
        # Seed _original_loaded_file (as load_code() does) so file_loaded()
        # swaps LinuxCNC's [FILTER] /tmp/emcflt-* path back to this real,
        # persistent path when writing last_gcode.txt. Without it, the
        # stale path from the previous load is reused and auto-resume
        # points at the wrong program (or a /tmp path deleted on shutdown).
        self._original_loaded_file = save_path
        ACTION.OPEN_PROGRAM(save_path)
        self.add_status('Print Cal: auto-loaded {}'
                        .format(os.path.basename(save_path)))

    # === CYLINDRICAL ROBOT — Restructure STATUS section vertically ===
    # The .ui has STATUS (frame_spindle) with widget_spindle_control on the
    # left (gauge + spindle controls + spindle_power + progressBar) and
    # groupBox_status on the right (MACHINE row + RUN TIME row). The
    # spindle gauge and controls are already hidden by init_widgets's
    # spindle-hide list, but progressBar lives INSIDE widget_spindle_control,
    # so the geometry still allocates space for that wrapper.
    #
    # We rebuild the STATUS column so the operator sees, top-down:
    #   1. PROGRESS bar
    #   2. MACHINE row
    #   3. RUN TIME row
    #   4. SPEEDS group
    # progressBar is reparented out of widget_spindle_control, the spindle
    # wrapper is hidden, and SPEEDS is appended at the bottom.
    def _move_speeds_to_status(self):
        try:
            speeds = self.w.frame_speeds
            old_overrides = self.w.verticalLayout_44   # SPEEDS' current parent
            host_h = self.w.horizontalLayout_56        # STATUS row layout
            progress = self.w.progressBar
            machine_box = self.w.groupBox_status
            spindle_wrap = self.w.widget_spindle_control
        except AttributeError:
            return

        # Detach SPEEDS from its original parent under OVERRIDES.
        old_overrides.removeWidget(speeds)

        # Build a single vertical column hosting all 5 sections in order.
        column = QtWidgets.QWidget(self.w.frame_spindle)
        column.setObjectName('frame_status_column')
        vb = QtWidgets.QVBoxLayout(column)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(6)

        # LAYERS box — mirrors SPEEDS' QGroupBox style (centered title,
        # WinPanel/Sunken display fields). Two rows: COMPLETED / REMAINING,
        # both updated from the parsed layer-start lines in periodic_update.
        layers_box = QtWidgets.QGroupBox('LAYERS')
        layers_box.setObjectName('frame_layers')
        layers_box.setAlignment(QtCore.Qt.AlignCenter)
        layers_box.setMaximumSize(16777215, 90)
        layers_box.setStyleSheet(
            'QGroupBox::title { color: #ffffff; font-weight: bold; }')
        lb_lay = QtWidgets.QVBoxLayout(layers_box)
        lb_lay.setContentsMargins(4, 4, 4, 2)
        lb_lay.setSpacing(4)

        def _mk_layer_row(label_text, edit_name):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(0)
            lbl = QtWidgets.QLabel(label_text)
            lbl.setMinimumHeight(27)
            lbl.setMaximumHeight(27)
            lbl.setIndent(5)
            lbl.setStyleSheet('color: #ffffff;')
            edit = QtWidgets.QLineEdit('0')
            edit.setObjectName(edit_name)
            edit.setReadOnly(True)
            edit.setMinimumSize(60, 27)
            edit.setMaximumSize(60, 27)
            edit.setAlignment(QtCore.Qt.AlignCenter)
            edit.setFrame(True)
            setattr(self.w, edit_name, edit)
            row.addWidget(lbl)
            row.addWidget(edit)
            return row

        lb_lay.addLayout(_mk_layer_row('COMPLETED', 'lbl_layers_done'))
        lb_lay.addLayout(_mk_layer_row('REMAINING', 'lbl_layers_left'))

        # addWidget reparents these out of their original layouts.
        vb.addWidget(progress)
        vb.addWidget(machine_box)
        vb.addWidget(layers_box)
        vb.addWidget(speeds)
        vb.addStretch(1)

        # Hide the now-empty spindle wrapper (its visible child was just
        # progressBar; we lifted that out above).
        spindle_wrap.hide()

        host_h.addWidget(column)

    # === CYLINDRICAL ROBOT — MDI command + history tab ===
    # Dedicated top tab inserted right after GCODES. Hosts a qtvcp
    # MDIHistory widget: type a one-liner, hit Enter to run, click an
    # old entry to recall it.

    def _setup_mdi_tab(self):
        global TAB_MDI
        try:
            bar = self.w.layout_buttonbar
            stack = self.w.stackedWidget_mainTab
            ref_btn = self.w.btn_gcodes
        except AttributeError:
            return

        # --- Build the page ---
        page = QtWidgets.QWidget()
        page.setObjectName('stackedWidget_mainTabPageMDI')
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        title = QtWidgets.QLabel('MDI COMMANDS  —  manual entries only')
        title.setStyleSheet('font: bold 12pt;')
        v.addWidget(title)

        self.w.mdihistory_tab = ManualMDIPanel(page)
        self.w.mdihistory_tab.setObjectName('mdihistory_tab')
        v.addWidget(self.w.mdihistory_tab, 1)

        TAB_MDI = stack.addWidget(page)  # new page index at end of stack
        self._mdi_tab_index = TAB_MDI

        # --- Build the button to match btn_gcodes' style/sizing ---
        btn = QtWidgets.QPushButton('MDI', ref_btn.parentWidget())
        btn.setObjectName('btn_mdi')
        btn.setSizePolicy(ref_btn.sizePolicy())
        btn.setMinimumSize(ref_btn.minimumSize())
        btn.setMaximumSize(ref_btn.maximumSize())
        btn.setCheckable(True)
        btn.setProperty('index', TAB_MDI)
        self.w.btn_mdi = btn

        # Insert in the bar right after btn_gcodes.
        gcodes_pos = bar.indexOf(ref_btn)
        bar.insertWidget(gcodes_pos + 1, btn)

        # Hook into the existing exclusive button group so it tracks state
        # alongside the other top tabs.
        try:
            self.w.page_buttonGroup.addButton(btn)
        except AttributeError:
            btn.clicked.connect(lambda: self.main_tab_changed(btn))

    # === CYLINDRICAL ROBOT — Side MDI panel under the GCODE viewer ===
    # The page widget hosts a QSplitter (gcode_mdi_splitter) with the
    # gcode_viewer on top and mdi_side_holder underneath. The holder is
    # split into two columns (mdi_side_panel_col | mdi_side_mode_col):
    # ManualMDIPanel on the left taking the bulk of the width, the three
    # MAN/MDI/AUTO mode buttons stacked on the right matching the panel's
    # height. The _MDIPanelSync class-level signal bus keeps this side
    # panel in sync with the MDI tab's instance.
    def _setup_mdi_side_panel(self):
        try:
            holder_layout = self.w.mdi_side_holder.layout()
            panel_col = self.w.mdi_side_panel_col
            mode_col = self.w.mdi_side_mode_col
            splitter = self.w.gcode_mdi_splitter
        except AttributeError:
            return
        self.w.mdihistory_side = ManualMDIPanel(panel_col)
        self.w.mdihistory_side.setObjectName('mdihistory_side')
        panel_col.layout().addWidget(self.w.mdihistory_side, 1)
        # Width split: panel takes the bulk, mode column hugs its buttons.
        holder_layout.setStretchFactor(panel_col, 1)
        holder_layout.setStretchFactor(mode_col, 0)
        # Give the gcode viewer most of the space by default; the user
        # can drag the splitter to rebalance.
        splitter.setSizes([500, 200])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        # Move the MAN/MDI/AUTO mode buttons next to the MDI entry so the
        # operator can switch modes without reaching to the right column.
        self._move_mode_buttons_to_mdi_side()

    def _move_mode_buttons_to_mdi_side(self):
        try:
            mode_col = self.w.mdi_side_mode_col
            mode_col_layout = mode_col.layout()
            man = self.w.manual_mode_button
            mdi = self.w.mdi_mode_button
            auto = self.w.auto_mode_button
            gb = self.w.groupBox_mode
        except AttributeError:
            return
        # Stack vertically: MAN on top, MDI, AUTO. Keep the original
        # 100x50 fixed sizing from the .ui — no resizing.
        for btn in (man, mdi, auto):
            btn.setParent(None)
            mode_col_layout.addWidget(btn)
        mode_col_layout.addStretch(1)
        gb.hide()

    def file_loaded(self, obj, filename):
        if os.path.basename(filename).count('.') > 1:
            self.last_loaded_program = ""
            return
        if filename is not None:
            self.add_status("Loaded file {}".format(filename))
            self.w.progressBar.reset()
            # If LinuxCNC handed us the [FILTER] temp path, swap in the
            # original path captured in load_code() so PREFS_ persists the
            # real file for the next-launch auto-resume.
            if filename.startswith('/tmp/emcflt-') and getattr(self, '_original_loaded_file', None):
                filename = self._original_loaded_file
            self.last_loaded_program = filename
            # Mirror the loaded program into the PRINT CAL tool so it always
            # shows the current part (it ignores its own exported files).
            if hasattr(self.w, 'printcal_widget'):
                try:
                    self.w.printcal_widget.set_source_file(filename)
                except Exception:
                    pass
            self.w.lbl_runtime.setText("00:00:00")
            if hasattr(self.w, 'lbl_est_runtime'):
                self.w.lbl_est_runtime.setText("--:--:--")
            # Refresh LAYERS box (total + reset done/left counters).
            self._layer_starts = self._parse_layer_starts(filename)
            self._total_layers = len(self._layer_starts)
            self._update_layer_display(0)
            # Persist NOW (not in closing_cleanup__) so a hard power-cut
            # mid-print still has the original .ngc path on disk for the
            # next-launch auto-resume. Written with fsync via atomic
            # replace — survives unclean shutdowns.
            try:
                _tmp = self._last_gcode_path + '.tmp'
                with open(_tmp, 'w') as _f:
                    _f.write(filename)
                    _f.flush()
                    os.fsync(_f.fileno())
                os.replace(_tmp, self._last_gcode_path)
            except (OSError, AttributeError):
                pass
        else:
            self.add_status("Filename not valid", CRITICAL)

    def percent_loaded_changed(self, fraction):
        # Use Qt %p% placeholder so the bar text always carries a % sign,
        # matching the POWER bar style (POWER %p% / PROGRESS %p%).
        if fraction < 0:
            self.w.progressBar.setValue(0)
            self.w.progressBar.setFormat('PROGRESS %p%')
        else:
            self.w.progressBar.setValue(fraction)
            self.w.progressBar.setFormat('LOADING %p%')

    def percent_done_changed(self, fraction):
        self.w.progressBar.setValue(fraction)
        if fraction < 0:
            self.w.progressBar.setValue(0)
            self.w.progressBar.setFormat('PROGRESS %p%')
        else:
            self.w.progressBar.setFormat('PROGRESS %p%')
        # CYLINDRICAL ROBOT — track natural completion to clear saved
        # positions when the print finishes (vs operator abort/stop).
        # Flag is reset on the next interp-run.
        if fraction >= 100:
            self._reached_100 = True

    def all_homed(self, obj):
        self.home_all = True
        self.w.btn_home_all.setText("ALL HOMED")
        if self.first_turnon is True:
            self.first_turnon = False
            if self.w.chk_reload_tool.isChecked():
                command = "M61 Q{} G43".format(self.reload_tool)
                ACTION.CALL_MDI(command)
            if self.last_loaded_program is not None and self.w.chk_reload_program.isChecked():
                if os.path.isfile(self.last_loaded_program):
                    self.w.cmb_gcode_history.addItem(self.last_loaded_program)
                    self.w.cmb_gcode_history.setCurrentIndex(self.w.cmb_gcode_history.count() - 1)
                    self.w.cmb_gcode_history.setToolTip(self.last_loaded_program)
                    ACTION.OPEN_PROGRAM(self.last_loaded_program)
        ACTION.SET_MANUAL_MODE()
        self.w.manual_mode_button.setChecked(True)

    def not_all_homed(self, obj, list):
        self.home_all = False
        self.w.btn_home_all.setText("HOME ALL")

    def hard_limit_tripped(self, obj, tripped, list_of_tripped):
        self.add_status("Hard limits tripped", CRITICAL)
        self.w.chk_override_limits.setEnabled(tripped)
        if not tripped:
            self.w.chk_override_limits.setChecked(False)

    # keep check button in synch of external changes
    def _check_override_limits(self,state,data):
        if 0 in data:
            self.w.chk_override_limits.setChecked(False)
        else:
            self.w.chk_override_limits.setChecked(True)

    #######################
    # CALLBACKS FROM FORM #
    #######################

    # main button bar
    def main_tab_changed(self, btn):
        index = btn.property("index")

        if index == TAB_USER:
            pass
        elif index == self.w.stackedWidget_mainTab.currentIndex():
            self.w.stackedWidget_dro.setCurrentIndex(0)

        if index is None: return

        # adjust the stack widgets depending on modes
        self.adjust_stacked_widgets(index)

    # gcode frame
    def cmb_gcode_history_clicked(self):
        if self.w.cmb_gcode_history.currentIndex() == 0: return
        filename = self.w.cmb_gcode_history.currentText()
        if filename == self.last_loaded_program:
            self.add_status("Selected program is already loaded", WARNING)
        else:
            # Seed _original_loaded_file so file_loaded() swaps the [FILTER]
            # /tmp/emcflt-* path back to this real path for last_gcode.txt.
            # Otherwise the stale previous path is reused and auto-resume
            # points at the wrong program.
            self._original_loaded_file = filename
            ACTION.OPEN_PROGRAM(filename)

    # program frame
    def btn_start_clicked(self, obj):
        if self.w.stackedWidget_mainTab.currentIndex() != 0:
            return
        # Auto-switch to ABSOLUTE on RUN — pressing RUN signals a real print,
        # which needs auto-save / auto-resume armed. CALIBRATE is for jogging
        # and tuning, never for a production run. Persisted to mode.json so
        # the next launch also boots in ABSOLUTE without any button press.
        try:
            import json as _json
            _need = True
            try:
                with open(self._op_mode_path) as _f:
                    _need = _json.load(_f).get('mode') != 'absolute'
            except (FileNotFoundError, ValueError):
                pass
            if _need:
                with open(self._op_mode_path, 'w') as _f:
                    _json.dump({'mode': 'absolute'}, _f)
                self.w.btn_op_mode.setText('MODE: ABSOLUTE')
                self.w.btn_op_mode.setChecked(True)
                STATUS.emit('update-machine-log',
                    '*** RUN pressed in CALIBRATE — switched to ABSOLUTE. ***',
                    None)
        except (AttributeError, OSError):
            pass
        if not STATUS.is_auto_mode():
            # AXIS-style: auto-flip into AUTO mode instead of rejecting the click.
            ACTION.SET_AUTO_MODE()
        if STATUS.is_auto_running():
            self.add_status("Program is already running", WARNING)
            return
        # Skip the stock RUNFROMLINE "Preset Dialog" (Spindle CW/CCW/RPM).
        # That dialog is for mill workflows where lines before the start
        # line might contain M3/M4 spindle commands that need presetting.
        # No spindle on this machine — go straight to RUN regardless of
        # whether we're starting at line 1 or mid-program (auto-resume).
        ACTION.RUN(self.start_line)

        self.start_timer()
        self.add_status("Started program from line {}".format(self.start_line))

    def btn_stop_clicked(self):
        if not self.w.btn_pause_spindle.isChecked(): return
        self.w.btn_pause_spindle.setChecked(False)
        self.btn_pause_spindle_clicked(False)

    def btn_reload_file_clicked(self):
        if self.last_loaded_program:
            self.w.progressBar.reset()
            self.add_status("Loaded program file {}".format(self.last_loaded_program))
            ACTION.OPEN_PROGRAM(self.last_loaded_program)

    def btn_pause_spindle_clicked(self, state):
        self.w.action_pause.setEnabled(not state)
        self.w.action_step.setEnabled(not state)
        if state:
        # set external offsets to lift spindle
            self.h['spindle-lift-on'] = True
            self.h['eoffset-clear'] = False
            self.h['eoffset-enable'] = self.w.chk_eoffsets.isChecked()
            fval = int(self.w.lineEdit_eoffset_count.text())
            self.h['eoffset-spindle-count'] = int(fval)
            self.w.spindle_eoffset_value.setText(self.w.lineEdit_eoffset_count.text())
            self.h['spindle-inhibit'] = True
            self.add_status("Spindle stopped and raised {}".format(fval))
            if not QHAL.hal.component_exists("z_level_compensation"):
                self.add_status("Z level compensation HAL component not loaded", CRITICAL)
                return
        else:
            # turn spindle back on
            self.h['spindle-inhibit'] = False
            self.add_status('Spindle re-started')

            # If spindle at speed is connected use it lower spindle
            if self.h.hal.pin_has_writer('spindle.0.at-speed'):
                self._spindle_wait=True
                return
            else:
                # or wait for dialog to close before lowering spindle
                if STATUS.is_auto_running():
                    info = "Wait for spindle at speed signal before resuming"
                    mess = {'NAME':'MESSAGE', 'ICON':'WARNING',
                            'ID':'_wait_resume_', 'MESSAGE':'CAUTION',
                            'NONBLOCKING':'True', 'MORE':info, 'TYPE':'OK'}
                    ACTION.CALL_DIALOG(mess)

    def btn_enable_comp_clicked(self, state):
        if state:
            fname = os.path.join(PATH.CONFIGPATH, "probe_points.txt")
            if not os.path.isfile(fname):
                self.add_status(fname + " not found", CRITICAL)
                self.w.btn_enable_comp.setChecked(False)
                return
            if not QHAL.hal.component_exists("z_level_compensation"):
                self.add_status("Z level compensation HAL component not loaded", CRITICAL)
                self.w.btn_enable_comp.setChecked(False)
                return
            self.h['comp-on'] = True
            self.h['eoffset-clear'] = False
            self.add_status("Z level compensation ON")
        else:
            if not QHAL.hal.component_exists("z_level_compensation"):
                self.add_status("Z level compensation HAL component not loaded", CRITICAL)
                return
            self.h['comp-on'] = False
            self.add_status("Z level compensation OFF", WARNING)


    # offsets frame
    def btn_goto_location_clicked(self):
        dest = self.w.sender().property('location')
        if dest == 'home':
            x = float(self.w.lbl_home_x.text())
            y = float(self.w.lbl_home_y.text())
        elif dest == 'sensor':
            x = float(self.w.lineEdit_sensor_x.text())
            y = float(self.w.lineEdit_sensor_y.text())
        else:
            return

        if STATUS.is_metric_mode():
            x = INFO.convert_machine_to_metric(x)
            y = INFO.convert_machine_to_metric(y)
        else:
            x = INFO.convert_machine_to_imperial(x)
            y = INFO.convert_machine_to_imperial(y)

        ACTION.CALL_MDI("G90")
        ACTION.CALL_MDI_WAIT("G53 G0 Z0")
        command = "G53 G0 X{:3.4f} Y{:3.4f}".format(x, y)
        ACTION.CALL_MDI_WAIT(command, self.calc_mdi_move_wait_time(x,y))
 
    def btn_ref_laser_clicked(self):
        x = float(self.w.lineEdit_laser_x.text())
        y = float(self.w.lineEdit_laser_y.text())

        if STATUS.is_metric_mode():
            x = INFO.convert_machine_to_metric(x)
            y = INFO.convert_machine_to_metric(y)
        else:
            x = INFO.convert_machine_to_imperial(x)
            y = INFO.convert_machine_to_imperial(y)

        self.add_status("Laser offsets set")
        command = "G10 L20 P0 X{:3.4f} Y{:3.4f}".format(x, y)
        ACTION.CALL_MDI(command)
    
    def btn_ref_camera_clicked(self):
        x = float(self.w.lineEdit_camera_x.text())
        y = float(self.w.lineEdit_camera_y.text())

        if STATUS.is_metric_mode():
            x = INFO.convert_machine_to_metric(x)
            y = INFO.convert_machine_to_metric(y)
        else:
            x = INFO.convert_machine_to_imperial(x)
            y = INFO.convert_machine_to_imperial(y)

        self.add_status("Camera offsets set")
        command = "G10 L20 P0 X{:3.4f} Y{:3.4f}".format(x, y)
        ACTION.CALL_MDI(command)

    def btn_touchoff_clicked(self):
        if STATUS.get_current_tool() == 0:
            self.add_status("Cannot touchoff with no tool loaded", CRITICAL)
            return
        if not STATUS.is_all_homed():
            self.add_status("Must be homed to perform tool touchoff", WARNING)
            return
         
         # instantiate dialog box   
        unit = "mm" if INFO.MACHINE_IS_METRIC else "in"
        sensor = self.w.sender().property('sensor')
        info = "Ensure tooltip is within {}{} of tool sensor and click OK".format(self.w.lineEdit_max_probe.text(), unit)
        mess = {'NAME':'MESSAGE', 'ID':sensor, 'MESSAGE':'TOOL TOUCHOFF', 'MORE':info, 'TYPE':'OKCANCEL'}
        ACTION.CALL_DIALOG(mess)
        
    def chk_lock_wph_changed(self, state):
        self.w.lineEdit_work_height.setReadOnly(not state)

    # DRO frame
    def btn_home_all_clicked(self, obj):
        if self.home_all is False:
            ACTION.SET_MACHINE_HOMING(-1)
        else:
        # instantiate dialog box
            info = "Unhome All Axes?"
            mess = {'NAME':'MESSAGE', 'ID':'_unhome_', 'MESSAGE':'UNHOME ALL', 'MORE':info, 'TYPE':'OKCANCEL'}
            ACTION.CALL_DIALOG(mess)

    def btn_home_clicked(self):
        axisnum = self.w.sender().property('joint')
        joint = INFO.get_jnum_from_axisnum(axisnum)
        if STATUS.is_joint_homed(joint) == True:
            ACTION.SET_MACHINE_UNHOMED(joint)
        else:
            ACTION.SET_MACHINE_HOMING(joint)

    # override frame
    def slow_button_clicked(self, state):
        # Z/X FAST-SLOW buttons are wired to this slot via the .ui; the Y
        # button (built in _add_y_jog_slider) calls _apply_slow_fast directly.
        self._apply_slow_fast(self.w.sender(), state)

    # SLOW: divide the slider's speed + range by slow_jog_factor (e.g. 5000 ->
    # 500) and use the slow page-step; FAST: multiply back and use the fast
    # page-step. Steps default to 100 (fast) / 10 (slow) — used by Z and X —
    # but a button may override them via 'fast_step'/'slow_step' properties
    # (Y uses 1000 / 100).
    def _apply_slow_fast(self, btn, state):
        if btn is None:
            return
        slider = btn.property('slider')
        if not slider:
            return
        w = self.w[slider]
        _fast = btn.property('fast_step')
        _slow = btn.property('slow_step')
        fast_step = int(_fast) if _fast is not None else 100
        slow_step = int(_slow) if _slow is not None else 10
        current = w.value()
        maxv = w.maximum()
        if state:
            btn.setText("SLOW")
            w.setMaximum(int(maxv / self.slow_jog_factor))
            w.setValue(int(current / self.slow_jog_factor))
            w.setPageStep(slow_step)
        else:
            btn.setText("FAST")
            w.setMaximum(int(maxv * self.slow_jog_factor))
            w.setValue(int(current * self.slow_jog_factor))
            w.setPageStep(fast_step)

    def slider_maxv_changed(self, value):
        maxpc = (float(value) / self.max_linear_velocity) * 100
        self.w.lbl_maxv_percent.setText("{:3.0f} %".format(maxpc))

    def slider_rapid_changed(self, value):
        rapid = (float(value) / 100) * self.max_linear_velocity * self.factor
        self.w.lbl_max_rapid.setText("{:4.0f}".format(rapid))

    def btn_maxv_100_clicked(self):
        self.w.slider_maxv_ovr.setValue(self.max_linear_velocity)

    def btn_maxv_50_clicked(self):
        self.w.slider_maxv_ovr.setValue(self.max_linear_velocity / 2)

    # file tab
    def btn_gcode_edit_clicked(self, state):
        if not STATUS.is_on_and_idle():
            return
        if state:
            self.w.filemanager.hide()
            self.w.gcode_editor.show()
            self.w.gcode_editor.editMode()
        else:
            self.w.filemanager.show()
            self.w.gcode_editor.hide()
            self.w.gcode_editor.readOnlyMode()

    def btn_load_file_clicked(self):
        if self.w.btn_gcode_edit.isChecked(): return
        fname = self.w.filemanager.getCurrentSelected()
        if fname[1] is True:
            self.load_code(fname[0])

    def btn_copy_file_clicked(self):
        if self.w.btn_gcode_edit.isChecked(): return
        if self.w.sender() == self.w.btn_copy_right:
            source = self.w.filemanager_usb.getCurrentSelected()
            target = self.w.filemanager.getCurrentSelected()
        elif self.w.sender() == self.w.btn_copy_left:
            source = self.w.filemanager.getCurrentSelected()
            target = self.w.filemanager_usb.getCurrentSelected()
        else:
            return
        if source[1] is False:
            self.add_status("Specified source is not a file", CRITICAL)
            return
        self.source_file = source[0]
        if target[1] is True:
            self.destination_file = os.path.join(os.path.dirname(target[0]), os.path.basename(source[0]))
        else:
            self.destination_file = os.path.join(target[0], os.path.basename(source[0]))
        if os.path.isfile(self.destination_file):
            info = "{} already exists in destination directory".format(self.destination_file)
            mess = {'NAME':'MESSAGE', 'ICON':'WARNING', 'ID':'_overwrite_', 'MESSAGE':'OVERWRITE FILE?', 'MORE':info, 'TYPE':'YESNO','NONBLOCKING':True}
            ACTION.CALL_DIALOG(mess)
        else:
            self.do_file_copy()

    # tool tab
    def btn_m61_clicked(self):
        checked = self.w.tooloffsetview.get_checked_list()
        if len(checked) > 1:
            self.add_status("Select only 1 tool to load", CRITICAL)
        elif checked:
            self.add_status("Loaded tool {}".format(checked[0]))
            ACTION.CALL_MDI("M61 Q{} G43".format(checked[0]))
        else:
            self.add_status("No tool selected", WARNING)

    # status tab
    def btn_clear_status_clicked(self):
        STATUS.emit('update-machine-log', None, 'DELETE')

    def btn_save_status_clicked(self):
        text = self.w.machinelog.toPlainText()
        filename = self.w.lbl_clock.text()
        filename = 'status_' + filename.replace(' ','_') + '.txt'
        self.add_status("Saving Status file to {}".format(filename))
        with open(filename, 'w') as f:
            f.write(text)

    def btn_dimensions_clicked(self, state):
        self.w.gcodegraphics.show_extents_option = state
        self.w.gcodegraphics.clear_live_plotter()
        
    # camview tab
    def cam_zoom_changed(self, value):
        self.w.camview.scale = float(value) / 10

    def cam_dia_changed(self, value):
        self.w.camview.diameter = value

    def cam_rot_changed(self, value):
        self.w.camview.rotation = float(value) / 10

    # scaling of the camera image for size aspect corrections
    # set from preference file
    def cam_xscale_changed(self, value):
        self.w.camview.scaleX  = float(value/100)
    def cam_xscale_percent(self):
        return self.w.camview.scaleX * 100
    def cam_yscale_changed(self, value):
        self.w.camview.scaleY  = float(value/100)
    def cam_yscale_percent(self):
        return self.w.camview.scaleY * 100

    # settings tab

    def chk_override_limits_checked(self, state):
        # only toggle override if it's not in synch with the button
        if state and not STATUS.is_limits_override_set():
            self.add_status("Override limits set", WARNING)
            ACTION.TOGGLE_LIMITS_OVERRIDE()
        elif not state and STATUS.is_limits_override_set():
            error = ACTION.TOGGLE_LIMITS_OVERRIDE()
            # if override can't be released set the check button to reflect this
            if error == False:
                self.w.chk_override_limits.blockSignals(True)
                self.w.chk_override_limits.setChecked(True)
                self.w.chk_override_limits.blockSignals(False)
            else:
                self.add_status("Override limits not set")

    def chk_run_from_line_changed(self, state):
        if not state:
            self.w.btn_cycle_start.setText('RUN')

    def chk_alpha_mode_changed(self, state):
        self.w.gcodegraphics.set_alpha_mode(state)

    def chk_inhibit_selection_changed(self, state):
        self.w.gcodegraphics.set_inhibit_selection(state)

    def chk_use_camera_changed(self, state):
        if not hasattr(self.w, 'btn_ref_camera'):
            return
        self.w.btn_ref_camera.setEnabled(state)
        if state :
            self.w.btn_camera.show()
        else:
            self.w.btn_camera.hide()

    def chk_use_sensor_changed(self, state):
        if not hasattr(self.w, 'btn_tool_sensor'):
            return
        self.w.btn_tool_sensor.setEnabled(state)

    def chk_use_touchplate_changed(self, state):
        if not hasattr(self.w, 'btn_touchplate'):
            return
        self.w.btn_touchplate.setEnabled(state)

    def chk_use_virtual_changed(self, state):
        codestring = "CALCULATOR" if state else "ENTRY"
        for i in ("x", "y", "z", "4", "5"):
            self.w["axistoolbutton_" + i].set_dialog_code(codestring)
        if self.probe:
            self.probe.dialog_code = codestring
        if not state:
            self.w.stackedWidget_dro.setCurrentIndex(0)

    # show ngcgui info tab (in the stackedWidget) if ngcgui utilites
    # tab is selected
    def tab_utilities_changed(self, num):
        if num == 2:
            self.w.stackedWidget.setCurrentIndex(PAGE_NGCGUI)
        else:
            self.w.stackedWidget.setCurrentIndex(PAGE_GCODE)

    def btn_gripper_clicked(self):
        AUX_PRGM.load_gcode_ripper()

    def btn_about_clicked(self):
        self.add_status("QtDragon_hd Version {} on Linuxcnc {} ".format(
            VERSION, STATUS.get_linuxcnc_version()), CRITICAL)
        info = ACTION.GET_ABOUT_INFO()
        self.w.aboutDialog_.showdialog()

    def btn_gcode_zoomin_clicked(self):
        self.w.gcode_viewer.editor.zoomIn()
    def btn_gcode_zoomout_clicked(self):
        self.w.gcode_viewer.editor.zoomOut()

    def btn_spindle_z_up_clicked(self):
        fval = int(self.w.lineEdit_eoffset_count.text())
        if INFO.MACHINE_IS_METRIC:
            fval += 5
        else:
            fval += 1
        self.w.lineEdit_eoffset_count.setText(str(fval))
        if self.h['spindle-lift-on'] == True:
            self.h['eoffset-spindle-count'] = int(fval)

    def btn_spindle_z_down_clicked(self):
        fval = int(self.w.lineEdit_eoffset_count.text())
        if INFO.MACHINE_IS_METRIC:
            fval -= 5
        else:
            fval -= 1
        if fval <0: fval = 0
        self.w.lineEdit_eoffset_count.setText(str(fval))
        if self.h['spindle-lift-on'] == True:
            self.h['eoffset-spindle-count'] = int(fval)

    def btn_pause_clicked(self):
        pass

    #####################
    # GENERAL FUNCTIONS #
    #####################
    def load_code(self, fname):
        if fname is None: return
        filename, file_extension = os.path.splitext(fname)

        # loading ngc then HTML/PDF

        if not file_extension in (".html", '.pdf'):
            if not (INFO.program_extension_valid(fname)):
                self.add_status("Unknown or invalid filename extension {}".format(file_extension), WARNING)
                return
            self.w.cmb_gcode_history.addItem(fname)
            self.w.cmb_gcode_history.setCurrentIndex(self.w.cmb_gcode_history.count() - 1)
            self.w.cmb_gcode_history.setToolTip(fname)
            # Remember the user's original path before LinuxCNC's [FILTER] rewrites
            # it to /tmp/emcflt-* (which gets deleted on shutdown — breaks auto-resume).
            self._original_loaded_file = fname
            ACTION.OPEN_PROGRAM(fname)
            self.add_status("Loaded program file : {}".format(fname))
            self.w.stackedWidget_mainTab.setCurrentIndex(TAB_MAIN)
            self.w.filemanager.recordBookKeeping()

            # adjust ending to check for related HTML setup files
            fname = filename+'.html'
            try:
                if os.path.exists(fname):
                    self.w.web_view.load(QtCore.QUrl.fromLocalFile(fname))
                    self.add_status("Loaded HTML file : {}".format(fname))
                else:
                    self.w.web_view.setHtml(self.html)
            except Exception as e:
                self.add_status("Can not Load HTML file {} :()".format(fname,e))
            # look for PDF setup files
            fname = filename+'.pdf'
            if os.path.exists(fname):
                self.PDFView.loadView(fname)
                self.add_status("Loaded PDF file : {}".format(fname))
            else:
                self.PDFView.loadSample('setup_tab')
            return

        # loading HTML/PDF directly

        if file_extension == ".html":
            try:
                self.w.web_view.load(QtCore.QUrl.fromLocalFile(fname))
                self.add_status("Loaded HTML file : {}".format(fname))
                self.w.stackedWidget_mainTab.setCurrentIndex(TAB_SETUP)
                self.w.stackedWidget.setCurrentIndex(0)
                self.w.tabWidget_setup.setCurrentIndex(0)
                self.w.btn_setup.setChecked(True)
            except Exception as e:
                self.add_status("Error loading HTML file {} : {}".format(fname,e))
        else:
            # load PDF into setup page
            if os.path.exists(fname):
                self.PDFView.loadView(fname)
                self.add_status("Loaded PDF file : {}".format(fname))
                self.w.stackedWidget_mainTab.setCurrentIndex(TAB_SETUP)
                self.w.stackedWidget.setCurrentIndex(0)
                self.w.tabWidget_setup.setCurrentIndex(1)
                self.w.btn_setup.setChecked(True)

    # NGCGui library overridden function
    # adds an error message to status
    def check_linuxcnc_paths_fail_override(self, fname):
        self.add_status("NGCGUI Path {} not in linuxcnc's SUBROUTINE_PATH INI entry".format(fname), CRITICAL)
        return ''

    def update_gcode_properties(self, props ):
        # substitute nice looking text:
        property_names = {
            'name': "Name:", 'size': "Size:",
    '       tools': "Tool order:", 'g0': "Rapid distance:",
            'g1': "Feed distance:", 'g': "Total distance:",
            'run': "Run time:",'machine_unit_sys':"Machine Unit System:",
            'x': "X bounds:",'x_zero_rxy':'X @ Zero Rotation:',
            'y': "Y bounds:",'y_zero_rxy':'Y @ Zero Rotation:',
            'z': "Z bounds:",'z_zero_rxy':'Z @ Zero Rotation:',
            'a': "A bounds:", 'b': "B bounds:",
            'c': "C bounds:",'toollist':'Tool Change List:',
            'gcode_units':"Gcode Units:"
        }

        smallmess = mess = ''
        if props:
            for i in props:
                smallmess += '<b>%s</b>: %s<br>' % (property_names.get(i), props[i])
                mess += '<span style=" font-size:18pt; font-weight:600; color:black;">%s </span>\
<span style=" font-size:18pt; font-weight:600; color:#aa0000;">%s</span>\
<br>'% (property_names.get(i), props[i])

        # put the details into the properties page
        self.w.textedit_properties.setText(mess)

        # Push the computed run-time estimate into the STATUS row.
        if hasattr(self.w, 'lbl_est_runtime'):
            run_val = props.get('run') if props else None
            self.w.lbl_est_runtime.setText(
                str(run_val).strip() if run_val else '--:--:--')
        return
        # pop a dialog of the properties
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(smallmess)
        msg.setWindowTitle("Gcode Properties")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.show()
        retval = msg.exec_()

    def disable_spindle_pause(self):
        self.h['eoffset-spindle-count'] = 0
        self.h['spindle-inhibit'] = False
        if self.w.btn_pause_spindle.isChecked():
            self.w.btn_pause_spindle.setChecked(False)

    def touchoff(self, selector):
        if selector == 'touchplate':
            z_offset = float(self.w.lineEdit_touch_height.text())
        elif selector == 'sensor':
            z_offset = float(self.w.lineEdit_sensor_height.text()) - float(self.w.lineEdit_work_height.text())
        else:
            self.add_alarm("Unknown touchoff routine specified")
            return
        self.add_status("Touchoff to {} started".format(selector))
        max_probe = self.w.lineEdit_max_probe.text()
        search_vel = self.w.lineEdit_search_vel.text()
        probe_vel = self.w.lineEdit_probe_vel.text()
        retract = self.w.lineEdit_retract_distance.text()
        safe_z = self.w.lineEdit_z_safe_travel.text()
        rtn = ACTION.TOUCHPLATE_TOUCHOFF(search_vel, probe_vel, max_probe, 
                z_offset, retract, safe_z, self.touchoff_return)
        if rtn == 0:
            self.add_status("Touchoff routine is already running", WARNING)

    def touchoff_return(self, data):
        self.add_status("Touchplate touchoff routine returned successfully")
        self.add_status("Touchplate returned:"+data, CRITICAL)

    def kb_jog(self, state, joint, direction, fast = False, linear = True):
        ACTION.SET_MANUAL_MODE()
        if not STATUS.is_man_mode() or not STATUS.machine_is_on():
            self.add_status('Machine must be ON and in Manual mode to jog', WARNING)
            return
        if linear:
            distance = STATUS.get_jog_increment()
            # Each axis has its own independent rate slider (joint 0->X,
            # 1->Y, 2->Z), except cartesian X in world mode, which jogs at the
            # shared linear rate (its slider is angular) — see _jog_rate_for.
            rate = self._jog_rate_for(joint)
        else:
            distance = STATUS.get_jog_increment_angular()
            rate = STATUS.get_jograte_angular()/60
        if state:
            if fast:
                rate = rate * 2
            ACTION.JOG(joint, direction, rate, distance)
        else:
            ACTION.JOG(joint, 0, 0, 0)

    def add_status(self, message, alertLevel = DEFAULT):
        if alertLevel==DEFAULT:
            self.set_style_default()
        elif alertLevel==WARNING:
            self.set_style_warning()
        else:
            self.set_style_critical()
        self.w.statusbar.setText(message)
        STATUS.emit('update-machine-log', message, 'TIME')

    def enable_auto(self, state):
        if state is True:
            self.w.btn_main.setChecked(True)
            self.w.stackedWidget_mainTab.setCurrentIndex(TAB_MAIN)
            if self.probe is not None:
                self.probe.hide()
            self.w.stackedWidget_dro.setCurrentIndex(0)

    def enable_onoff(self, state):
        if state:
            self.add_status("Machine ON")
        else:
            self.add_status("Machine OFF")
        self.w.btn_pause_spindle.setChecked(False)
        self.h['eoffset-spindle-count'] = 0
        for widget in self.onoff_list:
            if hasattr(self.w, widget):
                self.w[widget].setEnabled(state)

    def set_start_line(self, line):
        if self.w.chk_run_from_line.isChecked():
            self.start_line = line
            self.w.btn_cycle_start.setText("RUN\nLINE {}".format(self.start_line))
        else:
            self.start_line = 1

    def use_keyboard(self):
        if self.w.chk_use_keyboard.isChecked():
            return True
        else:
            self.add_status('Keyboard shortcuts are disabled')
            return False

    def do_file_copy(self):
        try:
            copyfile(self.source_file, self.destination_file)
            self.add_status("Copied file from {} to {}".format(self.source_file, self.destination_file))
        except Exception as e:
            self.add_status("Unable to copy file. %s" %e, WARNING)

    def periodic_update(self):
        # if waiting and up to speed, lower spindle
        if self._spindle_wait:
            if bool(self.h.hal.get_value('spindle.0.at-speed')):
                self.h['spindle-lift-on'] = False
                self.h['eoffset-spindle-count'] = 0
                self.add_status('Spindle lowered')
                self._spindle_wait = False

        self.update_runtimer()
        self._update_layer_from_status()

    # === CYLINDRICAL ROBOT — LAYERS box helpers ===
    # Layer = run of moves between Z-changes > 0.01. Tracked by
    # storing the 1-based ngc line number where each new layer
    # begins and bisecting against STATUS.stat.motion_line.
    _LAYER_Z_RE = re.compile(r'\bZ\s*([-+]?\d*\.?\d+)', re.IGNORECASE)
    _LAYER_Z_EPS = 0.01

    def _parse_layer_starts(self, filename):
        if not filename or not os.path.isfile(filename):
            return []
        starts = []
        prev_z = None
        try:
            with open(filename, 'r', errors='ignore') as f:
                for lineno, line in enumerate(f, 1):
                    s = line.lstrip()
                    if not s or s[0] in (';', '(', '%'):
                        continue
                    m = self._LAYER_Z_RE.search(line)
                    if not m:
                        continue
                    try:
                        z = float(m.group(1))
                    except ValueError:
                        continue
                    if prev_z is None or abs(z - prev_z) > self._LAYER_Z_EPS:
                        starts.append(lineno)
                        prev_z = z
        except OSError:
            return []
        return starts

    def _update_layer_display(self, current):
        if not hasattr(self.w, 'lbl_layers_done'):
            return
        total = self._total_layers
        cur = max(0, min(int(current), total))
        self.w.lbl_layers_done.setText(str(cur))
        self.w.lbl_layers_left.setText(str(max(0, total - cur)))

    def _update_layer_from_status(self):
        if not self._total_layers:
            return
        try:
            mline = int(STATUS.stat.motion_line)
        except (AttributeError, TypeError, ValueError):
            mline = 0
        if mline <= 0:
            # Interpreter idle: keep last shown count rather than
            # snapping to 0, except when the file just loaded
            # (handled in file_loaded which calls _update_layer_display(0)).
            return
        cur = bisect.bisect_right(self._layer_starts, mline)
        self._update_layer_display(cur)

    def update_runtimer(self):
        if not self.timer_on or STATUS.is_auto_paused():
            return

        tick = time.time()
        elapsed_time = tick - self.timer_tick
        self.run_time += elapsed_time
        self.timer_tick = tick

        hours, remainder = divmod(int(self.run_time), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.w.lbl_runtime.setText("{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds))

    def start_timer(self):
        self.run_time = 0
        self.timer_on = True
        self.timer_tick = time.time()

    def stop_timer(self):
        if self.timer_on:
            self.timer_on = False
            self.add_status("Run timer stopped at {}".format(self.w.lbl_runtime.text()))

    # web page zoom
    def zoomWeb(self):
        # webview
        try:
            f = self.w.web_view.zoomFactor() +.5
            if f > 2:f = 1
            self.w.web_view.setZoomFactor(f)
        except:
            pass

        # PDF
        try:
            f = self.PDFView.zoomFactor() +.5
            if f > 2:f = 1
            self.PDFView.setZoomFactor(f)
        except:
            pass

    # go directly the default HTML page
    def homeWeb(self):
        try:
            if os.path.exists(self.default_setup):
                self.w.web_view.load(QtCore.QUrl.fromLocalFile(self.default_setup))
            else:
                self.w.web_view.setHtml(self.html)
        except:
            pass
    # setup tab's web page back button
    def back(self):
        try:
            try:
                self.w.web_view.page().triggerAction(QWebEnginePage.Back)
            except:
                if os.path.exists(self.default_setup):
                    self.w.web_view.load(QtCore.QUrl.fromLocalFile(self.default_setup))
                else:
                    self.w.web_view.setHtml(self.html)
        except:
            pass

    # setup tab's web page forward button
    def forward(self):
        try:
            try:
                self.w.web_view.page().triggerAction(QWebEnginePage.Forward)
            except:
                self.w.web_view.load(QtCore.QUrl.fromLocalFile(self.docs))
        except:
            pass

    # setup tab's web page - enable/disable buttons
    def onLoadFinished(self):
        try:
            if self.w.web_view.history().canGoBack():
                self.backBtn.setEnabled(True)
            else:
                self.backBtn.setEnabled(False)

            if self.w.web_view.history().canGoForward():
                self.forBtn.setEnabled(True)
            else:
                self.forBtn.setEnabled(False)
        except:
            pass

    def writer(self):
        WRITER.show()

    def endcolor(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.clear_status_bar)
        self.timer.start(self.statusbar_reset_time)

    def clear_status_bar(self):
        self.set_style_default()
        self.w.statusbar.setText('')

    # change Status bar text color
    def set_style_default(self):
        self.w.statusbar.setStyleSheet(
                "background-color: rgb(252, 252, 252);color: rgb(0,0,0)")  #default white
    def set_style_warning(self):
        self.w.statusbar.setStyleSheet(
                "background-color: rgb(242, 246, 103);color: rgb(0,0,0)")  #yellow
        self.endcolor()
    def set_style_critical(self):
        self.w.statusbar.setStyleSheet(
                "background-color: rgb(255, 144, 0);color: rgb(0,0,0)")   #orange
        self.endcolor()

    def adjust_stacked_widgets(self,requestedIndex):
        IGNORE = -1
        SHOW_DRO = 0
        mode = STATUS.get_current_mode()
        if mode == STATUS.AUTO:
            seq = {TAB_MAIN: (TAB_MAIN,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_FILE: (TAB_MAIN,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_OFFSETS: (TAB_MAIN,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_TOOL: (TAB_MAIN,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_STATUS: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_PROBE: (TAB_MAIN,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_CAMVIEW: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_GCODES: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_SETUP: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_SETTINGS: (requestedIndex,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_UTILS: (TAB_MAIN,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_USER: (requestedIndex,PAGE_UNCHANGED,IGNORE,NO_MACRO),
                    TAB_PRINT_CAL: (requestedIndex,PAGE_UNCHANGED,IGNORE,NO_MACRO) }
        else:
            seq = {TAB_MAIN: (requestedIndex,PAGE_GCODE,SHOW_DRO,MACRO),
                    TAB_FILE: (requestedIndex,PAGE_GCODE,IGNORE,NO_MACRO),
                    TAB_OFFSETS: (requestedIndex,PAGE_GCODE,IGNORE,NO_MACRO),
                    TAB_TOOL: (requestedIndex,PAGE_GCODE,IGNORE,NO_MACRO),
                    TAB_STATUS: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_PROBE: (requestedIndex,PAGE_GCODE,SHOW_DRO,NO_MACRO),
                    TAB_CAMVIEW: (requestedIndex,PAGE_UNCHANGED,IGNORE,MACRO),
                    TAB_GCODES: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_SETUP: (requestedIndex,PAGE_UNCHANGED,IGNORE,NO_MACRO),
                    TAB_SETTINGS: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_UTILS: (requestedIndex,PAGE_UNCHANGED,SHOW_DRO,NO_MACRO),
                    TAB_USER: (requestedIndex,PAGE_UNCHANGED,IGNORE,MACRO),
                    TAB_PRINT_CAL: (requestedIndex,PAGE_UNCHANGED,IGNORE,MACRO) }

        rtn =  seq.get(requestedIndex)

        # if not found (None) use defaults
        if rtn is None:
            main_index = requestedIndex
            stacked_index = 0
            show_dro = 0
            show_macro = True
        else:
            main_index,stacked_index,show_dro,show_macro = rtn

        # prpbe widget in not a separate tab
        if main_index == TAB_PROBE:
            requestedIndex = TAB_MAIN
            self.probe.show()
            self.w.divider_line.show()
        elif self.probe is not None:
            self.probe.hide()
            self.w.divider_line.hide()

        # show DRO rather then keyboard.
        if show_dro > IGNORE:
            self.w.stackedWidget_dro.setCurrentIndex(0)

        # macros can only be run in manual or mdi mode
        if show_macro:
            self.w.frame_macro_buttons.show()
        else:
            self.w.frame_macro_buttons.hide()

        # show ngcgui info tab if utilities tab is selected
        # but only if the utilities tab has ngcgui selected
        if main_index == TAB_UTILS:
            if self.w.tabWidget_utilities.currentIndex() == 2:
                self.w.stackedWidget.setCurrentIndex(PAGE_NGCGUI)
            else:
                self.w.stackedWidget.setCurrentIndex(PAGE_GCODE)

        # toggle home/tool offsets buttons in DRO section
        if main_index == TAB_TOOL:
            num = 1
        else:
            num = 0
        for n,i in enumerate(INFO.AVAILABLE_AXES):
            if n >2:
                self.w['dro_button_stack_%s'%(n+1)].setCurrentIndex(num)
            else:
                self.w['dro_button_stack_%s'%i.lower()].setCurrentIndex(num)

        # adjust the stacked widget
        if stacked_index > PAGE_UNCHANGED:
            self.w.stackedWidget.setCurrentIndex(stacked_index)

        if stacked_index == TAB_FILE and self.w.btn_gcode_edit.isChecked():
            self.w.btn_gcode_edit.setChecked(False)
            self.w.btn_gcode_edit_clicked(False)

        # Set main tab to adjusted index. The original stock qtdragon had
        # a single USER button (index=TAB_USER=10) that cycled through all
        # user pages 10..N; we replaced it with dedicated buttons
        # (MACHINE CAL=10, JOINTS=11, PRINT CAL=12) and force-hid btn_user.
        # The cycle branch used to fire here on any click with index>=10,
        # which made MACHINE CAL flip between Calibrate / Joints / Print
        # Cal on each press. Direct navigation is what we want now.
        self.w.stackedWidget_mainTab.setCurrentIndex(main_index)

        # if indexes don't match then request is disallowed
        # give a warning and reset the button check
        if main_index != requestedIndex and not main_index in(TAB_CAMVIEW,TAB_GCODES,TAB_SETUP):
            self.add_status("Cannot switch pages while in AUTO mode", WARNING)
            self.w.stackedWidget_mainTab.setCurrentIndex(0)
            self.w.btn_main.setChecked(True)
    
    # calc wait time for mdi move based on dist and rapid speed, return seconds to wait
    def calc_mdi_move_wait_time(self, dest_x, dest_y, wait_buffer_secs=1):
        move_speed = (STATUS.stat.rapidrate * STATUS.get_max_velocity()) / 60
        pos_cur,pos_rel,dtg, = STATUS.get_position()
        move_dist = sqrt((dest_x - pos_cur[0]) ** 2 + (dest_y - pos_cur[1]) ** 2)
        return ceil(move_dist / move_speed) + wait_buffer_secs

    # set axis 4/5 dro widgets to the proper axis
    # TODO do this with all the axes for more flexibility
    def initiate_axis_dro(self, num, axis):
        self.w['label_axis_{}'.format(num)].setText(axis)
        self.w['label_home_{}'.format(num)].setText('HOME {}'.format(axis))
        jnum = INFO.GET_JOG_FROM_NAME.get(axis)
        # DRO uses axis index
        index = "XYZABCUVW".index(axis)
        self.w['dro_axis_{}'.format(num)].setProperty('Qjoint_number',index)
        self.w['action_zero_{}'.format(num)].setProperty('axis_letter',axis)
        self.w['axistoolbutton_{}'.format(num)].setProperty('axis_letter',axis)
        self.w['axistoolbutton_{}'.format(num)].setText('REF {}'.format(axis))
        self.w['btn_home_{}'.format(num)].setProperty('axis_letter',axis)
        self.w['btn_home_{}'.format(num)].setProperty('joint_number_status',jnum)
        self.w['btn_home_{}'.format(num)].setProperty('joint',index)
        self.w['offsettoolbutton_{}'.format(num)].setProperty('axis_letter',axis)
        self.w['plus_jogbutton_{}'.format(num)].setProperty('axis_letter',axis)
        self.w['plus_jogbutton_{}'.format(num)].setProperty('joint_number',jnum)
        self.w['hal_led_home_{}'.format(num)].setProperty('joint_number_status',jnum)
        a = axis.lower()
        try:
            icn = QtGui.QIcon(QtGui.QPixmap(':/buttons/images/{}_plus_jog_button.png'.format(a)))
            if icn.isNull(): raise Exception
            self.w['plus_jogbutton_{}'.format(num)].setIcon(icn)
        except Exception as e:
            self.w['plus_jogbutton_{}'.format(num)].setProperty('text','{}+'.format(axis))
        self.w['minus_jogbutton_{}'.format(num)].setProperty('axis_letter',axis)
        self.w['minus_jogbutton_{}'.format(num)].setProperty('joint_number',jnum)
        try:
            icn = QtGui.QIcon(QtGui.QPixmap(':/buttons/images/{}_minus_jog_button.png'.format(a)))
            if icn.isNull(): raise Exception
            self.w['minus_jogbutton_{}'.format(num)].setIcon(icn)
        except Exception as e:
            self.w['minus_jogbutton_{}'.format(num)].setProperty('text','{}-'.format(axis))

    #####################
    # KEY BINDING CALLS #
    #####################

    def on_keycall_ESTOP(self,event,state,shift,cntrl):
        if state:
            ACTION.SET_ESTOP_STATE(True)

    def on_keycall_POWER(self,event,state,shift,cntrl):
        if state:
            ACTION.SET_MACHINE_STATE(False)

    def on_keycall_ABORT(self,event,state,shift,cntrl):
        if state:
            ACTION.ABORT()

    def on_keycall_HOME(self,event,state,shift,cntrl):
        if state and not STATUS.is_all_homed() and self.use_keyboard():
            ACTION.SET_MACHINE_HOMING(-1)

    def on_keycall_PAUSE(self,event,state,shift,cntrl):
        print(state,STATUS.is_auto_mode(),self.use_keyboard())
        if state and STATUS.is_auto_mode() and self.use_keyboard():
            ACTION.PAUSE()

    def on_keycall_jograte(self,event,state,shift,cntrl,value):
        if state and self.use_keyboard():
            if value == 1:
                ACTION.SET_JOG_RATE_FASTER()
            else:
                ACTION.SET_JOG_RATE_SLOWER()

    # CYLINDRICAL ROBOT — '$' (Shift+4) toggles WORLD/JOINT jog mode,
    # matching classic AXIS GUI behaviour.
    def on_keycall_jog_mode_toggle(self,event,state,shift,cntrl):
        if state and self.use_keyboard():
            ACTION.TOGGLE_TELEOP_MODE()

    def on_keycall_angular_jograte(self,event,state,shift,cntrl,value):
        if state and self.use_keyboard():
            if value == 1:
                ACTION.SET_JOG_RATE_ANGULAR_FASTER()
            else:
                ACTION.SET_JOG_RATE_ANGULAR_SLOWER()

    def on_keycall_XPOS(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 0, 1, shift)

    def on_keycall_XNEG(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 0, -1, shift)

    def on_keycall_YPOS(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 1, 1, shift)

    def on_keycall_YNEG(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 1, -1, shift)

    def on_keycall_ZPOS(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 2, 1, shift)

    def on_keycall_ZNEG(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 2, -1, shift)
    
    def on_keycall_APOS(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 3, 1, shift, False)

    def on_keycall_ANEG(self,event,state,shift,cntrl):
        if self.use_keyboard():
            self.kb_jog(state, 3, -1, shift, False)

    def on_keycall_F4(self,event,state,shift,cntrl):
        if state:
            mess = {'NAME':'CALCULATOR', 'TITLE':'Calculator', 'ID':'_calculator_'}
            ACTION.CALL_DIALOG(mess)

    def on_keycall_F12(self,event,state,shift,cntrl):
        if state:
            self.styleeditor.load_dialog()

    ##############################
    # required class boiler code #
    ##############################
    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
    return [HandlerClass(halcomp, widgets, paths)]
