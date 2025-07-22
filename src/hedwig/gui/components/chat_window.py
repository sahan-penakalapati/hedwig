"""
Chat window component for Hedwig GUI.

Provides a chat-style interface for interacting with Hedwig agents,
including message display, input handling, and conversation management.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
from typing import List, Dict, Any, Callable, Optional
import re
from datetime import datetime
import os

from hedwig.gui.styles import ThemeManager


class Message:
    """Represents a chat message with metadata."""
    
    def __init__(self, content: str, sender: str, timestamp: Optional[datetime] = None, message_type: str = "text"):
        """
        Initialize a message.
        
        Args:
            content: Message content
            sender: Message sender ("user" or "assistant" or "system")
            timestamp: Message timestamp (defaults to now)
            message_type: Type of message ("text", "code", "error")
        """
        self.content = content
        self.sender = sender
        self.timestamp = timestamp or datetime.now()
        self.message_type = message_type


class ChatWindow(tk.Frame):
    """
    Chat window component for message display and input.
    
    Features:
    - Scrollable message history
    - Syntax highlighting for code blocks
    - User input with send button
    - Message timestamps
    - Copy and export functionality
    """
    
    def __init__(self, parent: tk.Widget, on_send_message: Callable[[str], None], theme_manager: ThemeManager):
        """
        Initialize the chat window.
        
        Args:
            parent: Parent widget
            on_send_message: Callback function for sending messages
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.on_send_message = on_send_message
        self.theme_manager = theme_manager
        
        # Message storage
        self.messages: List[Message] = []
        
        self.create_widgets()
        self.apply_theme()
        self.setup_event_handlers()
    
    def create_widgets(self) -> None:
        """Create chat window widgets."""
        # Configure grid weights
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Message display area
        self.create_message_display()
        
        # Input area
        self.create_input_area()
        
        # Add welcome message
        self.add_system_message("Welcome to Hedwig AI! How can I help you today?")
    
    def create_message_display(self) -> None:
        """Create the scrollable message display area."""
        # Frame for message display
        display_frame = tk.Frame(self)
        display_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=(5, 0))
        display_frame.grid_rowconfigure(0, weight=1)
        display_frame.grid_columnconfigure(0, weight=1)
        
        # Scrolled text widget for messages
        self.message_display = scrolledtext.ScrolledText(
            display_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=20,
            font=("Arial", 10),
            cursor="arrow"
        )
        self.message_display.grid(row=0, column=0, sticky=tk.NSEW)
        
        # Configure text tags for styling
        self.setup_text_tags()
        
        # Bind context menu
        self.message_display.bind("<Button-3>", self.show_context_menu)
    
    def create_input_area(self) -> None:
        """Create the message input area."""
        # Input frame
        input_frame = tk.Frame(self)
        input_frame.grid(row=1, column=0, sticky=tk.EW, padx=5, pady=5)
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Text input
        self.input_text = tk.Text(
            input_frame,
            height=3,
            font=("Arial", 10),
            wrap=tk.WORD
        )
        self.input_text.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        # Send button
        self.send_button = tk.Button(
            input_frame,
            text="Send",
            command=self.send_message,
            width=8,
            font=("Arial", 10, "bold")
        )
        self.send_button.grid(row=0, column=1, sticky=tk.NS)
    
    def setup_text_tags(self) -> None:
        """Setup text formatting tags for the message display."""
        # Get theme colors
        theme = self.theme_manager.current_theme
        
        # User message style
        self.message_display.tag_config(
            "user",
            foreground=theme.text_primary,
            background=theme.bg_accent,
            font=("Arial", 10),
            lmargin1=10,
            lmargin2=10,
            rmargin=50,
            spacing1=5,
            spacing3=5
        )
        
        # Assistant message style
        self.message_display.tag_config(
            "assistant",
            foreground=theme.text_primary,
            background=theme.bg_tertiary,
            font=("Arial", 10),
            lmargin1=50,
            lmargin2=50,
            rmargin=10,
            spacing1=5,
            spacing3=5
        )
        
        # System message style
        self.message_display.tag_config(
            "system",
            foreground=theme.text_muted,
            background=theme.bg_secondary,
            font=("Arial", 9, "italic"),
            lmargin1=20,
            lmargin2=20,
            rmargin=20,
            spacing1=3,
            spacing3=3
        )
        
        # Error message style
        self.message_display.tag_config(
            "error",
            foreground=theme.error,
            background=theme.bg_secondary,
            font=("Arial", 10),
            lmargin1=10,
            lmargin2=10,
            rmargin=10,
            spacing1=5,
            spacing3=5
        )
        
        # Code block style
        self.message_display.tag_config(
            "code",
            foreground=theme.text_accent,
            background=theme.bg_primary,
            font=("Courier", 9),
            lmargin1=20,
            lmargin2=20,
            rmargin=20,
            spacing1=3,
            spacing3=3
        )
        
        # Timestamp style
        self.message_display.tag_config(
            "timestamp",
            foreground=theme.text_muted,
            font=("Arial", 8),
            justify=tk.RIGHT
        )
        
        # URL style
        self.message_display.tag_config(
            "url",
            foreground=theme.text_accent,
            underline=True,
            font=("Arial", 10)
        )
    
    def setup_event_handlers(self) -> None:
        """Setup event handlers for the chat window."""
        # Enter key sends message, Shift+Enter adds new line
        self.input_text.bind("<Return>", self.on_enter_key)
        self.input_text.bind("<Shift-Return>", self.on_shift_enter)
        
        # Enable/disable send button based on input
        self.input_text.bind("<KeyRelease>", self.update_send_button)
        
        # Auto-resize input text
        self.input_text.bind("<KeyPress>", self.auto_resize_input)
        
        # Focus management
        self.bind("<FocusIn>", lambda e: self.input_text.focus_set())
    
    def apply_theme(self) -> None:
        """Apply current theme to chat window."""
        theme = self.theme_manager.current_theme
        
        # Main frame
        self.configure(bg=theme.bg_secondary)
        
        # Message display
        self.message_display.configure(
            bg=theme.bg_primary,
            fg=theme.text_primary,
            selectbackground=theme.text_accent,
            selectforeground=theme.bg_primary,
            insertbackground=theme.text_primary
        )
        
        # Input text
        self.input_text.configure(
            bg=theme.input_bg,
            fg=theme.input_fg,
            insertbackground=theme.text_primary,
            selectbackground=theme.text_accent,
            selectforeground=theme.bg_primary
        )
        
        # Send button
        button_style = self.theme_manager.get_style_config("button")
        self.send_button.configure(**button_style)
        
        # Update text tags
        self.setup_text_tags()
    
    def add_message(self, message: Message) -> None:
        """
        Add a message to the chat display.
        
        Args:
            message: Message object to add
        """
        self.messages.append(message)
        
        # Enable text widget for editing
        self.message_display.config(state=tk.NORMAL)
        
        try:
            # Add timestamp
            timestamp_str = message.timestamp.strftime("%H:%M")
            self.message_display.insert(tk.END, f"[{timestamp_str}] ", "timestamp")
            
            # Add sender label
            if message.sender == "user":
                self.message_display.insert(tk.END, "You: ")
            elif message.sender == "assistant":
                self.message_display.insert(tk.END, "Hedwig: ")
            elif message.sender == "system":
                self.message_display.insert(tk.END, "System: ")
            
            # Process and add message content
            self.add_formatted_content(message.content, message.sender)
            
            # Add newlines
            self.message_display.insert(tk.END, "\n\n")
            
            # Auto-scroll to bottom
            self.message_display.see(tk.END)
            
        finally:
            # Disable text widget
            self.message_display.config(state=tk.DISABLED)
    
    def add_formatted_content(self, content: str, sender: str) -> None:
        """
        Add formatted content with syntax highlighting.
        
        Args:
            content: Message content
            sender: Message sender for styling
        """
        # Check for code blocks
        code_pattern = r'```(\w+)?\n(.*?)\n```'
        parts = re.split(code_pattern, content, flags=re.DOTALL)
        
        for i, part in enumerate(parts):
            if i % 3 == 0:  # Regular text
                if part.strip():
                    # Check for URLs
                    url_pattern = r'https?://\S+'
                    url_parts = re.split(f'({url_pattern})', part)
                    
                    for j, url_part in enumerate(url_parts):
                        if j % 2 == 0:  # Regular text
                            self.message_display.insert(tk.END, url_part, sender)
                        else:  # URL
                            self.message_display.insert(tk.END, url_part, "url")
                            
            elif i % 3 == 2:  # Code block content
                if part.strip():
                    self.message_display.insert(tk.END, part, "code")
    
    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        message = Message(content, "user")
        self.add_message(message)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        message = Message(content, "assistant")
        self.add_message(message)
    
    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        message = Message(content, "system")
        self.add_message(message)
    
    def add_error_message(self, content: str) -> None:
        """Add an error message."""
        message = Message(content, "system", message_type="error")
        self.add_message(message)
        
        # Use error styling
        self.message_display.config(state=tk.NORMAL)
        # Find the last added content and apply error tag
        current_pos = self.message_display.index(tk.END + "-2l")
        end_pos = self.message_display.index(tk.END + "-1l")
        self.message_display.tag_add("error", current_pos, end_pos)
        self.message_display.config(state=tk.DISABLED)
    
    def send_message(self) -> None:
        """Send the current message."""
        content = self.input_text.get("1.0", tk.END).strip()
        
        if not content:
            return
        
        # Clear input
        self.input_text.delete("1.0", tk.END)
        
        # Call callback
        if self.on_send_message:
            self.on_send_message(content)
        
        # Update send button state
        self.update_send_button()
    
    def on_enter_key(self, event) -> str:
        """Handle Enter key press."""
        self.send_message()
        return "break"  # Prevent default behavior
    
    def on_shift_enter(self, event) -> None:
        """Handle Shift+Enter key press."""
        # Allow default behavior (new line)
        pass
    
    def update_send_button(self, event=None) -> None:
        """Update send button state based on input content."""
        content = self.input_text.get("1.0", tk.END).strip()
        
        if content:
            self.send_button.config(state=tk.NORMAL)
        else:
            self.send_button.config(state=tk.DISABLED)
    
    def auto_resize_input(self, event=None) -> None:
        """Auto-resize input text based on content."""
        # Get number of lines
        lines = int(self.input_text.index(tk.END + '-1c').split('.')[0])
        
        # Limit height between 1 and 6 lines
        new_height = max(1, min(6, lines))
        current_height = int(self.input_text.cget("height"))
        
        if new_height != current_height:
            self.input_text.config(height=new_height)
    
    def clear_messages(self) -> None:
        """Clear all messages from the chat."""
        self.messages.clear()
        
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete("1.0", tk.END)
        self.message_display.config(state=tk.DISABLED)
        
        # Add welcome message
        self.add_system_message("New conversation started. How can I help you?")
    
    def export_messages(self, filename: str) -> None:
        """
        Export messages to a text file.
        
        Args:
            filename: Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Hedwig AI Conversation Export\n")
            f.write("=" * 40 + "\n\n")
            
            for message in self.messages:
                timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                sender = message.sender.title()
                
                f.write(f"[{timestamp}] {sender}:\n")
                f.write(message.content + "\n\n")
    
    def show_context_menu(self, event) -> None:
        """Show context menu for message display."""
        context_menu = tk.Menu(self, tearoff=0)
        
        # Apply theme
        menu_style = self.theme_manager.get_style_config("menu")
        context_menu.configure(**menu_style)
        
        # Add menu items
        context_menu.add_command(label="Copy", command=self.copy_selection)
        context_menu.add_command(label="Select All", command=self.select_all)
        context_menu.add_separator()
        context_menu.add_command(label="Clear Chat", command=self.clear_messages)
        context_menu.add_command(label="Export Chat...", command=self.export_chat_dialog)
        
        # Show menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def copy_selection(self) -> None:
        """Copy selected text to clipboard."""
        try:
            selected_text = self.message_display.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass  # No selection
    
    def select_all(self) -> None:
        """Select all text in message display."""
        self.message_display.tag_add(tk.SEL, "1.0", tk.END)
    
    def export_chat_dialog(self) -> None:
        """Show export chat dialog."""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            title="Export Chat",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.export_messages(filename)
                messagebox.showinfo("Export", f"Chat exported successfully to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export chat:\n{str(e)}")
    
    def get_message_count(self) -> int:
        """Get the number of messages."""
        return len(self.messages)
    
    def get_last_message(self) -> Optional[Message]:
        """Get the last message."""
        return self.messages[-1] if self.messages else None
    
    def search_messages(self, query: str, case_sensitive: bool = False) -> List[Message]:
        """
        Search messages for a query.
        
        Args:
            query: Search query
            case_sensitive: Whether search is case sensitive
            
        Returns:
            List of matching messages
        """
        results = []
        
        for message in self.messages:
            content = message.content if case_sensitive else message.content.lower()
            search_query = query if case_sensitive else query.lower()
            
            if search_query in content:
                results.append(message)
        
        return results