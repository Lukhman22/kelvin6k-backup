#!/usr/bin/env python3
"""
Advanced CAD Path Generator for Polar Robot
Fusion 360-inspired interface with professional CAD features

Features:
- Sketch tools: Line, Polyline, Arc, Circle, Rectangle, Polygon, Spline
- Transform tools: Move, Copy, Mirror, Rotate, Scale, Array
- Modify tools: Offset, Fillet, Trim, Extend
- Text generation with multiple fonts
- Layer management
- Undo/Redo support
- Precise coordinate input
- Constraint system
"""

import math
import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

# Single-stroke font (uppercase, numbers, symbols)
FONT_DATA = {
    'A': [[(0,0),(0.5,1),(1,0)],[(0.2,0.4),(0.8,0.4)]],
    'B': [[(0,0),(0,1),(0.7,1),(0.9,0.8),(0.7,0.5),(0,0.5)],[(0.7,0.5),(0.9,0.2),(0.7,0),(0,0)]],
    'C': [[(1,0.8),(0.5,1),(0,0.7),(0,0.3),(0.5,0),(1,0.2)]],
    'D': [[(0,0),(0,1),(0.6,1),(1,0.6),(1,0.4),(0.6,0),(0,0)]],
    'E': [[(1,0),(0,0),(0,1),(1,1)],[(0,0.5),(0.7,0.5)]],
    'F': [[(0,0),(0,1),(1,1)],[(0,0.5),(0.7,0.5)]],
    'G': [[(1,0.8),(0.5,1),(0,0.6),(0,0.4),(0.5,0),(1,0.4),(1,0.5),(0.5,0.5)]],
    'H': [[(0,0),(0,1)],[(1,0),(1,1)],[(0,0.5),(1,0.5)]],
    'I': [[(0.3,0),(0.7,0)],[(0.5,0),(0.5,1)],[(0.3,1),(0.7,1)]],
    'J': [[(0,0.2),(0.3,0),(0.6,0),(0.6,1)]],
    'K': [[(0,0),(0,1)],[(1,1),(0,0.5),(1,0)]],
    'L': [[(0,1),(0,0),(1,0)]],
    'M': [[(0,0),(0,1),(0.5,0.5),(1,1),(1,0)]],
    'N': [[(0,0),(0,1),(1,0),(1,1)]],
    'O': [[(0.5,0),(0,0.3),(0,0.7),(0.5,1),(1,0.7),(1,0.3),(0.5,0)]],
    'P': [[(0,0),(0,1),(0.7,1),(1,0.8),(0.7,0.5),(0,0.5)]],
    'Q': [[(0.5,0),(0,0.3),(0,0.7),(0.5,1),(1,0.7),(1,0.3),(0.5,0)],[(0.6,0.3),(1,-0.1)]],
    'R': [[(0,0),(0,1),(0.7,1),(1,0.8),(0.7,0.5),(0,0.5)],[(0.5,0.5),(1,0)]],
    'S': [[(1,0.8),(0.5,1),(0,0.7),(0.5,0.5),(1,0.3),(0.5,0),(0,0.2)]],
    'T': [[(0,1),(1,1)],[(0.5,1),(0.5,0)]],
    'U': [[(0,1),(0,0.2),(0.5,0),(1,0.2),(1,1)]],
    'V': [[(0,1),(0.5,0),(1,1)]],
    'W': [[(0,1),(0.25,0),(0.5,0.5),(0.75,0),(1,1)]],
    'X': [[(0,0),(1,1)],[(0,1),(1,0)]],
    'Y': [[(0,1),(0.5,0.5),(1,1)],[(0.5,0.5),(0.5,0)]],
    'Z': [[(0,1),(1,1),(0,0),(1,0)]],
    '0': [[(0.5,0),(0,0.3),(0,0.7),(0.5,1),(1,0.7),(1,0.3),(0.5,0)]],
    '1': [[(0.3,0.8),(0.5,1),(0.5,0)]],
    '2': [[(0,0.7),(0.5,1),(1,0.7),(0,0),(1,0)]],
    '3': [[(0,0.8),(0.5,1),(1,0.7),(0.5,0.5),(1,0.3),(0.5,0),(0,0.2)]],
    '4': [[(0,1),(0,0.5),(1,0.5)],[(0.7,1),(0.7,0)]],
    '5': [[(1,1),(0,1),(0,0.5),(1,0.3),(0.5,0),(0,0.2)]],
    '6': [[(1,0.8),(0.5,1),(0,0.5),(0.5,0),(1,0.3),(0.5,0.5),(0,0.5)]],
    '7': [[(0,1),(1,1),(0.3,0)]],
    '8': [[(0.5,0.5),(0,0.7),(0.5,1),(1,0.7),(0.5,0.5),(0,0.3),(0.5,0),(1,0.3),(0.5,0.5)]],
    '9': [[(0,0.2),(0.5,0),(1,0.5),(0.5,1),(0,0.7),(0.5,0.5),(1,0.5)]],
    ' ': [],'.': [[(0.4,0.1),(0.6,0.1)]],',': [[(0.5,0.1),(0.4,0)]],
    '-': [[(0.2,0.5),(0.8,0.5)]],'+': [[(0.2,0.5),(0.8,0.5)],[(0.5,0.2),(0.5,0.8)]],
    '!': [[(0.5,0.3),(0.5,1)],[(0.5,0.1),(0.5,0)]],
}

class Shape:
    """Base shape class"""
    def __init__(self, shape_type, points, color='#00ff88'):
        self.type = shape_type
        self.points = points
        self.color = color
        self.selected = False
        self.layer = 0
    
    def get_bounds(self):
        if not self.points:
            return None
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def translate(self, dx, dy):
        self.points = [(x+dx, y+dy) for x, y in self.points]
    
    def rotate(self, cx, cy, angle_deg):
        angle = math.radians(angle_deg)
        new_points = []
        for x, y in self.points:
            dx, dy = x - cx, y - cy
            nx = cx + dx * math.cos(angle) - dy * math.sin(angle)
            ny = cy + dx * math.sin(angle) + dy * math.cos(angle)
            new_points.append((nx, ny))
        self.points = new_points
    
    def scale(self, cx, cy, factor):
        new_points = []
        for x, y in self.points:
            nx = cx + (x - cx) * factor
            ny = cy + (y - cy) * factor
            new_points.append((nx, ny))
        self.points = new_points
    
    def mirror(self, axis, value):
        if axis == 'x':
            self.points = [(2*value - x, y) for x, y in self.points]
        else:
            self.points = [(x, 2*value - y) for x, y in self.points]
    
    def copy(self):
        return Shape(self.type, self.points.copy(), self.color)

class ArcShape(Shape):
    """Arc shape with center, radius, angles"""
    def __init__(self, center, radius, start_angle, end_angle, cw=False, color='#00ff88'):
        self.center = center
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.cw = cw
        
        # Generate points for display
        points = self._generate_points()
        super().__init__('arc', points, color)
        self.arc_data = {
            'center': center,
            'radius': radius,
            'start_angle': start_angle,
            'end_angle': end_angle,
            'cw': cw
        }
    
    def _generate_points(self):
        points = []
        steps = 36
        angle_range = self.end_angle - self.start_angle
        for i in range(steps + 1):
            angle = self.start_angle + angle_range * i / steps
            x = self.center[0] + self.radius * math.cos(angle)
            y = self.center[1] + self.radius * math.sin(angle)
            points.append((x, y))
        return points


class CADApplication:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Polar CAD - Professional Path Generator")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e2e')
        
        # Work envelope
        self.min_radius = 650
        self.max_radius = 2600
        
        # View
        self.zoom = 0.25
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start = None
        
        # Grid
        self.grid_size = 50
        self.snap = True
        self.show_grid = True
        
        # Shapes and state
        self.shapes = []
        self.selected = []
        self.undo_stack = []
        self.redo_stack = []
        
        # Current tool
        self.tool = 'select'
        self.temp_points = []
        self.preview_shape = None
        
        # Colors
        self.current_color = '#00ff88'
        self.colors = ['#00ff88', '#ff4444', '#4444ff', '#ffff00', '#ff00ff', '#00ffff', '#ffffff']
        
        # Tool buttons dict
        self.tool_btns = {}
        
        self.create_ui()
        self.bind_shortcuts()
        self.root.after(100, self.fit_view)
    
    def create_ui(self):
        """Create Fusion 360-like UI"""
        
        # Menu bar
        menubar = tk.Menu(self.root, bg='#2d2d3d', fg='white')
        
        file_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d3d', fg='white')
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Export G-code", command=self.export_gcode, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d3d', fg='white')
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete", command=self.delete_selected, accelerator="Del")
        edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        self.root.config(menu=menubar)
        
        # Main toolbar
        toolbar = tk.Frame(self.root, bg='#2d2d3d', height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Tool groups
        self.create_tool_group(toolbar, "SKETCH", [
            ("Select", 'select', '⬚'),
            ("Line", 'line', '╱'),
            ("Polyline", 'polyline', '⌇'),
            ("Arc 3pt", 'arc3', '⌒'),
            ("Circle", 'circle', '○'),
            ("Rectangle", 'rect', '▭'),
            ("Polygon", 'polygon', '⬡'),
        ])
        
        tk.Frame(toolbar, width=2, bg='#444').pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.create_tool_group(toolbar, "MODIFY", [
            ("Move", 'move', '↔'),
            ("Copy", 'copy', '⧉'),
            ("Mirror", 'mirror', '⎅'),
            ("Rotate", 'rotate', '↻'),
            ("Offset", 'offset', '◯'),
            ("Array", 'array', '⊞'),
        ])
        
        tk.Frame(toolbar, width=2, bg='#444').pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.create_tool_group(toolbar, "CREATE", [
            ("Text", 'text', 'A'),
            ("Spiral", 'spiral', '🌀'),
            ("Star", 'star', '★'),
        ])
        
        # Right side - view controls
        view_frame = tk.Frame(toolbar, bg='#2d2d3d')
        view_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(view_frame, text="Fit", command=self.fit_view,
                  bg='#404050', fg='white', relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        
        self.snap_var = tk.BooleanVar(value=True)
        tk.Checkbutton(view_frame, text="Snap", variable=self.snap_var,
                       bg='#2d2d3d', fg='white', selectcolor='#404050',
                       command=lambda: setattr(self, 'snap', self.snap_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Main container
        main = tk.Frame(self.root, bg='#1e1e2e')
        main.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Properties
        left_panel = tk.Frame(main, bg='#252535', width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        self.create_properties_panel(left_panel)
        
        # Canvas
        canvas_frame = tk.Frame(main, bg='#1a1a2a')
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#1a1a2a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Button-2>', self.on_pan_start)
        self.canvas.bind('<B2-Motion>', self.on_pan)
        self.canvas.bind('<Button-3>', self.on_right_click)
        self.canvas.bind('<MouseWheel>', self.on_scroll)
        self.canvas.bind('<Button-4>', lambda e: self.zoom_at(e.x, e.y, 1.1))
        self.canvas.bind('<Button-5>', lambda e: self.zoom_at(e.x, e.y, 0.9))
        self.canvas.bind('<Motion>', self.on_motion)
        self.canvas.bind('<Shift-Button-1>', self.on_pan_start)
        self.canvas.bind('<Shift-B1-Motion>', self.on_pan)
        self.canvas.bind('<Configure>', lambda e: self.redraw())
        
        # Right panel - G-code preview
        right_panel = tk.Frame(main, bg='#252535', width=280)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)
        
        tk.Label(right_panel, text="G-CODE", bg='#252535', fg='#00ff88',
                 font=('Arial', 10, 'bold')).pack(anchor='w', padx=10, pady=5)
        
        self.gcode_text = tk.Text(right_panel, bg='#1a1a2a', fg='#00ff00',
                                   font=('Consolas', 9), wrap=tk.NONE)
        self.gcode_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar
        status = tk.Frame(self.root, bg='#2d2d3d', height=25)
        status.pack(fill=tk.X)
        status.pack_propagate(False)
        
        self.status_label = tk.Label(status, text="Ready", bg='#2d2d3d', fg='#888')
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.coord_label = tk.Label(status, text="X: 0  Y: 0", bg='#2d2d3d', fg='#888')
        self.coord_label.pack(side=tk.RIGHT, padx=10)
    
    def create_tool_group(self, parent, label, tools):
        """Create a group of tool buttons"""
        frame = tk.Frame(parent, bg='#2d2d3d')
        frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame, text=label, bg='#2d2d3d', fg='#666',
                 font=('Arial', 8)).pack(side=tk.TOP)
        
        btn_frame = tk.Frame(frame, bg='#2d2d3d')
        btn_frame.pack(side=tk.TOP)
        
        for name, tool_id, icon in tools:
            btn = tk.Button(btn_frame, text=f"{icon}", width=3,
                           command=lambda t=tool_id: self.set_tool(t),
                           bg='#404050', fg='white', relief=tk.FLAT,
                           font=('Arial', 12))
            btn.pack(side=tk.LEFT, padx=1, pady=2)
            self.tool_btns[tool_id] = btn
            
            # Tooltip
            btn.bind('<Enter>', lambda e, n=name: self.status_label.config(text=n))
            btn.bind('<Leave>', lambda e: self.status_label.config(text="Ready"))
    
    def create_properties_panel(self, parent):
        """Create properties panel"""
        # Input coordinates
        tk.Label(parent, text="COORDINATES", bg='#252535', fg='#00ff88',
                 font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10,5))
        
        coord_frame = tk.Frame(parent, bg='#252535')
        coord_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(coord_frame, text="X:", bg='#252535', fg='#aaa').grid(row=0, column=0)
        self.input_x = tk.Entry(coord_frame, width=10, bg='#1a1a2a', fg='white')
        self.input_x.grid(row=0, column=1, padx=2)
        
        tk.Label(coord_frame, text="Y:", bg='#252535', fg='#aaa').grid(row=0, column=2)
        self.input_y = tk.Entry(coord_frame, width=10, bg='#1a1a2a', fg='white')
        self.input_y.grid(row=0, column=3, padx=2)
        
        tk.Button(coord_frame, text="Add", command=self.add_point_input,
                  bg='#404050', fg='white').grid(row=0, column=4, padx=5)
        
        # Parameters
        tk.Label(parent, text="PARAMETERS", bg='#252535', fg='#00ff88',
                 font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(15,5))
        
        param_frame = tk.Frame(parent, bg='#252535')
        param_frame.pack(fill=tk.X, padx=10)
        
        params = [("Radius", "500"), ("Sides", "6"), ("Offset", "50"), 
                  ("Angle", "0"), ("Copies", "4")]
        self.params = {}
        
        for i, (name, default) in enumerate(params):
            tk.Label(param_frame, text=f"{name}:", bg='#252535', fg='#aaa').grid(row=i, column=0, sticky='w')
            entry = tk.Entry(param_frame, width=12, bg='#1a1a2a', fg='white')
            entry.insert(0, default)
            entry.grid(row=i, column=1, pady=1)
            self.params[name.lower()] = entry
        
        # Quick shapes
        tk.Label(parent, text="QUICK CREATE", bg='#252535', fg='#00ff88',
                 font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(15,5))
        
        quick_frame = tk.Frame(parent, bg='#252535')
        quick_frame.pack(fill=tk.X, padx=10)
        
        shapes = [
            ("Circle", self.quick_circle),
            ("Square", self.quick_square),
            ("Polygon", self.quick_polygon),
            ("Spiral", self.quick_spiral),
            ("Star", self.quick_star),
            ("Grid", self.quick_grid),
        ]
        
        for i, (name, cmd) in enumerate(shapes):
            row, col = i // 2, i % 2
            tk.Button(quick_frame, text=name, command=cmd,
                      bg='#404050', fg='white', width=10).grid(row=row, column=col, padx=2, pady=2)
        
        # Text input
        tk.Label(parent, text="TEXT", bg='#252535', fg='#00ff88',
                 font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(15,5))
        
        text_frame = tk.Frame(parent, bg='#252535')
        text_frame.pack(fill=tk.X, padx=10)
        
        self.text_input = tk.Entry(text_frame, width=25, bg='#1a1a2a', fg='white')
        self.text_input.insert(0, "HELLO")
        self.text_input.pack(fill=tk.X)
        
        text_params = tk.Frame(parent, bg='#252535')
        text_params.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(text_params, text="Size:", bg='#252535', fg='#aaa').grid(row=0, column=0)
        self.text_size = tk.Entry(text_params, width=6, bg='#1a1a2a', fg='white')
        self.text_size.insert(0, "150")
        self.text_size.grid(row=0, column=1)
        
        tk.Button(text_params, text="Create Text", command=self.create_text,
                  bg='#006600', fg='white').grid(row=0, column=2, padx=10)
        
        # Color picker
        tk.Label(parent, text="COLOR", bg='#252535', fg='#00ff88',
                 font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(15,5))
        
        color_frame = tk.Frame(parent, bg='#252535')
        color_frame.pack(fill=tk.X, padx=10)
        
        for i, color in enumerate(self.colors):
            btn = tk.Button(color_frame, width=2, bg=color,
                           command=lambda c=color: self.set_color(c))
            btn.pack(side=tk.LEFT, padx=1)
        
        # Actions
        tk.Label(parent, text="ACTIONS", bg='#252535', fg='#00ff88',
                 font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(20,5))
        
        tk.Button(parent, text="Delete Selected", command=self.delete_selected,
                  bg='#660000', fg='white', width=20).pack(padx=10, pady=2)
        tk.Button(parent, text="Clear All", command=self.clear_all,
                  bg='#664400', fg='white', width=20).pack(padx=10, pady=2)
        tk.Button(parent, text="Export G-code", command=self.export_gcode,
                  bg='#006600', fg='white', width=20).pack(padx=10, pady=5)
    
    def bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Delete>', lambda e: self.delete_selected())
        self.root.bind('<Escape>', lambda e: self.cancel_operation())
        self.root.bind('<Control-e>', lambda e: self.export_gcode())
        self.root.bind('<Control-n>', lambda e: self.new_file())
    
    def set_tool(self, tool):
        self.tool = tool
        self.temp_points = []
        self.preview_shape = None
        
        for t, btn in self.tool_btns.items():
            btn.config(bg='#006600' if t == tool else '#404050')
        
        self.status_label.config(text=f"Tool: {tool.title()}")
    
    def set_color(self, color):
        self.current_color = color
        for shape in self.selected:
            shape.color = color
        self.redraw()
    
    def snap_point(self, x, y):
        if self.snap:
            x = round(x / self.grid_size) * self.grid_size
            y = round(y / self.grid_size) * self.grid_size
        return x, y
    
    def world_to_canvas(self, x, y):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx = w/2 + x * self.zoom + self.pan_x
        cy = h/2 - y * self.zoom + self.pan_y
        return cx, cy
    
    def canvas_to_world(self, cx, cy):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        x = (cx - w/2 - self.pan_x) / self.zoom
        y = -(cy - h/2 - self.pan_y) / self.zoom
        return x, y
    
    def fit_view(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10:
            return
        self.zoom = min(w, h) * 0.4 / self.max_radius
        self.pan_x = 0
        self.pan_y = 0
        self.redraw()
    
    def zoom_at(self, x, y, factor):
        wx, wy = self.canvas_to_world(x, y)
        self.zoom *= factor
        self.zoom = max(0.01, min(3.0, self.zoom))
        ncx, ncy = self.world_to_canvas(wx, wy)
        self.pan_x += x - ncx
        self.pan_y += y - ncy
        self.redraw()
    
    def on_scroll(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_at(event.x, event.y, factor)
    
    def on_pan_start(self, event):
        self.drag_start = (event.x, event.y, self.pan_x, self.pan_y)
    
    def on_pan(self, event):
        if self.drag_start:
            self.pan_x = self.drag_start[2] + (event.x - self.drag_start[0])
            self.pan_y = self.drag_start[3] + (event.y - self.drag_start[1])
            self.redraw()
    
    def on_motion(self, event):
        x, y = self.canvas_to_world(event.x, event.y)
        x, y = self.snap_point(x, y)
        r = math.sqrt(x*x + y*y)
        self.coord_label.config(text=f"X: {x:.0f}  Y: {y:.0f}  r: {r:.0f}")
    
    def on_click(self, event):
        x, y = self.canvas_to_world(event.x, event.y)
        x, y = self.snap_point(x, y)
        
        if self.tool == 'select':
            self.handle_select(x, y, event)
        elif self.tool in ['line', 'polyline', 'arc3', 'circle', 'rect', 'polygon']:
            self.handle_draw(x, y)
        elif self.tool in ['move', 'copy', 'rotate', 'mirror', 'offset', 'array']:
            self.handle_transform(x, y)
    
    def on_drag(self, event):
        if self.tool == 'select' and self.drag_start:
            # Box selection
            pass
    
    def on_release(self, event):
        self.drag_start = None
    
    def on_right_click(self, event):
        """Finish current shape"""
        if self.tool == 'polyline' and len(self.temp_points) >= 2:
            self.save_undo()
            shape = Shape('polyline', self.temp_points.copy(), self.current_color)
            self.shapes.append(shape)
            self.temp_points = []
            self.update_gcode()
            self.redraw()
    
    def handle_select(self, x, y, event):
        """Handle selection"""
        clicked = None
        min_dist = 30 / self.zoom
        
        for shape in self.shapes:
            for px, py in shape.points:
                if math.sqrt((x-px)**2 + (y-py)**2) < min_dist:
                    clicked = shape
                    break
        
        if clicked:
            if event.state & 0x1:  # Shift
                if clicked in self.selected:
                    self.selected.remove(clicked)
                else:
                    self.selected.append(clicked)
            else:
                self.selected = [clicked]
        else:
            self.selected = []
        
        for s in self.shapes:
            s.selected = s in self.selected
        
        self.redraw()
    
    def handle_draw(self, x, y):
        """Handle drawing tools"""
        self.temp_points.append((x, y))
        
        if self.tool == 'line' and len(self.temp_points) == 2:
            self.save_undo()
            shape = Shape('line', self.temp_points.copy(), self.current_color)
            self.shapes.append(shape)
            self.temp_points = []
            self.update_gcode()
        
        elif self.tool == 'circle' and len(self.temp_points) == 2:
            self.save_undo()
            cx, cy = self.temp_points[0]
            px, py = self.temp_points[1]
            r = math.sqrt((px-cx)**2 + (py-cy)**2)
            
            points = []
            for i in range(37):
                angle = 2 * math.pi * i / 36
                points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            
            shape = Shape('polyline', points, self.current_color)
            self.shapes.append(shape)
            self.temp_points = []
            self.update_gcode()
        
        elif self.tool == 'rect' and len(self.temp_points) == 2:
            self.save_undo()
            x1, y1 = self.temp_points[0]
            x2, y2 = self.temp_points[1]
            points = [(x1,y1), (x2,y1), (x2,y2), (x1,y2), (x1,y1)]
            shape = Shape('polyline', points, self.current_color)
            self.shapes.append(shape)
            self.temp_points = []
            self.update_gcode()
        
        elif self.tool == 'arc3' and len(self.temp_points) == 3:
            self.save_undo()
            # 3-point arc
            p1, p2, p3 = self.temp_points
            arc_points = self.calc_3point_arc(p1, p2, p3)
            shape = Shape('arc', arc_points, self.current_color)
            self.shapes.append(shape)
            self.temp_points = []
            self.update_gcode()
        
        elif self.tool == 'polygon' and len(self.temp_points) == 2:
            self.save_undo()
            sides = int(self.params['sides'].get())
            cx, cy = self.temp_points[0]
            px, py = self.temp_points[1]
            r = math.sqrt((px-cx)**2 + (py-cy)**2)
            
            points = []
            for i in range(sides + 1):
                angle = 2 * math.pi * i / sides - math.pi/2
                points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            
            shape = Shape('polyline', points, self.current_color)
            self.shapes.append(shape)
            self.temp_points = []
            self.update_gcode()
        
        self.redraw()
    
    def calc_3point_arc(self, p1, p2, p3):
        """Calculate arc through 3 points"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        
        # Calculate center using perpendicular bisectors
        d = 2 * (x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
        if abs(d) < 0.001:
            return [p1, p2, p3]  # Collinear
        
        ux = ((x1*x1+y1*y1)*(y2-y3) + (x2*x2+y2*y2)*(y3-y1) + (x3*x3+y3*y3)*(y1-y2)) / d
        uy = ((x1*x1+y1*y1)*(x3-x2) + (x2*x2+y2*y2)*(x1-x3) + (x3*x3+y3*y3)*(x2-x1)) / d
        
        r = math.sqrt((x1-ux)**2 + (y1-uy)**2)
        
        # Generate arc points
        a1 = math.atan2(y1-uy, x1-ux)
        a2 = math.atan2(y2-uy, x2-ux)
        a3 = math.atan2(y3-uy, x3-ux)
        
        # Determine direction
        points = []
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            angle = a1 + t * (a3 - a1)  # Simplified
            points.append((ux + r * math.cos(angle), uy + r * math.sin(angle)))
        
        return points
    
    def handle_transform(self, x, y):
        """Handle transform tools"""
        if not self.selected:
            return
        
        if self.tool == 'move':
            if len(self.temp_points) == 0:
                self.temp_points.append((x, y))
            else:
                self.save_undo()
                dx = x - self.temp_points[0][0]
                dy = y - self.temp_points[0][1]
                for shape in self.selected:
                    shape.translate(dx, dy)
                self.temp_points = []
                self.update_gcode()
                self.redraw()
        
        elif self.tool == 'copy':
            if len(self.temp_points) == 0:
                self.temp_points.append((x, y))
            else:
                self.save_undo()
                dx = x - self.temp_points[0][0]
                dy = y - self.temp_points[0][1]
                for shape in self.selected:
                    new_shape = shape.copy()
                    new_shape.translate(dx, dy)
                    self.shapes.append(new_shape)
                self.temp_points = []
                self.update_gcode()
                self.redraw()
        
        elif self.tool == 'mirror':
            self.save_undo()
            for shape in self.selected:
                new_shape = shape.copy()
                new_shape.mirror('x', x)
                self.shapes.append(new_shape)
            self.update_gcode()
            self.redraw()
        
        elif self.tool == 'rotate':
            if len(self.temp_points) == 0:
                self.temp_points.append((x, y))  # Center
            else:
                self.save_undo()
                angle = float(self.params['angle'].get())
                cx, cy = self.temp_points[0]
                for shape in self.selected:
                    shape.rotate(cx, cy, angle)
                self.temp_points = []
                self.update_gcode()
                self.redraw()
        
        elif self.tool == 'array':
            self.save_undo()
            copies = int(self.params['copies'].get())
            angle_step = 360 / copies
            
            for shape in self.selected:
                bounds = shape.get_bounds()
                if not bounds:
                    continue
                cx = (bounds[0] + bounds[2]) / 2
                cy = (bounds[1] + bounds[3]) / 2
                
                for i in range(1, copies):
                    new_shape = shape.copy()
                    new_shape.rotate(0, 0, angle_step * i)
                    self.shapes.append(new_shape)
            
            self.update_gcode()
            self.redraw()
    
    def save_undo(self):
        self.undo_stack.append([s.copy() for s in self.shapes])
        self.redo_stack = []
    
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append([s.copy() for s in self.shapes])
            self.shapes = self.undo_stack.pop()
            self.selected = []
            self.update_gcode()
            self.redraw()
    
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append([s.copy() for s in self.shapes])
            self.shapes = self.redo_stack.pop()
            self.selected = []
            self.update_gcode()
            self.redraw()
    
    def cancel_operation(self):
        self.temp_points = []
        self.set_tool('select')
        self.redraw()
    
    def select_all(self):
        self.selected = self.shapes.copy()
        for s in self.shapes:
            s.selected = True
        self.redraw()
    
    def delete_selected(self):
        if self.selected:
            self.save_undo()
            for s in self.selected:
                if s in self.shapes:
                    self.shapes.remove(s)
            self.selected = []
            self.update_gcode()
            self.redraw()
    
    def clear_all(self):
        if self.shapes and messagebox.askyesno("Confirm", "Clear all?"):
            self.save_undo()
            self.shapes = []
            self.selected = []
            self.update_gcode()
            self.redraw()
    
    def new_file(self):
        self.shapes = []
        self.selected = []
        self.undo_stack = []
        self.redo_stack = []
        self.update_gcode()
        self.redraw()
    
    def add_point_input(self):
        try:
            x = float(self.input_x.get())
            y = float(self.input_y.get())
            self.temp_points.append((x, y))
            self.redraw()
        except:
            pass
    
    # Quick shape methods
    def quick_circle(self):
        r = float(self.params['radius'].get())
        points = [(r*math.cos(i*2*math.pi/36), r*math.sin(i*2*math.pi/36)) for i in range(37)]
        self.save_undo()
        self.shapes.append(Shape('polyline', points, self.current_color))
        self.update_gcode()
        self.redraw()
    
    def quick_square(self):
        r = float(self.params['radius'].get())
        points = [(-r,-r), (r,-r), (r,r), (-r,r), (-r,-r)]
        self.save_undo()
        self.shapes.append(Shape('polyline', points, self.current_color))
        self.update_gcode()
        self.redraw()
    
    def quick_polygon(self):
        r = float(self.params['radius'].get())
        sides = int(self.params['sides'].get())
        points = [(r*math.cos(i*2*math.pi/sides - math.pi/2), 
                   r*math.sin(i*2*math.pi/sides - math.pi/2)) for i in range(sides+1)]
        self.save_undo()
        self.shapes.append(Shape('polyline', points, self.current_color))
        self.update_gcode()
        self.redraw()
    
    def quick_spiral(self):
        r = float(self.params['radius'].get())
        points = []
        for i in range(181):
            t = i / 180
            angle = 6 * math.pi * t
            points.append((r*t*math.cos(angle), r*t*math.sin(angle)))
        self.save_undo()
        self.shapes.append(Shape('polyline', points, self.current_color))
        self.update_gcode()
        self.redraw()
    
    def quick_star(self):
        r = float(self.params['radius'].get())
        sides = int(self.params['sides'].get())
        points = []
        for i in range(sides * 2 + 1):
            angle = i * math.pi / sides - math.pi/2
            rad = r if i % 2 == 0 else r * 0.4
            points.append((rad*math.cos(angle), rad*math.sin(angle)))
        self.save_undo()
        self.shapes.append(Shape('polyline', points, self.current_color))
        self.update_gcode()
        self.redraw()
    
    def quick_grid(self):
        r = float(self.params['radius'].get())
        points = []
        step = r / 5
        for row in range(6):
            y = -r/2 + row * step
            if row % 2 == 0:
                points.extend([(-r/2, y), (r/2, y)])
            else:
                points.extend([(r/2, y), (-r/2, y)])
        self.save_undo()
        self.shapes.append(Shape('polyline', points, self.current_color))
        self.update_gcode()
        self.redraw()
    
    def create_text(self):
        text = self.text_input.get().upper()
        size = float(self.text_size.get())
        x_offset = 0
        
        self.save_undo()
        
        for char in text:
            if char in FONT_DATA:
                for stroke in FONT_DATA[char]:
                    points = [(x_offset + p[0]*size*0.6, p[1]*size) for p in stroke]
                    if len(points) >= 2:
                        self.shapes.append(Shape('polyline', points, self.current_color))
            x_offset += size * 0.7
        
        self.update_gcode()
        self.redraw()
    
    def redraw(self):
        self.canvas.delete("all")
        
        # Grid
        if self.show_grid:
            self.draw_grid()
        
        # Work envelope
        self.draw_envelope()
        
        # Shapes
        for shape in self.shapes:
            self.draw_shape(shape)
        
        # Temp points
        for x, y in self.temp_points:
            cx, cy = self.world_to_canvas(x, y)
            self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill='#ff8800')
        
        # Temp line preview
        if len(self.temp_points) >= 2:
            points = []
            for x, y in self.temp_points:
                cx, cy = self.world_to_canvas(x, y)
                points.extend([cx, cy])
            self.canvas.create_line(points, fill='#ff8800', width=2, dash=(4,4))
    
    def draw_grid(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        x1, y1 = self.canvas_to_world(0, h)
        x2, y2 = self.canvas_to_world(w, 0)
        
        gs = self.grid_size
        for x in range(int(x1/gs)*gs, int(x2/gs)*gs + gs, gs):
            cx, _ = self.world_to_canvas(x, 0)
            color = '#2a2a3a' if x != 0 else '#3a3a4a'
            self.canvas.create_line(cx, 0, cx, h, fill=color)
        
        for y in range(int(y1/gs)*gs, int(y2/gs)*gs + gs, gs):
            _, cy = self.world_to_canvas(0, y)
            color = '#2a2a3a' if y != 0 else '#3a3a4a'
            self.canvas.create_line(0, cy, w, cy, fill=color)
    
    def draw_envelope(self):
        for r in [self.min_radius, self.max_radius]:
            points = []
            for i in range(73):
                angle = 2 * math.pi * i / 72
                cx, cy = self.world_to_canvas(r*math.cos(angle), r*math.sin(angle))
                points.extend([cx, cy])
            color = '#4a2a00' if r == self.min_radius else '#004a2a'
            self.canvas.create_line(points, fill=color, width=2, smooth=True)
    
    def draw_shape(self, shape):
        if len(shape.points) < 2:
            return
        
        points = []
        for x, y in shape.points:
            cx, cy = self.world_to_canvas(x, y)
            points.extend([cx, cy])
        
        color = '#ffff00' if shape.selected else shape.color
        width = 3 if shape.selected else 2
        
        self.canvas.create_line(points, fill=color, width=width)
        
        # Vertices
        if shape.selected:
            for x, y in shape.points:
                cx, cy = self.world_to_canvas(x, y)
                self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=color)
    
    def update_gcode(self):
        gcode = self.generate_gcode()
        self.gcode_text.delete('1.0', tk.END)
        self.gcode_text.insert('1.0', gcode)
    
    def generate_gcode(self):
        lines = ["(Polar CAD Generator)", "G21 G90", ""]
        
        for shape in self.shapes:
            if len(shape.points) < 2:
                continue
            
            x, y = shape.points[0]
            lines.append(f"G0 X{x:.3f} Y{y:.3f}")
            
            for x, y in shape.points[1:]:
                lines.append(f"G1 X{x:.3f} Y{y:.3f} F1000")
            
            lines.append("")
        
        lines.append("M2")
        return '\n'.join(lines)
    
    def export_gcode(self):
        if not self.shapes:
            messagebox.showwarning("Warning", "No shapes to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".ngc",
            filetypes=[("G-code", "*.ngc")],
            initialdir="/home/kelvin6k/linuxcnc/nc_files"
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.generate_gcode())
            messagebox.showinfo("Success", f"Exported to:\n{filename}")
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = CADApplication()
    app.run()
