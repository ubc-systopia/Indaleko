"""
This script is used to construct a GUI for working with Indaleko.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
import logging

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig
from utils import IndalekoDocker

# pylint: enable=wrong-import-position

indaleko_icon_file = os.path.join(
    os.environ["INDALEKO_ROOT"], "figures", "indaleko-fantasy.png"
)


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"  # Main screen layout, top to bottom

        # Adding Top Banner
        top_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=100)
        self.icon = Image(source=indaleko_icon_file, size_hint=(0.2, 1))
        top_layout.add_widget(self.icon)
        self.main_label = Label(text="Indaleko Database Utility", size_hint=(0.8, 1))
        top_layout.add_widget(self.main_label)
        self.add_widget(top_layout)  # Adds the top banner to the screen

        # Adding Main Content Area (Left buttons + Right interaction area)
        main_content_layout = BoxLayout(orientation="horizontal")

        # Adding Left Side Button Menu (Utility buttons)
        left_layout = BoxLayout(orientation="vertical", size_hint_x=None, width=150)
        left_layout.padding = [10, 10, 10, 10]  # Add padding to make it visually better
        left_layout.spacing = 10  # Add some spacing between buttons

        if not os.path.exists(IndalekoDBConfig.default_db_config_file):

            # Buttons aligned at the top of the left column
            self.create_button = Button(text="Create", size_hint_y=None, height=50)
            self.create_button.bind(on_press=self.on_create_button_press)
            left_layout.add_widget(self.create_button)

            self.import_button = Button(text="Import", size_hint_y=None, height=50)
            self.import_button.bind(on_press=self.on_import_button_press)
            left_layout.add_widget(self.import_button)

        else:

            # Buttons aligned at the top of the left column
            self.search_button = Button(text="Search", size_hint_y=None, height=50)
            self.search_button.bind(on_press=self.on_search_button_press)
            left_layout.add_widget(self.search_button)

            self.maintenance_button = Button(
                text="Maintenance", size_hint_y=None, height=50
            )
            self.maintenance_button.bind(on_press=self.on_maintenance_button_press)
            left_layout.add_widget(self.maintenance_button)

        # Add a spacer widget to push buttons to the top
        left_layout.add_widget(Widget())

        main_content_layout.add_widget(
            left_layout
        )  # Adds the button menu to the left side

        # Adding Right-Side Interaction Area
        self.interaction_area = ScrollView(size_hint=(1, 1))
        self.interaction_content = Label(text="Select an option from the left menu.")
        self.interaction_area.add_widget(self.interaction_content)
        main_content_layout.add_widget(
            self.interaction_area
        )  # Adds the interaction area to the right side

        # Add the main content area to the main screen layout
        self.add_widget(main_content_layout)

    def on_create_button_press(self, instance):
        # Logic for when the "Create" button is pressed
        self.interaction_content.text = (
            "Starting database creation...\nRunning pre-flight checks..."
        )
        # Here you'd add the code for checking prerequisites and creating the database

    def on_import_button_press(self, instance):
        # Logic for when the "Import" button is pressed
        self.interaction_content.text = "Select a configuration file to import."
        file_chooser = FileChooserIconView(size_hint=(1, None), height=300)
        file_chooser.bind(on_submit=self.on_file_selected)
        self.interaction_area.clear_widgets()
        self.interaction_area.add_widget(file_chooser)

    def on_file_selected(self, filechooser, selection, touch):
        if selection:
            selected_file = selection[0]
            logging.info(f"Selected file: {selected_file}")
            self.interaction_content.text = (
                f"Importing configuration from: {selected_file}"
            )
            # Placeholder for the import logic
            # Implement logic here to load the configuration and update Indaleko setup
            self.interaction_area.clear_widgets()
            self.interaction_area.add_widget(self.interaction_content)

    def on_search_button_press(self, instance):
        # Logic for when the "Search" button is pressed
        self.interaction_area.clear_widgets()
        search_layout = BoxLayout(orientation="vertical")

        # Search Input Area
        self.query_input = TextInput(
            hint_text="Enter search query here...", size_hint=(1, 0.1)
        )
        search_layout.add_widget(self.query_input)

        # Search Button
        self.search_button_execute = Button(text="Execute Search", size_hint=(1, 0.2))
        self.search_button_execute.bind(on_press=self.perform_search)
        search_layout.add_widget(self.search_button_execute)

        # Result Display Area
        self.result_label = Label(
            text="Results will be shown here.", size_hint=(1, 0.7)
        )
        search_layout.add_widget(self.result_label)

        self.interaction_area.add_widget(search_layout)

    def perform_search(self, instance):
        query = self.query_input.text
        # Here you'd invoke the Indaleko search function, stubbed for now
        results = f"Performing search for: {query}"
        # Display results
        self.result_label.text = results

    def on_maintenance_button_press(self, instance):
        # Placeholder for the maintenance logic
        self.interaction_content.text = "Performing maintenance tasks..."
        # Placeholder for the maintenance logic
        # Implement logic here to perform maintenance tasks
        self.interaction_area.clear_widgets()
        self.interaction_area.add_widget(self.interaction_content)

    def show_error_popup(self, message):
        popup = Popup(title="Error", content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()


class IndalekoApp(App):
    def build(self):
        return MainScreen()


def main():
    """Main entry point for the Indaleko Kivy Console"""
    IndalekoApp().run()


if __name__ == "__main__":
    main()
