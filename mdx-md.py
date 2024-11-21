import streamlit as st
import os
import zipfile
import tempfile
from pathlib import Path
from zipfile import is_zipfile
import shutil
import json

# App title and custom header
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5em;
        text-align: center;
        font-weight: bold;
        margin-bottom: 0.5em;
        color: #6c63ff;
    }
    .subheader {
        font-size: 1.2em;
        color: #555;
        margin-bottom: 1em;
        text-align: center;
    }
    .divider {
        margin: 2em 0;
        border: 0.5px solid #ddd;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">GitHub Repo MDX to Markdown Converter</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Upload your GitHub repo as a ZIP file, and we will handle the rest!</div>', unsafe_allow_html=True)

# File uploader
uploaded_repo = st.file_uploader("Upload your GitHub repository as a ZIP file", type="zip")
output_file_name = st.text_input("Enter a name for the output ZIP file (without extension):", "converted_repo")

# Divider
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

def find_files(repo_path):
    """Find all files in the repository."""
    all_files = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            all_files.append(Path(root) / file)
    return all_files

def read_file_with_fallback(file_path):
    """Read a file and handle different encodings."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()

def convert_mdx_to_markdown_with_images(content, images_folder, relative_path):
    """
    Convert MDX content to Markdown, adjusting image references to relative paths.
    """
    # Placeholder for MDX-to-Markdown conversion
    markdown_content = content

    # Adjust image references
    for image_file in images_folder.glob("*"):
        if image_file.name in content:
            relative_image_path = os.path.relpath(image_file, relative_path)
            markdown_content = markdown_content.replace(image_file.name, relative_image_path)

    return markdown_content

def create_output_structure(repo_path, output_dir):
    """Replicate the directory structure in the output directory."""
    for root, dirs, files in os.walk(repo_path):
        for dir_name in dirs:
            relative_path = Path(root).relative_to(repo_path)
            (output_dir / relative_path / dir_name).mkdir(parents=True, exist_ok=True)

def process_files(all_files, repo_path, output_dir):
    """Process files by converting MDX, copying images, and handling mint.json."""
    mdx_to_md_map = {}
    images_folder = output_dir / "images"
    images_folder.mkdir(parents=True, exist_ok=True)

    # Iterate through all files
    for file_path in all_files:
        relative_path = file_path.relative_to(repo_path)
        target_path = output_dir / relative_path

        # Process MDX files
        if file_path.suffix == ".mdx":
            try:
                mdx_content = read_file_with_fallback(file_path)
            except Exception as e:
                st.error(f"Error reading
