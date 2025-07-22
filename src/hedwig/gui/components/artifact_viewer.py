"""
Artifact viewer component for Hedwig GUI.

Provides file browser and preview capabilities for generated artifacts,
with support for multiple file types and management operations.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
import subprocess
import sys
from datetime import datetime

from hedwig.core.config import get_config
from hedwig.core.logging_config import get_logger
from hedwig.gui.styles import ThemeManager


class ArtifactViewer(tk.Frame):
    """
    Artifact viewer component for browsing and managing generated files.
    
    Features:
    - Tree view of artifacts organized by type and date
    - File preview for supported formats
    - Quick actions (open, copy path, delete)
    - Search and filter capabilities
    - Drag and drop support
    """
    
    def __init__(self, parent: tk.Widget, theme_manager: ThemeManager, on_artifact_open: Optional[Callable[[str], None]] = None):
        """
        Initialize the artifact viewer.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
            on_artifact_open: Callback for opening artifacts
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_artifact_open = on_artifact_open
        self.logger = get_logger("hedwig.gui.artifact_viewer")
        
        # Get artifacts directory
        try:
            config = get_config()
            self.artifacts_dir = Path(config.data_dir) / "artifacts"
        except Exception:
            self.artifacts_dir = Path("artifacts")
        
        # Ensure artifacts directory exists
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # State
        self.artifacts: Dict[str, Dict[str, Any]] = {}
        self.filtered_artifacts: Dict[str, Dict[str, Any]] = {}
        self.current_filter = ""
        self.selected_artifact: Optional[str] = None
        
        self.create_widgets()
        self.apply_theme()
        self.setup_event_handlers()
        self.refresh_artifacts()
    
    def create_widgets(self) -> None:
        """Create artifact viewer widgets."""
        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header with title and controls
        self.create_header()
        
        # Main content area
        self.create_main_area()
        
        # Context menu
        self.create_context_menu()
    
    def create_header(self) -> None:
        """Create the header with title and controls."""
        header_frame = tk.Frame(self)
        header_frame.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="Artifacts",
            font=("Arial", 12, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Search entry
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        
        search_frame = tk.Frame(header_frame)
        search_frame.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        tk.Label(search_frame, text="Search:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=20,
            font=("Arial", 9)
        )
        self.search_entry.pack(side=tk.LEFT)
        
        # Refresh button
        self.refresh_button = tk.Button(
            header_frame,
            text="⟳",
            command=self.refresh_artifacts,
            width=3,
            font=("Arial", 10)
        )
        self.refresh_button.grid(row=0, column=2, padx=(5, 0))
    
    def create_main_area(self) -> None:
        """Create the main content area with file list and preview."""
        # Paned window for resizable panels
        self.paned_window = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashrelief=tk.FLAT,
            sashwidth=6
        )
        self.paned_window.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=(0, 5))
        
        # File list panel
        self.create_file_list()
        
        # Preview panel
        self.create_preview_panel()
        
        # Set initial pane sizes
        self.after(100, lambda: self.paned_window.sash_place(0, 200, 0))
    
    def create_file_list(self) -> None:
        """Create the file list tree view."""
        list_frame = tk.Frame(self)
        
        # Treeview with scrollbars
        tree_frame = tk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        columns = ("size", "modified", "type")
        self.file_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            height=15
        )
        
        # Configure columns
        self.file_tree.heading("#0", text="Name")
        self.file_tree.heading("size", text="Size")
        self.file_tree.heading("modified", text="Modified")
        self.file_tree.heading("type", text="Type")
        
        self.file_tree.column("#0", width=200)
        self.file_tree.column("size", width=80)
        self.file_tree.column("modified", width=120)
        self.file_tree.column("type", width=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        
        self.file_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack widgets
        self.file_tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        h_scrollbar.grid(row=1, column=0, sticky=tk.EW)
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Action buttons
        button_frame = tk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.open_button = tk.Button(
            button_frame,
            text="Open",
            command=self.open_selected_artifact,
            state=tk.DISABLED
        )
        self.open_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.copy_path_button = tk.Button(
            button_frame,
            text="Copy Path",
            command=self.copy_artifact_path,
            state=tk.DISABLED
        )
        self.copy_path_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_button = tk.Button(
            button_frame,
            text="Delete",
            command=self.delete_selected_artifact,
            state=tk.DISABLED
        )
        self.delete_button.pack(side=tk.RIGHT)
        
        self.paned_window.add(list_frame, minsize=200)
    
    def create_preview_panel(self) -> None:
        """Create the file preview panel."""
        preview_frame = tk.Frame(self)
        
        # Preview title
        self.preview_title = tk.Label(
            preview_frame,
            text="Preview",
            font=("Arial", 11, "bold")
        )
        self.preview_title.pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        # Preview content
        preview_content_frame = tk.Frame(preview_frame)
        preview_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        preview_content_frame.grid_rowconfigure(0, weight=1)
        preview_content_frame.grid_columnconfigure(0, weight=1)
        
        # Text preview with scrollbar
        self.preview_text = tk.Text(
            preview_content_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", 9),
            height=10
        )
        
        preview_scrollbar = ttk.Scrollbar(
            preview_content_frame,
            orient=tk.VERTICAL,
            command=self.preview_text.yview
        )
        
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        self.preview_text.grid(row=0, column=0, sticky=tk.NSEW)
        preview_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        
        # No preview message
        self.no_preview_label = tk.Label(
            preview_content_frame,
            text="Select an artifact to preview",
            font=("Arial", 10),
            justify=tk.CENTER
        )
        self.no_preview_label.grid(row=0, column=0, sticky=tk.NSEW)
        
        self.paned_window.add(preview_frame, minsize=150)
    
    def create_context_menu(self) -> None:
        """Create context menu for file operations."""
        self.context_menu = tk.Menu(self, tearoff=0)
        
        self.context_menu.add_command(label="Open", command=self.open_selected_artifact)
        self.context_menu.add_command(label="Open Folder", command=self.open_artifact_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Path", command=self.copy_artifact_path)
        self.context_menu.add_command(label="Rename...", command=self.rename_artifact)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_selected_artifact)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Properties", command=self.show_artifact_properties)
    
    def setup_event_handlers(self) -> None:
        """Setup event handlers for the artifact viewer."""
        # File selection
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.file_tree.bind("<Double-1>", lambda e: self.open_selected_artifact())
        
        # Context menu
        self.file_tree.bind("<Button-3>", self.show_context_menu)
        
        # Keyboard shortcuts
        self.file_tree.bind("<Return>", lambda e: self.open_selected_artifact())
        self.file_tree.bind("<Delete>", lambda e: self.delete_selected_artifact())
        
        # Refresh on focus
        self.bind("<FocusIn>", lambda e: self.refresh_artifacts())
    
    def apply_theme(self) -> None:
        """Apply current theme to artifact viewer."""
        theme = self.theme_manager.current_theme
        
        # Main frame
        self.configure(bg=theme.bg_secondary)
        
        # Preview components
        self.preview_title.configure(
            bg=theme.bg_secondary,
            fg=theme.text_primary
        )
        
        self.preview_text.configure(
            bg=theme.input_bg,
            fg=theme.input_fg,
            selectbackground=theme.text_accent,
            selectforeground=theme.bg_primary
        )
        
        self.no_preview_label.configure(
            bg=theme.bg_secondary,
            fg=theme.text_muted
        )
        
        # Search entry
        entry_style = self.theme_manager.get_style_config("entry")
        self.search_entry.configure(**entry_style)
        
        # Buttons
        button_style = self.theme_manager.get_style_config("button")
        self.refresh_button.configure(**button_style)
        self.open_button.configure(**button_style)
        self.copy_path_button.configure(**button_style)
        self.delete_button.configure(**button_style)
        
        # Context menu
        menu_style = self.theme_manager.get_style_config("menu")
        self.context_menu.configure(**menu_style)
        
        # Paned window
        self.paned_window.configure(bg=theme.bg_secondary)
    
    def refresh_artifacts(self) -> None:
        """Refresh the artifacts list from disk."""
        try:
            self.artifacts.clear()
            
            if not self.artifacts_dir.exists():
                return
            
            # Scan artifacts directory
            for file_path in self.artifacts_dir.iterdir():
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        
                        artifact_info = {
                            "path": str(file_path),
                            "name": file_path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                            "type": self.get_file_type(file_path),
                            "extension": file_path.suffix.lower()
                        }
                        
                        self.artifacts[str(file_path)] = artifact_info
                        
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Could not access {file_path}: {e}")
            
            # Update filtered artifacts and display
            self.apply_filter()
            self.update_file_list()
            
        except Exception as e:
            self.logger.error(f"Failed to refresh artifacts: {e}")
            messagebox.showerror("Error", f"Failed to refresh artifacts:\n{str(e)}")
    
    def get_file_type(self, file_path: Path) -> str:
        """
        Determine file type based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type string
        """
        extension = file_path.suffix.lower()
        
        type_mapping = {
            '.pdf': 'PDF',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.py': 'Python',
            '.js': 'JavaScript',
            '.html': 'HTML',
            '.css': 'CSS',
            '.json': 'JSON',
            '.xml': 'XML',
            '.csv': 'CSV',
            '.png': 'PNG Image',
            '.jpg': 'JPEG Image',
            '.jpeg': 'JPEG Image',
            '.gif': 'GIF Image',
            '.svg': 'SVG Image',
            '.zip': 'Archive',
            '.tar': 'Archive',
            '.gz': 'Archive'
        }
        
        return type_mapping.get(extension, 'File')
    
    def apply_filter(self) -> None:
        """Apply search filter to artifacts."""
        if not self.current_filter:
            self.filtered_artifacts = self.artifacts.copy()
        else:
            self.filtered_artifacts = {
                path: info for path, info in self.artifacts.items()
                if self.current_filter.lower() in info["name"].lower()
                or self.current_filter.lower() in info["type"].lower()
            }
    
    def update_file_list(self) -> None:
        """Update the file list display."""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Add filtered artifacts
        for artifact_info in sorted(self.filtered_artifacts.values(), key=lambda x: x["modified"], reverse=True):
            # Format size
            size = artifact_info["size"]
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            # Format modification time
            modified_str = artifact_info["modified"].strftime("%Y-%m-%d %H:%M")
            
            # Insert item
            item_id = self.file_tree.insert(
                "",
                tk.END,
                text=artifact_info["name"],
                values=(size_str, modified_str, artifact_info["type"]),
                tags=(artifact_info["type"].lower(),)
            )
            
            # Store path in item for reference
            self.file_tree.set(item_id, "path", artifact_info["path"])
    
    def on_search_change(self, *args) -> None:
        """Handle search filter change."""
        self.current_filter = self.search_var.get()
        self.apply_filter()
        self.update_file_list()
    
    def on_file_select(self, event) -> None:
        """Handle file selection change."""
        selection = self.file_tree.selection()
        
        if selection:
            item = selection[0]
            file_path = self.file_tree.set(item, "path")
            self.selected_artifact = file_path
            
            # Enable buttons
            self.open_button.config(state=tk.NORMAL)
            self.copy_path_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
            
            # Update preview
            self.update_preview(file_path)
            
        else:
            self.selected_artifact = None
            
            # Disable buttons
            self.open_button.config(state=tk.DISABLED)
            self.copy_path_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            
            # Clear preview
            self.clear_preview()
    
    def update_preview(self, file_path: str) -> None:
        """
        Update the preview panel with file content.
        
        Args:
            file_path: Path to the file to preview
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                self.show_preview_message("File not found")
                return
            
            # Check file size (limit preview to 1MB)
            if path.stat().st_size > 1024 * 1024:
                self.show_preview_message("File too large for preview")
                return
            
            # Preview based on file type
            extension = path.suffix.lower()
            
            if extension in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']:
                self.preview_text_file(path)
            elif extension == '.pdf':
                self.show_preview_message("PDF preview not available\nClick 'Open' to view in external viewer")
            elif extension in ['.png', '.jpg', '.jpeg', '.gif']:
                self.show_preview_message("Image preview not available\nClick 'Open' to view in external viewer")
            else:
                self.show_preview_message(f"Preview not available for {extension} files")
                
        except Exception as e:
            self.logger.error(f"Failed to preview {file_path}: {e}")
            self.show_preview_message(f"Preview error: {str(e)}")
    
    def preview_text_file(self, file_path: Path) -> None:
        """Preview a text-based file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(10000)  # Limit to first 10KB
                
                # Enable text widget
                self.preview_text.config(state=tk.NORMAL)
                self.preview_text.delete("1.0", tk.END)
                self.preview_text.insert("1.0", content)
                
                # Add truncation notice if needed
                if len(content) >= 10000:
                    self.preview_text.insert(tk.END, "\n\n... (preview truncated)")
                
                self.preview_text.config(state=tk.DISABLED)
                
                # Show text widget, hide message
                self.no_preview_label.grid_remove()
                self.preview_text.grid()
                
        except Exception as e:
            self.show_preview_message(f"Could not read file: {str(e)}")
    
    def show_preview_message(self, message: str) -> None:
        """Show a message in the preview area."""
        self.no_preview_label.config(text=message)
        self.preview_text.grid_remove()
        self.no_preview_label.grid()
    
    def clear_preview(self) -> None:
        """Clear the preview area."""
        self.show_preview_message("Select an artifact to preview")
    
    def open_selected_artifact(self) -> None:
        """Open the selected artifact."""
        if not self.selected_artifact:
            return
        
        if self.on_artifact_open:
            self.on_artifact_open(self.selected_artifact)
        else:
            # Default open behavior
            try:
                if sys.platform == "win32":
                    os.startfile(self.selected_artifact)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.selected_artifact])
                else:
                    subprocess.run(["xdg-open", self.selected_artifact])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file:\n{str(e)}")
    
    def open_artifact_folder(self) -> None:
        """Open the folder containing the selected artifact."""
        if not self.selected_artifact:
            return
        
        folder_path = Path(self.selected_artifact).parent
        
        try:
            if sys.platform == "win32":
                os.startfile(str(folder_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder_path)])
            else:
                subprocess.run(["xdg-open", str(folder_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder:\n{str(e)}")
    
    def copy_artifact_path(self) -> None:
        """Copy the selected artifact path to clipboard."""
        if not self.selected_artifact:
            return
        
        self.clipboard_clear()
        self.clipboard_append(self.selected_artifact)
        
        # Show temporary feedback
        messagebox.showinfo("Copied", "File path copied to clipboard")
    
    def rename_artifact(self) -> None:
        """Rename the selected artifact."""
        if not self.selected_artifact:
            return
        
        # TODO: Implement rename dialog
        messagebox.showinfo("Info", "Rename functionality coming soon!")
    
    def delete_selected_artifact(self) -> None:
        """Delete the selected artifact with confirmation."""
        if not self.selected_artifact:
            return
        
        file_name = Path(self.selected_artifact).name
        
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{file_name}'?\n\nThis action cannot be undone."
        )
        
        if result:
            try:
                Path(self.selected_artifact).unlink()
                self.refresh_artifacts()
                messagebox.showinfo("Deleted", f"'{file_name}' has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file:\n{str(e)}")
    
    def show_artifact_properties(self) -> None:
        """Show properties dialog for selected artifact."""
        if not self.selected_artifact:
            return
        
        # TODO: Implement properties dialog
        messagebox.showinfo("Info", "Properties dialog coming soon!")
    
    def show_context_menu(self, event) -> None:
        """Show context menu."""
        # Select item under cursor
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            self.file_tree.focus(item)
            
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def get_artifact_count(self) -> int:
        """Get the number of artifacts."""
        return len(self.filtered_artifacts)
    
    def get_selected_artifact(self) -> Optional[str]:
        """Get the currently selected artifact path."""
        return self.selected_artifact