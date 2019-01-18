from matplotlib.path import Path
from matplotlib.patches import PathPatch
from qtpy.QtCore import QObject, Signal, Qt
from qtpy.QtGui import QCursor


class VerticalMarker(QObject):

    x_moved = Signal(float)

    def __init__(self, canvas, color, x, y0=None, y1=None, line_width=1.0, picker_width=5):
        super(VerticalMarker, self).__init__()
        self.ax = canvas.figure.get_axes()[0]
        self.x = x
        self.y0 = y0
        self.y1 = y1
        y0, y1 = self._get_y0_y1()
        path = Path([(x, y0), (x, y1)], [Path.MOVETO, Path.LINETO])
        self.patch = PathPatch(path, facecolor='None', edgecolor=color, picker=picker_width,
                               linewidth=line_width, animated=True)
        self.ax.add_patch(self.patch)
        self.is_moving = False

    def _get_y0_y1(self):
        if self.y0 is None or self.y1 is None:
            y0, y1 = self.ax.get_ylim()
        if self.y0 is not None:
            y0 = self.y0
        if self.y1 is not None:
            y1 = self.y1
        return y0, y1

    def remove(self):
        self.patch.remove()

    def redraw(self):
        y0, y1 = self._get_y0_y1()
        vertices = self.patch.get_path().vertices
        vertices[0] = self.x, y0
        vertices[1] = self.x, y1
        self.ax.draw_artist(self.patch)

    def get_x_in_pixels(self):
        x_pixels, _ = self.patch.get_transform().transform((self.x, 0))
        return x_pixels

    def is_above(self, x, y):
        x_pixels, y_pixels = self.patch.get_transform().transform((x, y))
        if self.y0 is not None and y < self.y0:
            return False
        if self.y1 is not None and y > self.y1:
            return False
        return abs(self.get_x_in_pixels() - x_pixels) < 3

    def mouse_move_start(self, x, y):
        self.is_moving = self.is_above(x, y)

    def mouse_move_stop(self):
        self.is_moving = False

    def mouse_move(self, x, y=None):
        if self.is_moving and x is not None:
            self.x = x
            self.x_moved.emit(x)
            return True
        return False

    def get_cursor_at_y(self, y):
        return QCursor(Qt.SizeHorCursor)

    def override_cursor(self, x, y):
        if self.y0 is not None and y < self.y0:
            return None
        if self.y1 is not None and y > self.y1:
            return None
        if self.is_moving or self.is_above(x, y):
            return self.get_cursor_at_y(y)
        return None


class CentreMarker(VerticalMarker):

    selected_color = 'red'
    deselected_color = 'grey'

    def __init__(self, canvas, x, y0, y1):
        VerticalMarker.__init__(self, canvas, self.selected_color, x, y0, y1)
        self.is_at_top = False

    def _is_at_top(self, y):
        _, y1_pixels = self.patch.get_transform().transform((0, self.y1))
        _, y_pixels = self.patch.get_transform().transform((0, y))
        return abs(y1_pixels - y_pixels) < 10

    def get_cursor_at_y(self, y):
        is_at_top = self.is_at_top if self.is_moving else self._is_at_top(y)
        return QCursor(Qt.SizeAllCursor) if is_at_top else VerticalMarker.get_cursor_at_y(self, y)

    def mouse_move_start(self, x, y):
        VerticalMarker.mouse_move_start(self, x, y)
        self.is_at_top = self._is_at_top(y)

    def mouse_move_stop(self):
        VerticalMarker.mouse_move_stop(self)
        self.is_at_top = False

    def mouse_move(self, x, y=None):
        if not self.is_moving:
            return False
        if self.is_at_top:
            self.y1 = y
        self.x = x
        return True

    def height(self):
        return self.y1 - self.y0

    def set_height(self, height):
        self.y1 = self.y0 + height

    def select(self):
        self.patch.set_edgecolor(self.selected_color)

    def deselect(self):
        self.patch.set_edgecolor(self.deselected_color)


class PeakMarker(QObject):

    peak_moved = Signal(int, float, float)

    def __init__(self, canvas, peak_id, x, y_top, y_bottom):
        super(PeakMarker, self).__init__()
        self.peak_id = peak_id
        self.centre_marker = CentreMarker(canvas, x, y0=y_bottom, y1=y_top)
        self.is_selected = True

    def redraw(self):
        self.centre_marker.redraw()

    def override_cursor(self, x, y):
        return self.centre_marker.override_cursor(x, y)

    def mouse_move_start(self, x, y):
        self.centre_marker.mouse_move_start(x, y)

    def mouse_move_stop(self):
        self.centre_marker.mouse_move_stop()

    def mouse_move(self, x, y):
        moved = self.centre_marker.mouse_move(x, y)
        if moved:
            self.peak_moved.emit(self.peak_id, x, self.centre_marker.height())
            return True
        return False

    @property
    def is_moving(self):
        return self.centre_marker.is_moving

    def centre(self):
        return self.centre_marker.x

    def height(self):
        return self.centre_marker.height()

    def update_peak(self, centre, height):
        self.centre_marker.x = centre
        self.centre_marker.set_height(height)

    def select(self):
        self.centre_marker.select()
        self.is_selected = True

    def deselect(self):
        self.centre_marker.deselect()
        self.is_selected = False
