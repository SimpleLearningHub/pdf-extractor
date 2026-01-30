from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, Response, stream_with_context
import pypdf
from PIL import Image
from google import genai
import io, os
import json
import time

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
EXTRACTED_FOLDER = os.path.join('static', 'extracted_image')
EXTRACTED_TEXT_FOLDER = os.path.join('static', 'extracted_text')
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXTRACTED_FOLDER'] = EXTRACTED_FOLDER
app.config['EXTRACTED_TEXT_FOLDER'] = EXTRACTED_TEXT_FOLDER

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXTRACTED_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXTRACTED_TEXT_FOLDER'], exist_ok=True)


# Validates file extension
def allowed_file(filename):
    """
    Checks if the uploaded file has a valid extension.
    
    Args:
        filename (str): The name of the file.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_extracted_folder():
    """
    Clears the directory where extracted images are stored.
    This ensures that previous session data does not persist and clutter storage.
    """
    if os.path.exists(app.config['EXTRACTED_FOLDER']):
        for filename in os.listdir(app.config['EXTRACTED_FOLDER']):
            file_path = os.path.join(app.config['EXTRACTED_FOLDER'], filename)
            try:
                # Remove file or symbolic link
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

def extract_images_from_pdf(pdf_path):
    """
    Extracts all images from a PDF file and saves them to the configured folder.
    
    Args:
        pdf_path (str): The path to the source PDF file.
        
    Returns:
        int: The number of images extracted.
    """
    # Ensure directory exists (does not delete if already exists) to prevent FileNotFoundError
    os.makedirs(app.config['EXTRACTED_FOLDER'], exist_ok=True)
    clear_extracted_folder()
    
    reader = pypdf.PdfReader(pdf_path)
    image_count = 0
    
    # Iterate through each page of the PDF
    for page_num, page in enumerate(reader.pages):
        for image_file_object in page.images:
            image_count += 1
            # Determine image extension based on file object name
            ext = os.path.splitext(image_file_object.name)[1]
            if not ext:
                ext = ".png" # Default to png if no extension found
            
            # Construct a sequential filename
            filename = f"img_{image_count}{ext}"
            save_path = os.path.join(app.config['EXTRACTED_FOLDER'], filename)
            
            # Save the image data
            with open(save_path, "wb") as fp:
                fp.write(image_file_object.data)
                
    return image_count

def get_extracted_images():
    """
    Retrieves and sorts the list of extracted images from the storage folder.
    
    Returns:
        list: A sorted list of image filenames.
    """
    images = []
    if os.path.exists(app.config['EXTRACTED_FOLDER']):
        files = os.listdir(app.config['EXTRACTED_FOLDER'])
        
        # Filter for only supported image extensions
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'} 
        files = [f for f in files if os.path.splitext(f)[1].lower() in image_extensions]

        # Sort files numerically based on the 'img_N' pattern
        def sort_key(f):
            try:
                name_part = os.path.splitext(f)[0]
                num = int(name_part.split('_')[1])
                return num
            except (IndexError, ValueError):
                # Fallback for unexpected filenames
                return float('inf')

        files.sort(key=sort_key)
        images = files
    return images

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route handler. Renders the homepage, handles PDF uploads,
    and displays extracted images.
    """
    images = []
    if request.method == 'POST':
        # Handle file upload part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = "input.pdf"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            
            # Perform extraction
            count = extract_images_from_pdf(save_path)
            
            if count > 0:
                flash(f'Successfully extracted {count} images!')
            else:
                flash('No images found in the PDF.')
    
    # Always load existing images to display in the gallery
    images = get_extracted_images()
    
    # Check if a merged text file exists to show the download button
    has_merged = os.path.exists(os.path.join(app.config['EXTRACTED_TEXT_FOLDER'], 'merged_text.txt'))
    
    return render_template('index.html', images=images, has_merged=has_merged)

@app.route('/delete', methods=['POST'])
def delete_images():
    """
    Route to handle deletion of selected images and their corresponding extracted text files.
    """
    images_to_delete = request.form.getlist('images')
    deleted_count = 0
    
    if images_to_delete:
        for image_name in images_to_delete:
            # Security check to prevent path traversal attacks
            if '..' in image_name or '/' in image_name or '\\' in image_name:
                continue
            
            # Define paths
            file_path = os.path.join(app.config['EXTRACTED_FOLDER'], image_name)
            text_path = os.path.join(app.config['EXTRACTED_TEXT_FOLDER'], f"{image_name}.txt")
            
            try:
                # Remove image file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                # Remove corresponding text file if it exists
                if os.path.exists(text_path):
                    os.remove(text_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        
        if deleted_count > 0:
            flash(f'Successfully deleted {deleted_count} images.')
        else:
            flash('No images deleted.')
    else:
        flash('No images selected for deletion.')
        
    return redirect(url_for('index'))

@app.route('/extract_text', methods=['POST'])
def extract_text():
    """
    Route to handle text extraction from images using the Google GenAI API.
    Streams the response back to the client to update the progress bar.
    """
    api_key = request.form.get('api_key')
    prompt = request.form.get('prompt')
    model_name = request.form.get('model', 'gemini-1.5-flash')
    selected_images = request.form.getlist('images')

    # Basic Validation
    if not api_key or not prompt:
        return json.dumps({'error': 'Please provide both API Key and Prompt.'}), 400
    
    if not selected_images:
        return json.dumps({'error': 'No images selected.'}), 400

    # Store in session for user convenience (Note: Key is NOT permanently stored on server)
    session['api_key'] = api_key
    session['prompt'] = prompt
    session['model'] = model_name

    def generate():
        """Generator function to stream extraction progress and results."""
        try:
            # Initialize GenAI client
            client = genai.Client(api_key=api_key)
            # model = genai.GenerativeModel(model_name) # No longer needed in new SDK context like this
            
            # Ensure text output directory exists
            os.makedirs(app.config['EXTRACTED_TEXT_FOLDER'], exist_ok=True)
            
            merged_text_path = os.path.join(app.config['EXTRACTED_TEXT_FOLDER'], 'merged_text.txt')
            # Initialize/Clear merged text file
            with open(merged_text_path, 'w', encoding='utf-8') as f:
                f.write("")

            total_images = len(selected_images)
            success_count = 0
            
            for index, image_name in enumerate(selected_images):
                 # Security check
                 if '..' in image_name or '/' in image_name or '\\' in image_name:
                    continue
                 
                 image_path = os.path.join(app.config['EXTRACTED_FOLDER'], image_name)
                 if os.path.exists(image_path):
                     try:
                         # Notify client of start of extraction for this image
                         yield json.dumps({
                             'progress': index,
                             'total': total_images,
                             'status': f'Extracting text from {image_name}... ({index + 1}/{total_images})',
                             'current_image': image_name
                         }) + '\n'

                         # Perform generation
                         image = Image.open(image_path)
                         response = client.models.generate_content(model=model_name, contents=[prompt, image])
                         extracted_text = response.text
                         
                         # Save individual text result to a dedicated file
                         text_filename = f"{image_name}.txt"
                         with open(os.path.join(app.config['EXTRACTED_TEXT_FOLDER'], text_filename), 'w', encoding='utf-8') as f:
                             f.write(extracted_text)
                        
                         # Append to merged file for bulk download
                         with open(merged_text_path, 'a', encoding='utf-8') as f:
                             f.write(extracted_text)
                             f.write("\n\n")
                             
                         success_count += 1
                         
                     except Exception as e:
                         print(f"Failed to extract text from {image_name}: {e}")
                         yield json.dumps({'error': f"Error with {image_name}: {str(e)}"}) + '\n'

            # Final success message to client
            yield json.dumps({
                'progress': total_images,
                'total': total_images,
                'status': 'Extraction Complete!',
                'complete': True
            }) + '\n'

        except Exception as e:
             yield json.dumps({'error': f"API Error: {str(e)}"}) + '\n'

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

@app.route('/download_merged')
def download_merged():
    """
    Route to download the consolidated text file containing text from all processed images.
    """
    merged_path = os.path.join(app.config['EXTRACTED_TEXT_FOLDER'], 'merged_text.txt')
    if os.path.exists(merged_path):
        return send_file(merged_path, as_attachment=True, download_name='extracted_text_merged.txt')
    else:
        flash('No merged text file found.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
