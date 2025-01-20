from flask import Flask, request, jsonify, send_file, render_template
from video_processor import VideoProcessor
import os
import tempfile
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure processed videos folder
PROCESSED_FOLDER = 'processed'
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

# Store processing status
processing_status = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'gameplay' not in request.files or 'attention' not in request.files:
        return jsonify({'error': 'Missing files'}), 400
    
    gameplay_file = request.files['gameplay']
    attention_file = request.files['attention']
    
    if gameplay_file.filename == '' or attention_file.filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Create unique folder for this processing job
    job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    job_folder = os.path.join(PROCESSED_FOLDER, job_id)
    os.makedirs(job_folder)
    
    # Save uploaded files
    gameplay_path = os.path.join(job_folder, secure_filename(gameplay_file.filename))
    attention_path = os.path.join(job_folder, secure_filename(attention_file.filename))
    
    gameplay_file.save(gameplay_path)
    attention_file.save(attention_path)
    
    # Get processing parameters
    split_type = request.form.get('split_type', 'none')
    split_value = request.form.get('split_value', '0')
    
    # Start processing in background
    processing_status[job_id] = {
        'status': 'processing',
        'progress': 0,
        'files': []
    }
    
    try:
        # Initialize video processor
        processor = VideoProcessor(gameplay_path, attention_path)
        
        if split_type == 'none':
            # Process single video
            final_video = processor.process_videos()
            output_path = os.path.join(job_folder, 'part_1.mp4')
            final_video.write_videofile(output_path)
            processing_status[job_id]['files'].append(output_path)
            
        elif split_type == 'duration':
            # Split by duration
            duration = float(split_value)
            parts = processor.split_by_duration(duration)
            
            for i, part in enumerate(parts, 1):
                output_path = os.path.join(job_folder, f'part_{i}.mp4')
                part.write_videofile(output_path)
                processing_status[job_id]['files'].append(output_path)
                processing_status[job_id]['progress'] = (i / len(parts)) * 100
                
        elif split_type == 'parts':
            # Split by number of parts
            num_parts = int(split_value)
            parts = processor.split_by_parts(num_parts)
            
            for i, part in enumerate(parts, 1):
                output_path = os.path.join(job_folder, f'part_{i}.mp4')
                part.write_videofile(output_path)
                processing_status[job_id]['files'].append(output_path)
                processing_status[job_id]['progress'] = (i / num_parts) * 100
        
        processing_status[job_id]['status'] = 'completed'
        return jsonify({
            'job_id': job_id,
            'message': 'Processing started',
            'status': 'success'
        })
        
    except Exception as e:
        processing_status[job_id]['status'] = 'failed'
        processing_status[job_id]['error'] = str(e)
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(processing_status[job_id])

@app.route('/download/<job_id>/<filename>', methods=['GET'])
def download_file(job_id, filename):
    job_folder = os.path.join(PROCESSED_FOLDER, job_id)
    file_path = os.path.join(job_folder, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) 