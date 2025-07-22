"""
Settings dialog for Hedwig GUI configuration.

Provides a comprehensive settings interface for API keys, preferences,
and system configuration.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional
import os
from pathlib import Path

from hedwig.core.config import get_config
from hedwig.core.logging_config import get_logger
from hedwig.gui.styles import ThemeManager


class SettingsDialog:
    """
    Settings configuration dialog.
    
    Provides tabbed interface for different categories of settings:
    - API Keys and Authentication
    - Agent Configuration
    - Tool Settings
    - UI Preferences
    - Advanced Options
    """
    
    def __init__(self, parent: tk.Widget, theme_manager: ThemeManager):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent window
            theme_manager: Theme manager for styling
        """
        self.parent = parent
        self.theme_manager = theme_manager
        self.logger = get_logger("hedwig.gui.settings")
        
        # Dialog result
        self.result = False
        
        # Settings values
        self.settings = {}
        self.load_settings()
        
        # Create dialog
        self.create_dialog()
    
    def create_dialog(self) -> None:
        """Create the settings dialog window."""
        # Create dialog window
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Hedwig Settings")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.center_dialog()
        
        # Apply theme
        theme = self.theme_manager.current_theme
        self.dialog.configure(bg=theme.bg_primary)
        
        # Create main layout
        self.create_main_layout()
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # Focus on dialog
        self.dialog.focus_set()
    
    def center_dialog(self) -> None:
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get dialog size
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def create_main_layout(self) -> None:
        """Create the main dialog layout."""
        # Configure grid
        self.dialog.grid_rowconfigure(0, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)
        
        # Main frame
        main_frame = tk.Frame(self.dialog)
        main_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.create_notebook(main_frame)
        
        # Button frame
        self.create_button_frame(main_frame)
    
    def create_notebook(self, parent: tk.Widget) -> None:
        """Create the tabbed notebook interface."""
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 10))
        
        # Create tabs
        self.create_api_tab()
        self.create_agents_tab()
        self.create_tools_tab()
        self.create_ui_tab()
        self.create_advanced_tab()
    
    def create_api_tab(self) -> None:
        """Create API keys and authentication tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="API Keys")
        
        # Scrollable frame
        canvas = tk.Canvas(tab_frame)
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # API key entries
        row = 0
        
        # OpenAI API Key
        self.create_api_key_section(
            scrollable_frame, row, 
            "OpenAI API Key", "OPENAI_API_KEY",
            "Required for AI agent functionality"
        )
        row += 3
        
        # Anthropic API Key (Optional)
        self.create_api_key_section(
            scrollable_frame, row,
            "Anthropic API Key", "ANTHROPIC_API_KEY", 
            "Optional alternative to OpenAI"
        )
        row += 3
        
        # Firecrawl API Key
        self.create_api_key_section(
            scrollable_frame, row,
            "Firecrawl API Key", "FIRECRAWL_API_KEY",
            "For web scraping and research tools"
        )
        row += 3
        
        # Brave Search API Key
        self.create_api_key_section(
            scrollable_frame, row,
            "Brave Search API Key", "BRAVE_SEARCH_API_KEY",
            "For enhanced web search capabilities"
        )
    
    def create_api_key_section(self, parent: tk.Widget, row: int, label: str, key: str, description: str) -> None:
        """Create an API key input section."""
        # Label
        tk.Label(parent, text=label, font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=(10, 0)
        )
        
        # Description
        tk.Label(parent, text=description, font=("Arial", 9), fg="gray").grid(
            row=row+1, column=0, columnspan=2, sticky=tk.W, padx=5
        )
        
        # Entry frame
        entry_frame = tk.Frame(parent)
        entry_frame.grid(row=row+2, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=(5, 0))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        # Entry widget
        var = tk.StringVar(value=self.settings.get(key, ""))
        entry = tk.Entry(entry_frame, textvariable=var, show="*", font=("Arial", 10))
        entry.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        # Show/hide button
        def toggle_visibility():
            if entry.cget("show") == "*":
                entry.config(show="")
                toggle_btn.config(text="Hide")
            else:
                entry.config(show="*")
                toggle_btn.config(text="Show")
        
        toggle_btn = tk.Button(entry_frame, text="Show", command=toggle_visibility)
        toggle_btn.grid(row=0, column=1)
        
        # Store reference
        setattr(self, f"{key.lower()}_var", var)
    
    def create_agents_tab(self) -> None:
        """Create agent configuration tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Agents")
        
        # Agent settings
        settings_frame = tk.Frame(tab_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row = 0
        
        # LLM Model selection
        tk.Label(settings_frame, text="LLM Model:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        
        self.model_var = tk.StringVar(value=self.settings.get("HEDWIG_LLM_MODEL", "gpt-4"))
        model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            values=["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"],
            state="readonly"
        )
        model_combo.grid(row=row, column=1, sticky=tk.EW, padx=(10, 0), pady=(0, 5))
        row += 1
        
        # Max retries
        tk.Label(settings_frame, text="Max Retries:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        
        self.retries_var = tk.StringVar(value=self.settings.get("HEDWIG_MAX_RETRIES", "3"))
        retries_spin = tk.Spinbox(
            settings_frame,
            from_=1, to=10,
            textvariable=self.retries_var,
            width=10
        )
        retries_spin.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        row += 1
        
        # Security timeout
        tk.Label(settings_frame, text="Security Timeout (seconds):", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        
        self.timeout_var = tk.StringVar(value=self.settings.get("HEDWIG_SECURITY_TIMEOUT", "10"))
        timeout_spin = tk.Spinbox(
            settings_frame,
            from_=5, to=60,
            textvariable=self.timeout_var,
            width=10
        )
        timeout_spin.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        
        settings_frame.grid_columnconfigure(1, weight=1)
    
    def create_tools_tab(self) -> None:
        """Create tools configuration tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Tools")
        
        # Tools settings
        settings_frame = tk.Frame(tab_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row = 0
        
        # Browser settings
        tk.Label(settings_frame, text="Browser Settings", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
        )
        row += 1
        
        # Headless mode
        self.browser_headless_var = tk.BooleanVar(
            value=self.settings.get("HEDWIG_BROWSER_HEADLESS", "true").lower() == "true"
        )
        tk.Checkbutton(
            settings_frame,
            text="Run browser in headless mode",
            variable=self.browser_headless_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1
        
        # Browser timeout
        tk.Label(settings_frame, text="Browser Timeout (seconds):").grid(
            row=row, column=0, sticky=tk.W, pady=(5, 5)
        )
        
        self.browser_timeout_var = tk.StringVar(value=self.settings.get("HEDWIG_BROWSER_TIMEOUT", "30"))
        timeout_spin = tk.Spinbox(
            settings_frame,
            from_=10, to=120,
            textvariable=self.browser_timeout_var,
            width=10
        )
        timeout_spin.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 5))
        row += 1
        
        # PDF settings
        tk.Label(settings_frame, text="PDF Settings", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        row += 1
        
        # Page size
        tk.Label(settings_frame, text="Default Page Size:").grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        
        self.pdf_page_size_var = tk.StringVar(value=self.settings.get("HEDWIG_PDF_PAGE_SIZE", "letter"))
        page_size_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.pdf_page_size_var,
            values=["letter", "a4", "legal"],
            state="readonly"
        )
        page_size_combo.grid(row=row, column=1, sticky=tk.EW, padx=(10, 0), pady=(0, 5))
        row += 1
        
        # Auto-open artifacts
        self.auto_open_var = tk.BooleanVar(
            value=self.settings.get("HEDWIG_ENABLE_AUTO_OPEN", "true").lower() == "true"
        )
        tk.Checkbutton(
            settings_frame,
            text="Automatically open generated artifacts",
            variable=self.auto_open_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        settings_frame.grid_columnconfigure(1, weight=1)
    
    def create_ui_tab(self) -> None:
        """Create UI preferences tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Interface")
        
        # UI settings
        settings_frame = tk.Frame(tab_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row = 0
        
        # Theme selection
        tk.Label(settings_frame, text="Theme:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        
        self.theme_var = tk.StringVar(value=self.theme_manager.current_theme_name)
        theme_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.theme_var,
            values=["dark", "light"],
            state="readonly"
        )
        theme_combo.grid(row=row, column=1, sticky=tk.EW, padx=(10, 0), pady=(0, 5))
        row += 1
        
        # Log level
        tk.Label(settings_frame, text="Log Level:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        
        self.log_level_var = tk.StringVar(value=self.settings.get("HEDWIG_LOG_LEVEL", "INFO"))
        log_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly"
        )
        log_combo.grid(row=row, column=1, sticky=tk.EW, padx=(10, 0), pady=(10, 5))
        row += 1
        
        # Data directory
        tk.Label(settings_frame, text="Data Directory:", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        
        data_dir_frame = tk.Frame(settings_frame)
        data_dir_frame.grid(row=row, column=1, sticky=tk.EW, padx=(10, 0), pady=(10, 5))
        data_dir_frame.grid_columnconfigure(0, weight=1)
        
        self.data_dir_var = tk.StringVar(value=self.settings.get("HEDWIG_DATA_DIR", "~/.hedwig"))
        data_dir_entry = tk.Entry(data_dir_frame, textvariable=self.data_dir_var)
        data_dir_entry.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        def browse_data_dir():
            directory = filedialog.askdirectory(initialdir=os.path.expanduser(self.data_dir_var.get()))
            if directory:
                self.data_dir_var.set(directory)
        
        browse_btn = tk.Button(data_dir_frame, text="Browse...", command=browse_data_dir)
        browse_btn.grid(row=0, column=1)
        
        settings_frame.grid_columnconfigure(1, weight=1)
    
    def create_advanced_tab(self) -> None:
        """Create advanced options tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Advanced")
        
        # Advanced settings
        settings_frame = tk.Frame(tab_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Information text
        info_text = tk.Text(
            settings_frame,
            height=15,
            wrap=tk.WORD,
            font=("Arial", 9)
        )
        info_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        info_content = """Advanced Configuration

Environment Variables:
All settings can be configured via environment variables or the .env file.

API Base URLs:
- FIRECRAWL_BASE_URL: https://api.firecrawl.dev
- BRAVE_SEARCH_BASE_URL: https://api.search.brave.com/res/v1

Performance Settings:
- Thread pool size is automatically configured
- Memory usage is monitored and optimized
- Cache settings are managed automatically

Security Settings:
- All API keys are stored securely
- Tool execution follows risk-based security model
- User confirmation required for high-risk operations

Debug Information:
- Enable DEBUG log level for detailed logging
- Check ~/.hedwig/logs/ for log files
- Use system info dialog for diagnostics

For more information, see the project documentation."""
        
        info_text.insert("1.0", info_content)
        info_text.config(state=tk.DISABLED)
        
        # Reset button
        reset_btn = tk.Button(
            settings_frame,
            text="Reset to Defaults",
            command=self.reset_to_defaults
        )
        reset_btn.pack(pady=(10, 0))
    
    def create_button_frame(self, parent: tk.Widget) -> None:
        """Create dialog buttons."""
        button_frame = tk.Frame(parent)
        button_frame.grid(row=1, column=0, sticky=tk.EW, pady=(10, 0))
        
        # Cancel button
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=self.on_cancel,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # OK button
        ok_btn = tk.Button(
            button_frame,
            text="OK",
            command=self.on_ok,
            width=10
        )
        ok_btn.pack(side=tk.RIGHT)
    
    def load_settings(self) -> None:
        """Load current settings from environment and config."""
        try:
            # Load from environment variables
            env_vars = [
                "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "FIRECRAWL_API_KEY", "BRAVE_SEARCH_API_KEY",
                "HEDWIG_LLM_MODEL", "HEDWIG_MAX_RETRIES", "HEDWIG_SECURITY_TIMEOUT",
                "HEDWIG_BROWSER_HEADLESS", "HEDWIG_BROWSER_TIMEOUT", "HEDWIG_PDF_PAGE_SIZE",
                "HEDWIG_ENABLE_AUTO_OPEN", "HEDWIG_LOG_LEVEL", "HEDWIG_DATA_DIR"
            ]
            
            for var in env_vars:
                value = os.getenv(var)
                if value:
                    self.settings[var] = value
            
            # Load from config if available
            try:
                config = get_config()
                # Add config-specific settings here if needed
            except Exception:
                pass  # Config not available
            
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
    
    def save_settings(self) -> bool:
        """
        Save settings to environment file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Collect settings from UI
            new_settings = {
                "OPENAI_API_KEY": getattr(self, "openai_api_key_var", tk.StringVar()).get(),
                "ANTHROPIC_API_KEY": getattr(self, "anthropic_api_key_var", tk.StringVar()).get(),
                "FIRECRAWL_API_KEY": getattr(self, "firecrawl_api_key_var", tk.StringVar()).get(),
                "BRAVE_SEARCH_API_KEY": getattr(self, "brave_search_api_key_var", tk.StringVar()).get(),
                "HEDWIG_LLM_MODEL": self.model_var.get(),
                "HEDWIG_MAX_RETRIES": self.retries_var.get(),
                "HEDWIG_SECURITY_TIMEOUT": self.timeout_var.get(),
                "HEDWIG_BROWSER_HEADLESS": str(self.browser_headless_var.get()).lower(),
                "HEDWIG_BROWSER_TIMEOUT": self.browser_timeout_var.get(),
                "HEDWIG_PDF_PAGE_SIZE": self.pdf_page_size_var.get(),
                "HEDWIG_ENABLE_AUTO_OPEN": str(self.auto_open_var.get()).lower(),
                "HEDWIG_LOG_LEVEL": self.log_level_var.get(),
                "HEDWIG_DATA_DIR": self.data_dir_var.get()
            }
            
            # Update .env file
            env_file = Path(".env")
            
            # Read existing .env content
            existing_lines = []
            if env_file.exists():
                with open(env_file, 'r') as f:
                    existing_lines = f.readlines()
            
            # Update or add settings
            updated_lines = []
            updated_keys = set()
            
            for line in existing_lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=', 1)[0]
                    if key in new_settings:
                        # Update existing setting
                        if new_settings[key]:  # Only save non-empty values
                            updated_lines.append(f"{key}={new_settings[key]}\n")
                        updated_keys.add(key)
                    else:
                        # Keep other settings
                        updated_lines.append(line + "\n")
                else:
                    # Keep comments and empty lines
                    updated_lines.append(line + "\n")
            
            # Add new settings that weren't in the file
            for key, value in new_settings.items():
                if key not in updated_keys and value:  # Only save non-empty values
                    updated_lines.append(f"{key}={value}\n")
            
            # Write updated .env file
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            # Apply theme change if needed
            if hasattr(self, 'theme_var'):
                new_theme = self.theme_var.get()
                if new_theme != self.theme_manager.current_theme_name:
                    self.theme_manager.set_theme(new_theme)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        result = messagebox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\nThis will clear all API keys and preferences."
        )
        
        if result:
            # Clear all variables
            for attr_name in dir(self):
                if attr_name.endswith("_var") and hasattr(self, attr_name):
                    var = getattr(self, attr_name)
                    if isinstance(var, (tk.StringVar, tk.BooleanVar, tk.IntVar)):
                        if isinstance(var, tk.BooleanVar):
                            var.set(False)
                        else:
                            var.set("")
            
            # Set default values
            self.model_var.set("gpt-4")
            self.retries_var.set("3")
            self.timeout_var.set("10")
            self.browser_headless_var.set(True)
            self.browser_timeout_var.set("30")
            self.pdf_page_size_var.set("letter")
            self.auto_open_var.set(True)
            self.log_level_var.set("INFO")
            self.data_dir_var.set("~/.hedwig")
            self.theme_var.set("dark")
    
    def validate_settings(self) -> bool:
        """
        Validate current settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        # Check required API key
        if not getattr(self, "openai_api_key_var", tk.StringVar()).get().strip():
            messagebox.showerror("Validation Error", "OpenAI API Key is required.")
            return False
        
        # Validate numeric fields
        try:
            retries = int(self.retries_var.get())
            if not 1 <= retries <= 10:
                raise ValueError("Max retries must be between 1 and 10")
        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid max retries: {e}")
            return False
        
        try:
            timeout = int(self.timeout_var.get())
            if not 5 <= timeout <= 60:
                raise ValueError("Security timeout must be between 5 and 60 seconds")
        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid security timeout: {e}")
            return False
        
        try:
            browser_timeout = int(self.browser_timeout_var.get())
            if not 10 <= browser_timeout <= 120:
                raise ValueError("Browser timeout must be between 10 and 120 seconds")
        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid browser timeout: {e}")
            return False
        
        return True
    
    def on_ok(self) -> None:
        """Handle OK button click."""
        if self.validate_settings():
            if self.save_settings():
                self.result = True
                self.dialog.destroy()
    
    def on_cancel(self) -> None:
        """Handle Cancel button click."""
        self.result = False
        self.dialog.destroy()