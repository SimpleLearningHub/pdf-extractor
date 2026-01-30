# PDF Text Extractor

A robust Flask web application designed to extract text from images embedded within PDF files. It leverages Google's Gemini LLM to accurately transcribe text from images, making it an ideal tool for digitizing scanned documents or extracting content from image-heavy PDFs.

## Features

-   **PDF Image Extraction**: Automatically detects and extracts all images from an uploaded PDF file.
-   **AI-Powered Text Extraction**: Uses Google's Gemini models (e.g., Gemini 1.5 Flash) to transcribe text from extracted images.
-   **Bulk Processing**: Process multiple images at once with a progress bar.
-   **Merged Output**: Automatically compiles all extracted text into a single downloadable file.
-   **Session Management**: Remembers your API key and settings within the browser session for a smooth workflow.
-   **Secure**: API keys are not stored on the server's disk.

## Prerequisites

-   **Python**: Version 3.10 or higher recommended.
-   **Google AI API Key**: You need an API key from Google AI Studio to use the Gemini models. Get one [here](https://aistudio.google.com/).

## Installation

1.  **Clone the repository** (if applicable) or navigate to the project directory.

2.  **Install dependencies**:
    run the following command in your terminal to install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Start the Application**:
    Run the Flask app using the following command:
    ```bash
    python app.py
    ```
    You will see output indicating the server is running (usually at `http://127.0.0.1:5000`).

2.  **Open in Browser**:
    Navigate to `http://127.0.0.1:5000` in your web browser.

3.  **Upload a PDF**:
    -   Click "Choose File" and select a PDF document.
    -   Click "Upload". The app will extract all images found in the PDF and display them in a gallery.

4.  **Extract Text**:
    -   **Select Images**: Click on the images you want to process (or select all).
    -   **Enter Credentials**:
        -   **API Key**: Paste your Google GenAI API key.
        -   **Prompt**: Enter a prompt for the model (e.g., "Extract all text from this image verbatim").
    -   **Start Extraction**: Click the "Extract Text" button. A progress bar will show the status of each image.

5.  **Download Results**:
    -   Once extraction is complete, a "Download Merged Text" button will appear.
    -   Click it to download a single `.txt` file containing the extracted text from all processed images.
    -   Individual text files are also saved in `static/extracted_text/` for your reference.

## Project Structure

-   `app.py`: The main Flask application file containing all backend logic.
-   `templates/index.html`: The HTML frontend.
-   `static/`:
    -   `uploads/`: Temporary storage for uploaded PDFs.
    -   `extracted_image/`: Stores images extracted from the PDF.
    -   `extracted_text/`: Stores the crude text files extracted by the LLM.
-   `requirements.txt`: List of Python dependencies.

## Security Notes

-   **API Key**: Your Google API key is stored only in your browser's session (cookies). It is **never** saved to the server's disk or logged in any files.
-   **Data cleanup**: The `extracted_image` folder is cleared automatically at the start of each new PDF upload to ensure privacy between sessions.
