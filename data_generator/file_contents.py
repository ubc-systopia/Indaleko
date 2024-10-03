import os
import random
from faker import Faker

# Faker instance for generating text content
fake = Faker()

# Define some basic MIME types and file extensions for which we'll generate content
mime_types = {
    'txt': 'text/plain',
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
}

# Dummy content generator for text files
def generate_text_content(file_path):
    with open(file_path, 'w') as f:
        text_content = '\n'.join([fake.paragraph(nb_sentences=5) for _ in range(10)])
        f.write(text_content)

# Dummy content generator for PDF files (using simple text-based PDFs for now)
def generate_pdf_content(file_path):
    # This is a placeholder for real PDF content generation (can integrate a library like reportlab)
    with open(file_path, 'w') as f:
        f.write("%PDF-1.4\n")
        f.write(f"1 0 obj << /Type /Catalog >> endobj\n")
        f.write(f"Dummy PDF Content for {file_path}\n")

# Dummy content generator for JPEG image files
def generate_image_content(file_path):
    # Create a simple placeholder image (can be expanded with actual image generation)
    with open(file_path, 'wb') as f:
        f.write(b"\xFF\xD8\xFF\xE0")  # JPEG header bytes (placeholder)
        f.write(b"Dummy JPEG content")  # Dummy image data

# Function to generate file content based on MIME type
def generate_file_content(file_path, file_extension):
    if file_extension == 'txt':
        generate_text_content(file_path)
    elif file_extension == 'pdf':
        generate_pdf_content(file_path)
    elif file_extension == 'jpg':
        generate_image_content(file_path)

# Walk through the directory structure and generate content
def populate_file_contents(base_dir, mime_types):
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_extension = file.split('.')[-1]
            if file_extension in mime_types:
                file_path = os.path.join(root, file)
                generate_file_content(file_path, file_extension)

# Main function to populate file contents
if __name__ == "__main__":
    base_dir = 'synthetic_dataset'
    populate_file_contents(base_dir, mime_types)
    print(f"File contents generated for files in {base_dir}.")
