import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from video_processor import VideoProcessor
from moviepy.editor import VideoFileClip
import numpy as np
import os
from datetime import timedelta

class VideoProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Processor")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        self.gameplay_path = None
        self.attention_path = None
        self.gameplay_duration = 0
        
        # Style configuration
        style = ttk.Style()
        style.configure('Modern.TButton', padding=10, font=('Helvetica', 10))
        style.configure('Modern.TLabel', font=('Helvetica', 10), background='#f0f0f0')
        style.configure('Title.TLabel', font=('Helvetica', 12, 'bold'), background='#f0f0f0')
        style.configure('Preview.TLabel', font=('Helvetica', 9), background='#f0f0f0', foreground='#666666')
        
        # Main container
        self.main_frame = ttk.Frame(root, padding="20", style='Modern.TFrame')
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(self.main_frame, text="Video Splitter", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # File selection section
        file_frame = ttk.LabelFrame(self.main_frame, text="Video Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Gameplay video selection
        ttk.Button(file_frame, text="Select Gameplay Video", command=self.select_gameplay, style='Modern.TButton').grid(row=0, column=0, padx=5, pady=5)
        self.gameplay_label = ttk.Label(file_frame, text="No file selected", style='Modern.TLabel')
        self.gameplay_label.grid(row=0, column=1, pady=5)
        
        # Attention video selection
        ttk.Button(file_frame, text="Select Attention Video", command=self.select_attention, style='Modern.TButton').grid(row=1, column=0, padx=5, pady=5)
        self.attention_label = ttk.Label(file_frame, text="No file selected", style='Modern.TLabel')
        self.attention_label.grid(row=1, column=1, pady=5)
        
        # Splitting options section
        split_frame = ttk.LabelFrame(self.main_frame, text="Split Options", padding="10")
        split_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.split_var = tk.StringVar(value="none")
        
        # No splitting option
        ttk.Radiobutton(split_frame, text="No splitting", variable=self.split_var, 
                       value="none", command=self.update_preview).grid(row=0, column=0, pady=5)
        
        # Split by duration
        ttk.Radiobutton(split_frame, text="Split by duration (seconds)", variable=self.split_var, 
                       value="duration", command=self.update_preview).grid(row=1, column=0, pady=5)
        self.duration_entry = ttk.Entry(split_frame, width=15)
        self.duration_entry.grid(row=1, column=1, padx=5, pady=5)
        self.duration_entry.bind('<KeyRelease>', lambda e: self.update_preview())
        
        # Split by parts
        ttk.Radiobutton(split_frame, text="Split by number of parts", variable=self.split_var, 
                       value="parts", command=self.update_preview).grid(row=2, column=0, pady=5)
        self.parts_entry = ttk.Entry(split_frame, width=15)
        self.parts_entry.grid(row=2, column=1, padx=5, pady=5)
        self.parts_entry.bind('<KeyRelease>', lambda e: self.update_preview())
        
        # Preview section
        preview_frame = ttk.LabelFrame(self.main_frame, text="Preview", padding="10")
        preview_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.preview_label = ttk.Label(preview_frame, text="", style='Preview.TLabel', wraplength=700)
        self.preview_label.grid(row=0, column=0, pady=5)
        
        # Process button
        ttk.Button(self.main_frame, text="Process Videos", command=self.process_videos, 
                  style='Modern.TButton').grid(row=4, column=0, columnspan=2, pady=10)
        
        # Status label
        self.status_label = ttk.Label(self.main_frame, text="", style='Modern.TLabel')
        self.status_label.grid(row=5, column=0, columnspan=2)

    def format_time(self, seconds):
        return str(timedelta(seconds=int(seconds)))

    def update_preview(self):
        if not self.gameplay_path:
            self.preview_label.config(text="Please select videos first")
            return
            
        split_option = self.split_var.get()
        if split_option == "none":
            self.preview_label.config(text=f"Final video duration: {self.format_time(self.gameplay_duration)}")
            
        elif split_option == "duration":
            try:
                duration = float(self.duration_entry.get() or 0)
                if duration <= 0:
                    self.preview_label.config(text="Please enter a valid duration")
                    return
                    
                num_parts = int(np.ceil(self.gameplay_duration / duration))
                last_part_duration = self.gameplay_duration % duration or duration
                
                preview_text = f"This will create {num_parts} videos of {self.format_time(duration)} each"
                if last_part_duration != duration:
                    preview_text += f"\nLast part will be {self.format_time(last_part_duration)}"
                
                self.preview_label.config(text=preview_text)
                
            except ValueError:
                self.preview_label.config(text="Please enter a valid number")
                
        elif split_option == "parts":
            try:
                num_parts = int(self.parts_entry.get() or 0)
                if num_parts <= 0:
                    self.preview_label.config(text="Please enter a valid number of parts")
                    return
                    
                duration_per_part = self.gameplay_duration / num_parts
                preview_text = f"This will create {num_parts} videos of {self.format_time(duration_per_part)} each"
                self.preview_label.config(text=preview_text)
                
            except ValueError:
                self.preview_label.config(text="Please enter a valid number")

    def select_gameplay(self):
        self.gameplay_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        if self.gameplay_path:
            self.gameplay_label.config(text=os.path.basename(self.gameplay_path))
            # Get video duration
            temp_clip = VideoFileClip(self.gameplay_path)
            self.gameplay_duration = temp_clip.duration
            temp_clip.close()
            self.update_preview()

    def select_attention(self):
        self.attention_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        if self.attention_path:
            self.attention_label.config(text=os.path.basename(self.attention_path))
            self.update_preview()

    def process_videos(self):
        if not self.gameplay_path or not self.attention_path:
            self.status_label.config(text="Please select both videos first!")
            return
        
        try:
            processor = VideoProcessor(self.gameplay_path, self.attention_path)
            split_option = self.split_var.get()
            
            # Get the base name of the gameplay video (without extension)
            video_name = os.path.splitext(os.path.basename(self.gameplay_path))[0]
            
            # Create main TIKTOK directory if it doesn't exist
            tiktok_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "Работен плот", "TIKTOK")
            if not os.path.exists(tiktok_dir):
                os.makedirs(tiktok_dir)
            
            # Create a folder for this video
            output_dir = os.path.join(tiktok_dir, video_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            if split_option == "none":
                self.status_label.config(text="Processing video...")
                self.root.update()
                final_video = processor.process_videos()
                output_path = os.path.join(output_dir, "part 1.mp4")
                final_video.write_videofile(output_path)
                self.status_label.config(text=f"Video saved to {output_path}")
                
            elif split_option == "duration":
                try:
                    duration = float(self.duration_entry.get())
                    if duration <= 0:
                        raise ValueError("Duration must be positive")
                    
                    self.status_label.config(text="Processing videos...")
                    self.root.update()
                    parts = processor.split_by_duration(duration)
                    
                    for i, part in enumerate(parts, 1):
                        self.status_label.config(text=f"Processing part {i} of {len(parts)}...")
                        self.root.update()
                        output_path = os.path.join(output_dir, f"part {i}.mp4")
                        part.write_videofile(output_path)
                    
                    self.status_label.config(text=f"Created {len(parts)} videos in {output_dir}")
                    messagebox.showinfo("Success", f"Created {len(parts)} videos in {output_dir}")
                    
                except ValueError as e:
                    self.status_label.config(text="Please enter a valid positive duration!")
                    
            elif split_option == "parts":
                try:
                    num_parts = int(self.parts_entry.get())
                    if num_parts <= 0:
                        raise ValueError("Number of parts must be positive")
                    
                    self.status_label.config(text="Processing videos...")
                    self.root.update()
                    parts = processor.split_by_parts(num_parts)
                    
                    for i, part in enumerate(parts, 1):
                        self.status_label.config(text=f"Processing part {i} of {num_parts}...")
                        self.root.update()
                        output_path = os.path.join(output_dir, f"part {i}.mp4")
                        part.write_videofile(output_path)
                    
                    self.status_label.config(text=f"Created {num_parts} videos in {output_dir}")
                    messagebox.showinfo("Success", f"Created {num_parts} videos in {output_dir}")
                    
                except ValueError:
                    self.status_label.config(text="Please enter a valid positive number of parts!")
                    
        except Exception as e:
            error_msg = str(e)
            self.status_label.config(text=f"Error: {error_msg}")
            messagebox.showerror("Error", error_msg)

def main():
    root = tk.Tk()
    app = VideoProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 