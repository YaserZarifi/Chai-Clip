import os
import sys
import threading
import yt_dlp
import subprocess
import re
import customtkinter as ctk
from tkinter import filedialog, messagebox
from collections import deque

import requests
from PIL import Image
from io import BytesIO

class YouTubeDownloader:
    """
    A modern GUI application for downloading YouTube videos using customtkinter.
    """
    def __init__(self, root):
        """
        Initializes the application's GUI.
        """
        # self.root = root
        # self.root.title("Chai & Clip")
        # # self.root.geometry("600x600")
        # self.root.geometry("600x600")
        # self.root.resizable(False, False)

        self.root = root
        self.root.title("Chai & Clip")

        # --- Center the window on launch ---
        app_width = 600
        app_height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width / 2) - (app_width / 2)
        y = 50  # Position 150 pixels down from the top

        self.root.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")
        self.root.resizable(False, False)

        # self.thumbnail_image = None
        self.current_thumbnail_label = None

        # --- Set App Icon ---
        try:
            if getattr(sys, 'frozen', False):
                self.application_path = os.path.dirname(sys.executable)
            else:
                self.application_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(self.application_path, "logo.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading icon: {e}")

        self.download_thread = None
        # self.stop_download_flag = threading.Event()
        self.stop_operation_flag = threading.Event()
        self.available_formats = []
        self.final_filepath = None
        self.video_title_var = ctk.StringVar()
        self.original_video_title = ""
        self.speed_samples = deque(maxlen=15)
        self.cookie_file_path = None
        self.is_animating = False
        self.dot_count = 0

        self.last_clipboard_url = ""
        self.popup_window = None

        self.create_widgets()

        self.check_clipboard()

    def create_widgets(self):
        """
        Creates and arranges all the GUI widgets in the main window.
        """
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Top Bar ---
        top_bar_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_bar_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top_bar_frame, text="Chai & Clip", font=("Segoe UI", 18, "bold")).pack(side="left")
        self.cookie_status_label = ctk.CTkLabel(top_bar_frame, text="Status: Not Authenticated", font=("Segoe UI", 10), text_color="gray")
        self.cookie_status_label.pack(side="right", padx=10)

        # --- URL Input & Analysis ---
        url_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        url_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(url_frame, text="YouTube URL:", font=("Segoe UI", 14)).pack(side="left")
        self.url_entry = ctk.CTkEntry(url_frame, font=("Segoe UI", 12), height=35)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        self.analyze_button = ctk.CTkButton(url_frame, text="Analyze", command=self.start_fetch_thread, height=35, width=80)
        self.analyze_button.pack(side="left")


        # --- Thumbnail & Uploader Info ---
        self.info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        # self.info_frame.pack(fill="x", pady=(15, 5))

        # self.thumbnail_label = ctk.CTkLabel(self.info_frame, text="", height=270) # Placeholder for thumbnail
        # self.thumbnail_label.pack()

        self.uploader_label = ctk.CTkLabel(self.info_frame, text="", font=("Segoe UI", 12, "italic")) # Placeholder for uploader
        self.uploader_label.pack(pady=(5, 0))

        # --- Video Title Input ---
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(title_frame, text="Video Title:", font=("Segoe UI", 14)).pack(side="left", padx=(0, 22))
        self.title_entry = ctk.CTkEntry(title_frame, textvariable=self.video_title_var, font=("Segoe UI", 12), state='disabled', height=35)
        self.title_entry.pack(fill="x", expand=True)

        # --- Quality Selection ---
        quality_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        quality_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(quality_frame, text="Select Quality:", font=("Segoe UI", 14)).pack(side="left", padx=(0, 5))
        self.quality_combobox = ctk.CTkComboBox(quality_frame, state='readonly', font=("Segoe UI", 12), height=35, dropdown_font=("Segoe UI", 12))
        self.quality_combobox.pack(fill="x", expand=True)
        self.quality_combobox.set("Click 'Analyze' to see options")
        self.quality_combobox.configure(state='disabled')
        self.quality_combobox.configure(command=self.on_quality_change)

        # --- Download Path Selection ---
        path_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(path_frame, text="Save to:", font=("Segoe UI", 14)).pack(side="left", padx=(0, 42))
        self.path_var = ctk.StringVar(value=os.path.join(os.path.expanduser('~'), 'Downloads'))
        self.path_entry = ctk.CTkEntry(path_frame, textvariable=self.path_var, font=("Segoe UI", 12), state='disabled', height=35)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.browse_button = ctk.CTkButton(path_frame, text="Browse...", command=self.browse_directory, height=35, width=80)
        self.browse_button.pack(side="left", padx=(10, 0))

        # --- Progress Display & Stats ---
        progress_stats_frame = ctk.CTkFrame(main_frame)
        progress_stats_frame.pack(fill="x", pady=(20, 10))
        
        self.progress_bar = ctk.CTkProgressBar(progress_stats_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", expand=True, pady=(0, 5))
        
        self.progress_label = ctk.CTkLabel(progress_stats_frame, text="0%", font=("Segoe UI", 12))
        self.progress_label.pack()

        stats_frame = ctk.CTkFrame(progress_stats_frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)
        stats_frame.columnconfigure((0, 1, 2), weight=1)
        
        self.size_label = ctk.CTkLabel(stats_frame, text="Size: ---", font=("Segoe UI", 12))
        self.size_label.grid(row=0, column=0, sticky="w")
        self.speed_label = ctk.CTkLabel(stats_frame, text="Speed: ---", font=("Segoe UI", 12))
        self.speed_label.grid(row=0, column=1)
        self.eta_label = ctk.CTkLabel(stats_frame, text="ETA: ---", font=("Segoe UI", 12))
        self.eta_label.grid(row=0, column=2, sticky="e")

        # --- Control Buttons ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        self.download_button = ctk.CTkButton(button_frame, text="Download", command=self.start_download, state="disabled", height=40, width=120, font=("Segoe UI", 14, "bold"))
        self.download_button.pack(side="left", padx=10)
        self.stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_operation, state="disabled", height=40, width=120, fg_color="#D32F2F", hover_color="#B71C1C")
        self.stop_button.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(main_frame, text="Enter a YouTube URL to begin.", font=("Segoe UI", 12, 'italic'))
        self.status_label.pack(pady=(10, 0))






    def check_clipboard(self):
        """Periodically checks the clipboard and shows a popup if a new YouTube URL is found."""
        try:
            clipboard_content = self.root.clipboard_get()
            # Check if the content is new
            if clipboard_content != self.last_clipboard_url:
                youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
                match = re.search(youtube_regex, clipboard_content)

                if match:
                    # If it's a valid URL, update the last URL and show the popup
                    self.last_clipboard_url = clipboard_content
                    self.show_url_popup(clipboard_content)

        except Exception:
            # Clipboard might be empty or contain non-text data
            self.last_clipboard_url = "" # Reset on error

        self.root.after(1500, self.check_clipboard) # Check every 1.5 seconds


    # def show_url_popup(self, url):
    #     """Creates and shows a small popup to analyze a detected URL."""
    #     # If a popup already exists, just bring it to the front
    #     if self.popup_window and self.popup_window.winfo_exists():
    #         self.popup_window.lift()
    #         return

    #     self.popup_window = ctk.CTkToplevel(self.root)
    #     self.popup_window.title("")
    #     self.popup_window.geometry("350x120")
    #     self.popup_window.resizable(False, False)
    #     self.popup_window.transient(self.root)

    #     # Position the popup in the bottom-right corner of the main window
    #     main_x = self.root.winfo_x()
    #     main_y = self.root.winfo_y()
    #     main_w = self.root.winfo_width()
    #     main_h = self.root.winfo_height()
    #     self.popup_window.geometry(f"+{main_x + main_w - 360}+{main_y + main_h - 130}")

    #     popup_frame = ctk.CTkFrame(self.popup_window, fg_color="transparent")
    #     popup_frame.pack(expand=True, fill="both", padx=10, pady=10)

    #     # Display a truncated version of the URL
    #     display_url = (url[:45] + '...') if len(url) > 45 else url
    #     ctk.CTkLabel(popup_frame, text="YouTube URL detected in clipboard:", font=("Segoe UI", 12)).pack()
    #     ctk.CTkLabel(popup_frame, text=display_url, font=("Segoe UI", 10, "italic")).pack(pady=(0, 10))

    #     button_frame = ctk.CTkFrame(popup_frame, fg_color="transparent")
    #     button_frame.pack()

    #     analyze_button = ctk.CTkButton(button_frame, text="Analyze Now", command=lambda: self.analyze_from_popup(url))
    #     analyze_button.pack(side="left", padx=5)

    #     dismiss_button = ctk.CTkButton(button_frame, text="Dismiss", fg_color="gray", hover_color="dimgray", command=self.on_popup_close)
    #     dismiss_button.pack(side="left", padx=5)

    #     self.popup_window.protocol("WM_DELETE_WINDOW", self.on_popup_close)
    #     self.popup_window.after(100, self.popup_window.lift) # Ensure it appears on top

    def show_url_popup(self, url):
        """Creates a bigger, bolder, centered, top-most popup to analyze a detected URL."""
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.lift()
            return

        self.popup_window = ctk.CTkToplevel(self.root)
        self.popup_window.title("New URL Detected")
        
        # --- MODIFICATION: Make the window always on top ---
        self.popup_window.attributes("-topmost", True)

        # --- MODIFICATION: Increase size and center on the screen ---
        popup_width = 450
        popup_height = 180
        screen_width = self.popup_window.winfo_screenwidth()
        screen_height = self.popup_window.winfo_screenheight()
        x = (screen_width / 2) - (popup_width / 2)
        y = (screen_height / 2) - (popup_height / 2)
        self.popup_window.geometry(f"{popup_width}x{popup_height}+{int(x)}+{int(y)}")
        
        self.popup_window.resizable(False, False)
        self.popup_window.transient(self.root)

        popup_frame = ctk.CTkFrame(self.popup_window, fg_color="transparent")
        popup_frame.pack(expand=True, fill="both", padx=20, pady=15)
        
        # --- MODIFICATION: Use bigger, bolder fonts ---
        display_url = (url[:55] + '...') if len(url) > 55 else url
        ctk.CTkLabel(popup_frame, text="YouTube URL Detected!", font=("Segoe UI", 18, "bold")).pack(pady=(0, 5))
        ctk.CTkLabel(popup_frame, text=display_url, font=("Segoe UI", 12, "italic")).pack(pady=(0, 15))

        button_frame = ctk.CTkFrame(popup_frame, fg_color="transparent")
        button_frame.pack()
        
        # --- MODIFICATION: Enlarge the buttons ---
        analyze_button = ctk.CTkButton(button_frame, text="Analyze Now", command=lambda: self.analyze_from_popup(url), 
                                       height=40, width=130, font=("Segoe UI", 14, "bold"))
        analyze_button.pack(side="left", padx=10)
        
        dismiss_button = ctk.CTkButton(button_frame, text="Dismiss", fg_color="gray", hover_color="dimgray", 
                                       command=self.on_popup_close, height=40, width=130, font=("Segoe UI", 14, "bold"))
        dismiss_button.pack(side="left", padx=10)

        self.popup_window.protocol("WM_DELETE_WINDOW", self.on_popup_close)
        self.popup_window.after(100, self.popup_window.lift)



    def analyze_from_popup(self, url):
        """Pastes the URL from the popup and starts the analysis."""
        self.url_entry.delete(0, 'end')
        self.url_entry.insert(0, url)
        self.start_fetch_thread()
        self.on_popup_close()

    def on_popup_close(self):
        """Safely closes the popup and resets the tracking variable."""
        if self.popup_window:
            self.popup_window.destroy()
            self.popup_window = None


    def import_cookies(self):
        file_path = filedialog.askopenfilename(
            title="Select cookies.txt file",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if file_path:
            self.cookie_file_path = file_path
            self.cookie_status_label.configure(text="Status: Cookies Loaded", text_color="green")
            print(f"Cookies loaded from: {file_path}")
            # Automatically re-analyze after importing cookies
            # self.start_fetch_thread()
            # Start the analysis animation
            self.is_animating = True
            self.animate_status_dots()
            # Call the new dedicated function in a thread
            threading.Thread(target=self.fetch_with_cookies, daemon=True).start()

    def show_cookie_error_dialog(self):
        """Shows a custom dialog with a guide button when cookies are needed."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Authentication Required")
        dialog.geometry("450x220")
        dialog.resizable(False, False)
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(main_frame, text="YouTube is blocking requests.", font=("Segoe UI", 16, "bold")).pack(pady=(0, 5))
        ctk.CTkLabel(main_frame, text="For a permanent fix, please import a cookies file.\nIt's highly recommended to read the guide first.", 
                     font=("Segoe UI", 12), justify="left").pack(pady=(0, 20))
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)

        def open_guide_and_close():
            guide_path = os.path.join(self.application_path, "Guide.pdf")
            if os.path.exists(guide_path):
                self.open_path(guide_path)
            else:
                messagebox.showerror("Error", "Guide.pdf not found in the application directory.")
            dialog.destroy()

        def import_cookies_and_close():
            dialog.destroy()
            self.import_cookies()

        ctk.CTkButton(button_frame, text="Open Guide", command=open_guide_and_close).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Import Cookies", command=import_cookies_and_close).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
        
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)

    def start_fetch_thread(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL first.")
            return
        self.stop_operation_flag.clear() # Reset the flag
        self.stop_button.configure(state="normal") # Enable the stop button

        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.quality_combobox.set("Fetching qualities...")
        self.quality_combobox.configure(state='disabled')
        self.title_entry.configure(state='disabled')
        self.video_title_var.set("")

        self.is_animating = True
        self.animate_status_dots()
        
        threading.Thread(target=self.fetch_qualities, args=(url,), daemon=True).start()


    def animate_status_dots(self, base_text="Analyzing"):
        if not self.is_animating:
            return

        self.dot_count += 1
        dots = "." * ((self.dot_count % 3) + 1)
        self.status_label.configure(text=f"{base_text} {dots.ljust(3)}")
        
        self.root.after(500, self.animate_status_dots, base_text)
    

    # def load_thumbnail(self, url):
    #     """Downloads and displays the video thumbnail."""

    #     try:
    #         response = requests.get(url, stream=True)
    #         response.raise_for_status()
            
    #         image_data = response.content
    #         raw_image = Image.open(BytesIO(image_data))
            
    #         w, h = raw_image.size
    #         aspect_ratio = h / w
    #         new_width = 480
    #         new_height = int(new_width * aspect_ratio)

    #         resized_image = raw_image.resize((new_width, new_height), Image.LANCZOS)
    #         self.thumbnail_image = ctk.CTkImage(light_image=resized_image, dark_image=resized_image, size=(new_width, new_height))
            
    #         # --- MODIFICATION: This block is now run on the main thread ---
    #         def update_ui_with_image():
    #             # Show the frame
    #             self.info_frame.pack(fill="x", pady=(15, 5))
    #             # Set the image AND clear the loading text
    #             self.thumbnail_label.configure(image=self.thumbnail_image, text="") 
    #             # Resize the main window dynamically
    #             self.root.geometry(f"600x{600 + new_height + 40}") # 600 base + image height + padding

    #         self.root.after(0, update_ui_with_image)

    #     except Exception as e:
    #         print(f"Failed to load thumbnail: {e}")
    #         def show_error_message():
    #             # Show the frame to display the error
    #             self.info_frame.pack(fill="x", pady=(15, 5))
    #             # Set the error text
    #             self.thumbnail_label.configure(text="Thumbnail not available", image=None)
    #             # Ensure window is compact
    #             self.root.geometry("600x650") 

    #         self.root.after(0, show_error_message)





    # def load_thumbnail(self, url):
    #     """Downloads and prepares the thumbnail in a background thread."""
    #     try:
    #         response = requests.get(url, stream=True)
    #         response.raise_for_status()

    #         image_data = response.content
    #         raw_image = Image.open(BytesIO(image_data))

    #         w, h = raw_image.size
    #         aspect_ratio = h / w
    #         new_width = 480
    #         new_height = int(new_width * aspect_ratio)

    #         resized_image = raw_image.resize((new_width, new_height), Image.LANCZOS)

    #         # Pass the prepared Pillow image to the main thread for UI updates
    #         self.root.after(0, self.update_ui_with_thumbnail, resized_image)

    #     except Exception as e:
    #         print(f"Failed to load thumbnail: {e}")
    #         # If it fails, pass None to the UI update function
    #         self.root.after(0, self.update_ui_with_thumbnail, None)


    # def update_ui_with_thumbnail(self, pillow_image):
    #     """Creates the CTkImage and updates the UI from the main thread."""
    #     if pillow_image:
    #         # ... (image creation logic is the same) ...
    #         self.thumbnail_image = ctk.CTkImage(light_image=pillow_image, 
    #                                         dark_image=pillow_image, 
    #                                         size=pillow_image.size)
            
    #         # Use the new variable name here
    #         self.current_thumbnail_label.configure(image=self.thumbnail_image, text="") 
    #         self.root.geometry(f"600x{600 + pillow_image.height + 40}")
    #     else:
    #         # And here
    #         self.current_thumbnail_label.configure(text="Thumbnail not available", image=None)
    #         self.root.geometry("600x650")

    def update_ui_with_results(self, info, pillow_image):
        """Updates the entire UI at once when all data is ready."""
        self.is_animating = False

        # --- Part 1: Destroy old thumbnail label if it exists ---
        if self.current_thumbnail_label:
            self.current_thumbnail_label.destroy()
            self.current_thumbnail_label = None

        self.info_frame.pack_forget()
        self.root.geometry("600x600")

        # --- Part 2: Display Thumbnail (or error) ---
        uploader_name = f"Uploader: {info.get('uploader', 'N/A')}"
        self.uploader_label.configure(text=uploader_name)

        self.current_thumbnail_label = ctk.CTkLabel(self.info_frame, text="")
        self.info_frame.pack(fill="x", pady=(15, 5))
        self.current_thumbnail_label.pack()

        if pillow_image:
            self.thumbnail_image = ctk.CTkImage(light_image=pillow_image, 
                                                dark_image=pillow_image, 
                                                size=pillow_image.size)
            self.current_thumbnail_label.configure(image=self.thumbnail_image)
            self.root.geometry(f"600x{600 + pillow_image.height + 40}")
        else:
            self.current_thumbnail_label.configure(text="Thumbnail not available")
            self.root.geometry("600x650")

        # --- Part 3: Display Qualities and Title ---
        self.original_video_title = info.get('title', 'Untitled Video')
        self.available_formats = []
        formats = info.get('formats', [])
        for f in formats:
            if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                filesize_mb = f.get('filesize') or f.get('filesize_approx')
                filesize_str = f"{filesize_mb / (1024*1024):.2f} MB" if filesize_mb else "N/A"
                if f.get('acodec') != 'none':
                    display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str}"
                else:
                    display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str} (Requires FFmpeg)"
                self.available_formats.append({'text': display_text, 'height': f.get('height', 0)})

        if self.available_formats:
            self.available_formats.sort(key=lambda x: x['height'], reverse=True)
            display_list = [f['text'] for f in self.available_formats]
            self.quality_combobox.configure(values=display_list, state='readonly')
            highest_quality_text = display_list[0]
            self.quality_combobox.set(highest_quality_text)
            self.on_quality_change(highest_quality_text)
            self.download_button.configure(state="normal")
            self.title_entry.configure(state="normal")
            self.status_label.configure(text="Select a quality and download.")
        else:
            self.status_label.configure(text="No MP4 formats found.")
            messagebox.showwarning("Warning", "Could not find any MP4 formats.")

        self.analyze_button.configure(state="normal")





    # def fetch_qualities(self, url):
    #     info = None
    #     pillow_image = None

    #     try:
    #         # --- Tier 1: Metadata Fetch ---
    #         with yt_dlp.YoutubeDL({'noplaylist': True, 'quiet': True}) as ydl:
    #             info = ydl.extract_info(url, download=False)

    #         if self.stop_operation_flag.is_set(): return

    #         # --- Tier 2: Thumbnail Fetch (in the same thread) ---
    #         if info:
    #             thumbnail_url = info.get('thumbnail')
    #             if thumbnail_url:
    #                 try:
    #                     response = requests.get(thumbnail_url, stream=True)
    #                     response.raise_for_status()
    #                     image_data = response.content
    #                     raw_image = Image.open(BytesIO(image_data))

    #                     w, h = raw_image.size
    #                     aspect_ratio = h / w
    #                     new_width = 480
    #                     new_height = int(new_width * aspect_ratio)
    #                     pillow_image = raw_image.resize((new_width, new_height), Image.LANCZOS)
    #                 except Exception as e:
    #                     print(f"Failed to load thumbnail: {e}")

    #     except yt_dlp.utils.DownloadError as e:
    #         if self.stop_operation_flag.is_set(): return
    #         error_message = str(e).lower()

    #         blocking_errors = ["sign in to confirm you're not a bot", "http error 429", "too many requests", "winerror 10054", "forcibly closed by the remote host"]
    #         private_video_errors = ["private video", "video unavailable"]
    #         invalid_url_errors = ["is not a valid url"]

    #         if any(err in error_message for err in invalid_url_errors):
    #             self.root.after(0, lambda: messagebox.showerror("Invalid URL", "The URL you entered does not appear to be a valid YouTube link."))
    #             self.root.after(0, self.reset_ui_after_error)
    #             return

    #         if any(err in error_message for err in private_video_errors):
    #             self.root.after(0, lambda: messagebox.showerror("Video Not Found", "This video is private, has been deleted, or is otherwise unavailable."))
    #             self.root.after(0, self.reset_ui_after_error)
    #             return

    #         if any(err in error_message for err in blocking_errors):
    #             # --- Tier 2: Try with browser cookies ---
    #             browsers = ['chrome', 'firefox', 'edge', 'opera', 'brave']
    #             for browser in browsers:
    #                 if self.stop_operation_flag.is_set(): return
    #                 try:
    #                     ydl_opts_cookies = {'noplaylist': True, 'quiet': True, 'cookiesfrombrowser': (browser,)}
    #                     with yt_dlp.YoutubeDL(ydl_opts_cookies) as ydl:
    #                         info = ydl.extract_info(url, download=False)
    #                     print(f"Successfully extracted info using {browser} cookies.")
    #                     break 
    #                 except Exception as browser_e:
    #                     print(f"Could not get info with {browser} cookies: {browser_e}.")
    #                     info = None

    #             if self.stop_operation_flag.is_set(): return
    #             error_message = str(e).lower()

    #             if not info:
    #                 self.root.after(0, self.show_cookie_error_dialog)
    #                 self.root.after(0, self.reset_ui_after_error)
    #                 return
    #         else:
    #             if self.stop_operation_flag.is_set(): return
    #             self.root.after(0, lambda: messagebox.showerror("Connection Error", "Could not connect to YouTube. Please check your internet connection and try again."))
    #             self.root.after(0, self.reset_ui_after_error)
    #             return

    #     except Exception as e:
    #         if self.stop_operation_flag.is_set(): return
    #         self.root.after(0, lambda: messagebox.showerror("An Unexpected Error Occurred", f"An unknown error occurred. Please restart the application and try again.\n\nDetails: {str(e)}"))
    #         self.root.after(0, self.reset_ui_after_error)
    #         return

    #     if self.stop_operation_flag.is_set(): return

    #     if not info:
    #         self.root.after(0, self.reset_ui_after_error)
    #         return

    #     self.root.after(0, self.update_ui_after_analysis, info)


    def fetch_qualities(self, url):
        info = None
        pillow_image = None
        
        try:
            # --- Tier 1: Metadata Fetch ---
            with yt_dlp.YoutubeDL({'noplaylist': True, 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)

            if self.stop_operation_flag.is_set(): return

            # --- Tier 2: Thumbnail Fetch (in the same thread) ---
            if info:
                thumbnail_url = info.get('thumbnail')
                if thumbnail_url:
                    try:
                        response = requests.get(thumbnail_url, stream=True, timeout=10)
                        response.raise_for_status()
                        image_data = response.content
                        raw_image = Image.open(BytesIO(image_data))
                        
                        w, h = raw_image.size
                        aspect_ratio = h / w
                        new_width = 480
                        new_height = int(new_width * aspect_ratio)
                        pillow_image = raw_image.resize((new_width, new_height), Image.LANCZOS)
                    except Exception as e:
                        print(f"Failed to load thumbnail: {e}")
                        pillow_image = None # Ensure it's None on failure

        except yt_dlp.utils.DownloadError as e:
            if self.stop_operation_flag.is_set(): return
            error_message = str(e).lower()
            
            blocking_errors = ["sign in to confirm you're not a bot", "http error 429", "too many requests", "winerror 10054", "forcibly closed by the remote host"]
            private_video_errors = ["private video", "video unavailable"]
            invalid_url_errors = ["is not a valid url"]

            if any(err in error_message for err in invalid_url_errors):
                self.root.after(0, lambda: messagebox.showerror("Invalid URL", "The URL you entered does not appear to be a valid YouTube link."))
                self.root.after(0, self.reset_ui_after_error)
                return

            if any(err in error_message for err in private_video_errors):
                self.root.after(0, lambda: messagebox.showerror("Video Not Found", "This video is private, has been deleted, or is otherwise unavailable."))
                self.root.after(0, self.reset_ui_after_error)
                return

            if any(err in error_message for err in blocking_errors):
                browsers = ['chrome', 'firefox', 'edge', 'opera', 'brave']
                for browser in browsers:
                    if self.stop_operation_flag.is_set(): return
                    try:
                        ydl_opts_cookies = {'noplaylist': True, 'quiet': True, 'cookiesfrombrowser': (browser,)}
                        with yt_dlp.YoutubeDL(ydl_opts_cookies) as ydl:
                            info = ydl.extract_info(url, download=False)
                        print(f"Successfully extracted info using {browser} cookies.")
                        break 
                    except Exception as browser_e:
                        print(f"Could not get info with {browser} cookies: {browser_e}.")
                        info = None
                
                if self.stop_operation_flag.is_set(): return
                if not info:
                    self.root.after(0, self.show_cookie_error_dialog)
                    self.root.after(0, self.reset_ui_after_error)
                    return
            else:
                if self.stop_operation_flag.is_set(): return
                self.root.after(0, lambda: messagebox.showerror("Connection Error", "Could not connect to YouTube. Please check your internet connection and try again."))
                self.root.after(0, self.reset_ui_after_error)
                return

        except Exception as e:
            if self.stop_operation_flag.is_set(): return
            self.root.after(0, lambda: messagebox.showerror("An Unexpected Error Occurred", f"An unknown error occurred. Please restart the application and try again.\n\nDetails: {str(e)}"))
            self.root.after(0, self.reset_ui_after_error)
            return

        if self.stop_operation_flag.is_set(): return

        if not info:
            self.root.after(0, self.reset_ui_after_error)
            return
        
        # --- Final Step: Call the main UI updater with all data ready ---
        self.root.after(0, self.update_ui_with_results, info, pillow_image)

    # def fetch_with_cookies(self):
    #     """A specific fetcher that ONLY uses the manually imported cookie file."""
    #     url = self.url_entry.get()
    #     if not self.cookie_file_path or not os.path.exists(self.cookie_file_path):
    #         messagebox.showerror("Error", "Cookie file not found or not specified.")
    #         self.reset_ui_after_error()
    #         return
            
    #     try:
    #         ydl_opts = {'noplaylist': True, 'quiet': True, 'cookiefile': self.cookie_file_path}
    #         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #             info = ydl.extract_info(url, download=False)
    #         self.root.after(0, self.update_ui_after_analysis, info)
    #     except Exception as e:
    #         messagebox.showerror("Analysis with Cookies Failed", f"Could not analyze the video using the provided cookies.\n\nError: {e}")
    #         self.root.after(0, self.reset_ui_after_error)


    def fetch_with_cookies(self):
        """A specific fetcher that uses a cookie file and also fetches the thumbnail."""
        url = self.url_entry.get()
        info = None
        pillow_image = None

        if not self.cookie_file_path or not os.path.exists(self.cookie_file_path):
            messagebox.showerror("Error", "Cookie file not found or not specified.")
            self.reset_ui_after_error()
            return

        try:
            ydl_opts = {'noplaylist': True, 'quiet': True, 'cookiefile': self.cookie_file_path}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info:
                thumbnail_url = info.get('thumbnail')
                if thumbnail_url:
                    try:
                        response = requests.get(thumbnail_url, stream=True)
                        response.raise_for_status()
                        image_data = response.content
                        raw_image = Image.open(BytesIO(image_data))

                        w, h = raw_image.size
                        aspect_ratio = h / w
                        new_width = 480
                        new_height = int(new_width * aspect_ratio)
                        pillow_image = raw_image.resize((new_width, new_height), Image.LANCZOS)
                    except Exception as e:
                        print(f"Failed to load thumbnail: {e}")

        except Exception as e:
            messagebox.showerror("Analysis with Cookies Failed", f"Could not analyze the video using the provided cookies.\n\nError: {e}")
            self.root.after(0, self.reset_ui_after_error)
            return

        if not info:
            self.root.after(0, self.reset_ui_after_error)
            return

        self.root.after(0, self.update_ui_with_results, info, pillow_image)



    # def update_ui_after_analysis(self, info):
    #     """Safely updates the UI with fetched video info from the main thread."""
    #     self.is_animating = False
        
    #     # --- NEW SOLUTION: Destroy the old label completely ---
    #     if self.current_thumbnail_label:
    #         self.current_thumbnail_label.destroy()
    #         self.current_thumbnail_label = None
        
    #     self.info_frame.pack_forget()
    #     self.root.geometry("600x600")
    #     # --- END NEW SOLUTION ---

    #     thumbnail_url = info.get('thumbnail')
    #     uploader_name = f"Uploader: {info.get('uploader', 'N/A')}"
    #     self.uploader_label.configure(text=uploader_name)

    #     # Create a brand new label for the new thumbnail
    #     self.current_thumbnail_label = ctk.CTkLabel(self.info_frame, text="Loading thumbnail...")
    #     # Pack the container frame to make the "Loading..." text visible
    #     self.info_frame.pack(fill="x", pady=(15, 5))
    #     self.current_thumbnail_label.pack()
        
    #     if thumbnail_url:
    #         threading.Thread(target=self.load_thumbnail, args=(thumbnail_url,), daemon=True).start()
    #     else:
    #         # If no URL, pass None to the UI updater to show an error
    #         self.root.after(0, self.update_ui_with_thumbnail, None)


    #     self.original_video_title = info.get('title', 'Untitled Video')
    #     self.available_formats = []
    #     formats = info.get('formats', [])
    #     for f in formats:
    #         if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
    #             filesize_mb = f.get('filesize') or f.get('filesize_approx')
    #             filesize_str = f"{filesize_mb / (1024*1024):.2f} MB" if filesize_mb else "N/A"
    #             if f.get('acodec') != 'none':
    #                 display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str}"
    #                 is_merged = True
    #             else:
    #                 display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str} (Requires FFmpeg)"
    #                 is_merged = False
    #             self.available_formats.append({'text': display_text, 'format_id': f['format_id'], 'is_merged': is_merged, 'height': f.get('height', 0)})
        
    #     if self.available_formats:
    #         self.available_formats.sort(key=lambda x: x['height'], reverse=True)
    #         display_list = [f['text'] for f in self.available_formats]
    #         self.quality_combobox.configure(values=display_list)
            
    #         # Get the highest quality format object (the first one after sorting)
    #         highest_quality_format = self.available_formats[0]
            
    #         # Set the combobox to display the text of the highest quality format
    #         self.quality_combobox.set(highest_quality_format['text'])
            
    #         # Directly update the video title based on this default highest quality
    #         quality_str = f"{highest_quality_format['height']}p"
    #         initial_title = f"{self.original_video_title} - [{quality_str}] - By Chai & Clip"
    #         self.video_title_var.set(initial_title)

    #         # highest_quality_format_text = display_list[0]
    #         # print("----------------------------------------@@@@@@@@@@")
    #         # print(highest_quality_format_text)
    #         # self.quality_combobox.set(highest_quality_format_text)
            
    #         # # Now that the value is set, call the function to update the title
    #         # self.on_quality_change(highest_quality_format_text)
            
    #         # self.quality_combobox.configure(state='readonly')

    #         # --- Set highest quality and update title automatically ---
            
    #         self.quality_combobox.configure(state='readonly')
            
    #         highest_quality_format_text = display_list[0]
    #         self.quality_combobox.set(highest_quality_format_text)
            
    #         self.on_quality_change(highest_quality_format_text)


    #         self.download_button.configure(state="normal")
    #         self.title_entry.configure(state="normal")
    #         self.status_label.configure(text="Select a quality and download.")
    #     else:
    #         self.status_label.configure(text="No MP4 formats found.")
    #         messagebox.showwarning("Warning", "Could not find any MP4 formats.")
        
    #     self.analyze_button.configure(state="normal")

    # def on_quality_change(self, choice):
    #     selected_value = self.quality_combobox.get()
    #     selected_format = next((f for f in self.available_formats if f['text'] == selected_value), None)
    #     if not selected_format: return
    #     quality_str = f"{selected_format['height']}p"
    #     new_title = f"{self.original_video_title} - [{quality_str}] - By Chai & Clip"
    #     self.video_title_var.set(new_title)



    def on_quality_change(self, choice):
        selected_value = self.quality_combobox.get()
        selected_format = next((f for f in self.available_formats if f['text'] == selected_value), None)
        if not selected_format: return
        quality_str = f"{selected_format['height']}p"
        new_title = f"{self.original_video_title} - [{quality_str}] - By Chai & Clip"
        self.video_title_var.set(new_title)

    def start_download(self):
        # self.stop_download_flag.clear()
        self.stop_operation_flag.clear()
        self.final_filepath = None
        self.speed_samples.clear()
        self.download_button.configure(state="disabled")
        self.analyze_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.browse_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.status_label.configure(text="Preparing download...")
        
        url = self.url_entry.get()
        path = self.path_var.get()
        selected_value = self.quality_combobox.get()
        selected_format = next((f for f in self.available_formats if f['text'] == selected_value), None)

        if not selected_format:
            messagebox.showerror("Error", "Please select a valid quality.")
            self.reset_ui()
            return
        
        self.download_thread = threading.Thread(target=self.download_video, args=(url, path, selected_format), daemon=True)
        self.download_thread.start()

    # def stop_download(self):
    #     self.status_label.configure(text="Stopping download...")
    #     self.stop_download_flag.set()
    #     self.stop_button.configure(state="disabled")

    def stop_operation(self):
        """Stops the current operation (analysis or download) and resets the UI."""
        if self.is_animating:
            self.is_animating = False

        self.status_label.configure(text="Stopping operation...")
        self.stop_operation_flag.set()
        self.stop_button.configure(state="disabled")

        # Immediately reset the main UI elements to allow for a new operation
        self.analyze_button.configure(state="normal")
        self.browse_button.configure(state="normal")
        self.status_label.configure(text="Operation cancelled. Ready for new URL.")

    def update_download_progress(self, d):
        def format_bytes(b):
            if b is None: return "---";
            if b < 1024: return f"{b} B";
            if b < 1024**2: return f"{b/1024:.2f} KiB";
            if b < 1024**3: return f"{b/1024**2:.2f} MiB";
            return f"{b/1024**3:.2f} GiB"
        def format_time(s):
            if s is None: return "---";
            mins, secs = divmod(int(s), 60);
            return f"{mins:02d}:{secs:02d}"
        # total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        # if total_bytes:
        #     percentage = d['downloaded_bytes'] / total_bytes;
        #     speed = d.get('speed');
        #     if speed is not None: self.speed_samples.append(speed)
        #     avg_speed = sum(self.speed_samples) / len(self.speed_samples) if self.speed_samples else 0
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total_bytes:
            percentage = d['downloaded_bytes'] / total_bytes
            speed = d.get('speed')

            if speed and speed > 0:
                self.speed_samples.append(speed)

            # avg_speed = sum(self.speed_samples) / len(self.speed_samples) if self.speed_samples else 0
        
            # self.progress_bar.set(percentage);
            # self.progress_label.configure(text=f"{int(percentage*100)}%");
            # self.size_label.configure(text=f"Size: {format_bytes(total_bytes)}");
            # self.speed_label.configure(text=f"Speed: {format_bytes(avg_speed)}/s");
            # self.eta_label.configure(text=f"ETA: {format_time(d.get('eta'))}");
            # self.status_label.configure(text="Downloading...")

            avg_speed = sum(self.speed_samples) / len(self.speed_samples) if self.speed_samples else 0

        eta_seconds = None
        if avg_speed > 0:
            remaining_bytes = total_bytes - d['downloaded_bytes']
            eta_seconds = remaining_bytes / avg_speed

        self.progress_bar.set(percentage)
        self.progress_label.configure(text=f"{int(percentage*100)}%")
        self.size_label.configure(text=f"Size: {format_bytes(total_bytes)}")
        self.speed_label.configure(text=f"Speed: {format_bytes(avg_speed)}/s")
        self.eta_label.configure(text=f"ETA: {format_time(eta_seconds)}") 
        self.status_label.configure(text="Downloading...")

    def progress_hook(self, d):
        # if self.stop_download_flag.is_set(): raise Exception("Download stopped by user.")
        if self.stop_operation_flag.is_set(): raise Exception("Download stopped by user.")
        if d['status'] == 'downloading': self.root.after(0, self.update_download_progress, d)
        elif d['status'] == 'finished':
            self.final_filepath = d.get('info_dict', {}).get('filepath')
            self.root.after(0, lambda: self.status_label.configure(text="Download complete! Finalizing..."))

    def download_video(self, url, path, selected_format):
        try:
            ffmpeg_path = os.path.join(self.application_path, "ffmpeg.exe")
            custom_title = self.video_title_var.get()
            sanitized_title = re.sub(r'[\\/*?:"<>|]', "", custom_title)
            format_id = selected_format['format_id']
            # format_spec = f'{format_id}+bestaudio/best' if not selected_format['is_merged'] else format_id
            # ydl_opts = {'format': format_spec, 'outtmpl': os.path.join(path, f'{sanitized_title}.%(ext)s'), 'progress_hooks': [self.progress_hook], 'noplaylist': True, 'merge_output_format': 'mp4', 'ffmpeg_location': ffmpeg_path, 'nocolor': True,}
            format_spec = f'{format_id}+bestaudio/best' if not selected_format['is_merged'] else format_id

            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(path, f'{sanitized_title}.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'noplaylist': True,
                'merge_output_format': 'mp4',
                'ffmpeg_location': ffmpeg_path,
                'nocolor': True,
            }

            if self.cookie_file_path:
                ydl_opts['cookiefile'] = self.cookie_file_path
            # if self.cookie_file_path: ydl_opts['cookiefile'] = self.cookie_file_path


            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            # if not self.stop_download_flag.is_set():
            if not self.stop_operation_flag.is_set():
                final_expected_path = os.path.join(path, f"{sanitized_title}.mp4")
                if os.path.exists(final_expected_path): self.final_filepath = final_expected_path
                if self.final_filepath: self.root.after(0, self.show_success_dialog, self.final_filepath)
                else: messagebox.showinfo("Success", "Download completed, but could not verify the final file path.")
        except Exception as e:
            if "Download stopped by user" not in str(e):
                self.status_label.configure(text=f"Error: {str(e)}")
                messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            self.reset_ui()

    def show_success_dialog(self, file_path):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Success")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(main_frame, text="Download completed successfully!", font=("Segoe UI", 16)).pack(pady=10)
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)
        ctk.CTkButton(button_frame, text="Open File", command=lambda: (self.open_path(file_path), dialog.destroy())).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Open Directory", command=lambda: (self.open_path(os.path.dirname(file_path)), dialog.destroy())).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Close", command=dialog.destroy).pack(side="left", padx=5)
        dialog.transient(self.root)
        dialog.grab_set()

    def open_path(self, path):
        try:
            if sys.platform == "win32": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open path:\n{e}")

    def reset_ui_after_error(self):
        """Resets only the UI elements necessary after an analysis error."""

        self.is_animating = False

        self.status_label.configure(text="Analysis failed. Please try again.")
        self.analyze_button.configure(state="normal")
        self.quality_combobox.set("Click 'Analyze' to see options")
        self.quality_combobox.configure(state='disabled')
        self.title_entry.configure(state='disabled')
        self.video_title_var.set("")

        # Hide the info frame and shrink the window
        self.info_frame.pack_forget()
        self.root.geometry("600x600")
        
        # --- NEW Reset Logic ---
        if self.current_thumbnail_label:
            self.current_thumbnail_label.destroy()
            self.current_thumbnail_label = None

        self.info_frame.pack_forget()
        self.root.geometry("600x600")
        
        self.uploader_label.configure(text="")
        self.thumbnail_image = None # This variable is still used, so clear it



    def reset_ui(self):
        self.download_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.browse_button.configure(state="normal")
        self.analyze_button.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.size_label.configure(text="Size: ---")
        self.speed_label.configure(text="Speed: ---")
        self.eta_label.configure(text="ETA: ---")
        self.quality_combobox.set("Click 'Analyze' to see options")
        self.quality_combobox.configure(state='disabled')
        self.title_entry.configure(state='disabled')
        self.video_title_var.set("")
        # if not self.stop_download_flag.is_set():
        if not self.stop_operation_flag.is_set():
             self.status_label.configure(text="Enter a new URL to begin.")
             

        # --- NEW Reset Logic ---
        if self.current_thumbnail_label:
            self.current_thumbnail_label.destroy()
            self.current_thumbnail_label = None

        self.info_frame.pack_forget()
        self.root.geometry("600x600")
        
        self.uploader_label.configure(text="")
        self.thumbnail_image = None # This variable is still used, so clear it

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        myappid = u'mycompany.chaiandclip.downloader.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app_root = ctk.CTk()
    downloader_app = YouTubeDownloader(app_root)
    app_root.mainloop()
