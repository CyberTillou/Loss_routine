import sys
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QTextEdit, QHBoxLayout, QLabel, QLineEdit, QDialog,
                             QFileDialog)
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
from PyQt5.QtGui import QFont, QColor, QPalette, QDoubleValidator
import os
from datetime import datetime
import pyqtgraph.exporters
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtCore import QRegularExpression

# Import your external modules (adjust paths as needed)
from tunics_laser import TunicsLaser
from powermeter import FM_DLL, FM_Communication, FM_Measure, FM_Synchronizer


class SaveFolderDialog(QDialog):
    def __init__(self, current_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saving data to file")
        self.resize(600, 100)

        layout = QVBoxLayout()

        label = QLabel("Path to file directory")
        layout.addWidget(label)

        h_layout = QHBoxLayout()
        self.path_edit = QLineEdit(current_path)
        h_layout.addWidget(self.path_edit)

        self.browse_button = QPushButton("📁")
        h_layout.addWidget(self.browse_button)
        self.browse_button.clicked.connect(self.browse_folder)

        layout.addLayout(h_layout)

        btn_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)

    def get_path(self):
        return self.path_edit.text()


class ScanThread(QThread):
    new_data = pyqtSignal(float, float)
    log_signal = pyqtSignal(str)
    scan_finished = pyqtSignal()

    def __init__(self, laser_resource, dll_path, wl_start, wl_stop, wl_step, delay):
        super().__init__()
        self.laser_resource = laser_resource
        self.dll_path = dll_path
        self.wl_start = wl_start
        self.wl_stop = wl_stop
        self.wl_step = wl_step
        self.delay = delay
        self._running = True

    def run(self):
        try:
            self.log_signal.emit("Init laser...")
            self.laser = TunicsLaser(self.laser_resource)

            self.log_signal.emit("Init powermeter DLL...")
            fm_dll = FM_DLL(self.dll_path)
            self.comm = FM_Communication(fm_dll)
            self.comm.initialize()
            self.comm.open()

            sync = FM_Synchronizer(fm_dll, self.comm.handle)
            sync.synchronize()

            self.measure = FM_Measure(fm_dll, self.comm.handle)

            wl = self.wl_start
            while wl <= self.wl_stop and self._running:
                self.laser.set_wavelength(wl)
                time.sleep(self.delay)

                self.measure.get_measurements(iterations=2, delay=0.5)
                power = self.measure.data_buffer[0].measure
                self.log_signal.emit(f"Wavelength: {wl:.3f} nm, Power: {power:.6f} W")
                self.new_data.emit(wl, power)

                wl += self.wl_step

            self.log_signal.emit("Scan finished.")

        except Exception as e:
            self.log_signal.emit(f"Error during scan: {e}")

        finally:
            self.log_signal.emit("Closing communication ports...")
            try:
                if hasattr(self, 'comm'):
                    self.comm.close()
                    self.comm.deinitialize()
            except Exception as e:
                self.log_signal.emit(f"Error closing powermeter: {e}")

            try:
                if hasattr(self, 'laser'):
                    self.laser.close()
            except Exception as e:
                self.log_signal.emit(f"Error closing laser: {e}")

            self.scan_finished.emit()

    def stop(self):
        self._running = False


class PowerScanGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loss scan")
        self.resize(800, 650)

        QApplication.setStyle('Fusion')

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(230, 230, 230))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(200, 0, 0))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

        self.save_folder = r"C:\Users\tperson\Desktop\loss_measurment\measurment_result"

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Input fields layout
        input_layout = QHBoxLayout()

        regex = QRegularExpression(r"^-?\d{0,5}(\.\d{0,5})?$")  # accepte jusqu’à 5 chiffres + décimale
        float_validator = QRegularExpressionValidator(regex, self)

        self.label_start = QLabel("Start Wavelength (nm):")
        self.input_start = QLineEdit("1549.0")
        self.input_start.setValidator(float_validator)
        input_layout.addWidget(self.label_start)
        input_layout.addWidget(self.input_start)

        self.label_stop = QLabel("Stop Wavelength (nm):")
        self.input_stop = QLineEdit("1551.0")
        self.input_stop.setValidator(float_validator)
        input_layout.addWidget(self.label_stop)
        input_layout.addWidget(self.input_stop)

        self.label_step = QLabel("Step (nm):")
        self.input_step = QLineEdit("0.05")
        self.input_step.setValidator(float_validator)
        input_layout.addWidget(self.label_step)
        input_layout.addWidget(self.input_step)

        main_layout.addLayout(input_layout)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('bottom', 'Wavelength (nm)', color='#101010', size='12pt')
        self.plot_widget.setLabel('left', 'Power (mW)', color='#101010', size='12pt')
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#101010', width=1.5))
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color='#101010', width=1.5))
        self.plot_widget.getAxis('bottom').setTextPen(pg.mkPen('#101010'))
        self.plot_widget.getAxis('left').setTextPen(pg.mkPen('#101010'))
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot_widget.plot([], [], pen=pg.mkPen('r', width=2))
        main_layout.addWidget(self.plot_widget)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFont(QFont('Consolas', 10))
        self.log_console.setStyleSheet("background-color: #f0f0f0; color: #101010; border: 1px solid #ccc;")
        main_layout.addWidget(self.log_console, 1)

        self.choose_folder_button = QPushButton("Choose save folder")
        main_layout.addWidget(self.choose_folder_button)
        self.choose_folder_button.clicked.connect(self.open_save_folder_dialog)

        self.start_button = QPushButton("Start Scan")
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setEnabled(False)

        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #f5a9a9;
                color: #888;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e53935;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #f5a9a9;
                color: #888;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)

        main_layout.addWidget(self.start_button)
        main_layout.addWidget(self.stop_button)

        self.setLayout(main_layout)

        self.start_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)

        self.data_x = []
        self.data_y = []

        self.laser_resource = "ASRL4::INSTR"
        self.dll_path = r"C:\Program Files (x86)\Coherent\FieldMaxII PC\Drivers\Win10\FieldMax2Lib\x64\FieldMax2Lib.dll"

        self.thread = None

    def open_save_folder_dialog(self):
        dialog = SaveFolderDialog(self.save_folder, self)
        if dialog.exec_() == QDialog.Accepted:
            self.save_folder = dialog.get_path()
            self.log(f"Save folder set to: {self.save_folder}")

    def save_data(self):
        if not self.data_x or not self.data_y:
            self.log("No data to save.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = f"{timestamp}_losses"
        full_path = os.path.join(self.save_folder, folder_name)

        try:
            os.makedirs(full_path, exist_ok=True)
            file_path = os.path.join(full_path, "data.txt")

            with open(file_path, "w") as f:
                f.write("Wavelength (nm)\tPower (mW)\n")
                for wl, power in zip(self.data_x, self.data_y):
                    f.write(f"{wl:.3f}\t{power:.6f}\n")

            self.log(f"Data saved at : {file_path}")
        except Exception as e:
            self.log(f"Error while saving : {e}")
        
        # Save plot as PNG
        png_path = os.path.join(full_path, "plot.png")
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        exporter.parameters()['width'] = 800  # optional, size in pixels
        exporter.export(png_path)
        self.log(f"Graphique sauvegardé dans : {png_path}")

    def log(self, msg):
        self.log_console.append(msg)

    def update_plot(self, wl, power):
        self.data_x.append(wl)
        self.data_y.append(power * 1000)  # Convert W to mW
        self.curve.setData(self.data_x, self.data_y)

    def start_scan(self):
        try:
            wl_start = float(self.input_start.text())
            wl_stop = float(self.input_stop.text())
            wl_step = float(self.input_step.text())
            if wl_start >= wl_stop:
                self.log("Error: Start wavelength must be less than Stop wavelength.")
                return
            if wl_step <= 0:
                self.log("Error: Step must be positive.")
                return
        except ValueError:
            self.log("Error: Invalid numeric input for wavelengths or step.")
            return

        self.data_x.clear()
        self.data_y.clear()
        self.curve.clear()

        # 🔒 Fix axis range from start to stop
        self.plot_widget.setXRange(wl_start, wl_stop)
        self.plot_widget.enableAutoRange(axis='x', enable=False)  # Disable auto scaling on X

        delay = 0.5

        self.thread = ScanThread(self.laser_resource, self.dll_path, wl_start, wl_stop, wl_step, delay)
        self.thread.new_data.connect(self.update_plot)
        self.thread.log_signal.connect(self.log)
        self.thread.scan_finished.connect(self.scan_finished)
        self.thread.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log("Scan started...")

    def stop_scan(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait()  # Wait for the thread to finish cleanup
            self.thread = None
            self.log("Scan stopped.")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def scan_finished(self):
        self.log("Scan finished.")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.save_data()

    def closeEvent(self, event):
        if self.thread:
            self.thread.stop()
            self.thread.wait()
            self.thread = None
        event.accept()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PowerScanGUI()
    window.show()
    sys.exit(app.exec_())
