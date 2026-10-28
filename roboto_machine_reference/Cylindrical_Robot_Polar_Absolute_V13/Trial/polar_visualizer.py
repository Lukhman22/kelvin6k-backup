#!/usr/bin/env python3
"""
Polar Robot Visualizer - CARTESIAN DISPLAY
Shows the actual Cartesian world coordinates from LinuxCNC
Trails show straight lines as commanded

The polarkins in LinuxCNC converts X,Y to angle,radius internally.
This visualizer displays the commanded X,Y positions directly.
"""

import hal
import math
import os
import tkinter as tk
from tkinter import ttk, filedialog

class CartesianVisualizer:
    def __init__(self):
        # HAL component - get world position (Cartesian)
        self.h = hal.component("polar_viz")
        self.h.newpin("x-pos", hal.HAL_FLOAT, hal.HAL_IN)  # Cartesian X
        self.h.newpin("y-pos", hal.HAL_FLOAT, hal.HAL_IN)  # Cartesian Y
        self.h.newpin("angle", hal.HAL_FLOAT, hal.HAL_IN)  # For display only
        self.h.newpin("radius", hal.HAL_FLOAT, hal.HAL_IN) # For display only
        self.h.newpin("homed", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("enabled", hal.HAL_BIT, hal.HAL_IN)
        self.h.ready()
        
        # Work envelope (polar limits)
        self.min_radius = 650
        self.max_radius = 2600
        self.tool_offset = -235.0  # Perpendicular tool offset (mm) - negative = right/clockwise
        
        # View state
        self.zoom = 0.15
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start = None
        
        # Trail
        self.trail = []
        self.show_trail = True
        self.max_trail = 2000
        
        # Position tracking
        self.last_x = None
        self.last_y = None
        
        # Home
        self.home_x = 0
        self.home_y = 0
        self.is_homed = False
        
        # Create window
        self.root = tk.Tk()
        self.root.title("Polar Robot Visualizer - Cartesian Display")
        self.root.geometry("1000x750")
        self.root.configure(bg='#1a1a2e')
        # QtDragon embeds its own polar view, so the Tk window is redundant
        # there. Hide it when POLAR_VIZ_HIDDEN=1 (set by start_linuxcnc_qtdragon.sh).
        if os.environ.get("POLAR_VIZ_HIDDEN") == "1":
            self.root.withdraw()
        
        self.create_gui()
        self.running = True
        self.update_display()
    
    def create_gui(self):
        """Create GUI"""
        # Top bar
        top_frame = tk.Frame(self.root, bg='#1a1a2e')
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(top_frame, text="● NOT HOMED", fg='#ff4444',
                                      bg='#1a1a2e', font=('Arial', 12, 'bold'))
        self.status_label.pack(side=tk.LEFT)
        
        self.zoom_label = tk.Label(top_frame, text="Zoom: 100%", fg='#888',
                                    bg='#1a1a2e', font=('Arial', 10))
        self.zoom_label.pack(side=tk.RIGHT, padx=10)
        
        self.trail_count = tk.Label(top_frame, text="Trail: 0 points", fg='#888',
                                     bg='#1a1a2e', font=('Arial', 10))
        self.trail_count.pack(side=tk.RIGHT, padx=10)
        
        # Canvas
        canvas_frame = tk.Frame(self.root, bg='#1a1a2e')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#0a0a15', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Mouse bindings
        self.canvas.bind('<MouseWheel>', self.on_scroll)
        self.canvas.bind('<Button-4>', self.on_scroll_up)
        self.canvas.bind('<Button-5>', self.on_scroll_down)
        self.canvas.bind('<ButtonPress-1>', self.on_drag_start)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_drag_end)
        self.canvas.bind('<Double-Button-1>', self.fit_to_envelope)
        
        # Info panel
        info_frame = tk.Frame(self.root, bg='#1a1a2e')
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Cartesian coords (PRIMARY)
        cart_frame = tk.Frame(info_frame, bg='#1a1a2e')
        cart_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(cart_frame, text="CARTESIAN (World)", fg='#00ff88', bg='#1a1a2e',
                 font=('Arial', 11, 'bold')).pack(anchor='w')
        self.x_label = tk.Label(cart_frame, text="X: 0.00 mm", fg='#fff',
                                 bg='#1a1a2e', font=('Arial', 12, 'bold'))
        self.x_label.pack(anchor='w')
        self.y_label = tk.Label(cart_frame, text="Y: 0.00 mm", fg='#fff',
                                 bg='#1a1a2e', font=('Arial', 12, 'bold'))
        self.y_label.pack(anchor='w')
        
        # Polar coords (for reference)
        polar_frame = tk.Frame(info_frame, bg='#1a1a2e')
        polar_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(polar_frame, text="POLAR (Joints)", fg='#888', bg='#1a1a2e',
                 font=('Arial', 10)).pack(anchor='w')
        self.angle_label = tk.Label(polar_frame, text="θ: 0.00°", fg='#aaa',
                                     bg='#1a1a2e', font=('Arial', 10))
        self.angle_label.pack(anchor='w')
        self.radius_label = tk.Label(polar_frame, text="r: 0.00 mm", fg='#aaa',
                                      bg='#1a1a2e', font=('Arial', 10))
        self.radius_label.pack(anchor='w')
        
        # Controls
        btn_frame = tk.Frame(info_frame, bg='#1a1a2e')
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(btn_frame, text="Fit", command=self.fit_to_envelope,
                  bg='#333', fg='#fff', width=6).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear_trail,
                  bg='#333', fg='#fff', width=6).pack(side=tk.LEFT, padx=2)
        
        self.trail_btn = tk.Button(btn_frame, text="Trail: ON", command=self.toggle_trail,
                                    bg='#006600', fg='#fff', width=8)
        self.trail_btn.pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="Export", command=self.export_gcode,
                  bg='#444', fg='#fff', width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="+", command=lambda: self.zoom_by(1.2),
                  bg='#333', fg='#fff', width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="-", command=lambda: self.zoom_by(0.8),
                  bg='#333', fg='#fff', width=3).pack(side=tk.LEFT, padx=2)
        
        self.root.after(100, self.fit_to_envelope)
    
    def get_center(self):
        return self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
    
    def world_to_canvas(self, wx, wy):
        """World (Cartesian mm) to canvas pixels"""
        cx, cy = self.get_center()
        x = cx + (wx * self.zoom) + self.pan_x
        y = cy - (wy * self.zoom) + self.pan_y
        return x, y
    
    def on_scroll(self, event):
        if event.delta > 0:
            self.zoom_at(event.x, event.y, 1.1)
        else:
            self.zoom_at(event.x, event.y, 0.9)
    
    def on_scroll_up(self, event):
        self.zoom_at(event.x, event.y, 1.1)
    
    def on_scroll_down(self, event):
        self.zoom_at(event.x, event.y, 0.9)
    
    def zoom_at(self, x, y, factor):
        cx, cy = self.get_center()
        self.pan_x = (self.pan_x - (x - cx)) * factor + (x - cx)
        self.pan_y = (self.pan_y - (y - cy)) * factor + (y - cy)
        self.zoom *= factor
        self.zoom = max(0.01, min(1.0, self.zoom))
        self.zoom_label.config(text=f"Zoom: {self.zoom*700:.0f}%")
    
    def zoom_by(self, factor):
        self.zoom *= factor
        self.zoom = max(0.01, min(1.0, self.zoom))
        self.zoom_label.config(text=f"Zoom: {self.zoom*700:.0f}%")
    
    def on_drag_start(self, event):
        self.drag_start = (event.x, event.y)
    
    def on_drag(self, event):
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start = (event.x, event.y)
    
    def on_drag_end(self, event):
        self.drag_start = None
    
    def fit_to_envelope(self, event=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return
        size = min(w, h) * 0.85
        self.zoom = size / (2 * self.max_radius)
        self.pan_x = 0
        self.pan_y = 0
        self.zoom_label.config(text=f"Zoom: {self.zoom*700:.0f}%")
    
    def clear_trail(self):
        self.trail = []
        self.last_x = None
        self.last_y = None
    
    def toggle_trail(self):
        self.show_trail = not self.show_trail
        if self.show_trail:
            self.trail_btn.config(text="Trail: ON", bg='#006600')
        else:
            self.trail_btn.config(text="Trail: OFF", bg='#660000')
    
    def export_gcode(self):
        """Export trail as G-code"""
        if len(self.trail) < 2:
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".ngc",
            filetypes=[("G-code", "*.ngc"), ("All files", "*.*")],
            initialdir="/home/kelvin6k/linuxcnc/nc_files"
        )
        if not filename:
            return
        
        with open(filename, 'w') as f:
            f.write("; Exported from Polar Robot Visualizer\n")
            f.write("G21 ; mm\n")
            f.write("G90 ; absolute\n")
            f.write(f"G0 X{self.trail[0][0]:.3f} Y{self.trail[0][1]:.3f}\n")
            for x, y in self.trail[1:]:
                f.write(f"G1 X{x:.3f} Y{y:.3f} F1000\n")
            f.write("M2\n")
        
        print(f"Exported {len(self.trail)} points to {filename}")
    
    def draw_grid(self):
        self.canvas.delete("grid")
        
        # Cartesian grid
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        # Grid spacing based on zoom
        grid_mm = 500
        if self.zoom > 0.1:
            grid_mm = 200
        if self.zoom > 0.2:
            grid_mm = 100
        
        # Vertical lines
        for x in range(-5000, 5001, grid_mm):
            cx, _ = self.world_to_canvas(x, 0)
            if 0 <= cx <= w:
                color = '#333' if x != 0 else '#555'
                self.canvas.create_line(cx, 0, cx, h, fill=color, tags='grid')
        
        # Horizontal lines
        for y in range(-5000, 5001, grid_mm):
            _, cy = self.world_to_canvas(0, y)
            if 0 <= cy <= h:
                color = '#333' if y != 0 else '#555'
                self.canvas.create_line(0, cy, w, cy, fill=color, tags='grid')
        
        # Work envelope circles
        for r in [self.min_radius, self.max_radius]:
            points = []
            for a in range(0, 361, 5):
                rad = math.radians(a)
                wx = r * math.cos(rad)
                wy = r * math.sin(rad)
                cx, cy = self.world_to_canvas(wx, wy)
                points.extend([cx, cy])
            if len(points) >= 4:
                color = '#662200' if r == self.min_radius else '#006622'
                self.canvas.create_line(points, fill=color, width=2, 
                                        smooth=True, tags='grid')
        
        # Axis labels
        ox, oy = self.world_to_canvas(0, 0)
        self.canvas.create_text(w-20, oy, text="X+", fill='#666', font=('Arial', 10), tags='grid')
        self.canvas.create_text(ox+15, 15, text="Y+", fill='#666', font=('Arial', 10), tags='grid')
    
    def update_display(self):
        if not self.running:
            return
        
        try:
            # Get Cartesian position from LinuxCNC (what polarkins commanded)
            cmd_x = self.h['x-pos']
            cmd_y = self.h['y-pos']
            
            # Get joint values (angle, radius) from commanded position
            # polarkins converts: angle = atan2(y, x), radius = sqrt(x² + y²)
            angle_deg = math.degrees(math.atan2(cmd_y, cmd_x))
            radius_mm = math.sqrt(cmd_x**2 + cmd_y**2)
            
            # Calculate actual TOOL position with offset
            # Tool is perpendicular to radius arm
            # X_tool = r·cos(θ) - offset·sin(θ)
            # Y_tool = r·sin(θ) + offset·cos(θ)
            angle_rad = math.radians(angle_deg)
            cart_x = radius_mm * math.cos(angle_rad) - self.tool_offset * math.sin(angle_rad)
            cart_y = radius_mm * math.sin(angle_rad) + self.tool_offset * math.cos(angle_rad)
            
            homed = self.h['homed']
            
            if homed and not self.is_homed:
                self.is_homed = True
                # Force trail start at physical home (650, 0)
                # This ensures the visualizer treats this as the absolute start point
                self.trail = [(650.0, 0.0)]
                self.last_x = 650.0
                self.last_y = 0.0
                self.trail_count.config(text="Trail: Reset to (650, 0)")
            elif not homed:
                self.is_homed = False
            
            # Update labels
            self.x_label.config(text=f"X: {cart_x:.1f} mm")
            self.y_label.config(text=f"Y: {cart_y:.1f} mm")
            self.angle_label.config(text=f"θ: {angle_deg:.2f}°", fg='#00ffff') # Cyan
            self.radius_label.config(text=f"r: {radius_mm:.1f} mm", fg='#00ffff') # Cyan
            
            if self.is_homed:
                self.status_label.config(text="● HOMED", fg='#00ff88')
            else:
                self.status_label.config(text="● NOT HOMED", fg='#ff4444')
            
            # Add to trail (only if moved)
            if self.show_trail:
                if self.last_x is None or abs(cart_x - self.last_x) > 0.5 or abs(cart_y - self.last_y) > 0.5:
                    self.trail.append((cart_x, cart_y))
                    # No limit - trails persist until cleared manually
                    self.last_x = cart_x
                    self.last_y = cart_y
            
            self.trail_count.config(text=f"Trail: {len(self.trail)} points")
            
            # Redraw
            self.canvas.delete("all")
            self.draw_grid()
            
            # Draw trail (Cyan lines)
            if len(self.trail) > 1:
                # Optimized drawing: create one line object for the whole trail if possible, or segments
                # Tkinter canvas line accepts multiple points: x1,y1, x2,y2, ...
                points = []
                for p in self.trail:
                    x, y = self.world_to_canvas(*p)
                    points.extend([x, y])
                
                if len(points) >= 4:
                    self.canvas.create_line(points, fill='#00ffff', width=2) # Cyan color
            
            # Draw home marker at (650, 0)
            hx, hy = self.world_to_canvas(650, 0)
            self.canvas.create_oval(hx-6, hy-6, hx+6, hy+6,
                                    outline='#ffff00', width=2, tags='grid')
            
            # Draw tool position
            cx, cy = self.world_to_canvas(cart_x, cart_y)
            self.canvas.create_oval(cx-10, cy-10, cx+10, cy+10,
                                    fill='#00ffff', outline='white', width=2) # Cyan fill
            
        except Exception as e:
            print(f"Error: {e}")
        
        self.root.after(30, self.update_display)
    
    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

if __name__ == '__main__':
    viz = CartesianVisualizer()
    viz.run()
