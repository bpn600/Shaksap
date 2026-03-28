import os
import sqlite3
import webbrowser
from datetime import datetime
import kivymd_extensions.akivymd  # NOQA
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window  # Add this import
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ObjectProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivymd.app import MDApp  # This is the main app class
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from pygments.styles.dracula import background

from database import (
    init_db, get_all_notes,
    delete_note, get_note_by_id,
    get_db_path  # Add this import
)

# Window.size = (400, 600)

class ScreenManagement(ScreenManager):
    pass

class FolderDialog(Popup):
    """Popup dialog for creating/editing folders"""
    def __init__(self, on_save=None, folder_data=None, **kwargs):
        super().__init__(**kwargs)
        self.on_save = on_save
        self.folder_data = folder_data
        self.selected_color = "#2196F3"  # Default color

        # Create dialog content
        content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(20),
            size_hint_y=None,
            height=dp(400),  # Increased height for color buttons
            md_bg_color=(145/255, 163/255, 176/255, 1)
        )

        # Folder name input
        self.name_input = MDTextField(
            hint_text="  Folder Name",
            mode="round",   # ['rectangle', 'round', 'fill', 'line']
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(self.name_input)

        # Color selection label
        color_label = Label(
            text="Select Folder Color:",
            font_size='14sp',
            size_hint_y=None,
            height=dp(30),
            color=(0, 0, 0, 1),
            halign='left'
        )
        content.add_widget(color_label)

        # Color picker grid with preset colors
        color_grid = GridLayout(
            cols=5,
            spacing=dp(8),
            size_hint_y=None,
            height=dp(80),
            padding=[dp(5), dp(5)]
        )

        # Preset colors
        preset_colors = [
            "#FF5252",  # Red
            "#FF4081",  # Pink
            "#E040FB",  # Purple
            "#7C4DFF",  # Deep Purple
            "#536DFE",  # Indigo
            "#2196F3",  # Blue
            "#00BCD4",  # Cyan
            "#4CAF50",  # Green
            "#FFC107",  # Amber
            "#FF9800",  # Orange
            "#795548",  # Brown
            "#607D8B",  # Blue Grey
        ]

        self.color_buttons = []
        for color in preset_colors:
            color_btn = Button(
                background_normal='',
                background_color=self.hex_to_rgba(color),
                size_hint=(1, 1),
                on_release=lambda x, c=color: self.select_color(c)
            )
            color_grid.add_widget(color_btn)
            self.color_buttons.append(color_btn)

        content.add_widget(color_grid)

        # Custom color input (optional)
        custom_color_row = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint_y=None,
            height=dp(50),
            padding=[0, dp(5), 0, 0]
        )
        custom_color_row.add_widget(Label(
            text="Custom:",
            size_hint_x=None,
            width=dp(50),
            color=(0, 0, 0, 1)
        ))

        self.color_picker = MDTextField(
            text=self.selected_color,
            mode="fill",
            size_hint_x=1,
            height=dp(50)
        )
        self.color_picker.bind(text=self.on_color_text_change)
        custom_color_row.add_widget(self.color_picker)
        content.add_widget(custom_color_row)

        # Preview color
        preview_layout = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint_y=None,
            height=dp(40),
            padding=[0, dp(5)]
        )
        preview_layout.add_widget(Label(
            text="Preview:",
            size_hint_x=None,
            width=dp(60),
            color=(0, 0, 0, 1)
        ))
        self.preview_box = MDBoxLayout(
            size_hint_x=1,
            md_bg_color=self.hex_to_rgba(self.selected_color),
            radius=[dp(5), dp(5), dp(5), dp(5)]
        )
        preview_layout.add_widget(self.preview_box)
        content.add_widget(preview_layout)

        # Buttons
        button_row = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint_y=None,
            height=dp(50),
            padding=[0, dp(10), 0, 0]
        )

        save_btn = MDFlatButton(
            text="Save",
            on_release=self.save_folder
        )
        cancel_btn = MDFlatButton(
            text="Cancel",
            on_release=self.dismiss
        )

        button_row.add_widget(save_btn)
        button_row.add_widget(cancel_btn)
        content.add_widget(button_row)

        # If editing existing folder, pre-fill data
        if folder_data:
            self.name_input.text = folder_data[1]  # folder name
            self.selected_color = folder_data[3] if len(folder_data) > 3 else "#2196F3"
            self.color_picker.text = self.selected_color
            self.update_preview_color(self.selected_color)
            self.title = "Edit Folder"
        else:
            self.title = "New Folder"
            # Highlight default color button
            self.highlight_selected_color()

        self.content = content
        self.size_hint = (0.85, None)
        self.height = dp(520)

    def hex_to_rgba(self, hex_color):
        """Convert hex color to RGBA tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return (r/255, g/255, b/255, 1)
        return (33/255, 150/255, 243/255, 1)  # Default blue

    def select_color(self, color):
        """Select a color from preset buttons"""
        self.selected_color = color
        self.color_picker.text = color
        self.update_preview_color(color)
        self.highlight_selected_color()

    def on_color_text_change(self, instance, value):
        """Handle manual color input"""
        if value and value.startswith('#') and len(value) == 7:
            try:
                # Validate hex color
                int(value[1:], 16)
                self.selected_color = value
                self.update_preview_color(value)
                self.highlight_selected_color()
            except ValueError:
                # Invalid hex color
                pass

    def update_preview_color(self, color):
        """Update preview box color"""
        self.preview_box.md_bg_color = self.hex_to_rgba(color)

    def highlight_selected_color(self):
        """Highlight the selected preset color button"""
        for btn in self.color_buttons:
            # Reset all buttons to normal size
            btn.size_hint = (1, 1)
            # Add border to selected button
            if btn.background_color == self.hex_to_rgba(self.selected_color):
                # You might want to add a border or effect to highlight
                btn.size_hint = (0.9, 0.9)
            else:
                btn.size_hint = (1, 1)

    def save_folder(self, instance):
        """Save folder data"""
        folder_name = self.name_input.text.strip()
        if not folder_name:
            toast("Please enter a folder name")
            return

        if self.on_save:
            self.on_save(folder_name, self.selected_color)
        self.dismiss()

class Card:
    pass

class DashboardScreen(Screen):
    current_folder_id = NumericProperty(None, allownone=True)
    current_folder_name = StringProperty("")

    # Responsive properties
    folder_card_height = NumericProperty(dp(60))
    note_card_height = NumericProperty(dp(100))
    grid_spacing = NumericProperty(dp(8))
    section_spacing = NumericProperty(dp(10))
    screen_padding = NumericProperty(dp(10))
    header_height = NumericProperty(dp(50))
    top_margin = NumericProperty(dp(44))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.folder_dialog = None
        self.folders = []
        self.current_folder_id = None
        self.current_folder_name = ""
        self.dragging_note = None

        # Bind window size changes
        Window.bind(on_resize=self.on_window_resize)
        Clock.schedule_once(self.calculate_responsive_sizes, 0.1)
        Clock.schedule_once(self.load_folders, 0.5)

        # Bind orientation changes for mobile
        if platform == 'android' or platform == 'ios':
            Window.bind(on_orientation=self.on_orientation_change)

    def on_enter(self):
        """Load folders and notes when screen is entered"""
        self.calculate_responsive_sizes()
        self.load_folders()
        self.load_notes_in_folder()
        self.update_navigation_buttons()  # Update button visibility

    def update_navigation_buttons(self):
        """Update the visibility of menu and back buttons based on current folder"""
        if hasattr(self.ids, 'menu_button') and hasattr(self.ids, 'back_button'):
            if self.current_folder_id is not None:
                # In a folder - hide menu, show back
                self.ids.menu_button.opacity = 0
                self.ids.menu_button.disabled = True
                self.ids.back_button.opacity = 1
                self.ids.back_button.disabled = False
            else:
                # Not in a folder - show menu, hide back
                self.ids.menu_button.opacity = 1
                self.ids.menu_button.disabled = False
                self.ids.back_button.opacity = 0
                self.ids.back_button.disabled = True

        # Update header title
        if hasattr(self.ids, 'header_title'):
            if self.current_folder_id is None:
                self.ids.header_title.text = "My Notes"
            else:
                self.ids.header_title.text = self.current_folder_name

    def recalculate_folder_text_sizes(self, dt=None):
        """Recalculate folder text sizes on orientation/resize changes"""
        # Force update of all folder widgets with new sizes
        if hasattr(self, 'ids') and hasattr(self.ids, 'folders_grid'):
            current_folders = self.folders if self.current_folder_id is None else []

            # Only update if we're showing folders
            if self.current_folder_id is None:
                self.update_folders_display()

    def on_orientation_change(self, window, orientation):
        """Handle orientation changes on mobile"""
        Clock.schedule_once(lambda dt: self.calculate_responsive_sizes(), 0.1)
        Clock.schedule_once(lambda dt: self.update_folders_display(), 0.2)
        Clock.schedule_once(lambda dt: self.load_notes_in_folder(), 0.2)

    def on_window_resize(self, window, width, height):
        """Handle window resize events"""
        self.calculate_responsive_sizes()
        Clock.schedule_once(lambda dt: self.update_folders_display(), 0.1)
        Clock.schedule_once(lambda dt: self.load_notes_in_folder(), 0.1)

    def calculate_responsive_sizes(self, dt=None):
        """Calculate responsive sizes based on screen dimensions"""
        screen_width = Window.width
        screen_height = Window.height

        # Base calculations
        base_padding = min(dp(6), screen_width * 0.025)
        base_spacing = min(dp(8), screen_width * 0.02)

        # Responsive margins and padding
        self.screen_padding = base_padding
        self.grid_spacing = base_spacing
        self.section_spacing = min(dp(10), screen_width * 0.025)

        # Header height responsive
        if screen_width < 400:
            self.header_height = dp(45)
            self.top_margin = dp(40)
        elif screen_width < 600:
            self.header_height = dp(50)
            self.top_margin = dp(44)
        else:
            self.header_height = dp(60)
            self.top_margin = dp(48)

        # Adjust folder card height based on screen size
        if screen_width < 400:  # Small screens
            self.folder_card_height = dp(50)
            self.note_card_height = dp(85)
        elif screen_width < 600:  # Medium screens
            self.folder_card_height = dp(60)
            self.note_card_height = dp(100)
        elif screen_width < 900:  # Tablet
            self.folder_card_height = dp(70)
            self.note_card_height = dp(120)
        else:  # Large screens
            self.folder_card_height = dp(80)
            self.note_card_height = dp(140)

        # Force folder display update if screen size changed
        if hasattr(self, 'folders'):
            Clock.schedule_once(lambda dt: self.update_folders_display(), 0.05)

    def load_folders(self, dt=None):
        """Load and display all folders"""
        from database import get_all_folders
        self.folders = get_all_folders()
        self.update_folders_display()

    def update_folders_display(self):
        """Update the folders grid with current folders"""
        grid = self.ids.folders_grid
        grid.clear_widgets()

        # Update grid properties for responsiveness
        screen_width = Window.width

        # Responsive grid settings
        if screen_width < 400:
            grid.spacing = dp(4)
            grid.padding = [self.screen_padding, dp(4)]
        elif screen_width < 600:
            grid.spacing = dp(6)
            grid.padding = [self.screen_padding, dp(6)]
        else:
            grid.spacing = dp(8)
            grid.padding = [self.screen_padding, dp(8)]

        # Only show folders when not in a specific folder
        if self.current_folder_id is None:
            # Add "Folders List" title with responsive sizing
            title_font_size = max(16, min(20, screen_width // 20))

            title_container = MDBoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(50),
                spacing=dp(4)
            )

            title_label = Label(
                text="Folders",
                font_size=f'{title_font_size}sp',
                bold=True,
                size_hint_y=None,
                height=dp(35),
                color=(0, 0, 0, 0.87),
                halign='left',
                valign='middle',
                text_size=(screen_width - (self.screen_padding * 2), None)
            )
            title_label.bind(size=title_label.setter('text_size'))

            separator = MDBoxLayout(
                size_hint_y=None,
                height=dp(2),
                md_bg_color=(0.8, 0.8, 0.8, 1)
            )

            title_container.add_widget(title_label)
            title_container.add_widget(separator)
            grid.add_widget(title_container)

            # Add default "All Notes" folder
            all_notes_widget = self.create_folder_widget(None, "All Notes", "#4CAF50")
            grid.add_widget(all_notes_widget)

            # Add user folders
            for folder in self.folders:
                folder_widget = self.create_folder_widget(
                    folder[0],
                    folder[1],
                    folder[3] if len(folder) > 3 else "#2196F3"
                )
                grid.add_widget(folder_widget)

    def create_folder_widget(self, folder_id, folder_name, color):
        """Create a responsive widget for displaying a folder with right-aligned buttons"""
        from kivymd.uix.card import MDCard
        from kivy.metrics import dp
        from kivy.core.text import Label as CoreLabel
        from kivy.clock import Clock

        # Get current screen dimensions
        screen_width = Window.width

        # Responsive calculations based on screen size
        if screen_width < 400:  # Small phones
            folder_card_height = dp(55)
            icon_size = dp(18)
            font_size_base = 12
            horizontal_padding = dp(8)
            vertical_padding = dp(8)
            button_width = dp(32)
            spacing = dp(4)
            count_width = dp(35)
        elif screen_width < 600:  # Medium phones
            folder_card_height = dp(65)
            icon_size = dp(20)
            font_size_base = 14
            horizontal_padding = dp(10)
            vertical_padding = dp(10)
            button_width = dp(35)
            spacing = dp(6)
            count_width = dp(40)
        elif screen_width < 900:  # Tablets
            folder_card_height = dp(80)
            icon_size = dp(24)
            font_size_base = 16
            horizontal_padding = dp(12)
            vertical_padding = dp(12)
            button_width = dp(40)
            spacing = dp(8)
            count_width = dp(45)
        else:  # Large screens
            folder_card_height = dp(90)
            icon_size = dp(28)
            font_size_base = 18
            horizontal_padding = dp(15)
            vertical_padding = dp(15)
            button_width = dp(45)
            spacing = dp(10)
            count_width = dp(50)

        # Create card
        card = MDCard(
            orientation='horizontal',
            size_hint=(1, None),
            height=folder_card_height,
            padding=[horizontal_padding, vertical_padding],
            spacing=spacing,
            md_bg_color=self.hex_to_rgba(color),
            elevation=2,
            ripple_behavior=True,
            radius=[dp(12), dp(12), dp(12), dp(12)]
        )

        # Folder name container (left side) - takes remaining space
        name_container = MDBoxLayout(
            orientation='vertical',
            size_hint_x=1,  # Will expand to fill available space
            pos_hint={'center_y': 0.5}
        )

        # Calculate available width for folder name
        # Subtract fixed width elements: count + buttons + padding + spacing
        fixed_width = count_width + (button_width * 2) + (spacing * 3) + (horizontal_padding * 2)
        name_available_width = screen_width - fixed_width
        name_available_width = max(name_available_width, dp(80))  # Minimum width

        # Calculate optimal font size for folder name
        def get_text_width(text, font_size):
            temp_label = CoreLabel(text=text, font_size=font_size, font_name="assets/font/NotoSansLimbu-Regular.ttf")
            temp_label.refresh()
            return temp_label.texture.width

        optimal_font_size = font_size_base + 4
        while optimal_font_size > 12 and get_text_width(folder_name, optimal_font_size) > name_available_width:
            optimal_font_size -= 1

        name_font_size = max(12, optimal_font_size)

        name_label = Label(
            text=folder_name,
            font_size=f'{name_font_size}sp',
            font_name="assets/font/NotoSansLimbu-Regular.ttf",
            bold=True,
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle',
            shorten=True,
            shorten_from='right',
            text_size=(name_available_width, None),
            size_hint_y=None,
            height=folder_card_height - (vertical_padding * 2)
        )
        name_label.bind(size=name_label.setter('text_size'))
        name_container.add_widget(name_label)

        # Right side container (count and buttons) - fixed width
        right_container = MDBoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            width=count_width + (button_width * 2) + (spacing * 2) if folder_id else count_width,
            spacing=spacing,
            pos_hint={'center_y': 0.5}
        )

        # Get note count
        from database import get_folder_stats
        note_count = get_folder_stats(folder_id) if folder_id else self.get_total_notes()

        # Note count container (fixed width)
        count_container = MDBoxLayout(
            orientation='vertical',
            size_hint_x=None,
            width=count_width,
            pos_hint={'center_y': 0.5}
        )

        count_label = Label(
            text=str(note_count),
            font_size=f'{font_size_base}sp',
            font_name="assets/font/NotoSansLimbu-Regular.ttf",
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            bold=True,
            size_hint_y=None,
            height=folder_card_height - (vertical_padding * 2)
        )
        count_container.add_widget(count_label)
        right_container.add_widget(count_container)

        # Buttons container (for edit and delete) - fixed width
        if folder_id is not None:
            buttons_container = MDBoxLayout(
                orientation='horizontal',
                size_hint_x=None,
                width=(button_width * 2) + spacing,
                spacing=spacing,
                pos_hint={'center_y': 0.5}
            )

            # Edit button with container
            edit_btn_container = MDBoxLayout(
                orientation='horizontal',
                size_hint_x=None,
                width=button_width,
                pos_hint={'center_y': 0.5}
            )

            edit_btn = MDIconButton(
                icon="pencil",
                icon_size=icon_size,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                size_hint=(1, 1),
                md_bg_color=(0, 0, 0, 0),
                ripple_scale=0.8
            )
            edit_btn.bind(on_release=lambda x, fid=folder_id, name=folder_name, col=color:
            self.edit_folder(fid, name, col))
            edit_btn_container.add_widget(edit_btn)

            # Delete button with container
            delete_btn_container = MDBoxLayout(
                orientation='horizontal',
                size_hint_x=None,
                width=button_width,
                pos_hint={'center_y': 0.5}
            )

            delete_btn = MDIconButton(
                icon="delete",
                icon_size=icon_size,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                size_hint=(1, 1),
                md_bg_color=(0, 0, 0, 0),
                ripple_scale=0.8
            )
            delete_btn.bind(on_release=lambda x, fid=folder_id: self.confirm_delete_folder(fid))
            delete_btn_container.add_widget(delete_btn)

            buttons_container.add_widget(edit_btn_container)
            buttons_container.add_widget(delete_btn_container)
            right_container.add_widget(buttons_container)

        # Add containers to card
        card.add_widget(name_container)
        card.add_widget(right_container)

        # Make card clickable
        card.bind(on_release=lambda x, fid=folder_id, name=folder_name: self.select_folder(fid, name))

        # Store metadata
        card.folder_id = folder_id
        card.folder_name = folder_name

        return card

    def animate_card_press(self, card):
        """Animate card on press for visual feedback"""
        anim = Animation(
            elevation=1,
            duration=0.1,
            t='out_quad'
        )
        anim.start(card)
        Clock.schedule_once(lambda dt: self.animate_card_release(card), 0.1)

    def animate_card_release(self, card):
        """Animate card release"""
        anim = Animation(
            elevation=2,
            duration=0.1,
            t='out_quad'
        )
        anim.start(card)

    def get_total_notes(self):
        """Get total number of notes"""
        from database import get_note_stats
        stats = get_note_stats()
        return stats['note_count']

    def select_folder(self, folder_id, folder_name):
        """Select a folder to view its notes"""
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name
        self.load_notes_in_folder()
        self.update_navigation_buttons()  # Update button visibility
        toast(f"Showing notes in {folder_name}")

    def go_back_to_dashboard(self):
        """Go back to the dashboard view (show all folders)"""
        self.current_folder_id = None
        self.current_folder_name = ""
        self.load_folders()
        self.load_notes_in_folder()
        self.update_navigation_buttons()  # Update button visibility
        toast("Showing all folders")

    def get_current_folder_name(self):
        """Get the name of the currently selected folder"""
        if self.current_folder_id is not None:
            return self.current_folder_name
        return "My Notes"

    def load_notes_in_folder(self):
        """Load and display notes from selected folder with date grouping"""
        from database import get_notes_with_date_grouping
        grouped_notes = get_notes_with_date_grouping(self.current_folder_id)
        self.display_notes_grouped(grouped_notes)

    def display_notes_grouped(self, grouped_notes):
        """Display notes grouped by date categories"""
        grid = self.ids.notes_grid
        grid.clear_widgets()

        if not grouped_notes or not any(grouped_notes.values()):
            # Show empty state
            empty_label = Label(
                text="No notes in this folder\nTap + to create a new note",
                font_name="assets/font/NotoSansLimbu-Regular.ttf",
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(150),
                color=(0.5, 0.5, 0.5, 1)
            )
            grid.add_widget(empty_label)
            return

        # Add "Recent Notes" title at the top
        # recent_notes_header = self._create_category_header("Recent Notes", is_main_header=True)
        # grid.add_widget(recent_notes_header)

        # Define display order for categories
        category_order = ['Today', 'Yesterday', 'Previous 7 Days', 'Previous 30 Days']

        # Track if any notes were displayed
        notes_displayed = False

        # Display predefined categories
        for category in category_order:
            if category in grouped_notes and grouped_notes[category]:
                self._add_category_header(grid, category)
                for note in grouped_notes[category]:
                    note_widget = self.create_note_widget(note)
                    grid.add_widget(note_widget)
                    notes_displayed = True

        # Display months
        if grouped_notes.get('Months'):
            # Sort months chronologically (newest first)
            sorted_months = sorted(grouped_notes['Months'].keys(),
                                   key=lambda x: datetime.strptime(x, '%B %Y'),
                                   reverse=True)
            for month in sorted_months:
                self._add_category_header(grid, month)
                for note in grouped_notes['Months'][month]:
                    note_widget = self.create_note_widget(note)
                    grid.add_widget(note_widget)
                    notes_displayed = True

        # Display years (for older notes)
        if grouped_notes.get('Year'):
            # Get current year
            current_year = datetime.now().year
            # Filter out years that are already covered by months
            year_notes = {}
            for year, notes in grouped_notes['Year'].items():
                # Check if this year's notes are not already shown in months
                year_has_month = False
                if grouped_notes.get('Months'):
                    for month_key in grouped_notes['Months'].keys():
                        if year in month_key:
                            year_has_month = True
                            break

                # Only show year category if it's not current year or not covered by months
                if int(year) < current_year - 1 and not year_has_month:
                    year_notes[year] = notes

            if year_notes:
                sorted_years = sorted(year_notes.keys(), reverse=True)
                for year in sorted_years:
                    self._add_category_header(grid, year)
                    for note in year_notes[year]:
                        note_widget = self.create_note_widget(note)
                        grid.add_widget(note_widget)
                        notes_displayed = True

        # Add "No More Notes ..." at the end if there are notes displayed
        if notes_displayed:
            self._add_end_of_notes_marker(grid)

    def _add_end_of_notes_marker(self, grid):
        """Add a 'No More Notes ...' marker at the end of notes list"""
        from kivymd.uix.card import MDCard

        screen_width = Window.width
        horizontal_padding = min(dp(12), screen_width * 0.03)

        # Create container for the end marker
        end_marker_container = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(80),
            spacing=dp(8),
            padding=[horizontal_padding, dp(15)]
        )

        # Add separator line
        separator = MDBoxLayout(
            size_hint_y=None,
            height=dp(1),
            md_bg_color=(0.8, 0.8, 0.8, 0.5),
            size_hint_x=1
        )
        end_marker_container.add_widget(separator)

        # Add the "No More Notes ..." text
        end_marker_label = Label(
            text="No More Notes ...",
            font_size='14sp',
            color=(0.5, 0.5, 0.5, 0.7),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=dp(40),
            italic=True,
            text_size=(screen_width - (horizontal_padding * 2), None)
        )
        end_marker_label.bind(size=end_marker_label.setter('text_size'))
        end_marker_container.add_widget(end_marker_label)

        # Add some bottom padding
        padding_widget = MDBoxLayout(
            size_hint_y=None,
            height=dp(10)
        )
        end_marker_container.add_widget(padding_widget)

        grid.add_widget(end_marker_container)

    def _create_category_header(self, category_title, is_main_header=False):
        """Create a category header for the notes grid"""
        header_container = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(60) if is_main_header else dp(50),
            spacing=dp(2)
        )

        header_label = Label(
            text=category_title,
            font_size='22sp' if is_main_header else '18sp',
            bold=True,
            size_hint_y=None,
            height=dp(45) if is_main_header else dp(35),
            color=(0, 0, 0, 0.87),
            halign='left',
            valign='middle',
            text_size=(Window.width - (self.screen_padding * 2), None)
        )
        header_label.bind(size=header_label.setter('text_size'))

        # Add a separator line
        separator = MDBoxLayout(
            size_hint_y=None,
            height=dp(2) if is_main_header else dp(1),
            md_bg_color=(0.8, 0.8, 0.8, 1)
        )

        header_container.add_widget(header_label)
        header_container.add_widget(separator)

        # Add extra spacing for main header
        if is_main_header:
            spacing_widget = MDBoxLayout(
                size_hint_y=None,
                height=dp(5)
            )
            header_container.add_widget(spacing_widget)

        return header_container

    def _add_category_header(self, grid, category_title):
        """Add a category header to the notes grid"""
        header_container = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(50),
            spacing=dp(2)
        )

        header_label = Label(
            text=category_title,
            font_size='18sp',
            bold=True,
            size_hint_y=None,
            height=dp(35),
            color=(0, 0, 0, 0.87),
            halign='left',
            valign='middle',
            text_size=(Window.width - (self.screen_padding * 2), None)
        )
        header_label.bind(size=header_label.setter('text_size'))

        separator = MDBoxLayout(
            size_hint_y=None,
            height=dp(1),
            md_bg_color=(0.8, 0.8, 0.8, 1)
        )

        header_container.add_widget(header_label)
        header_container.add_widget(separator)
        grid.add_widget(header_container)

    def display_notes(self, notes):
        """Display notes in the grid"""
        grid = self.ids.notes_grid
        grid.clear_widgets()

        if not notes:
            # Show empty state
            empty_label = Label(
                text="No notes in this folder\nTap + to create a new note",
                font_name="assets/font/NotoSansLimbu-Regular.ttf",
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(150),
                color=(0.5, 0.5, 0.5, 1)
            )
            grid.add_widget(empty_label)
            return

        # Display notes
        for note in notes:
            note_widget = self.create_note_widget(note)
            grid.add_widget(note_widget)

        # Add "Last Notes" title at the end
        last_notes_title_container = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(50),
            spacing=dp(2)
        )

        # Last Notes title label
        last_notes_title_label = Label(
            text="Last Notes",
            font_size='18sp',
            bold=True,
            size_hint_y=None,
            height=dp(35),
            color=(0, 0, 0, 0.87),
            halign='left',
            valign='middle',
            text_size=(Window.width - (self.screen_padding * 2), None)
        )
        last_notes_title_label.bind(size=last_notes_title_label.setter('text_size'))

        # Simple separator line
        last_notes_separator = MDBoxLayout(
            size_hint_y=None,
            height=dp(1),
            md_bg_color=(0.8, 0.8, 0.8, 1)
        )

        last_notes_title_container.add_widget(last_notes_title_label)
        last_notes_title_container.add_widget(last_notes_separator)
        grid.add_widget(last_notes_title_container)

    def create_note_widget(self, note):
        """Create a responsive widget for displaying a note"""
        from kivymd.uix.card import MDCard

        # Note structure: (id, content, created, created_raw, note_date)
        # or (id, content, created) from older version
        note_id = note[0]
        note_content = note[1] if note[1] else "Empty note"
        note_date = note[2] if len(note) > 2 else ""  # The formatted date string

        # Calculate responsive font sizes based on screen width
        screen_width = Window.width
        content_font_size = max(12, min(16, screen_width // 25))
        date_font_size = max(10, min(13, screen_width // 30))
        icon_size = max(16, min(22, screen_width // 20))

        # Calculate padding and spacing
        horizontal_padding = min(dp(12), screen_width * 0.03)
        vertical_padding = min(dp(12), screen_width * 0.001)

        # Calculate available width for text content
        # Account for card padding and icon buttons
        text_available_width = screen_width - (horizontal_padding * 2) - dp(20)  # Reserve space for icons

        # Create card with responsive height
        card = MDCard(
            orientation='vertical',
            size_hint=(1, None),
            height=self.note_card_height,
            padding=[horizontal_padding, vertical_padding],
            spacing=min(dp(5), screen_width * 0.012),
            md_bg_color=(1, 1, 1, 1),
            elevation=2,
            ripple_behavior=True,
            radius=[min(dp(12), screen_width * 0.03), min(dp(12), screen_width * 0.03),
                    min(dp(12), screen_width * 0.03), min(dp(12), screen_width * 0.03)]
        )

        # Store note data
        card.note_id = note_id
        card.note_content = note_content

        # Calculate how many lines of text can fit based on card height
        line_height = content_font_size * 1.2  # Approximate line height
        max_lines = int((self.note_card_height * 0.55) / line_height)

        # Ensure at least 2 lines of text
        max_lines = max(2, max_lines)

        # Preview text with word wrapping
        preview = note_content

        # Create content label with proper text wrapping
        content_label = Label(
            text=preview,
            font_name="assets/font/NotoSansLimbu-Regular.ttf",
            font_size=f'{content_font_size}sp',
            size_hint_y=None,
            height=self.note_card_height * 0.55,  # Fixed height for text area
            text_size=(text_available_width, None),  # Width constraint for wrapping
            halign='left',
            valign='top',
            color=(0, 0, 0, 1),
            shorten=False,  # Don't shorten - allow wrapping
            markup=False
        )

        # Force text to wrap by setting text_size properly
        content_label.bind(size=content_label.setter('text_size'))
        content_label.text = preview  # Re-set text to trigger wrapping

        # If text exceeds max_lines, add ellipsis
        lines = content_label.text.split('\n')
        if len(lines) > max_lines:
            truncated_text = '\n'.join(lines[:max_lines - 1]) + '...'
            content_label.text = truncated_text
            content_label.height = self.note_card_height * 0.55  # Maintain height

        card.add_widget(content_label)

        # Footer with date and actions
        footer = MDBoxLayout(
            orientation='horizontal',
            spacing=min(dp(5), screen_width * 0.012),
            size_hint_y=None,
            height=self.note_card_height * 0.35,
            size_hint=(1, None),
            pos_hint={'center_y': 0.5},
        )

        # Date label with responsive width
        date_label = Label(
            text=note_date,
            font_name="assets/font/NotoSansLimbu-Regular.ttf",
            font_size=f'{date_font_size}sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_x=0.6,
            halign='left',
            valign='middle',
            shorten=True,
            text_size=(None, self.note_card_height * 0.35)
        )

        move_btn = MDIconButton(
            icon="folder-move",
            icon_size=f'{icon_size}sp',
            size_hint_x=None,
            width=min(dp(35), screen_width * 0.09),
            theme_text_color="Custom",
            text_color=(0.2, 0.6, 1, 1),
            ripple_scale=0.8
        )
        move_btn.bind(on_release=lambda x, nid=note_id: self.show_move_dialog(nid))

        edit_btn = MDIconButton(
            icon="pencil",
            icon_size=f'{icon_size}sp',
            size_hint_x=None,
            width=min(dp(35), screen_width * 0.09),
            theme_text_color="Custom",
            text_color=(0.4, 0.4, 0.4, 1),
            ripple_scale=0.8
        )
        edit_btn.bind(on_release=lambda x, nid=note_id: self.edit_note(nid))

        delete_btn = MDIconButton(
            icon="delete",
            icon_size=f'{icon_size}sp',
            size_hint_x=None,
            width=min(dp(35), screen_width * 0.09),
            theme_text_color="Custom",
            text_color=(1, 0.2, 0.2, 1),
            ripple_scale=0.8
        )
        delete_btn.bind(on_release=lambda x, nid=note_id: self.confirm_delete_note(nid))

        footer.add_widget(date_label)
        footer.add_widget(move_btn)
        footer.add_widget(edit_btn)
        footer.add_widget(delete_btn)

        card.add_widget(footer)

        # Make card clickable
        card.bind(on_release=lambda x, nid=note_id: self.edit_note(nid))

        return card

    def hex_to_rgba(self, hex_color):
        """Convert hex color to RGBA tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return (r / 255, g / 255, b / 255, 1)
        return (33 / 255, 150 / 255, 243 / 255, 1)

    def show_move_dialog(self, note_id):
        """Show dialog to select folder for moving note"""
        from database import get_all_folders

        folders = get_all_folders()
        if not folders:
            toast("No folders available. Create a folder first!")
            return

        # Create dialog with folder list
        content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(20),
            size_hint_y=None,
            height=dp(300)
        )

        # Title
        content.add_widget(Label(
            text="Move to Folder:",
            font_size='16sp',
            bold=True,
            size_hint_y=None,
            height=dp(30),
            color=(0, 0, 0, 1)
        ))

        # Scrollable folder list
        scroll = ScrollView(size_hint=(1, 0.9))
        folder_list = MDBoxLayout(
            orientation='vertical',
            spacing=dp(5),
            size_hint_y=None,
            height=len(folders) * dp(55)
        )

        # Add "All Notes" option
        all_notes_btn = MDFlatButton(
            text="All Notes",
            size_hint_y=None,
            height=dp(50),
            on_release=lambda x: self.move_note_to_folder(note_id, None)
        )
        folder_list.add_widget(all_notes_btn)

        # Add user folders
        for folder in folders:
            folder_btn = MDFlatButton(
                text=folder[1],  # folder name
                size_hint_y=None,
                height=dp(50),
                on_release=lambda x, fid=folder[0]: self.move_note_to_folder(note_id, fid)
            )
            folder_list.add_widget(folder_btn)

        scroll.add_widget(folder_list)
        content.add_widget(scroll)

        dialog = MDDialog(
            title="Move Note",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def move_note_to_folder(self, note_id, folder_id):
        """Move note to specified folder"""
        from database import update_note_folder

        if update_note_folder(note_id, folder_id):
            folder_name = "All Notes" if folder_id is None else self.get_folder_name(folder_id)
            toast(f"Note moved to {folder_name}")
            self.load_notes_in_folder()
        else:
            toast("Error moving note")

    def get_folder_name(self, folder_id):
        """Get folder name by ID"""
        from database import get_folder_by_id
        folder = get_folder_by_id(folder_id)
        return folder[1] if folder else "Unknown"

    def edit_note(self, note_id):
        """Open note in edit mode"""
        from database import get_note_by_id
        note = get_note_by_id(note_id)
        if note:
            app = MDApp.get_running_app()
            main_screen = app.root.get_screen('main_screen')
            main_screen.current_note_id = note_id
            main_screen.text_input.text = note[1] if note[1] else ""
            app.root.current = "main_screen"

    def confirm_delete_note(self, note_id):
        """Show confirmation dialog for deleting a note"""
        dialog = MDDialog(
            title="Delete Note",
            text="Are you sure you want to delete this note?",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="Delete",
                    on_release=lambda x: self.delete_note_action(note_id, dialog)
                )
            ]
        )
        dialog.open()

    def delete_note_action(self, note_id, dialog):
        """Execute note deletion"""
        from database import delete_note
        if delete_note(note_id):
            toast("Note deleted")
            self.load_notes_in_folder()
            self.load_folders()  # Update folder stats
        else:
            toast("Error deleting note")
        dialog.dismiss()

    def confirm_delete_folder(self, folder_id):
        """Show confirmation dialog for deleting a folder"""
        dialog = MDDialog(
            title="Delete Folder",
            text="Deleting this folder will move its notes to 'All Notes'. Continue?",
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="Delete",
                    on_release=lambda x: self.delete_folder_action(folder_id, dialog)
                )
            ]
        )
        dialog.open()

    def delete_folder_action(self, folder_id, dialog):
        """Execute folder deletion"""
        from database import delete_folder
        if delete_folder(folder_id):
            toast("Folder deleted")
            self.load_folders()
            if self.current_folder_id == folder_id:
                self.current_folder_id = None
                self.load_notes_in_folder()
                self.update_navigation_buttons()  # Update button visibility
        else:
            toast("Error deleting folder")
        dialog.dismiss()

    def edit_folder(self, folder_id, folder_name, color):
        """Edit existing folder"""
        from database import update_folder

        def on_save(new_name, new_color):
            if update_folder(folder_id, new_name, new_color):
                toast("Folder updated")
                self.load_folders()
            else:
                toast("Folder name already exists")

        dialog = FolderDialog(
            on_save=on_save,
            folder_data=(folder_id, folder_name, None, color)
        )
        dialog.open()

    def create_new_folder(self):
        """Create a new folder with color selection"""
        from database import create_folder

        def on_save(folder_name, color):
            if create_folder(folder_name, color):
                toast(f"Folder '{folder_name}' created")
                self.load_folders()
            else:
                toast("Folder name already exists")

        dialog = FolderDialog(on_save=on_save)
        dialog.open()

    def go_note_screen(self):
        """Navigate to note screen with current folder context"""
        app = MDApp.get_running_app()
        main_screen = app.root.get_screen('main_screen')
        main_screen.current_folder_id = self.current_folder_id
        main_screen.current_note_id = None
        main_screen.text_input.text = ""
        app.root.current = "main_screen"

    def update_stats(self):
        """Update dashboard statistics"""
        from database import get_note_stats
        stats = get_note_stats()
        # Update stats display if you have labels for them
        # For now, just reload folders to update counts
        self.load_folders()
        self.load_notes_in_folder()  # This will reload notes for current folder

class MainScreen(Screen):
    numpad_visible = BooleanProperty(False)
    text_input = ObjectProperty(None)
    numpad_height = NumericProperty(0)

    shift_active = BooleanProperty(False)
    shift_state = StringProperty('letters')

    undo_stack = []
    redo_stack = []
    max_stack_size = 100

    current_note_id = NumericProperty(None, allownone=True)  # Add allownone=True
    current_folder_id = NumericProperty(None, allownone=True)

    LIMBU_CHARS = {
        'letters': [
            "᥆", "᥇", "᥈", "᥉", "᥊", "᥋", "᥌", "᥍", "᥎", "᥏", "=",
            "ᤎ", "ᤗ", "ᤆ", "ᤋ", "ᤌ", "ᤃ", "ᤅ", "ᤕ", "ᤇ", "ᤣ", "ᤤ",
            "ᤒ", "ᤁ", "ᤔ", "ᤠ", "ᤏ", "ᤈ", "ᤘ", "ᤐ", "ᤡ", "ᤛ", "ᤢ",
            "ᤙ", "ᤜ", "ᤀ", "ᤂ", "ᤍ", "ᤗ", "ᤖ", "ᤑ", "ᤄ", "ᤥ", " ᤦ",
            "ᤰ", "ᤶ", "ᤳ", "ᤴ", "ᤸ", "ᤷ", "ᤱ", "ᤵ", ".", "ᤧ", "।",
        ],
        'shifted': [
            "I", "§", "!", "@", "#", "$", "£", "%", "^", "&", "*",
            "ᤩ", "ᤪ", "ᤫ", "ᤉ", "᥄", "᥅", "ᤝ", "᤹", "ᤊ", "ᤞ", "ᤚ",
            "᤺", "᤻", "?", "™", "(", ")",  "[", "]", "/", ":", ";",
            "{", "}", "+",  "÷", "-", ",", ".", "?",  "©", "<", ">",
            "~", "`", "̈", "„", "”", "…", "»", "«", "Ø", "©", "®",
        ]
    }

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.suggested_words = []
        self.current_suggestion_index = -1
        self._skip_text_update = False
        Clock.schedule_once(self._bind_text_input)

        self.save_state()

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        Clock.schedule_once(self.setup_focus, 0.1)
        # Only bind on_focus since we don't actually need on_keyboard for our case
        Window.bind(on_focus=self._on_window_focus)

        self.sound = None
        self.ctrl_sound()

    def _bind_text_input(self, dt):
        """Bind the text input after the widget is created"""
        self.text_input.bind(text=self.on_textinput_text)

    def on_textinput_text(self, instance, value):
        """Handle text changes without causing recursion"""
        if self._skip_text_update:
            return

        if value:
            words = value.split()
            current_word = words[-1] if words else ""
            if current_word:
                self._update_suggestions(current_word)
        else:
            self.ids.suggestion_words.text = ''
            self.suggested_words = []
            self.current_suggestion_index = -1

    def _update_suggestions(self, search_term):
        """Update suggestions from database"""
        from database import search_words_in_notes
        self.suggested_words = search_words_in_notes(search_term)

        if self.suggested_words:
            highlighted_suggestions = []
            for i, word in enumerate(self.suggested_words):
                if i == 0:
                    highlighted_suggestions.append(f"[b][color=00FF00]{word}[/color][/b]")
                else:
                    highlighted_suggestions.append(word)
            self.ids.suggestion_words.text = " | ".join(highlighted_suggestions)
            self.current_suggestion_index = 0
        else:
            self.ids.suggestion_words.text = ''
            self.current_suggestion_index = -1

    def _insert_suggestion(self, word):
        """Insert suggestion at cursor position and maintain focus/numpad"""
        if not word:
            return

        self._skip_text_update = True
        text = self.text_input.text
        cursor_pos = self.text_input.cursor_index()
        last_space = text.rfind(' ', 0, cursor_pos)
        last_newline = text.rfind('\n', 0, cursor_pos)
        word_start = max(last_space, last_newline)
        word_start = word_start + 1 if word_start != -1 else 0
        new_text = text[:word_start] + word + " " + text[cursor_pos:]
        new_cursor_pos = word_start + len(word) + 1
        self.text_input.text = new_text
        self.text_input.cursor = self.text_input.get_cursor_from_index(new_cursor_pos)
        self._skip_text_update = False

        # Clear suggestions after insertion
        self.ids.suggestion_words.text = ''
        self.suggested_words = []
        self.current_suggestion_index = -1

        # Force focus and ensure cursor visible
        Clock.schedule_once(lambda dt: self._force_focus_and_scroll(), 0.05)

    def _force_focus_and_scroll(self):
        """Force text input focus and ensure cursor is visible"""
        self.text_input.focus = True
        self._ensure_cursor_visible()
        # Ensure numpad stays visible
        self.numpad_visible = True

    def _maintain_input_focus(self):
        """Ensure text input stays focused and numpad remains visible"""
        self.text_input.focus = True
        self.numpad_visible = True
        Clock.schedule_once(lambda dt: self._ensure_cursor_visible(), 0.1)

    def on_touch_down(self, touch):
        """Handle suggestion selection with proper focus handling"""
        if self.ids.suggestion_words.collide_point(*touch.pos) and self.suggested_words:
            rel_x = touch.pos[0] - self.ids.suggestion_words.x
            total_width = self.ids.suggestion_words.width
            portion = rel_x / total_width
            index = min(int(portion * len(self.suggested_words)), len(self.suggested_words) - 1)
            self._insert_suggestion(self.suggested_words[index])
            return True
        return super(MainScreen, self).on_touch_down(touch)

    def _on_window_focus(self, instance, value):
        if value:
            self.text_input.focus = True
            self._ensure_cursor_visible()

    def toggle_shift(self, *args):
        """Cycle between letters and shifted characters"""
        self.text_input.focus = True
        self.numpad_visible = True

        # Toggle between 'letters' and 'shifted' states
        if self.shift_state == 'letters':
            self.shift_state = 'shifted'
        else:
            self.shift_state = 'letters'

        self.update_keypad_labels()
        return True

    def setup_command_buttons(self, dt):
        """Setup command buttons with proper focus handling"""
        number_row = self.ids.number_row
        for button in number_row.children:
            if button.icon == 'apple-keyboard-shift':
                button.bind(on_release=self.toggle_shift)
            elif button.icon == 'text-box-minus-outline':
                button.bind(on_release=lambda x: self.clear_text_input())
            elif button.icon == 'keyboard-space':
                button.bind(on_release=lambda x: self.insert_space())
            elif button.icon == 'backspace-outline':
                button.bind(on_release=lambda x: self.backspace())
            elif button.icon == 'keyboard-return':
                button.bind(on_release=lambda x: self.insert_newline())

    def update_keypad_labels(self):
        """Update keypad buttons based on current shift state"""
        # Find the grid layout containing the buttons
        numpad_grid = None
        for child in self.ids.numpad.children:
            if isinstance(child, GridLayout) and child.cols == 11:
                numpad_grid = child
                break

        if numpad_grid:
            # Get all Lim_Key_Pad_Button widgets
            buttons = [child for child in numpad_grid.children if hasattr(child, 'text')]

            # Ensure we have enough characters for all buttons
            current_chars = self.LIMBU_CHARS[self.shift_state]

            # Update each button's text
            for i, button in enumerate(reversed(buttons)):  # Reverse because GridLayout children are in reverse order
                if i < len(current_chars):
                    button.text = current_chars[i]
                else:
                    # Fallback for any extra buttons
                    button.text = " "

    def on_kv_post(self, *args):
        super().on_kv_post(*args)
        Clock.schedule_once(lambda dt: setattr(self.text_input, 'focus', True), 0.2)

    def setup_focus(self, dt):
        self.text_input.focus = True

    def on_textinput_focus(self, instance, value):
        # Don't lose focus if we're interacting with suggestions
        if not value and self.ids.suggestion_words.collide_point(*Window.mouse_pos):
            instance.focus = True
            return

        if not value and any(btn.state == 'down' for btn in self.ids.number_row.children):
            instance.focus = True
            return

        self.numpad_visible = value
        if value:
            self.show_numpad()
            instance._trigger_update_graphics()
        else:
            self.hide_numpad()
            self.save_state()

    def show_numpad(self):
        anim = Animation(numpad_height=390, duration=0.2)
        anim.start(self)

    def hide_numpad(self):
        anim = Animation(numpad_height=0, duration=0.2)
        anim.start(self)

    def insert_text(self, text):
        if self.text_input:
            cursor_pos = self.text_input.cursor_index()
            self.text_input.text = (self.text_input.text[:cursor_pos] +
                                    text + self.text_input.text[cursor_pos:])
            self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_pos + len(text))
            self.text_input.focus = True
            self._ensure_cursor_visible()
            self.save_state()

    def backspace(self):
        if not self.text_input or not self.text_input.text:
            return

        cursor_pos = self.text_input.cursor_index()
        if cursor_pos == 0:
            return

        text = self.text_input.text
        char_to_delete = text[cursor_pos - 1]

        if char_to_delete == '\n':
            pre_text = text[:cursor_pos - 1]
            post_text = text[cursor_pos:]
            self.text_input.text = pre_text + post_text
            new_cursor_pos = cursor_pos - 1
        elif ord(char_to_delete) >= 0x0300 and ord(char_to_delete) <= 0x036F:
            if cursor_pos > 1:
                self.text_input.text = text[:cursor_pos - 2] + text[cursor_pos:]
                new_cursor_pos = cursor_pos - 2
        else:
            self.text_input.text = text[:cursor_pos - 1] + text[cursor_pos:]
            new_cursor_pos = cursor_pos - 1

        self.text_input.cursor = self.text_input.get_cursor_from_index(new_cursor_pos)
        self.text_input.focus = True
        self._ensure_cursor_visible()
        self.text_input._trigger_update_graphics()
        self.save_state()

    def clear_text_input(self):
        if self.text_input:
            self.text_input.text = ''
            self.text_input.focus = True
            self.save_state()

    def insert_space(self):
        self.insert_text(' ')
        self.save_state()

    def insert_newline(self):
        if self.text_input:
            cursor_pos = self.text_input.cursor_index()
            self.text_input.text = (self.text_input.text[:cursor_pos] +
                                    '\n' +
                                    self.text_input.text[cursor_pos:])
            self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_pos + 1)
            self.text_input.focus = True
            self._ensure_cursor_visible()
            self.text_input._trigger_update_graphics()
            self.save_state()

    def _scroll_to_cursor_after_newline(self, cursor_pos):
        """Special handling for scrolling after newline insertion"""
        if not self.text_input:
            return
        lines = self.text_input._lines
        line_number = 0
        total_chars = 0
        for i, line in enumerate(lines):
            total_chars += len(line)
            if total_chars >= cursor_pos:
                line_number = i
                break
        total_lines = len(lines)
        visible_lines = max(1, int(self.text_input.height / self.text_input.line_height))

        if total_lines > visible_lines:
            target_scroll = 1 - (line_number / (total_lines - visible_lines))
            Animation(scroll_y=max(0, min(1, target_scroll)),
                      duration=0.1).start(self.text_input)
        self.text_input._trigger_update_graphics()

    def _ensure_cursor_visible(self):
        """Ensure cursor is visible in the viewport with proper line tracking"""
        if not self.text_input or not self.text_input.focus:
            return
        cursor_row = self.text_input.cursor_row
        total_lines = len(self.text_input._lines)
        visible_lines = max(1, int(self.text_input.height / self.text_input.line_height))

        if total_lines > visible_lines:
            # Calculate the visible area
            first_visible_line = int((1 - self.text_input.scroll_y) * (total_lines - visible_lines))
            last_visible_line = first_visible_line + visible_lines - 1

            if cursor_row < first_visible_line:
                target_scroll = 1 - (cursor_row / (total_lines - visible_lines))
            elif cursor_row > last_visible_line:
                target_scroll = 1 - ((cursor_row - visible_lines + 1) / (total_lines - visible_lines))
            else:
                return
            anim = Animation(scroll_y=max(0, min(1, target_scroll)),
                             duration=0.1)
            anim.start(self.text_input)

    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if text and (text.isdigit() or text == '.'):
            self.insert_text(text)
            return True
        elif keycode[1] == 'backspace':
            self.backspace()
            return True
        elif keycode[1] == 'enter':
            self.insert_newline()
            return True
        elif keycode[1] == 'spacebar':
            self.insert_space()
            return True
        return False

    def _on_keyboard(self, window, key, *args):
        """Handle keyboard events from Window"""
        if key == 13:
            self.insert_newline()
            return True
        elif key == 8:
            self.backspace()
            return True
        elif key == 32:
            self.insert_space()
            return True
        return False

    def close_note_screen(self):
        self.current_note_id = None
        app = MDApp.get_running_app()
        app.direction = "up"
        app.root.current = "dashboard_screen"
        self.ids.text_input.text = ""

    def adjust_appbar_width(self, dt):
        appbar = self.ids.floating_appbar
        scroll_view = self.ids.appbar_scroll
        button_count = len(appbar.children)
        button_width = dp(50)
        spacing = appbar.spacing * (button_count - 1)
        padding = appbar.padding[0] + appbar.padding[2]
        required_width = (button_width * button_count) + spacing + padding
        appbar.width = required_width
        if required_width > scroll_view.width:
            scroll_view.scroll_x = 0

    def open_menu(self, button):
        """Open share menu with auto left/right positioning based on available space"""
        button_pos = button.to_window(*button.pos)
        window_width = Window.width
        space_right = window_width - button_pos[0]
        space_left = button_pos[0]
        position = "bottom"
        hor_growth = "right" if space_right > space_left else "left"

        menu_items = [
            {
                "text": "Facebook",
                "viewclass": "OneLineListItem",
                "height": dp(48),
                "on_release": lambda: self.share_facebook(),
            },
            {
                "text": "Twitter",
                "viewclass": "OneLineListItem",
                "height": dp(48),
                "on_release": lambda: self.share_twitter(),
            },
            {
                "text": "LinkedIn",
                "viewclass": "OneLineListItem",
                "height": dp(48),
                "on_release": lambda: self.share_linkedin(),
            },
            {
                "text": "YouTube",
                "viewclass": "OneLineListItem",
                "height": dp(48),
                "on_release": lambda: self.share_youtube(),
            },
        ]

        max_width = dp(150)
        for item in menu_items:
            text_width = len(item["text"]) * dp(10)
            max_width = max(max_width, text_width + dp(48))

        self.menu = MDDropdownMenu(
            caller=button,
            items=menu_items,
            # width_mult=2,
            max_height=dp(48 * 4),
            position=position,
            ver_growth="down",
            hor_growth=hor_growth,
        )
        self.menu.open()

    def close_share_menu(self):
        self.menu.dismiss()

    def share_facebook(self):
        msg = self.ids.text_input.text
        from kivy.utils import platform

        if platform == 'ios':
            url = f"fb://profile"
            try:
                webbrowser.open(url)
            except Exception as e:
                url = f"https://www.facebook.com/sharer/sharer.php?u=&quote={msg}"
                webbrowser.open(url)

        elif platform == 'android':
            url = f"intent://#Intent;package=com.facebook.katana;scheme=fb;end"
            try:
                webbrowser.open(url)
            except Exception as e:
                url = f"https://www.facebook.com/sharer/sharer.php?u=&quote={msg}"
                webbrowser.open(url)
        else:
            url = f"https://www.facebook.com/sharer/sharer.php?u=&quote={msg}"
            webbrowser.open(url)
        self.close_share_menu()

    def share_twitter(self):
        """Share text via Twitter with platform-specific handling"""
        msg = self.ids.text_input.text
        from kivy.utils import platform

        import urllib.parse
        encoded_msg = urllib.parse.quote(msg)

        if platform == 'ios':
            twitter_app_url = f"twitter://post?message={encoded_msg}"
            twitter_web_url = f"https://twitter.com/intent/tweet?text={encoded_msg}"

            try:
                webbrowser.open(twitter_app_url)
            except Exception as e:
                webbrowser.open(twitter_web_url)

        elif platform == 'android':
            twitter_app_url = f"intent://twitter.com/intent/tweet?text={encoded_msg}#Intent;package=com.twitter.android;scheme=https;end"
            twitter_web_url = f"https://twitter.com/intent/tweet?text={encoded_msg}"

            try:
                webbrowser.open(twitter_app_url)
            except Exception as e:
                webbrowser.open(twitter_web_url)
        else:
            twitter_web_url = f"https://twitter.com/intent/tweet?text={encoded_msg}"
            webbrowser.open(twitter_web_url)
        self.close_share_menu()

    def share_linkedin(self):
        """Share text via LinkedIn with platform-specific handling"""
        msg = self.ids.text_input.text
        from kivy.utils import platform
        import urllib.parse
        encoded_msg = urllib.parse.quote(msg)

        if platform == 'ios':
            linkedin_app_url = "linkedin://profile"
            linkedin_web_url = f"https://www.linkedin.com/sharing/share-offsite/?url=&text={encoded_msg}"

            try:
                webbrowser.open(linkedin_app_url)
            except Exception as e:
                webbrowser.open(linkedin_web_url)
        elif platform == 'android':
            linkedin_app_url = f"intent://linkedin.com/#Intent;package=com.linkedin.android;scheme=https;end"
            linkedin_web_url = f"https://www.linkedin.com/sharing/share-offsite/?url=&text={encoded_msg}"

            try:
                webbrowser.open(linkedin_app_url)
            except Exception as e:
                webbrowser.open(linkedin_web_url)
        else:
            linkedin_web_url = f"https://www.linkedin.com/sharing/share-offsite/?url=&text={encoded_msg}"
            webbrowser.open(linkedin_web_url)
        self.close_share_menu()

    def share_youtube(self):
        """Share text via YouTube with platform-specific handling"""
        msg = self.ids.text_input.text
        from kivy.utils import platform
        import urllib.parse
        encoded_msg = urllib.parse.quote(msg)
        if platform == 'ios':
            youtube_app_url = "youtube://"
            youtube_web_url = "https://www.youtube.com"
            try:
                webbrowser.open(youtube_app_url)
                toast("Opened YouTube app - please share manually")
            except Exception as e:
                webbrowser.open(youtube_web_url)
        elif platform == 'android':
            youtube_app_url = f"intent://www.youtube.com/#Intent;package=com.google.android.youtube;scheme=https;end"
            youtube_web_url = "https://www.youtube.com"
            try:
                webbrowser.open(youtube_app_url)
                toast("Opened YouTube app - please share manually")
            except Exception as e:
                webbrowser.open(youtube_web_url)
        else:
            youtube_web_url = "https://www.youtube.com"
            webbrowser.open(youtube_web_url)
        self.close_share_menu()

    def copy(self):
        """Copy all text to clipboard with toast notification"""
        if self.text_input and self.text_input.text.strip():
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.text_input.text)
            toast("Copied All")
        else:
            toast("Note is empty - nothing to copy!")

    def paste(self):
        if self.text_input:
            from kivy.core.clipboard import Clipboard
            self.insert_text(Clipboard.paste())

    def save_state(self):
        """Save current text state to undo stack"""
        if self.text_input:
            current_text = self.text_input.text
            if self.undo_stack and self.undo_stack[-1] == current_text:
                return

            self.undo_stack.append(current_text)
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)
            self.redo_stack = []

    def save(self, button):
        """Save or update note with folder context"""
        if not self.text_input or not self.text_input.text.strip():
            toast("Note is empty - nothing to save!")
            return

        from database import convert_to_limbu_numbers

        init_db()
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            if self.current_note_id is not None:
                cursor.execute('''
                    UPDATE notes SET content = ? WHERE id = ?
                ''', (self.text_input.text, self.current_note_id))
                toast("Note updated successfully")
            else:
                raw_timestamp = datetime.now()
                formatted_timestamp = raw_timestamp.strftime('%d-%m-%Y | %H:%M:%S')
                limb_timestamp = convert_to_limbu_numbers(formatted_timestamp)
                # Make sure folder_id is being saved
                cursor.execute('''
                    INSERT INTO notes (content, created, created_raw, folder_id)
                    VALUES (?, ?, ?, ?)
                ''', (self.text_input.text, limb_timestamp, raw_timestamp, self.current_folder_id))
                toast("Note saved successfully")
            conn.commit()
            app = MDApp.get_running_app()
            dashboard = app.root.get_screen('dashboard_screen')
            dashboard.update_stats()
            # Also reload the current folder notes if we're in a folder
            if self.current_folder_id is not None:
                dashboard.load_notes_in_folder()
        except Exception as e:
            toast(f"Error saving note: {str(e)}")
        finally:
            conn.close()
            self.current_note_id = None

    def undo(self):
        """Undo the last text change"""
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            previous_text = self.undo_stack[-1]
            self.text_input.text = previous_text
            self.text_input.focus = True
            self._ensure_cursor_visible()

    def redo(self):
        """Redo the last undone change"""
        if self.redo_stack:
            self.undo_stack.append(self.redo_stack.pop())
            self.text_input.text = self.undo_stack[-1]
            self.text_input.focus = True
            self._ensure_cursor_visible()

    def show_selection_menu(self, touch):
        """Show context menu for text selection"""
        if not self.text_input.selection_text:
            return False
        box = BoxLayout(orientation='horizontal', size_hint=(None, None),
                        size=(dp(180), dp(48)), spacing=dp(5))
        cut_btn = Button(text='Cut', size_hint_x=None, width=dp(60))
        copy_btn = Button(text='Copy', size_hint_x=None, width=dp(60))
        paste_btn = Button(text='Paste', size_hint_x=None, width=dp(60))
        cut_btn.bind(on_release=lambda x: self.cut_selection())
        copy_btn.bind(on_release=lambda x: self.copy_selection())
        paste_btn.bind(on_release=lambda x: self.paste_text())
        box.add_widget(cut_btn)
        box.add_widget(copy_btn)
        box.add_widget(paste_btn)
        cursor_pos = self.text_input.to_window(*self.text_input.to_local(*touch.pos))
        self.selection_menu = Popup(
            title='',
            content=box,
            size_hint=(None, None),
            size=(dp(200), dp(80)),
            pos=(cursor_pos[0] - dp(100), cursor_pos[1] - dp(40)),
            auto_dismiss=True
        )
        self.selection_menu.open()
        return True

    def cut_selection(self):
        """Cut selected text to clipboard"""
        if self.text_input.selection_text:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.text_input.selection_text)
            self.delete_selection()
            self.selection_menu.dismiss()
            self.text_input.focus = True

    def copy_selection(self):
        """Copy selected text to clipboard"""
        if self.text_input.selection_text:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.text_input.selection_text)
            self.selection_menu.dismiss()
            self.text_input.focus = True

    def paste_text(self):
        """Paste text at cursor position"""
        from kivy.core.clipboard import Clipboard
        text = Clipboard.paste()
        if text:
            if self.text_input.selection_text:
                self.delete_selection()
            cursor_pos = self.text_input.cursor_index()
            self.text_input.text = (self.text_input.text[:cursor_pos] +
                                    text +
                                    self.text_input.text[cursor_pos:])
            self.text_input.cursor = self.text_input.get_cursor_from_index(
                cursor_pos + len(text))
            self.selection_menu.dismiss()
            self.text_input.focus = True

    def delete_selection(self):
        """Delete currently selected text"""
        if not self.text_input.selection_text:
            return
        text = self.text_input.text
        start, end = sorted((self.text_input.cursor_index(),
                             self.text_input.selection_from))
        self.text_input.text = text[:start] + text[end:]
        self.text_input.cursor = self.text_input.get_cursor_from_index(start)
        self.text_input.selection_text = ''

    def cmd_sound(self):
        if self.sound:
            try:
                self.sound.play()
            except Exception as e:
                print(f"Error playing sound: {e}")

    def ctrl_sound(self):
        try:
            # Use relative path that works on Android
            sound_path = 'clickbtn.mp3'
            if platform == 'android':
                # For Android, copy sound to accessible location
                from android.storage import app_storage_path
                import shutil
                assets_dir = app_storage_path()
                target_path = os.path.join(assets_dir, 'clickbtn.mp3')
                if not os.path.exists(target_path):
                    # Copy from assets if not exists
                    if os.path.exists('assets/sound/clickbtn.mp3'):
                        shutil.copy('assets/sound/clickbtn.mp3', target_path)
                sound_path = target_path

            self.sound = SoundLoader.load(sound_path)
            if not self.sound:
                print(f"Sound file not found at: {sound_path}")
        except Exception as e:
            print(f"Error loading sound: {e}")
            self.sound = None

class MainApp(MDApp):  # Remove "App" from inheritance
    def build(self):
        try:
            # Initialize database first
            from database import init_db
            init_db()

            self.title = 'Notes'
            Builder.load_file("main.kv")

            sm = ScreenManagement(transition=FadeTransition())
            sm.add_widget(DashboardScreen(name='dashboard_screen'))  # Commented out for now
            sm.add_widget(MainScreen(name='main_screen'))
            return sm
        except Exception as e:
            print(f"Error in build: {e}")
            # Show error screen or message
            from kivy.uix.label import Label
            return Label(text=f"App Error: {str(e)}")

    def on_start(self):
        """Called when app starts"""
        try:
            # Additional initialization
            pass
        except Exception as e:
            print(f"Error on start: {e}")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sound = None
        self.init_sound()

    def play_sound(self):
        if self.sound:
            try:
                self.sound.play()
            except Exception as e:
                print(f"Error playing sound: {e}")

    def init_sound(self):
        try:
            self.sound = SoundLoader.load('assets/sound/textsound.mp3')
            if not self.sound:
                print("Sound file not found or couldn't be loaded")
        except Exception as e:
            print(f"Error loading sound: {e}")

if __name__ == '__main__':
    MainApp().run()