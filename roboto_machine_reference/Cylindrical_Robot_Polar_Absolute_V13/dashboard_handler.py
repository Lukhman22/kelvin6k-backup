#!/usr/bin/env python3
import hal
import hal_glib
import math
import cairo
import sys
import os

# Try to import GTK and GObject
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GObject, Gdk, GLib
    HAS_GTK3 = True
except ImportError:
    HAS_GTK3 = False
    print("GTK3 not found, falling back (unlikely for Python3)")

# LinuxCNC module
import linuxcnc

class HandlerClass:
    def __init__(self, halcomp, builder, useropts):
        self.halcomp = halcomp
        self.builder = builder
        
        # Load polar visualizer logic
        try:
            self.viz_widget = self.builder.get_object("polar_viz")
            if not self.viz_widget:
                print("Error: 'polar_viz' widget not found in Glade file")
                return

            # Connect signals
            # GTK3 uses 'draw' instead of 'expose-event'
            self.viz_widget.connect("draw", self._on_draw)
            
            # Events
            self.viz_widget.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                                       Gdk.EventMask.BUTTON_RELEASE_MASK | 
                                       Gdk.EventMask.POINTER_MOTION_MASK | 
                                       Gdk.EventMask.SCROLL_MASK)
            
            self.viz_widget.connect("button-press-event", self._on_button_press)
            self.viz_widget.connect("button-release-event", self._on_button_release)
            self.viz_widget.connect("motion-notify-event", self._on_motion)
            self.viz_widget.connect("scroll-event", self._on_scroll)
            
        except Exception as e:
            print(f"Error initializing visualizer widget: {e}")

        # Parameters
        self.min_radius = 650
        self.max_radius = 2600
        self.tool_offset = -235.0
        
        # View State
        self.zoom = 0.10
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start = None
        
        # Create HAL pins
        self.halcomp.newpin("viz-x", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("viz-y", hal.HAL_FLOAT, hal.HAL_IN)
        self.halcomp.newpin("viz-homed", hal.HAL_BIT, hal.HAL_IN)

        # Timer for redraw
        GLib.timeout_add(100, self._update_viz)
        
        # Trail
        self.trail = []
        self.last_pos = None

    def _update_viz(self):
        if hasattr(self, 'viz_widget') and self.viz_widget:
            self.viz_widget.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        
        # Background
        cr.set_source_rgb(0.05, 0.05, 0.1) # Dark blue/black
        cr.rectangle(0, 0, w, h)
        cr.fill()
        
        # Transform for zoom/pan
        cx, cy = w/2, h/2
        cr.translate(cx + self.pan_x, cy + self.pan_y)
        cr.scale(self.zoom, -self.zoom) # Flip Y for standard Cartesian
        
        # Draw Stuff
        self._draw_grid(cr)
        self._draw_trail(cr)
        self._draw_tool(cr)
        
        return False

    def _draw_grid(self, cr):
        cr.set_line_width(2.0 / self.zoom)
        
        # Min Radius
        cr.set_source_rgba(0.4, 0.1, 0.0, 0.5)
        cr.arc(0, 0, self.min_radius, 0, 2*math.pi)
        cr.stroke()
        
        # Max Radius
        cr.set_source_rgba(0.0, 0.4, 0.1, 0.5)
        cr.arc(0, 0, self.max_radius, 0, 2*math.pi)
        cr.stroke()
        
        # Crosshairs
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        cr.move_to(-3000, 0)
        cr.line_to(3000, 0)
        cr.move_to(0, -3000)
        cr.line_to(0, 3000)
        cr.stroke()
        
        # Home marker
        cr.set_source_rgb(1, 1, 0)
        cr.arc(650, 0, 10/self.zoom, 0, 2*math.pi)
        cr.stroke()

    def _draw_trail(self, cr):
        if len(self.trail) < 2: return
        
        cr.set_source_rgb(0, 1, 1) # Cyan
        cr.set_line_width(1.5 / self.zoom)
        
        cr.move_to(*self.trail[0])
        for p in self.trail[1:]:
            cr.line_to(*p)
        cr.stroke()

    def _draw_tool(self, cr):
        x = self.halcomp["viz-x"]
        y = self.halcomp["viz-y"]
        homed = self.halcomp["viz-homed"]
        
        if self.last_pos:
            dist = math.hypot(x - self.last_pos[0], y - self.last_pos[1])
            if dist > 1.0:
                self.trail.append((x, y))
                if len(self.trail) > 2000: self.trail.pop(0)
                self.last_pos = (x, y)
        else:
            self.last_pos = (x, y)
            
        if homed and len(self.trail) == 0:
             self.trail.append((x, y))

        cr.set_source_rgb(0, 1, 0) if homed else cr.set_source_rgb(1, 0, 0)
        cr.arc(x, y, 15/self.zoom, 0, 2*math.pi)
        cr.fill()
        
        # Arm vector
        cr.set_source_rgba(1, 1, 1, 0.2)
        cr.set_line_width(1.0 / self.zoom)
        cr.move_to(0, 0)
        cr.line_to(x, y)
        cr.stroke()

    # --- Interaction ---
    def _on_scroll(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            factor = 1.1
        else:
            factor = 0.9
        
        self.zoom *= factor
        self.zoom = max(0.01, min(1.0, self.zoom))
        widget.queue_draw()
        return True

    def _on_button_press(self, widget, event):
        if event.button == 1:
            self.drag_start = (event.x, event.y)
        return True

    def _on_button_release(self, widget, event):
        self.drag_start = None
        return True

    def _on_motion(self, widget, event):
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start = (event.x, event.y)
            widget.queue_draw()
        return True

def get_handlers(halcomp, builder, useropts):
    return [HandlerClass(halcomp, builder, useropts)]
