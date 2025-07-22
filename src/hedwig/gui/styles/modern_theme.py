"""
Modern theme definitions for Hedwig GUI.

Provides dark and light theme configurations with modern color palettes
and styling for professional desktop application appearance.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ColorScheme:
    """Color scheme definition for GUI themes."""
    
    # Background colors
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_accent: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_muted: str
    text_accent: str
    
    # Interactive elements
    button_bg: str
    button_fg: str
    button_hover: str
    button_active: str
    
    # Input fields
    input_bg: str
    input_fg: str
    input_border: str
    input_focus: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str
    
    # Borders and separators
    border_light: str
    border_medium: str
    border_dark: str


# Dark Theme (Default)
DARK_THEME = ColorScheme(
    # Background colors - Modern dark palette
    bg_primary="#1e1e1e",      # Main background
    bg_secondary="#2d2d2d",    # Panel backgrounds
    bg_tertiary="#3c3c3c",     # Elevated elements
    bg_accent="#4a4a4a",       # Highlighted areas
    
    # Text colors - High contrast for readability
    text_primary="#ffffff",     # Primary text
    text_secondary="#cccccc",   # Secondary text
    text_muted="#888888",       # Muted text
    text_accent="#0d7377",      # Accent text (teal)
    
    # Interactive elements - Modern button styling
    button_bg="#0d7377",        # Primary button background
    button_fg="#ffffff",        # Button text
    button_hover="#14a085",     # Hover state
    button_active="#0a5d61",    # Active/pressed state
    
    # Input fields - Clean input styling
    input_bg="#2d2d2d",         # Input background
    input_fg="#ffffff",         # Input text
    input_border="#4a4a4a",     # Border color
    input_focus="#0d7377",      # Focus border
    
    # Status colors - Clear visual feedback
    success="#4caf50",          # Green for success
    warning="#ff9800",          # Orange for warnings
    error="#f44336",            # Red for errors
    info="#2196f3",             # Blue for information
    
    # Borders and separators
    border_light="#4a4a4a",     # Light borders
    border_medium="#3c3c3c",    # Medium borders
    border_dark="#2d2d2d"       # Dark borders
)

# Light Theme
LIGHT_THEME = ColorScheme(
    # Background colors - Clean light palette
    bg_primary="#ffffff",       # Main background
    bg_secondary="#f5f5f5",     # Panel backgrounds
    bg_tertiary="#eeeeee",      # Elevated elements
    bg_accent="#e0e0e0",        # Highlighted areas
    
    # Text colors - Good contrast on light background
    text_primary="#212121",     # Primary text
    text_secondary="#424242",   # Secondary text
    text_muted="#757575",       # Muted text
    text_accent="#0d7377",      # Accent text (teal)
    
    # Interactive elements - Consistent with dark theme
    button_bg="#0d7377",        # Primary button background
    button_fg="#ffffff",        # Button text
    button_hover="#14a085",     # Hover state
    button_active="#0a5d61",    # Active/pressed state
    
    # Input fields - Clean light input styling
    input_bg="#ffffff",         # Input background
    input_fg="#212121",         # Input text
    input_border="#cccccc",     # Border color
    input_focus="#0d7377",      # Focus border
    
    # Status colors - Same as dark theme for consistency
    success="#4caf50",          # Green for success
    warning="#ff9800",          # Orange for warnings
    error="#f44336",            # Red for errors
    info="#2196f3",             # Blue for information
    
    # Borders and separators
    border_light="#e0e0e0",     # Light borders
    border_medium="#cccccc",    # Medium borders
    border_dark="#999999"       # Dark borders
)


class ThemeManager:
    """Manages GUI themes and provides styling utilities."""
    
    def __init__(self, default_theme: str = "dark"):
        """
        Initialize theme manager.
        
        Args:
            default_theme: Default theme name ("dark" or "light")
        """
        self.themes = {
            "dark": DARK_THEME,
            "light": LIGHT_THEME
        }
        self.current_theme_name = default_theme
        self.current_theme = self.themes[default_theme]
    
    def set_theme(self, theme_name: str) -> None:
        """
        Set the current theme.
        
        Args:
            theme_name: Name of theme to activate
            
        Raises:
            ValueError: If theme name is not recognized
        """
        if theme_name not in self.themes:
            raise ValueError(f"Unknown theme: {theme_name}")
        
        self.current_theme_name = theme_name
        self.current_theme = self.themes[theme_name]
    
    def get_style_config(self, widget_type: str) -> Dict[str, Any]:
        """
        Get style configuration for a specific widget type.
        
        Args:
            widget_type: Type of widget ("frame", "button", "entry", etc.)
            
        Returns:
            Dictionary of style options for the widget
        """
        theme = self.current_theme
        
        configs = {
            "frame": {
                "bg": theme.bg_secondary,
                "highlightthickness": 0,
            },
            
            "main_frame": {
                "bg": theme.bg_primary,
                "highlightthickness": 0,
            },
            
            "button": {
                "bg": theme.button_bg,
                "fg": theme.button_fg,
                "activebackground": theme.button_hover,
                "activeforeground": theme.button_fg,
                "relief": "flat",
                "borderwidth": 0,
                "highlightthickness": 0,
                "font": ("Arial", 10),
                "cursor": "hand2"
            },
            
            "entry": {
                "bg": theme.input_bg,
                "fg": theme.input_fg,
                "insertbackground": theme.text_primary,
                "selectbackground": theme.text_accent,
                "selectforeground": theme.bg_primary,
                "relief": "flat",
                "borderwidth": 1,
                "highlightthickness": 1,
                "highlightcolor": theme.input_focus,
                "highlightbackground": theme.input_border,
                "font": ("Arial", 10)
            },
            
            "text": {
                "bg": theme.input_bg,
                "fg": theme.input_fg,
                "insertbackground": theme.text_primary,
                "selectbackground": theme.text_accent,
                "selectforeground": theme.bg_primary,
                "relief": "flat",
                "borderwidth": 1,
                "highlightthickness": 1,
                "highlightcolor": theme.input_focus,
                "highlightbackground": theme.input_border,
                "font": ("Arial", 10),
                "wrap": "word"
            },
            
            "label": {
                "bg": theme.bg_secondary,
                "fg": theme.text_primary,
                "font": ("Arial", 10)
            },
            
            "listbox": {
                "bg": theme.input_bg,
                "fg": theme.input_fg,
                "selectbackground": theme.text_accent,
                "selectforeground": theme.bg_primary,
                "relief": "flat",
                "borderwidth": 1,
                "highlightthickness": 0,
                "font": ("Arial", 9)
            },
            
            "scrollbar": {
                "bg": theme.bg_tertiary,
                "troughcolor": theme.bg_secondary,
                "activebackground": theme.text_accent,
                "highlightthickness": 0,
                "relief": "flat",
                "borderwidth": 0
            },
            
            "menu": {
                "bg": theme.bg_secondary,
                "fg": theme.text_primary,
                "activebackground": theme.text_accent,
                "activeforeground": theme.bg_primary,
                "relief": "flat",
                "borderwidth": 0,
                "font": ("Arial", 9)
            },
            
            "menubar": {
                "bg": theme.bg_tertiary,
                "fg": theme.text_primary,
                "activebackground": theme.text_accent,
                "activeforeground": theme.bg_primary,
                "relief": "flat",
                "borderwidth": 0,
                "font": ("Arial", 10)
            }
        }
        
        return configs.get(widget_type, {})
    
    def get_color(self, color_name: str) -> str:
        """
        Get a color value from the current theme.
        
        Args:
            color_name: Name of the color attribute
            
        Returns:
            Hex color string
        """
        return getattr(self.current_theme, color_name, "#000000")
    
    def is_dark_theme(self) -> bool:
        """Check if current theme is dark."""
        return self.current_theme_name == "dark"


# Global theme manager instance
theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return theme_manager