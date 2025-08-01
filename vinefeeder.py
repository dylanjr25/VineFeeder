from PyQt6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QLabel,QLineEdit,QPushButton,QCheckBox,QFrame,)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHBoxLayout, QSlider
import sys
import os
import importlib.util
import yaml
from beaupy import select
import threading
from pretty import pretty_print
from rich.console import Console
from parsing_utils import prettify
import click
import subprocess
from batchloader import batchload

PAGE_SIZE = 8  # size of beaupy pagination


console = Console()


"""
Example usage:
    python vinefeeder.py --help       # Show help text
    python vinefeeder.py              # Launch VineFeeder GUI
    In the GUI:-
    	enter search text and select a service
    or
    	enter a video URL for direct download
    	and select a service
    or
    	leave the seach box blank and select a service
    	a further menu will appear in the terminal
    After a download has finished and 'Ready!' appears
    another service may be started.
    In the terminal:-
    	enter the number(s) of the service to download
        see
    
    	 
"""


class VineFeeder(QWidget):
    def __init__(self):
        """
        Initialize the VineFeeder object.

        This method sets up the VineFeeder object by calling necessary functions to
        initialize the UI, store available services dynamically, load services,
        and create buttons dynamically.
        """
        super().__init__()
        self.init_ui()
        self.available_services = {}  # Store available services dynamically
        self.available_service_media_dict = {}
        self.available_services_hlg_status = {}
        self.available_services_options = {}
        self.load_services()  # Discover and load services
        self.create_service_buttons()  # Create buttons dynamically

    def init_ui(self):
        """
        Initialize the UI components and layout.

        This method creates the necessary UI components and sets up the layout.
        
        """
        self.setWindowTitle("VineFeeder")
        layout = QVBoxLayout()

        self.search_url_label = QLabel("URL or Search")
        layout.addWidget(self.search_url_label)
        self.search_url_entry = QLineEdit()
        self.search_url_entry.setStyleSheet("""
            QLineEdit {
                border: 2px solid pink;
            }
            QLineEdit:focus {
                border: 2px solid hotpink;
                outline: none;
            }
        """)

        layout.addWidget(self.search_url_entry)

        highlighted_frame = QFrame()
        self.highlighted_layout = QVBoxLayout()
        highlighted_frame.setLayout(self.highlighted_layout)
        highlighted_frame.setStyleSheet(
            "border: 1px solid pink;"
        )  
        layout.addWidget(highlighted_frame)
        #
        sechighlighted_frame = QFrame()
        self.sechighlighted_layout = QVBoxLayout()
        sechighlighted_frame.setLayout(self.sechighlighted_layout)
        sechighlighted_frame.setStyleSheet(
            "border: 1px solid pink;"
          
        )  
        layout.addWidget(sechighlighted_frame)

        # Batch Mode Layout
        batch_mode_layout = QHBoxLayout()
        self.batch_slider = QSlider(Qt.Orientation.Horizontal)
        self.batch_slider.setMinimum(0)
        self.batch_slider.setMaximum(1)
        self.batch_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.batch_slider.setSingleStep(1)
        self.batch_slider.setFixedWidth(80)
        self.batch_slider.valueChanged.connect(self.toggle_batch_mode)
        self.batch_slider.setStyleSheet("""QSlider::groove:horizontal {
            border: 1px solid #999999;
            height: 5px; 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 hotpink, stop:1 #c4c4c4);
            margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                height: 18px;
                margin: -12px 0; 
                border-radius: 3px;
            }
            """)
        
        # Batch Mode Label
        self.batch_label = QLabel("Batch Mode")
        self.batch_label.setStyleSheet("color: white; padding-left: 5px; border: none;")

        batch_mode_layout.addWidget(self.batch_label)
        batch_mode_layout.addWidget(self.batch_slider)

        batch_mode_frame = QFrame()
        batch_mode_frame.setLayout(batch_mode_layout)
        batch_mode_frame.setStyleSheet("border: none;")
        self.sechighlighted_layout.addWidget(batch_mode_frame)

        # Batch File Existence Indicator
        self.batch_file_status = QLabel("")
        self.sechighlighted_layout.addWidget(self.batch_file_status)


        # Run Batch Button
        self.run_batch_button = QPushButton("Run Batch")
        self.run_batch_button.clicked.connect(batchload)
        self.run_batch_button.setEnabled(False)  # Initially disabled
        self.style_batch_button(self.run_batch_button)
        self.sechighlighted_layout.addWidget(self.run_batch_button)

        # Load batch mode from config
        self.load_batch_mode()

        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        self.dark_mode_checkbox.setChecked(True)  # Set dark mode by default
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        layout.addWidget(self.dark_mode_checkbox, alignment=Qt.AlignmentFlag.AlignLeft)

        self.setLayout(layout)
        # Poll for batch.txt changes every 2 seconds
        self.batch_poll_timer = QTimer(self)
        self.batch_poll_timer.timeout.connect(self.update_batch_file_indicator)
        self.batch_poll_timer.start(2000)  # 2000 ms = 2 seconds

        # Use a timer to delay the dark mode application slightly
        QTimer.singleShot(100, self.toggle_dark_mode)  # 100ms delay to ensure rendering

    def load_batch_mode(self):
        try:
            with open("./config.yaml", "r") as f:
                cfg = yaml.safe_load(f)
                batch_on = cfg.get("BATCH_DOWNLOAD", False)
                self.batch_slider.setValue(1 if batch_on else 0)
                self.run_batch_button.setEnabled(batch_on)
        except Exception as e:
            print(f"[warning] Could not load batch mode config: {e}")
            self.batch_slider.setValue(0)
            self.run_batch_button.setEnabled(False)

        self.update_batch_file_indicator()


    def toggle_batch_mode(self):
        state = self.batch_slider.value() == 1

        if state:
            self.batch_label.setStyleSheet("color: lightgreen; padding-left: 5px; border: none;")
        else:
            # Let toggle_dark_mode handle the fallback color
            self.toggle_dark_mode()  # Refresh dark/light mode colors

        self.run_batch_button.setEnabled(state)
        self.update_batch_file_indicator()

        # Update config.yaml
        config_path = "./config.yaml"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
            else:
                cfg = {}

            cfg["BATCH_DOWNLOAD"] = state

            with open(config_path, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False)
        except Exception as e:
            print(f"[warning] Could not update config.yaml: {e}")




    def style_batch_button(self, button):
        button.setStyleSheet("""
            color: white;
            background-color:#1E1E2E;
            border: none;
            padding: 5px;
        """)

    def update_batch_file_indicator(self):
        exists = os.path.exists("./batch.txt")
        if hasattr(self, "_batch_file_last_state") and self._batch_file_last_state == exists:
            return  # no change
        self._batch_file_last_state = exists

        if exists:
            self.batch_file_status.setText("✅ batch file exists")
            self.batch_file_status.setStyleSheet("color: lightgreen; padding-left: 25px; border: none;")
        else:
            self.batch_file_status.setText("❌ batch file missing")
            self.batch_file_status.setStyleSheet("color: hotpink; padding-left: 25px; border: none;")

       

    def toggle_dark_mode(self):
        """
        Toggle the application's dark mode on or off.

        This method is connected to the dark mode checkbox's stateChanged signal.
        When the checkbox is checked, the application is set to dark mode. When unchecked,
        the application is set to light mode.

        In dark mode, the window and text colors are changed to dark colors,
        and the search label and dark mode checkbox text are changed to white.
        Buttons are also set to have a white text color and a dark grey background color.

        In light mode, the window and text colors are set back to their default values,
        and the search label and dark mode checkbox text are changed back to black.
        Buttons are also reset to their default appearance.

        NOTE: This method uses a QTimer to delay the application of the dark mode style slightly.
        This is to ensure that the rendering of the UI components is complete
        before applying the style changes.
        """
        if self.dark_mode_checkbox.isChecked():
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(
                QPalette.ColorRole.Base, QColor(30, 30, 54)
            )  # QColor(35, 35, 35))
            palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
            self.setPalette(palette)
            self.search_url_label.setStyleSheet("color: white;")
            self.dark_mode_checkbox.setStyleSheet("color: white;")

            # Set button text to white in dark mode, remove red border
            for i in range(self.highlighted_layout.count()):
                button = self.highlighted_layout.itemAt(i).widget()
                if isinstance(button, QPushButton):
                    button.setStyleSheet("""
                        color: white;
                        background-color:#1E1E2E;
                        border: none;
                        padding: 5px;
                    """)
                    button.repaint()  # Force update of the button's appearance

        else:
            self.setPalette(QApplication.palette())
            self.search_url_label.setStyleSheet("color: black;")
            self.dark_mode_checkbox.setStyleSheet("color: black;")
            self.batch_label.setStyleSheet("color: black;")

            for i in range(self.highlighted_layout.count()):
                button = self.highlighted_layout.itemAt(i).widget()
                if isinstance(button, QPushButton):
                    button.setStyleSheet("""
                        color: black;
                        background-color: #aeaeae;
                        border: none;
                        padding: 5px;
                    """)
                    button.repaint()  # Force update of the button's appearance
        # Update batch_label based on dark mode and batch mode state
        if self.batch_slider.value() == 1:
            self.batch_label.setStyleSheet("color: lightgreen; padding-left: 5px; border: none;")
        else:
            if self.dark_mode_checkbox.isChecked():
                self.batch_label.setStyleSheet("color: white; padding-left: 5px; border: none;")
            else:
                self.batch_label.setStyleSheet("color: black; padding-left: 5px; border: none;")
            

    def load_services(self):
        """Dynamically load services from the services folder."""
        services_path = "./services"  # This can be dynamically loaded from config.yaml
        if not os.path.exists(services_path):
            print(f"Services folder {services_path} not found!")
            return

        for service in os.listdir(services_path):
            service_dir = os.path.join(services_path, service)
            if os.path.isdir(service_dir):
                config_file = os.path.join(service_dir, "config.yaml")
                init_file = os.path.join(service_dir, "__init__.py")
                if os.path.exists(config_file) and os.path.exists(init_file):
                    # Load the service config
                    with open(config_file, "r") as f:
                        service_config = yaml.safe_load(f)
                        service_name = service_config.get("service_name", service)
                        service_media_dict = service_config.get("media_dict", {})
                        service_hlg_status = service_config.get("hlg_status", False)
                        service_options = service_config.get("options", {})
                        self.available_services_hlg_status[service_name] = (
                            service_hlg_status  # UHD wanted?
                        )
                        self.available_services_options[service_name] = service_options
                        self.available_service_media_dict[service_name] = (
                            service_media_dict
                        )
                        # Add the service to available_services dict
                        self.available_services[service_name] = init_file

    def create_service_buttons(self):
        """Create buttons for each dynamically loaded service in alphabetical order."""
        # Sort the services alphabetically by their names
        for service_name in sorted(self.available_services.keys()):
            button = QPushButton(service_name)
            button.clicked.connect(
                self.run_load_service_thread(service_name)
            )  # Bind to threaded service loading
            self.highlighted_layout.addWidget(button)
            #

    def do_action_select(self, service_name):
        """
        Top level choice for action required. Called if search_box is empty.
        Uses beaupy to display a list of 4 options:
            - Search by keyword
            - Greedy Search by URL
            - Browse by Category
            - Download by URL
        Uses the selected option to call the appropriate function:
            - 0 for greedy search with url
            - 1 for direct url download
            - 2 for browse
            - 3 for search with keyword
        Returns a tuple of the function selector and the url or None if no valid data is entered.
        """

        fn = [
            "Greedy Search by URL",
            "Download by URL",
            "Browse by Category",
            "Search by keyword(s)",
        ]
        # check for batch.txt
        self.update_batch_file_indicator()

        action = select(
            fn, preprocessor=lambda val: prettify(val), cursor="🢧", cursor_style="pink1"
        )

        if "Greedy" in action:
            url = input("URL for greedy search ")
            return 0, url, None

        elif "Download" in action:
            url = input("URL for direct download ")
            return 1, url, None

        elif "Browse" in action:
            media_dict = self.available_service_media_dict[service_name]
            beaupylist = []
            for item in media_dict:
                beaupylist.append(item)
            found = select(
                beaupylist,
                preprocessor=lambda val: prettify(val),
                cursor="🢧",
                cursor_style="pink1",
                page_size=PAGE_SIZE,
                pagination=True,
            )
            url = media_dict[found]
            return 2, url, found  # found is category

        elif "Search" in action:
            keyword = input("Keyword(s) for search ")
            return 3, keyword, None

        else:
            print("No valid data entered!")
            sys.exit(0)

    def run_load_service_thread(self, service_name):
        """Start a new thread to load the service."""
        return lambda: threading.Thread(
            target=self.load_service, args=(service_name,)
        ).start()

    def load_service(self, service_name):
        
        self.update_batch_file_indicator()
        
        """Dynamically load the service's __init__.py when the button is clicked."""
        init_file = self.available_services.get(service_name)
        if init_file:
            try:
                # Load the service module
                spec = importlib.util.spec_from_file_location(service_name, init_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"[info] Loaded service: {service_name}\n\n")

                # Get text from input box, or pass None if empty
                text = self.search_url_entry.text().strip()
                text_to_pass = text if text else None

                # Dynamically instantiate the loader class
                loader_class_name = f"{service_name.capitalize()}Loader"  # Assuming class name is based on service name (e.g., All4Loader)

                if hasattr(module, loader_class_name):
                    loader_class = getattr(module, loader_class_name)
                    loader_instance = loader_class()  # Instantiate the service class
                    hlg_status = self.available_services_hlg_status[
                        service_name
                    ]  # UHD if available.
                    options = self.available_services_options[service_name]
                    if hasattr(loader_instance, "receive"):
                        if text_to_pass:
                            if "http" in text_to_pass:
                                loader_instance.receive(
                                    1, text_to_pass, None, hlg_status, options
                                )
                                self.clear_search_box()  # inx 1 signifies direct download
                                loader_instance.clean_terminal()
                                sys.exit(0)
                            else:
                                loader_instance.receive(
                                    3, text_to_pass, None, hlg_status, options
                                )  # inx 3 for keyword search
                                self.clear_search_box()
                                loader_instance.clean_terminal()
                                sys.exit(0)
                        else:
                            inx, text_to_pass, found = self.do_action_select(
                                service_name
                            )  # returns a (int , url)
                            loader_instance.receive(
                                inx, text_to_pass, found, hlg_status, options
                            )
                            loader_instance.clean_terminal()
                            sys.exit(0)
                    else:
                        print(
                            f"Service class {loader_class_name} has no 'receive' method"
                        )
                else:
                    print(f"No class {loader_class_name} found in {service_name}")
            except Exception as e:
                print(f"Error loading service: {service_name}  {e}")
                print("Try again")
                sys.exit(0)
        else:
            print(f"Service {service_name} not found!")
            print("Try again")
            sys.exit(0)

    def clear_search_box(self):
        self.search_url_entry.clear()


@click.command()
@click.option(
    "--service-folder",
    type=str,
    default="services",
    help="Specify a service folder for adding **Devine** download options.",
)
@click.option(
    "--list-services",
    is_flag=True,
    help="List available services in the specified service folder.",
)
@click.option(
    "--select-series",
    is_flag=True,
    help="How to select which series you need from those available",
)
def cli(service_folder, list_services, select_series):
    """
    python vinefeeder.py --help to show help\n
    python vinefeeder.py --list-services  to list available services\n
    python vinefeeder.py --service-folder <folder_name> to edit config.yaml
    python vinefeeder.py --select-series  list, range or 'all'\n\n
    In the GUI:-
    The text box will take keyword(s) or a URL for download from a button selected service.
    Or leave the text box blank for further options when the service button is clicked.\n
    Batch Mode: slide the slider to the right to engage Batch Mode. 
    All devine commands will be saved to a batch.txt file in the VineFeeder folder.
    When a green 'batch file exists' notice is present the 'Run Batch' button will process
    the batch.txt file.
    At the end of download the option to delete the batch.txt file will appear.
    It may be deleted manually at any time. 

    """
    # Ensure service-folder paths are handled correctly
    if os.path.isabs(service_folder):
        base_path = os.path.abspath(service_folder)
    else:
        base_path = (
            os.path.abspath(os.path.join("services", service_folder))
            if service_folder != "services"
            else os.path.abspath("services")
        )

    # Handle --list-services option
    if list_services:
        if not os.path.exists(base_path):
            print(f"Error: The service folder '{base_path}' does not exist!")
            return

        print(f"Available services in '{base_path}':")
        for service in os.listdir(base_path):
            service_dir = os.path.join(base_path, service)
            config_path = os.path.join(service_dir, "config.yaml")
            if os.path.isdir(service_dir) and os.path.exists(config_path):
                print(f" - {service}")
        return

    # Handle --select-series option
    if select_series:
        print("Series Selection:")
        print(
            "Check the available series.\nUse, for example,\n1,3,7 or a range 3..8,\nor 'all' or 0 to show all series."
        )
        return

    # Default behavior: Open config.yaml
    config_path = os.path.join(base_path, "config.yaml")

    # Check if the services folder exists
    if not os.path.exists(base_path):
        print(f"Error: The service folder '{base_path}' does not exist!")
        return

    # Check if config.yaml exists
    if not os.path.exists(config_path):
        print(
            f"Error: The file '{config_path}' does not exist! Please create it or specify a valid service folder."
        )
        return

    # Open the file in the system's default text editor
    try:
        if os.name == "nt":  # For Windows
            os.startfile(config_path)
        elif os.name == "posix":  # For Linux/Mac
            subprocess.run(["xdg-open", config_path], check=True)
        else:
            print("Unsupported operating system.")
    except Exception as e:
        print(f"Failed to open the file: {e}")


def main():
    """
    Entry point for the script. Decides between GUI launch and CLI behavior.
    """
    if len(sys.argv) == 1:
        # say hello nicely
        pretty_print()
        app = QApplication(sys.argv)
        window = VineFeeder()
        window.show()
        sys.exit(app.exec())
    else:
        # CLI arguments passed, handle them with click
        cli()


if __name__ == "__main__":
    main()
