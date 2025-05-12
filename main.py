import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yt_dlp
import tkinter.font as tkfont
from tkinter import filedialog

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        root.title("YouTube Downloader")
        root.geometry("650x520")
        root.minsize(650, 520)

        # Set ttk styles for better appearance
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TButton', font=('Segoe UI', 10), padding=6)
        style.configure('TLabel', font=('Segoe UI', 11))
        style.configure('TEntry', font=('Segoe UI', 10))
        style.configure('TProgressbar', thickness=18)

        # URL input frame
        url_frame = ttk.Frame(root, padding=15)
        url_frame.pack(fill='x')
        ttk.Label(url_frame, text="YouTube URL:").pack(side='left')
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=('Segoe UI', 10))
        self.url_entry.pack(side='left', fill='x', expand=True, padx=(10, 0))

        # Fetch qualities button
        self.fetch_btn = ttk.Button(root, text="Get Video Formats", width=25, command=self.fetch_qualities)
        self.fetch_btn.pack(pady=(0, 15))

        # Loading bar (hidden initially)
        self.loading_bar = ttk.Progressbar(root, mode='indeterminate')
        self.loading_bar.pack(fill='x', padx=20)
        self.loading_bar.pack_forget()

        # Quality options frame (no scrolling, centered content)
        self.quality_frame = ttk.Frame(root, padding=(20, 10))
        self.quality_frame.pack(fill='both', expand=True)

        # Download progress bar (hidden initially)
        self.download_progress = ttk.Progressbar(root, length=610)
        self.download_progress.pack(pady=(0, 20), padx=20)
        self.download_progress.pack_forget()

        self.formats = []
        self.all_formats = []

        # Create the menu bar
        menu_bar = tk.Menu(root)
        root.config(menu=menu_bar)

        # Create the File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Add Preferences option
        file_menu.add_command(label="Choose Destination Folder", command=self.open_preferences)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

    def open_preferences(self):
        folder_selected = filedialog.askdirectory(initialdir='.', title="Select Download Folder")
        if folder_selected:
            self.download_folder = folder_selected
            messagebox.showinfo("Preferences", f"Download folder set to:\n{self.download_folder}")

    def fetch_qualities(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return

        # Disable controls during fetch
        self.fetch_btn.config(state='disabled')
        self.url_entry.config(state='disabled')
        self.clear_quality_options()
        self.download_progress['value'] = 0
        self.download_progress.pack_forget()

        # Show loading bar
        self.loading_bar.pack(pady=5)
        self.loading_bar.start()

        # Start background thread to fetch formats
        threading.Thread(target=self._fetch_formats_thread, args=(url,), daemon=True).start()

    def _fetch_formats_thread(self, url):
        ydl_opts = {'quiet': True, 'skip_download': True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = info.get('formats', [])
            self.all_formats = formats  # store all formats for reference

            # Filter mp4 formats with format_note, no duplicates on (height, format_note)
            seen = set()
            filtered_formats = []
            for f in formats:
                format_note = f.get('format_note')
                if f.get('ext') == 'mp4' and format_note and format_note.strip():
                    height = f.get('height')
                    vcodec = f.get('vcodec')
                    if height and vcodec != 'none':
                        key = (height, format_note)
                        if key not in seen:
                            seen.add(key)
                            filtered_formats.append(f)

            self.formats = filtered_formats
            self.root.after(0, self.show_quality_options)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch formats:\n{e}"))
        finally:
            self.root.after(0, self._fetch_cleanup)

    def _fetch_cleanup(self):
        self.loading_bar.stop()
        self.loading_bar.pack_forget()
        self.fetch_btn.config(state='normal')
        self.url_entry.config(state='normal')

    def clear_quality_options(self):
        for widget in self.quality_frame.winfo_children():
            widget.destroy()

    def show_quality_options(self):
        self.clear_quality_options()
        if not self.formats:
            messagebox.showinfo("No formats", "No suitable mp4 formats found.")
            return

        label = ttk.Label(self.quality_frame, text="Select quality to download:", font=('Segoe UI', 11, 'bold'))
        label.pack(pady=(0, 12))

        # Centered buttons with horizontal padding to constrain width
        for i, fmt in enumerate(self.formats):
            btn_label = f"{fmt['height']}p - {fmt.get('format_note', 'N/A')}"
            btn = ttk.Button(self.quality_frame, text=btn_label, command=lambda i=i: self.start_download(i))
            btn.pack(fill='x', pady=5, padx=150)

    def start_download(self, index):
        # Disable controls during download
        for widget in self.quality_frame.winfo_children():
            widget.config(state='disabled')
        self.fetch_btn.config(state='disabled')
        self.url_entry.config(state='disabled')

        # Show and reset progress bar
        self.download_progress.pack(pady=5)
        self.download_progress['value'] = 0

        selected_format = self.formats[index]
        video_format_id = selected_format['format_id']

        threading.Thread(target=self.download_thread, args=(self.url_var.get(), video_format_id), daemon=True).start()

    def download_thread(self, url, video_format_id):
        ydl_opts = {
            'format': f"{video_format_id}+bestaudio",
            'noplaylist': True,
            'outtmpl': '%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
            'progress_hooks': [self.progress_hook],
            'quiet': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.root.after(0, lambda: messagebox.showinfo("Success", "Download completed!"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Download failed:\n{e}"))
        finally:
            self.root.after(0, self.reset_ui)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes:
                progress = downloaded_bytes / total_bytes * 100
                self.root.after(0, lambda: self.download_progress.config(value=progress))
        elif d['status'] == 'finished':
            self.root.after(0, lambda: self.download_progress.config(value=100))

    def reset_ui(self):
        self.download_progress.pack_forget()
        self.download_progress.config(value=0)
        self.fetch_btn.config(state='normal')
        self.url_entry.config(state='normal')
        for widget in self.quality_frame.winfo_children():
            widget.config(state='normal')


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()