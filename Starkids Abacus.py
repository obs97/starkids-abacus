import sys
import random
import math
import struct
import os
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QPushButton, QColorDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QFont, QColor, QFontMetrics, QIcon

# Check for Windows sound module
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Registry key identifiers for storing settings under Starkids Abacus
ORGANIZATION_NAME = "StarkidsAbacusStudio"
APPLICATION_NAME = "StarkidsAbacusTrainer"

# Default fallback configurations
FALLBACK_BG = "#1e1e1e"
FALLBACK_TEXT = "#ffffff"


def get_resource_path(relative_path):
    """
    Finds the absolute path to a resource, handling both standard script execution
    and PyInstaller standalone executable bundling.
    """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def create_ultra_short_beep_file():
    """Generates a tiny, 10ms crisp wave file to prevent delays."""
    if not HAS_WINSOUND:
        return None
        
    frequency = 950       
    duration_ms = 10      
    sample_rate = 11025
    
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = []
    
    for i in range(num_samples):
        t = i / sample_rate
        val = int(32767 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', val))
        
    data = b''.join(samples)
    
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + len(data),
        b'WAVE',
        b'fmt ',
        16,             
        1,              
        1,              
        sample_rate,
        sample_rate * 2,
        2,
        16,             
        b'data',
        len(data)
    )
    
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, "starkids_instant_beep.wav")
    try:
        with open(file_path, "wb") as f:
            f.write(header + data)
        return file_path
    except Exception:
        return None


BEEP_FILE_PATH = create_ultra_short_beep_file()


def play_beep_instant():
    if HAS_WINSOUND and BEEP_FILE_PATH:
        winsound.PlaySound(
            BEEP_FILE_PATH, 
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
        )


# ==========================================
# PHASE 2: THE FLASHING SCREEN (THE GAME)
# ==========================================
class FlashGameWindow(QWidget):
    def __init__(self, digits, quantity, speed, bg_color, text_color, font_size, enable_sound, sound_latency, parent_window):
        super().__init__()
        self.digits = digits
        self.quantity = quantity
        self.speed = speed
        self.bg_color = bg_color       
        self.text_color = text_color   
        self.font_size = font_size     
        self.enable_sound = enable_sound 
        self.sound_latency = sound_latency 
        self.parent_window = parent_window 
        
        self.numbers = []
        self.current_index = 0
        self.total_sum = 0
        self.answer_shown = False 
        
        self.init_ui()
        self.generate_new_numbers()

    def init_ui(self):
        self.setWindowTitle("Starkids Abacus - Playing")
        self.resize(1000, 650)
        
        # NEW: Set custom logo image in the window title bar header
        icon_path = get_resource_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setStyleSheet(f"background-color: {self.bg_color}; color: {self.text_color};")
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. MAIN DISPLAY
        self.display_label = QLabel("")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        initial_size = self.font_size if self.font_size > 0 else 110
        self.display_label.setFont(QFont("Arial", initial_size, QFont.Weight.Bold))
        self.display_label.setStyleSheet(f"color: {self.text_color};")
        main_layout.addWidget(self.display_label, stretch=1)
        
        # 2. HINT DISPLAY
        self.hint_label = QLabel("Get Ready...")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setFont(QFont("Arial", 14))
        self.hint_label.setStyleSheet("color: #888888;")
        main_layout.addWidget(self.hint_label)
        
        main_layout.addSpacing(25)
        
        # 3. THREE-BUTTON CONTROL ROW
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.back_btn = QPushButton("Esc: Back")
        self.back_btn.setMinimumHeight(45)
        self.back_btn.setFont(QFont("Arial", 11))
        self.back_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: white; border-radius: 5px; }
            QPushButton:hover { background-color: #444444; }
        """)
        self.back_btn.clicked.connect(self.go_back)
        
        self.repeat_btn = QPushButton("Space: Repeat")
        self.repeat_btn.setMinimumHeight(45)
        self.repeat_btn.setFont(QFont("Arial", 11))
        self.repeat_btn.clicked.connect(self.repeat_sequence)
        
        self.action_btn = QPushButton("Show Answer")
        self.action_btn.setMinimumHeight(45)
        self.action_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.action_btn.clicked.connect(self.handle_action_button)
        
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.repeat_btn)
        button_layout.addWidget(self.action_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def generate_new_numbers(self):
        if self.digits == 1:
            start_range = 1
            end_range = 9
        else:
            start_range = 10**(self.digits - 1)
            end_range = (10**self.digits) - 1
            
        self.numbers = [random.randint(start_range, end_range) for _ in range(self.quantity)]
        self.total_sum = sum(self.numbers)

    def showEvent(self, event):
        super().showEvent(event)
        self.adjust_font_size_for_auto()
        self.start_new_round(is_repeat=False)

    def adjust_font_size_for_auto(self):
        if self.font_size != 0:
            return

        max_single_num = (10**self.digits) - 1
        template_single = f"{max_single_num:,}"
        template_sum = f"{self.total_sum:,}"
        
        longest_string = template_single if len(template_single) > len(template_sum) else template_sum
        longest_string = " " + longest_string + " "

        target_width = self.width() - 40
        target_height = self.height() - 120 

        low_size = 10
        high_size = 600
        best_size = 110 

        while low_size <= high_size:
            mid_size = (low_size + high_size) // 2
            test_font = QFont("Arial", mid_size, QFont.Weight.Bold)
            metrics = QFontMetrics(test_font)
            rect = metrics.boundingRect(longest_string)

            if rect.width() <= target_width and rect.height() <= target_height:
                best_size = mid_size
                low_size = mid_size + 1 
            else:
                high_size = mid_size - 1 

        self.display_label.setFont(QFont("Arial", best_size, QFont.Weight.Bold))

    def start_new_round(self, is_repeat=False):
        self.current_index = 0
        self.answer_shown = False
        
        self.action_btn.setEnabled(False)
        self.back_btn.setEnabled(False)
        self.repeat_btn.setEnabled(False)
        
        self.action_btn.setText("Wait...")
        self.action_btn.setStyleSheet("background-color: #444444; color: #777777; border-radius: 5px;")
        self.repeat_btn.setStyleSheet("background-color: #444444; color: #777777; border-radius: 5px;")
        
        self.display_label.setText("")
        self.display_label.setStyleSheet(f"color: {self.text_color};")
        self.hint_label.setText("Get Ready...")
        self.hint_label.setStyleSheet("color: #888888;")
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_next_number)
        QTimer.singleShot(1000, self.start_flashing)

    def start_flashing(self):
        self.hint_label.setText("") 
        self.timer.start(self.speed)

    def show_next_number(self):
        if self.current_index < len(self.numbers):
            if self.enable_sound:
                play_beep_instant()
                QTimer.singleShot(self.sound_latency, self.update_visual_number)
            else:
                self.update_visual_number()
        else:
            self.timer.stop()
            self.display_label.setText("") 
            
            self.hint_label.setText("Press ENTER to show sum | Press SPACE to repeat")
            self.hint_label.setStyleSheet("color: #4A90E2;") 
            
            self.back_btn.setEnabled(True)
            self.repeat_btn.setEnabled(True)
            self.action_btn.setEnabled(True)
            
            self.action_btn.setText("Enter: Show Answer")
            self.action_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {self.text_color}; 
                    color: {self.get_contrast_color_text(self.text_color)}; 
                    border-radius: 5px; 
                }}
            """)
            self.repeat_btn.setStyleSheet("""
                QPushButton { background-color: #5e35b1; color: white; border-radius: 5px; }
                QPushButton:hover { background-color: #4527a0; }
            """)

    def update_visual_number(self):
        if self.current_index < len(self.numbers):
            formatted_num = f"{self.numbers[self.current_index]:,}"
            self.display_label.setText(formatted_num)
            self.current_index += 1

    def repeat_sequence(self):
        if self.current_index >= len(self.numbers):
            self.start_new_round(is_repeat=True)

    def reveal_answer(self):
        formatted_sum = f"{self.total_sum:,}"
        self.display_label.setText(formatted_sum)
        self.display_label.setStyleSheet(f"color: {self.text_color};") 
        
        self.hint_label.setText("Press ENTER for next round | Press SPACE to repeat | Press ESC to go back")
        self.hint_label.setStyleSheet("color: #888888;")
        self.answer_shown = True
        
        self.repeat_btn.setEnabled(True)
        self.repeat_btn.setStyleSheet("""
            QPushButton { background-color: #5e35b1; color: white; border-radius: 5px; }
            QPushButton:hover { background-color: #4527a0; }
        """)
        
        self.action_btn.setText("Enter: Next Round")
        self.action_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {self.text_color}; 
                color: {self.get_contrast_color_text(self.text_color)}; 
                border-radius: 5px; 
            }}
        """)

    def get_contrast_color_text(self, hex_color):
        qcolor = QColor(hex_color)
        return "white" if qcolor.lightness() < 128 else "black"

    def handle_action_button(self):
        if self.current_index >= len(self.numbers):
            if not self.answer_shown:
                self.reveal_answer()
            else:
                self.generate_new_numbers()
                self.adjust_font_size_for_auto() 
                self.start_new_round(is_repeat=False)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.action_btn.isEnabled():
                self.handle_action_button()
                    
        elif event.key() == Qt.Key.Key_Space:
            if self.repeat_btn.isEnabled():
                self.repeat_sequence()

        elif event.key() == Qt.Key.Key_Escape:
            if self.back_btn.isEnabled():
                self.go_back()

    def go_back(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        self.parent_window.show()
        self.close()


# ==========================================
# PHASE 1: THE SETTINGS SCREEN
# ==========================================
class FlashAnzanSettings(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        self.bg_color = self.settings.value("bg_color", FALLBACK_BG)
        self.text_color = self.settings.value("text_color", FALLBACK_TEXT)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Starkids Abacus - Settings")
        self.resize(400, 460)

        # NEW: Set custom logo image in the settings title bar header
        icon_path = get_resource_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()

        self.digits_input = QSpinBox()
        self.digits_input.setRange(1, 10)
        self.digits_input.setValue(2) 

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(2, 100)
        self.quantity_input.setValue(10) 

        self.speed_input = QSpinBox()
        self.speed_input.setRange(100, 5000)
        self.speed_input.setSingleStep(100) 
        self.speed_input.setValue(500) 

        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(0, 200)
        self.font_size_input.setValue(0) 
        self.font_size_input.setSingleStep(5)
        self.font_size_input.setSpecialValueText("Auto") 

        self.sound_checkbox = QCheckBox()
        self.sound_checkbox.setChecked(True) 
        self.sound_checkbox.setText("Enable Flashing Beep Sounds")

        self.latency_input = QSpinBox()
        self.latency_input.setRange(0, 500)
        self.latency_input.setValue(35) 
        self.latency_input.setSingleStep(5)
        self.latency_input.setSuffix(" ms")

        self.sound_checkbox.toggled.connect(self.latency_input.setEnabled)

        form_layout.addRow(QLabel("Number of Digits:"), self.digits_input)
        form_layout.addRow(QLabel("Quantity of Numbers:"), self.quantity_input)
        form_layout.addRow(QLabel("Speed Interval (ms):"), self.speed_input)
        form_layout.addRow(QLabel("Number Font Size:"), self.font_size_input)
        form_layout.addRow(QLabel("Sound Effects:"), self.sound_checkbox)
        form_layout.addRow(QLabel("Sound Latency Offset:"), self.latency_input)

        color_layout = QHBoxLayout()
        
        self.bg_color_btn = QPushButton("Background Color")
        self.bg_color_btn.clicked.connect(self.select_background_color)
        self.update_button_color_preview(self.bg_color_btn, self.bg_color)
        
        self.text_color_btn = QPushButton("Number Color")
        self.text_color_btn.clicked.connect(self.select_text_color)
        self.update_button_color_preview(self.text_color_btn, self.text_color)
        
        color_layout.addWidget(self.bg_color_btn)
        color_layout.addWidget(self.text_color_btn)

        default_actions_layout = QHBoxLayout()
        
        self.save_default_btn = QPushButton("Set as Default")
        self.save_default_btn.clicked.connect(self.save_current_as_default)
        self.save_default_btn.setStyleSheet("background-color: #37474f; color: white; padding: 5px; border-radius: 4px;")
        
        self.use_default_btn = QPushButton("Use Default (Reset)")
        self.use_default_btn.clicked.connect(self.use_fallback_defaults)
        self.use_default_btn.setStyleSheet("background-color: #37474f; color: white; padding: 5px; border-radius: 4px;")
        
        default_actions_layout.addWidget(self.save_default_btn)
        default_actions_layout.addWidget(self.use_default_btn)

        self.start_button = QPushButton("START GAME")
        self.start_button.setMinimumHeight(45)
        self.start_button.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #2e7d32; color: white; border-radius: 5px;")
        self.start_button.clicked.connect(self.on_start_clicked)

        main_layout.addLayout(form_layout)
        main_layout.addSpacing(15)
        main_layout.addLayout(color_layout)
        main_layout.addLayout(default_actions_layout)
        main_layout.addSpacing(20) 
        main_layout.addWidget(self.start_button)
        
        self.setLayout(main_layout)

    def select_background_color(self):
        color = QColorDialog.getColor(QColor(self.bg_color), self, "Select Background Color")
        if color.isValid():
            self.bg_color = color.name()
            self.update_button_color_preview(self.bg_color_btn, self.bg_color)

    def select_text_color(self):
        color = QColorDialog.getColor(QColor(self.text_color), self, "Select Number Color")
        if color.isValid():
            self.text_color = color.name()
            self.update_button_color_preview(self.text_color_btn, self.text_color)

    def update_button_color_preview(self, button, hex_color):
        qcolor = QColor(hex_color)
        text_contrast = "white" if qcolor.lightness() < 128 else "black"
        button.setStyleSheet(f"background-color: {hex_color}; color: {text_contrast}; border: 1px solid #999; padding: 5px; border-radius: 4px;")

    def save_current_as_default(self):
        self.settings.setValue("bg_color", self.bg_color)
        self.settings.setValue("text_color", self.text_color)

    def use_fallback_defaults(self):
        self.bg_color = FALLBACK_BG
        self.text_color = FALLBACK_TEXT
        self.update_button_color_preview(self.bg_color_btn, self.bg_color)
        self.update_button_color_preview(self.text_color_btn, self.text_color)

    def on_start_clicked(self):
        digits = self.digits_input.value()
        quantity = self.quantity_input.value()
        speed = self.speed_input.value()
        font_size = self.font_size_input.value()
        enable_sound = self.sound_checkbox.isChecked() 
        sound_latency = self.latency_input.value()
        
        self.game_window = FlashGameWindow(digits, quantity, speed, self.bg_color, self.text_color, font_size, enable_sound, sound_latency, self)
        self.game_window.show()
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FlashAnzanSettings()
    window.show()
    sys.exit(app.exec())