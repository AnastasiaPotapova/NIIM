from main_imports import *

class GraphPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.plots = []
        self.curves = []
        self.vlines = []
        self.data = []

        for i in range(3):
            plot = pg.PlotWidget()
            curve = plot.plot(np.zeros(100), pen='g')
            vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=1.5))
            plot.addItem(vline)

            self.plots.append(plot)
            self.curves.append(curve)
            self.vlines.append(vline)
            self.data.append(np.zeros(100))
            layout.addWidget(plot)

        self.current_index = 0
        self.mark_requested = False

    def update_plots(self, actual_data):
        if self.current_index > 0:
            self.current_index -= 1
        for i in range(3):
            self.data[i] = np.roll(self.data[i], -1)
            self.data[i][-1] = actual_data[i]
            self.curves[i].setData(self.data[i])
            if self.current_index:
                self.vlines[i].setValue(self.current_index)

    def mark_event(self):
        self.mark_requested = True
        self.current_index = 100

