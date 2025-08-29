import os
import sys
import threading
import yt_dlp
import subprocess
import re
import customtkinter as ctk
from tkinter import filedialog, messagebox
from collections import deque

import json

import webbrowser

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
        # If the application is run as a bundled executable, the path is in sys._MEIPASS
                self.application_path = sys._MEIPASS
            else:
                self.application_path = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(self.application_path, "assets", "logo.ico")
            
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
        # self.cookie_file_path = None
        self.is_animating = False
        self.dot_count = 0

        self.last_clipboard_url = ""
        self.popup_window = None

        self.download_mode = "Video" # Default mode is Video

        self.settings_window = None
        self.settings = self._load_settings()

        self.create_widgets()
        self._apply_settings()
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
        # --- Settings Button ---
        # Using a placeholder text '⚙' for the gear icon
        self.settings_button = ctk.CTkButton(top_bar_frame, text="⚙", font=("Segoe UI", 20),
                                            width=30, height=30, command=self.open_settings_window)
        self.settings_button.pack(side="right")
        self.cookie_status_label = ctk.CTkLabel(top_bar_frame, text="Status: Not Authenticated", font=("Segoe UI", 10), text_color="gray")
        self.cookie_status_label.pack(side="right", padx=10)

        

        # --- URL Input & Analysis ---
        url_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        url_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(url_frame, text="YouTube URL:", font=("Segoe UI", 14)).pack(side="left")
        # self.url_entry = ctk.CTkEntry(url_frame, font=("Segoe UI", 12), height=35)
        # self.url_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        # self.analyze_button = ctk.CTkButton(url_frame, text="Analyze", command=self.start_fetch_thread, height=35, width=80)
        # self.analyze_button.pack(side="left")


        self.url_entry = ctk.CTkEntry(url_frame, font=("Segoe UI", 12), height=35)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(10, 5)) # Reduced padding

        self.clear_button = ctk.CTkButton(url_frame, text="Clear", command=self.clear_interface, 
                                        height=35, width=60, fg_color="gray", hover_color="dimgray")
        self.clear_button.pack(side="left", padx=(0, 5))

        self.analyze_button = ctk.CTkButton(url_frame, text="Analyze", command=self.start_fetch_thread, height=35, width=80)
        self.analyze_button.pack(side="left")

        # --- Download Mode Selector ---
        mode_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        mode_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(mode_frame, text="Download Mode:", font=("Segoe UI", 14)).pack(side="left", padx=(0, 10))

        self.mode_selector = ctk.CTkSegmentedButton(mode_frame, values=["Video", "Audio"],
                                                    command=self._on_mode_change,
                                                    font=("Segoe UI", 12, "bold"))
        self.mode_selector.set("Video") # Set default value
        self.mode_selector.pack(side="left", expand=True, fill="x")


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

                # --- Footer ---
        footer_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", pady=(10, 0))

        # "Developed by" Label
        ctk.CTkLabel(footer_frame, text="Developed by YaserZarifi", font=("Segoe UI", 10, "italic"), text_color="gray").pack(side="left", padx=10)

        # "Send Feedback" Link
        feedback_font = ctk.CTkFont(family="Segoe UI", size=10, underline=True)
        feedback_label = ctk.CTkLabel(footer_frame, text="Send Feedback", font=feedback_font, text_color="#5cb8f2", cursor="hand2")
        feedback_label.pack(side="right", padx=10)
        feedback_label.bind("<Button-1>", lambda e: self.open_feedback_link())






    def check_clipboard(self):
        """Periodically checks the clipboard and shows a popup if a new YouTube URL is found."""

        # First, check if the feature is enabled in settings
        if not self.settings.get("clipboard_popup_enabled", True):
            # If disabled, just reschedule the check and do nothing else.
            self.root.after(1500, self.check_clipboard)
            return
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



    def show_url_popup(self, url):
        """Creates a bigger, bolder, centered, top-most popup to analyze a detected URL."""
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.lift()
            return

        self.popup_window = ctk.CTkToplevel(self.root)
        self.popup_window.title("New URL Detected")
        
        # --- MODIFICATION: Make the window always on top ---
        self.popup_window.attributes("-topmost", True)

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
        # for f in formats:
        #     if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
        #         filesize_mb = f.get('filesize') or f.get('filesize_approx')
        #         filesize_str = f"{filesize_mb / (1024*1024):.2f} MB" if filesize_mb else "N/A"
        #         if f.get('acodec') != 'none':
        #             display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str}"
        #         else:
        #             display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str} (Requires FFmpeg)"
        #         self.available_formats.append({'text': display_text, 'height': f.get('height', 0)})

        for f in formats:
            if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                filesize_mb = f.get('filesize') or f.get('filesize_approx')
                filesize_str = f"{filesize_mb / (1024*1024):.2f} MB" if filesize_mb else "N/A"

                is_merged = f.get('acodec') != 'none'

                if is_merged:
                    display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str}"
                else:
                    display_text = f"{f.get('height', 'N/A')}p - {f.get('fps', 'N/A')}fps - {filesize_str} (Requires FFmpeg)"

                # --- FIX: Add the missing data back into the dictionary ---
                self.available_formats.append({
                    'text': display_text, 
                    'height': f.get('height', 0),
                    'format_id': f['format_id'], 
                    'is_merged': is_merged
                })
        if self.available_formats:
            self.available_formats.sort(key=lambda x: x['height'], reverse=True)
            display_list = [f['text'] for f in self.available_formats]
            self.quality_combobox.configure(values=display_list, state='readonly')

            if self.download_mode == "Audio":
                self.quality_combobox.configure(state="disabled")


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



    def on_quality_change(self, choice):
        """Updates the filename when quality or mode changes."""
        if not self.original_video_title:
            return

        if self.download_mode == "Video":
            selected_value = self.quality_combobox.get()
            selected_format = next((f for f in self.available_formats if f['text'] == selected_value), None)
            if not selected_format: return
            quality_str = f"{selected_format['height']}p"
            new_title = f"{self.original_video_title} - [{quality_str}] - By NavaGir"
        else: # Audio mode
            new_title = f"{self.original_video_title} - [Audio] - By NavaGir"

        self.video_title_var.set(new_title)



    def _on_mode_change(self, selected_mode: str):
        """Called when the user switches between Video and Audio mode."""
        self.download_mode = selected_mode

        # If no video has been analyzed yet, do nothing further
        if not self.original_video_title:
            return

        if selected_mode == "Audio":
            # Disable quality selection for audio
            self.quality_combobox.configure(state="disabled")
            self.status_label.configure(text="Audio mode: Highest quality will be downloaded as MP3.")
        else: # Video mode
            # Re-enable quality selection
            self.quality_combobox.configure(state="readonly")
            self.status_label.configure(text="Select a quality and download.")

        # Update the title to reflect the new mode and extension
        self.on_quality_change(None)


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
            ffmpeg_path = os.path.join(self.application_path, "assets", "ffmpeg.exe")
            custom_title = self.video_title_var.get()
            sanitized_title = re.sub(r'[\\/*?:"<>|]', "", custom_title)

            ydl_opts = {
                'progress_hooks': [self.progress_hook],
                'noplaylist': True,
                'ffmpeg_location': ffmpeg_path,
                'nocolor': True,
            }

            if self.cookie_file_path:
                ydl_opts['cookiefile'] = self.cookie_file_path

            # --- NEW: Logic for Video vs Audio Download ---
            if self.download_mode == "Video":
                selected_format = next((f for f in self.available_formats if f['text'] == self.quality_combobox.get()), None)
                format_id = selected_format['format_id']
                format_spec = f'{format_id}+bestaudio/best' if not selected_format['is_merged'] else format_id

                ydl_opts['format'] = format_spec
                ydl_opts['outtmpl'] = os.path.join(path, f'{sanitized_title}.%(ext)s')
                ydl_opts['merge_output_format'] = 'mp4'
                final_extension = 'mp4'

            else: # Audio Mode
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['outtmpl'] = os.path.join(path, f'{sanitized_title}.%(ext)s')
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192', # Standard high quality
                }]
                final_extension = 'mp3'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not self.stop_operation_flag.is_set():
                final_expected_path = os.path.join(path, f"{sanitized_title}.{final_extension}")
                if os.path.exists(final_expected_path):
                    self.final_filepath = final_expected_path

                if self.final_filepath:
                    self.root.after(0, self.show_success_dialog, self.final_filepath)
                else:
                    messagebox.showinfo("Success", f"Download completed, but could not verify the final file path: {final_expected_path}")

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


                # Reset download mode
        self.mode_selector.set("Video")
        self.download_mode = "Video"


    def clear_interface(self):
        """Clears the URL entry and resets the entire UI to its initial state."""
        self.url_entry.delete(0, 'end')
        self.last_clipboard_url = "" # Reset clipboard tracking

        # Stop any ongoing operations like analysis
        if self.is_animating:
            self.stop_operation()

        self.reset_ui()
        self.status_label.configure(text="Enter a YouTube URL to begin.")

        # Reset download mode
        self.mode_selector.set("Video")
        self.download_mode = "Video"




    def open_feedback_link(self):
        """Opens the default email client with a pre-filled feedback email."""
        # IMPORTANT: Replace with your actual email address
        email_address = "yaserzarifi1378@gmail.com"
        subject = "Feedback for Chai & Clip App"

        # This creates a 'mailto' link that opens the user's email client
        mailto_link = f"mailto:{email_address}?subject={subject}"

        try:
            webbrowser.open(mailto_link)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open email client.\n\nPlease send feedback manually to:\n{email_address}")
            print(f"Failed to open mailto link: {e}")


    
    def _load_settings(self):
        """Loads settings from config.json, with defaults for missing values."""
        defaults = {
            "theme": "System",
            "download_path": os.path.join(os.path.expanduser('~'), 'Downloads'),
            "default_mode": "Video",
            "clipboard_popup_enabled": True
        }
        try:
            with open("config.json", "r") as f:
                settings = json.load(f)
                # Ensure all keys from defaults are present
                for key, value in defaults.items():
                    settings.setdefault(key, value)
                return settings
        except (FileNotFoundError, json.JSONDecodeError):
            return defaults

    def _save_settings(self):
        """Saves the current settings to config.json."""
        with open("config.json", "w") as f:
            json.dump(self.settings, f, indent=4)

    def open_settings_window(self):
        """Opens the settings window."""
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = ctk.CTkToplevel(self.root)
        self.settings_window.title("Settings")
        # --- Center the settings window ---
        popup_width = 500
        popup_height = 320
        screen_width = self.settings_window.winfo_screenwidth()
        screen_height = self.settings_window.winfo_screenheight()
        x = (screen_width / 2) - (popup_width / 2)
        y = (screen_height / 2) - (popup_height / 2)
        self.settings_window.geometry(f"{popup_width}x{popup_height}+{int(x)}+{int(y)}")
        
        self.settings_window.resizable(False, False)
        self.settings_window.transient(self.root)

        settings_frame = ctk.CTkFrame(self.settings_window)
        settings_frame.pack(expand=True, fill="both", padx=15, pady=15)

        # --- Theme Setting ---
        theme_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(theme_frame, text="Appearance Theme:", font=("Segoe UI", 14)).pack(side="left")

        theme_menu = ctk.CTkOptionMenu(theme_frame, values=["Light", "Dark", "System"],
                                    command=lambda theme: self.settings.update({"theme": theme}))
        theme_menu.set(self.settings["theme"])
        theme_menu.pack(side="right")

        # --- Default Mode Setting ---
        mode_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        mode_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(mode_frame, text="Default Start Mode:", font=("Segoe UI", 14)).pack(side="left")

        mode_selector_settings = ctk.CTkSegmentedButton(mode_frame, values=["Video", "Audio"],
                                                        font=("Segoe UI", 12, "bold"))
        mode_selector_settings.set(self.settings["default_mode"])
        mode_selector_settings.pack(side="right")

        # --- Clipboard Popup Setting ---
        clipboard_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        clipboard_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(clipboard_frame, text="Clipboard URL Popup:", font=("Segoe UI", 14)).pack(side="left")

        clipboard_switch = ctk.CTkSwitch(clipboard_frame, text="", width=0)
        if self.settings["clipboard_popup_enabled"]:
            clipboard_switch.select()  # Turn the switch on if the setting is True
        clipboard_switch.pack(side="right")

        # --- Download Path Setting ---
        path_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(path_frame, text="Default Download Path:", font=("Segoe UI", 14)).pack(side="left")

        def browse_new_path():
            directory = filedialog.askdirectory()
            if directory:
                path_entry.delete(0, 'end')
                path_entry.insert(0, directory)

        path_entry = ctk.CTkEntry(path_frame, font=("Segoe UI", 12))
        path_entry.insert(0, self.settings["download_path"])
        path_entry.pack(side="left", expand=True, fill="x", padx=(10, 5))

        browse_btn = ctk.CTkButton(path_frame, text="Browse...", width=80, command=browse_new_path)
        browse_btn.pack(side="left")

        # --- Save and Close Button ---
        def save_and_close():

            # Update settings from UI elements
            self.settings["theme"] = theme_menu.get()
            self.settings["download_path"] = path_entry.get()
            self.settings["default_mode"] = mode_selector_settings.get()
            self.settings["clipboard_popup_enabled"] = bool(clipboard_switch.get())


            self._save_settings()
            self._apply_settings() # Apply settings immediately
            self.settings_window.destroy()

        save_button = ctk.CTkButton(settings_frame, text="Save and Close", command=save_and_close, height=40)
        save_button.pack(side="bottom", pady=20)

        self.settings_window.protocol("WM_DELETE_WINDOW", save_and_close) # Also save on closing with 'X'

    def _apply_settings(self):
        """Applies the loaded settings to the application."""
        ctk.set_appearance_mode(self.settings["theme"])
        self.path_var.set(self.settings["download_path"])

        default_mode = self.settings["default_mode"]
        self.mode_selector.set(default_mode)
        self.download_mode = default_mode

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        myappid = u'mycompany.chaiandclip.downloader.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # ctk.set_appearance_mode("dark")

    ctk.set_default_color_theme("blue")
    
    app_root = ctk.CTk()
    downloader_app = YouTubeDownloader(app_root)
    app_root.mainloop()
