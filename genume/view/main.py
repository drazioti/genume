import gi
import os
import math
import logging as log
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from genume.registry.registry import Registry
from genume.view.event_panels import FixedVBox
from genume.registry.category import CategoryEntry
from genume.constants import ASSETS_ROOT, ASSETS_LOGO, ASSETS_REFRESH


CSS = os.path.join(ASSETS_ROOT, "styles.css")

# Default minimum window size.
WIDTH = 640
HEIGHT = 480


class MainWindow(Gtk.Window):
    selected_tab = None

    def __init__(self, titlebar=True):
        Gtk.Window.__init__(self, title="genume")
        self.set_default_size(WIDTH, HEIGHT)
        # Prepare registry and also start first refresh.
        self.refresh_progress = -1
        self.reg = Registry()
        self.reg.observer.connect("refresh_complete", self.finish_async_refresh)

        # Load css once.
        self.load_css()
        # Setup the layout.
        if titlebar:
            self.set_titlebar(self.generate_header_bar())
        self.main_view, self.roots_container = self.generate_main_view()
        self.add(self.main_view)
        # Handle events.
        self.connect("destroy", Gtk.main_quit)

        # Finish up and enter the main loop.
        self.show_all()
        self.refresh()
        Gtk.main()

    def refresh(self):
        """Updates the registry and refreshes the view."""
        if self.refresh_progress == -1:
            self.refresh_progress = 0
            self.reg.request_refresh()
        else:
            log.warn("User is being impatient!")

    def finish_async_refresh(self, _):
        """Applies new registry tree to view."""
        # 0: Get required objects.
        subtrees_container = self.subtrees_container
        roots_container = self.roots_container
        # 1: Clean up previous view.
        for i in range(subtrees_container.get_n_pages()):
            subtrees_container.remove_page(-1)
        for c in roots_container.get_children():
            roots_container.remove(c)
        # 2: Fill view from registy.
        root = self.reg.get_async_data()
        for name, entry in root.items():
            if isinstance(entry, CategoryEntry):
                self.generate_root_and_subtree(name, entry, roots_container, self.subtrees_container)
            else:
                log.error("Scripts on the root scripts folder are not supported yet!")
        # 3: Finish up
        self.refresh_progress = -1
        self.show_all()

    def generate_header_bar(self):
        bar = Gtk.HeaderBar(
            title="genume",
            show_close_button=True
        )

        menu_button = Gtk.MenuButton()
        menu_button.add(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_button.set_popup(self.generate_header_bar_menu())
        bar.pack_end(menu_button)
        return bar

    def generate_header_bar_menu(self):
        """Generates and returns a menu for the header bar menu button."""

        menu = Gtk.Menu(halign=Gtk.Align.END)

        def add(name, func):
            item = Gtk.MenuItem(name)
            item.connect("activate", func)
            menu.append(item)

        def add_separator():
            menu.append(Gtk.SeparatorMenuItem())

        add_separator()
        add("About", self.request_about)
        add("Close", self.request_close)

        menu.show_all()
        return menu

    def generate_main_view(self):
        """Generate and return the content of the window."""

        main_view = Gtk.Overlay()

        def scroll_wrap(container, vertical=False):
            s = Gtk.ScrolledWindow()
            s.set_policy(
                Gtk.PolicyType.AUTOMATIC if vertical else Gtk.PolicyType.NEVER,
                Gtk.PolicyType.AUTOMATIC)
            s.add(container)
            return s

        def set_button_location(s, b, allocation):
            allocation.x = 200 - 25
            allocation.y = HEIGHT - 100
            allocation.width = 50
            allocation.height = 50
            return allocation

        grid = Gtk.Box()
        grid.set_size_request(WIDTH, HEIGHT)
        main_view.add(grid)

        refresh_button = self.generate_refresh_button()
        main_view.add_overlay(refresh_button)
        # main_view.set_overlay_pass_through(refresh_button, True)
        main_view.connect("get-child-position", set_button_location)

        roots_container = self.generate_roots_container()

        # The inner container is used so that the only content that is
        # scrollable is the tabs and not the logo.
        inner_container = Gtk.VBox()
        inner_container.pack_end(scroll_wrap(roots_container), True, True, 0)

        grid.pack_start(inner_container, False, False, 0)

        subtrees_container = self.generate_subtrees_container()

        grid.pack_start(scroll_wrap(subtrees_container, True), True, True, 0)

        # Fill the layout.

        # Add logo.
        inner_container.pack_start(self.load_logo(), False, False, 0)

        self.subtrees_container = subtrees_container
        return (main_view, roots_container)

    def load_css(self):
        style_provider = Gtk.CssProvider()

        css = open(CSS, 'rb')
        css_data = css.read()
        css.close()

        style_provider.load_from_data(css_data)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def load_logo(self):
        logo = Item()
        logo.setImage(ASSETS_LOGO)
        logo.noEventListeners()
        logo.addClass("logo")
        return logo

    def generate_refresh_button(self):
        container = Gtk.Fixed()
        container.set_size_request(50, 50)
        event = Gtk.EventBox()
        event.set_size_request(50, 50)
        button = Gtk.Box()
        icon = Gtk.Image()
        icon.set_from_file(ASSETS_REFRESH)
        icon.set_opacity(0.9)
        button.pack_start(icon, True, True, 0)
        button.get_style_context().add_class("refresh-button")

        def on_mouse_enter(w, e):
            self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
            button.get_style_context().add_class("refresh-button-hover")

        def on_mouse_leave(w, e):
            self.get_window().set_cursor(None)
            button.get_style_context().remove_class("refresh-button-hover")

        def refresh(w, e):
            self.request_refresh(self)

        event.connect("button-press-event", refresh)
        event.connect("enter-notify-event", on_mouse_enter)

        event.connect("leave-notify-event", on_mouse_leave)

        event.add(button)
        container.add(event)

        return container

    def generate_root_and_subtree(self, name, entry: CategoryEntry, roots_container, subtrees_container):
        """Generate a root tab and the corresponding subtree view."""

        root = self.generate_root(name, entry)
        roots_container.pack_start(root, False, False, 0)

        subtree = self.generate_subtree(name, entry)
        subtrees_container.append_page(subtree, Gtk.Label(label=name))

        # Setup the events.
        root.page_index = subtrees_container.get_n_pages() - 1
        root.parent = self

    def generate_roots_container(self):
        mainBox = Gtk.VBox()
        mainBox.set_name("tab-holder")

        return mainBox

    def generate_root(self, name, entry: CategoryEntry):
        """Generate the tab like button that correspond to the given entry."""

        item = Item()
        item.setTitle(name)

        # Make the first tab active.
        if (self.selected_tab is None):
            self.selected_tab = item
            item.addClass("tab-active")

        # After refresh:
        # Keep the active atribute of the selected class.
        if (self.selected_tab is not None and item.title == self.selected_tab.title):
            self.selected_tab = item
            item.addClass("tab-active")

        return item

    def generate_subtrees_container(self):
        backBox = Gtk.Notebook(show_tabs=False)
        # backBox.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse(primary_color_light))
        return backBox

    def generate_subtree(self, name, entry: CategoryEntry):
        """Generate the list like view that correspond to the given entry."""
        log.debug("Adding %d entries to %s" % (len(entry), name))
        tree = Gtk.TreeView(self.create_treestore(entry))
        tree.expand_all()
        # Enable this if the show_tabs value is set to True.
        # tree.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse(primary_color_light))

        # TODO: find a way to set this background
        for i, column_title in enumerate(["Name", "Value"]):
            tree.append_column(Gtk.TreeViewColumn(
                column_title,
                Gtk.CellRendererText(),
                text=i
            ))
        return tree

    def create_treestore(self, entry: CategoryEntry):
        store = Gtk.TreeStore(str, str)
        self.create_subtreestore(store, None, entry)
        return store

    def create_subtreestore(self, store, parent, entry: CategoryEntry):
        for name, entry in entry.items():
            if isinstance(entry, CategoryEntry):
                x = store.append(parent, [self.format_name(name), None])
                self.create_subtreestore(store, x, entry)
            else:
                store.append(parent, [self.format_name(name), repr(entry)])

    def format_name(self, name):
        # TODO: extend
        return name.replace("_", " ")

    def show_root(self, button):
        """Changes to the tab given by the page_index value of the button."""
        self.subtrees_container.set_current_page(button.page_index)

    def request_refresh(self, _):
        self.refresh()

    def request_about(self, _):
        # TODO: show about dialog
        pass

    def request_close(self, _):
        self.close()

    def show_root(self, page_index):
        self.subtrees_container.set_current_page(page_index)


class Item(FixedVBox):
    """This class represents a root element."""

    title = ""
    page_index = ""
    parent = MainWindow

    def __init__(self):
        FixedVBox.__init__(self)

        self.setSize(200, 50)

        self.setOnClickHandler(self.on_click)
        self.setOnMouseEnterHandler(self.on_mouse_enter)
        self.setOnMouseLeaveHandler(self.on_mouse_leave)

    def setTitle(self, title=""):
        label = Gtk.Label(title)
        label.get_style_context().add_class("label")
        self.addChild(label)
        self.title = title

    def setImage(self, path):
        image = Gtk.Image()
        image.set_from_file(path)
        self.addChild(image)

    def noEventListeners(self):
        self.removeOnClickHandler()
        self.removeOnMouseEnterHandler()
        self.removeOnMouseLeaveHandler()

    # Event handlers.

    def on_click(self, widget, event):
        log.info("Switching to %d" % (self.page_index))
        self.parent.show_root(self.page_index)
        self.addClass("tab-active")
        if(self.parent.selected_tab is not None):
            self.parent.selected_tab.removeClass("tab-active")
        self.parent.selected_tab = self

    def on_mouse_enter(self, widget, event):
        self.addClass("tab-hover")
        self.parent.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_mouse_leave(self, widget, event):
        self.removeClass("tab-hover")
        self.parent.get_window().set_cursor(None)
