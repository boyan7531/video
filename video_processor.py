from moviepy.editor import VideoFileClip, CompositeVideoClip, clips_array, ColorClip, concatenate_videoclips, TextClip
import numpy as np
import os
from moviepy.config import change_settings
import whisper
import tempfile
import math
import textwrap

# Configure ImageMagick path
IMAGEMAGICK_BINARY = os.path.join(r"C:\Program Files\ImageMagick-7.1.1-Q16", "magick.exe")
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

class VideoProcessor:
    def __init__(self, gameplay_path, attention_path):
        # Load the videos
        self.gameplay = VideoFileClip(gameplay_path)
        self.attention = VideoFileClip(attention_path)
        
        # Target dimensions for TikTok (1080x1920)
        self.target_width = 1080
        self.target_height = 1920
        
        # Scale factors (1.2 for gameplay, 1.8 for attention video)
        self.gameplay_scale = 1.2
        self.attention_scale = 1.8
        
        # Initialize whisper model
        self.whisper_model = whisper.load_model("base")
        
        # Reduce max chars per line to ensure no more than 2 lines
        self.max_chars_per_line = 22
        
    def extract_audio_segment(self, start_time, end_time):
        """Extract audio segment from gameplay video and save it temporarily"""
        temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        # Extract the exact segment we want to transcribe
        audio_segment = self.gameplay.subclip(start_time, end_time).audio
        # Write the audio segment starting from 0 for proper whisper processing
        audio_segment.write_audiofile(temp_audio_file.name, fps=16000)
        return temp_audio_file.name
        
    def split_text_into_chunks(self, text, max_lines=2):
        """Split text into chunks that fit within max_lines"""
        # First, wrap the text according to max chars per line
        wrapped_lines = textwrap.wrap(text, width=self.max_chars_per_line)
        
        if len(wrapped_lines) <= max_lines:
            return ['\n'.join(wrapped_lines)]
            
        # If we have more lines than max_lines, split into chunks
        chunks = []
        current_chunk = []
        
        for line in wrapped_lines:
            if len(current_chunk) < max_lines:
                current_chunk.append(line)
            else:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks
        
    def generate_subtitles(self, start_time, end_time):
        """Generate subtitles using Whisper for the specified time segment"""
        # Extract audio segment
        audio_file = self.extract_audio_segment(start_time, end_time)
        
        try:
            # Transcribe using whisper
            result = self.whisper_model.transcribe(audio_file)
            
            # Process segments and create subtitle clips
            subtitle_clips = []
            for segment in result["segments"]:
                text = segment["text"].strip()
                if text:
                    # Add a small delay compensation (0.285 seconds) to account for processing
                    delay_compensation = 0.285
                    
                    # Since we extracted a segment starting at start_time, we need to:
                    # 1. Take whisper's timing (which is relative to the extracted audio starting at 0)
                    # 2. Add our delay compensation
                    segment_start = segment["start"] + delay_compensation
                    segment_end = segment["end"] + delay_compensation
                    total_duration = segment_end - segment_start
                    
                    # Split text into chunks if it would result in more than 2 lines
                    text_chunks = self.split_text_into_chunks(text, max_lines=2)
                    chunk_duration = total_duration / len(text_chunks)
                    
                    # Create a clip for each chunk
                    for i, chunk in enumerate(text_chunks):
                        chunk_start = segment_start + (i * chunk_duration)
                        
                        # Add fade in/out effect for smooth transitions
                        fade_duration = min(0.2, chunk_duration / 4)
                        
                        txt_clip = (TextClip(
                            chunk,
                            font='Fervent-Bold',  # Using bold font variant
                            fontsize=90,
                            color='white',
                            size=(self.target_width * 0.9, None),
                            method='caption',
                            stroke_color='black',
                            stroke_width=2
                        )
                        .set_duration(chunk_duration)
                        .crossfadein(fade_duration)
                        .crossfadeout(fade_duration))
                        
                        txt_clip = txt_clip.set_start(chunk_start)
                        subtitle_clips.append(txt_clip)
        
        finally:
            # Clean up audio file
            os.unlink(audio_file)
        
        return subtitle_clips
        
    def process_videos(self, start_time=0, end_time=None):
        if end_time is None:
            end_time = self.gameplay.duration

        # Get gameplay subclip
        gameplay_clip = self.gameplay.subclip(start_time, end_time)
        
        # Calculate how many times we need to loop the attention video
        clip_duration = end_time - start_time
        attention_full_duration = self.attention.duration
        loops_needed = int(np.ceil(clip_duration / attention_full_duration))
        
        # Create a list to store the attention video segments
        attention_segments = []
        remaining_duration = clip_duration
        current_time = 0
        
        # Create the looped attention video
        while remaining_duration > 0:
            segment_duration = min(remaining_duration, attention_full_duration)
            segment = self.attention.subclip(0, segment_duration)
            attention_segments.append(segment)
            remaining_duration -= segment_duration
            current_time += segment_duration
        
        # Concatenate all attention segments
        attention_clip = concatenate_videoclips(attention_segments)
            
        # Resize gameplay video (scaled up and positioned higher)
        gameplay_resized = gameplay_clip.resize(width=self.target_width * self.gameplay_scale)
        gameplay_height = gameplay_resized.h
        gameplay_y = (self.target_height * 0.3) - (gameplay_height / 2)
        
        # Resize attention video (scaled up more and positioned below)
        attention_resized = attention_clip.resize(width=self.target_width * self.attention_scale)
        attention_resized = attention_resized.without_audio()  # Mute second video
        attention_height = attention_resized.h
        attention_y = gameplay_y + gameplay_height + 20  # 20px gap
        
        # Center videos horizontally
        gameplay_x = -(gameplay_resized.w - self.target_width) / 2
        attention_x = -(attention_resized.w - self.target_width) / 2
        
        # Generate subtitles
        subtitle_clips = self.generate_subtitles(start_time, end_time)
        
        # Position all subtitle clips
        subtitle_y = gameplay_y + gameplay_height - 100  # Changed from -150 to -100
        positioned_subtitles = []
        for sub_clip in subtitle_clips:
            sub_w = sub_clip.w if hasattr(sub_clip, 'w') else self.target_width * 0.9
            subtitle_x = (self.target_width - sub_w) / 2
            positioned_sub = sub_clip.set_position((subtitle_x, subtitle_y))
            positioned_subtitles.append(positioned_sub)
        
        # Create black background
        background = ColorClip(size=(self.target_width, self.target_height), 
                             color=(0, 0, 0),
                             duration=end_time - start_time)
        
        # Set the duration for both clips explicitly
        gameplay_positioned = gameplay_resized.set_position((gameplay_x, gameplay_y)).set_duration(end_time - start_time)
        attention_positioned = attention_resized.set_position((attention_x, attention_y)).set_duration(end_time - start_time)
        
        # Create final composition with background
        clips_to_compose = [background, gameplay_positioned, attention_positioned] + positioned_subtitles
        final_video = CompositeVideoClip(
            clips_to_compose,
            size=(self.target_width, self.target_height)
        ).set_duration(end_time - start_time)
        
        return final_video
    
    def split_by_duration(self, duration_per_part):
        """Split video into parts of specified duration"""
        total_duration = self.gameplay.duration  # Use gameplay duration as the total
        parts = []
        
        current_time = 0
        while current_time < total_duration:
            end_time = min(current_time + duration_per_part, total_duration)
            part = self.process_videos(current_time, end_time)
            parts.append(part)
            current_time = end_time
            
        return parts
    
    def split_by_parts(self, num_parts):
        """Split video into specified number of parts"""
        total_duration = self.gameplay.duration  # Use gameplay duration as the total
        duration_per_part = total_duration / num_parts
        return self.split_by_duration(duration_per_part) 