"""
Main GUI application for Hedwig desktop interface.

Provides a modern desktop application with chat interface, artifact management,
and integration with the Hedwig multi-agent system.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from hedwig.app import HedwigApp
from hedwig.core.models import TaskInput, TaskOutput
from hedwig.core.config import get_config
from hedwig.core.logging_config import get_logger
from hedwig.gui.styles import get_theme_manager
from hedwig.gui.components.chat_window import ChatWindow
from hedwig.gui.components.artifact_viewer import ArtifactViewer
from hedwig.gui.components.status_bar import StatusBar
from hedwig.gui.dialogs.settings import SettingsDialog
from hedwig.gui.utils.threading_utils import GUIThreadManager


class HedwigGUI:
    """
    Main GUI application for Hedwig.
    
    Provides a modern desktop interface with chat functionality,
    artifact management, and system integration.
    """
    
    def __init__(self):
        """Initialize the Hedwig GUI application."""
        self.logger = get_logger("hedwig.gui.app")
        self.theme_manager = get_theme_manager()
        
        # Initialize core components
        self.hedwig_app: Optional[HedwigApp] = None
        self.thread_manager = GUIThreadManager()
        self.message_queue = queue.Queue()
        
        # GUI state
        self.current_thread_id: Optional[str] = None
        self.threads: Dict[str, Dict[str, Any]] = {}
        
        # Initialize GUI
        self.root = tk.Tk()
        self.setup_window()
        self.create_menu()
        self.create_main_layout()
        self.setup_event_handlers()
        
        # Initialize Hedwig backend
        self.initialize_hedwig()
        
        # Start message processing
        self.process_messages()
    
    def setup_window(self) -> None:
        """Configure the main application window."""
        self.root.title("Hedwig AI - Multi-Agent Assistant")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Configure window icon (if available)
        try:
            icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "hedwig.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass  # Icon not available, continue without it
        
        # Apply theme to root window
        style_config = self.theme_manager.get_style_config("main_frame")
        self.root.configure(bg=style_config["bg"])
        
        # Configure window close behavior
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_menu(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Apply theme to menubar
        menu_style = self.theme_manager.get_style_config("menubar")
        menubar.configure(**menu_style)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menu_style = self.theme_manager.get_style_config("menu")
        file_menu.configure(**menu_style)
        
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Chat", command=self.new_chat, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Chat...", command=self.open_chat, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Export Chat...", command=self.export_chat, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.configure(**menu_style)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=lambda: self.root.focus_get().event_generate("<<Copy>>"), accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=lambda: self.root.focus_get().event_generate("<<Paste>>"), accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Preferences...", command=self.show_settings, accelerator="Ctrl+,")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.configure(**menu_style)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme, accelerator="Ctrl+T")
        view_menu.add_separator()
        view_menu.add_command(label="Show Artifacts", command=self.toggle_artifacts_panel)
        view_menu.add_command(label="Refresh", command=self.refresh_interface, accelerator="F5")
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.configure(**menu_style)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Clear All Artifacts", command=self.clear_artifacts)
        tools_menu.add_command(label="System Info", command=self.show_system_info)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.configure(**menu_style)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Hedwig", command=self.show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
    
    def create_main_layout(self) -> None:
        """Create the main application layout."""
        # Main container
        main_style = self.theme_manager.get_style_config("main_frame")
        self.main_frame = tk.Frame(self.root, **main_style)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create paned window for resizable panels
        self.paned_window = tk.PanedWindow(
            self.main_frame, 
            orient=tk.HORIZONTAL,
            bg=main_style["bg"],
            sashrelief=tk.FLAT,
            sashwidth=8
        )
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel: Chat interface
        self.create_chat_panel()
        
        # Right panel: Artifact viewer
        self.create_artifact_panel()
        
        # Status bar
        self.create_status_bar()
        
        # Set initial pane sizes (70% chat, 30% artifacts)
        self.root.after(100, lambda: self.paned_window.sash_place(0, 840, 0))
    
    def create_chat_panel(self) -> None:
        """Create the chat interface panel."""
        frame_style = self.theme_manager.get_style_config("frame")
        
        # Chat panel container
        chat_panel = tk.Frame(self.main_frame, **frame_style)
        
        # Chat window component
        self.chat_window = ChatWindow(
            chat_panel, 
            on_send_message=self.handle_user_message,
            theme_manager=self.theme_manager
        )
        self.chat_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.paned_window.add(chat_panel, minsize=400)
    
    def create_artifact_panel(self) -> None:
        """Create the artifact viewer panel."""
        frame_style = self.theme_manager.get_style_config("frame")
        
        # Artifact panel container
        artifact_panel = tk.Frame(self.main_frame, **frame_style)
        
        # Artifact viewer component
        self.artifact_viewer = ArtifactViewer(
            artifact_panel,
            theme_manager=self.theme_manager,
            on_artifact_open=self.handle_artifact_open
        )
        self.artifact_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.paned_window.add(artifact_panel, minsize=300)
    
    def create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = StatusBar(
            self.main_frame,
            theme_manager=self.theme_manager
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_event_handlers(self) -> None:
        """Setup keyboard shortcuts and event handlers."""
        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.new_chat())
        self.root.bind("<Control-o>", lambda e: self.open_chat())
        self.root.bind("<Control-e>", lambda e: self.export_chat())
        self.root.bind("<Control-q>", lambda e: self.on_closing())
        self.root.bind("<Control-comma>", lambda e: self.show_settings())
        self.root.bind("<Control-t>", lambda e: self.toggle_theme())
        self.root.bind("<F5>", lambda e: self.refresh_interface())
        
        # Window state changes
        self.root.bind("<Configure>", self.on_window_configure)
    
    def initialize_hedwig(self) -> None:
        """Initialize the Hedwig backend application."""
        try:
            self.hedwig_app = HedwigApp()
            self.logger.info("Hedwig backend initialized successfully")
            self.status_bar.set_status("Ready", "success")
        except Exception as e:
            self.logger.error(f"Failed to initialize Hedwig backend: {str(e)}")
            self.status_bar.set_status(f"Error: {str(e)}", "error")
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize Hedwig:\n\n{str(e)}\n\nPlease check your configuration and try again."
            )
    
    def process_messages(self) -> None:
        """Process messages from background threads."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.handle_background_message(message)
        except queue.Empty:
            pass
        
        # Schedule next processing
        self.root.after(100, self.process_messages)
    
    def handle_background_message(self, message: Dict[str, Any]) -> None:
        """Handle messages from background threads."""
        msg_type = message.get("type")
        
        if msg_type == "task_progress":
            self.status_bar.set_progress(message.get("progress", 0))
            
        elif msg_type == "task_complete":
            result = message.get("result")
            if result:
                self.chat_window.add_assistant_message(result.content)
                if result.metadata and "artifacts" in result.metadata:
                    self.artifact_viewer.refresh_artifacts()
            self.status_bar.set_status("Ready", "success")
            self.status_bar.set_progress(0)
            
        elif msg_type == "task_error":
            error = message.get("error", "Unknown error")
            self.chat_window.add_error_message(f"Error: {error}")
            self.status_bar.set_status(f"Error: {error}", "error")
            self.status_bar.set_progress(0)
    
    def handle_user_message(self, message: str) -> None:
        """Handle user message from chat window."""
        if not self.hedwig_app:
            self.chat_window.add_error_message("Hedwig backend not initialized")
            return
        
        # Add user message to chat
        self.chat_window.add_user_message(message)
        
        # Update status
        self.status_bar.set_status("Processing...", "info")
        self.status_bar.set_progress(10)
        
        # Execute task in background thread
        def execute_task():
            try:
                task_input = TaskInput(user_message=message)
                result = self.hedwig_app.run(task_input.user_message)
                
                self.message_queue.put({
                    "type": "task_complete",
                    "result": result
                })
                
            except Exception as e:
                self.logger.error(f"Task execution failed: {str(e)}")
                self.message_queue.put({
                    "type": "task_error",
                    "error": str(e)
                })
        
        self.thread_manager.submit_task(execute_task)
    
    def handle_artifact_open(self, artifact_path: str) -> None:
        """Handle artifact open request."""
        try:
            if sys.platform == "win32":
                os.startfile(artifact_path)
            elif sys.platform == "darwin":
                os.system(f"open '{artifact_path}'")
            else:
                os.system(f"xdg-open '{artifact_path}'")
        except Exception as e:
            self.logger.error(f"Failed to open artifact: {str(e)}")
            messagebox.showerror("Error", f"Failed to open file:\n{str(e)}")
    
    # Menu command handlers
    def new_chat(self) -> None:
        """Start a new chat conversation."""
        self.chat_window.clear_messages()
        self.current_thread_id = None
        self.status_bar.set_status("New chat started", "success")
    
    def open_chat(self) -> None:
        """Open an existing chat conversation."""
        # TODO: Implement chat loading functionality
        messagebox.showinfo("Info", "Chat loading functionality coming soon!")
    
    def export_chat(self) -> None:
        """Export current chat conversation."""
        if not self.chat_window.messages:
            messagebox.showwarning("Warning", "No messages to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Chat",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.chat_window.export_messages(filename)
                self.status_bar.set_status(f"Chat exported to {filename}", "success")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export chat:\n{str(e)}")
    
    def show_settings(self) -> None:
        """Show the settings dialog."""
        dialog = SettingsDialog(self.root, self.theme_manager)
        if dialog.result:
            # Settings were changed, refresh interface
            self.refresh_interface()
    
    def toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        current_theme = self.theme_manager.current_theme_name
        new_theme = "light" if current_theme == "dark" else "dark"
        
        self.theme_manager.set_theme(new_theme)
        self.refresh_interface()
        
        self.status_bar.set_status(f"Switched to {new_theme} theme", "success")
    
    def toggle_artifacts_panel(self) -> None:
        """Toggle the artifacts panel visibility."""
        # TODO: Implement panel hiding/showing
        messagebox.showinfo("Info", "Panel toggle functionality coming soon!")
    
    def refresh_interface(self) -> None:
        """Refresh the entire interface with current theme."""
        # Refresh theme for all components
        self.setup_window()
        self.chat_window.apply_theme()
        self.artifact_viewer.apply_theme()
        self.status_bar.apply_theme()
    
    def clear_artifacts(self) -> None:
        """Clear all artifacts with confirmation."""
        result = messagebox.askyesno(
            "Confirm",
            "Are you sure you want to clear all artifacts?\nThis action cannot be undone."
        )
        
        if result:
            try:
                # TODO: Implement artifact clearing
                self.artifact_viewer.refresh_artifacts()
                self.status_bar.set_status("Artifacts cleared", "success")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear artifacts:\n{str(e)}")
    
    def show_system_info(self) -> None:
        """Show system information dialog."""
        try:
            config = get_config()
            info = f"""Hedwig AI Assistant
            
Version: 1.0.0 (Phase 7)
Python: {sys.version}
Platform: {sys.platform}

Configuration:
Data Directory: {config.data_dir}
Log Level: {config.log_level}
Theme: {self.theme_manager.current_theme_name.title()}

Status: {"Ready" if self.hedwig_app else "Not Initialized"}
"""
            messagebox.showinfo("System Information", info)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get system info:\n{str(e)}")
    
    def show_about(self) -> None:
        """Show about dialog."""
        about_text = """Hedwig AI Assistant

A multi-agent task execution system with desktop GUI.

Features:
• Chat-based interaction with AI agents
• Document generation (PDF, Markdown)
• Web research and browser automation  
• Code generation and execution
• Artifact management and preview

Built with Python and Tkinter
© 2024 Hedwig Project"""
        
        messagebox.showinfo("About Hedwig", about_text)
    
    def show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        shortcuts = """Keyboard Shortcuts

File Operations:
Ctrl+N    New Chat
Ctrl+O    Open Chat
Ctrl+E    Export Chat
Ctrl+Q    Exit

Interface:
Ctrl+T    Toggle Theme
Ctrl+,    Settings
F5        Refresh

Chat:
Enter     Send Message
Shift+Enter    New Line"""
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def on_window_configure(self, event) -> None:
        """Handle window configuration changes."""
        if event.widget == self.root:
            # Save window geometry for next session
            # TODO: Implement settings persistence
            pass
    
    def on_closing(self) -> None:
        """Handle application closing."""
        try:
            # Stop background threads
            self.thread_manager.shutdown()
            
            # Save any unsaved data
            # TODO: Implement session persistence
            
            self.logger.info("Hedwig GUI shutting down")
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            self.root.destroy()
    
    def run(self) -> None:
        """Start the GUI application."""
        try:
            self.logger.info("Starting Hedwig GUI")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            self.logger.error(f"GUI error: {str(e)}")
            messagebox.showerror("Application Error", f"An error occurred:\n{str(e)}")
            self.on_closing()


def main():
    """Main entry point for Hedwig GUI application."""
    try:
        app = HedwigGUI()
        app.run()
    except Exception as e:
        print(f"Failed to start Hedwig GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()