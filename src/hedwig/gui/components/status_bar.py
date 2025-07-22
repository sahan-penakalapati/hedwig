"""
Status bar component for Hedwig GUI.

Provides status messages, progress indication, and system information display.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import time
from datetime import datetime

from hedwig.gui.styles import ThemeManager


class StatusBar(tk.Frame):
    """
    Status bar component for displaying application status and progress.
    
    Features:
    - Status messages with color coding
    - Progress bar for long operations
    - Connection status indicator
    - Timestamp display
    """
    
    def __init__(self, parent: tk.Widget, theme_manager: ThemeManager):
        """
        Initialize the status bar.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # Status state
        self.current_status = "Ready"
        self.current_type = "success"
        self.progress_value = 0
        
        self.create_widgets()
        self.apply_theme()
    
    def create_widgets(self) -> None:
        """Create status bar widgets."""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        
        # Status message label
        self.status_label = tk.Label(
            self,
            text="Ready",
            anchor=tk.W,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.status_label.grid(row=0, column=0, sticky=tk.W+tk.E, padx=(0, 5))
        
        # Progress bar (initially hidden)
        self.progress_frame = tk.Frame(self)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=200
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            width=10
        )
        self.progress_label.pack(side=tk.LEFT)
        
        # Connection status indicator
        self.connection_frame = tk.Frame(self)
        self.connection_frame.grid(row=0, column=2, sticky=tk.E, padx=5)
        
        self.connection_dot = tk.Label(
            self.connection_frame,
            text="●",
            font=("Arial", 12),
            width=2
        )
        self.connection_dot.pack(side=tk.LEFT)
        
        self.connection_label = tk.Label(
            self.connection_frame,
            text="Connected",
            font=("Arial", 8)
        )
        self.connection_label.pack(side=tk.LEFT)
        
        # Timestamp
        self.time_label = tk.Label(
            self,
            text="",
            font=("Arial", 8),
            width=20,
            anchor=tk.E
        )
        self.time_label.grid(row=0, column=3, sticky=tk.E, padx=(5, 0))
        
        # Update time periodically
        self.update_time()
    
    def apply_theme(self) -> None:
        """Apply current theme to status bar."""
        # Get theme colors
        theme = self.theme_manager.current_theme
        
        # Main frame
        self.configure(bg=theme.bg_tertiary)
        
        # Status label
        status_colors = {
            "success": theme.success,
            "warning": theme.warning,
            "error": theme.error,
            "info": theme.info
        }
        
        status_color = status_colors.get(self.current_type, theme.text_primary)
        
        self.status_label.configure(
            bg=theme.bg_secondary,
            fg=status_color,
            font=("Arial", 9, "bold" if self.current_type != "success" else "normal")
        )
        
        # Progress frame and labels
        self.progress_frame.configure(bg=theme.bg_tertiary)
        self.progress_label.configure(
            bg=theme.bg_tertiary,
            fg=theme.text_secondary,
            font=("Arial", 8)
        )
        
        # Connection status
        self.connection_frame.configure(bg=theme.bg_tertiary)
        self.connection_dot.configure(
            bg=theme.bg_tertiary,
            fg=theme.success  # Green dot for connected
        )
        self.connection_label.configure(
            bg=theme.bg_tertiary,
            fg=theme.text_secondary
        )
        
        # Time label
        self.time_label.configure(
            bg=theme.bg_tertiary,
            fg=theme.text_muted
        )
    
    def set_status(self, message: str, status_type: str = "info") -> None:
        """
        Set the status message.
        
        Args:
            message: Status message to display
            status_type: Type of status ("success", "warning", "error", "info")
        """
        self.current_status = message
        self.current_type = status_type
        
        self.status_label.configure(text=message)
        self.apply_theme()  # Reapply theme to update colors
    
    def set_progress(self, value: int, message: str = "") -> None:
        """
        Set progress bar value.
        
        Args:
            value: Progress value (0-100)
            message: Optional progress message
        """
        self.progress_value = max(0, min(100, value))
        
        if value > 0:
            # Show progress bar
            self.progress_frame.grid(row=0, column=1, sticky=tk.W, padx=10)
            self.progress_bar.configure(value=self.progress_value)
            
            if message:
                self.progress_label.configure(text=message)
            else:
                self.progress_label.configure(text=f"{self.progress_value}%")
        else:
            # Hide progress bar
            self.progress_frame.grid_remove()
    
    def set_connection_status(self, connected: bool, message: str = "") -> None:
        """
        Set connection status indicator.
        
        Args:
            connected: Whether connection is active
            message: Optional connection message
        """
        theme = self.theme_manager.current_theme
        
        if connected:
            color = theme.success
            text = message or "Connected"
        else:
            color = theme.error
            text = message or "Disconnected"
        
        self.connection_dot.configure(fg=color)
        self.connection_label.configure(text=text)
    
    def show_temporary_message(self, message: str, status_type: str = "info", duration: int = 3000) -> None:
        """
        Show a temporary status message.
        
        Args:
            message: Message to display
            status_type: Type of status
            duration: Duration in milliseconds
        """
        # Save current status
        previous_status = self.current_status
        previous_type = self.current_type
        
        # Show temporary message
        self.set_status(message, status_type)
        
        # Restore previous status after duration
        self.after(duration, lambda: self.set_status(previous_status, previous_type))
    
    def update_time(self) -> None:
        """Update the timestamp display."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        
        # Schedule next update
        self.after(1000, self.update_time)
    
    def pulse_progress(self) -> None:
        """Start a pulsing progress animation for indeterminate operations."""
        self.progress_bar.configure(mode='indeterminate')
        self.progress_bar.start(10)
        self.progress_frame.grid(row=0, column=1, sticky=tk.W, padx=10)
    
    def stop_pulse(self) -> None:
        """Stop the pulsing progress animation."""
        self.progress_bar.stop()
        self.progress_bar.configure(mode='determinate', value=0)
        self.progress_frame.grid_remove()


class StatusBarManager:
    """
    Manager for coordinating status bar updates across the application.
    
    Provides centralized status management with message queuing and
    automatic timeout handling.
    """
    
    def __init__(self, status_bar: StatusBar):
        """
        Initialize the status bar manager.
        
        Args:
            status_bar: StatusBar widget to manage
        """
        self.status_bar = status_bar
        self.message_queue = []
        self.current_timeout_id: Optional[str] = None
    
    def show_status(self, message: str, status_type: str = "info", timeout: Optional[int] = None) -> None:
        """
        Show a status message with optional timeout.
        
        Args:
            message: Status message
            status_type: Type of status
            timeout: Timeout in milliseconds (None for permanent)
        """
        # Cancel any existing timeout
        if self.current_timeout_id:
            self.status_bar.after_cancel(self.current_timeout_id)
            self.current_timeout_id = None
        
        # Set the status
        self.status_bar.set_status(message, status_type)
        
        # Set timeout if specified
        if timeout:
            self.current_timeout_id = self.status_bar.after(
                timeout,
                lambda: self.show_status("Ready", "success")
            )
    
    def show_progress(self, message: str, progress: int) -> None:
        """
        Show progress with message.
        
        Args:
            message: Progress message
            progress: Progress value (0-100)
        """
        self.status_bar.set_status(message, "info")
        self.status_bar.set_progress(progress, f"{progress}%")
    
    def clear_progress(self) -> None:
        """Clear progress display and return to ready state."""
        self.status_bar.set_progress(0)
        self.show_status("Ready", "success")
    
    def show_error(self, error: str, timeout: int = 5000) -> None:
        """
        Show an error message with timeout.
        
        Args:
            error: Error message
            timeout: Timeout in milliseconds
        """
        self.show_status(f"Error: {error}", "error", timeout)
    
    def show_success(self, message: str, timeout: int = 3000) -> None:
        """
        Show a success message with timeout.
        
        Args:
            message: Success message
            timeout: Timeout in milliseconds
        """
        self.show_status(message, "success", timeout)