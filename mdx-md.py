import streamlit as st
import os
import zipfile
import tempfile
from pathlib import Path
from zipfile import is_zipfile
import shutil  # Import added for file operations

# Helper functions
def find_files(repo_path):
    """Find MDX and image files in the repo."""
    mdx_files = []
    image_files = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            full_path = Path(root) / file
            if file.endswith(".mdx"):
                mdx_files.append(full_path)
            elif file.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                image_files.append(full_path)
    return mdx_files, image_files

def convert_mdx_to_gitbook(markdown_content):
    """Convert MDX content to GitBook-compatible Markdown."""
    import re
    cleaned_content = re.sub(r'<[^<>]+>', '', markdown_content)  # Remove JSX tags
    cleaned_content = re.sub(r'{[^{}]+}', '', cleaned_content)   # Remove JSX expressions
    cleaned_content = re.sub(r'^(import|export).*\n', '', cleaned_content, flags=re.MULTILINE)  # Remove imports/exports
    return cleaned_content

def convert_mdx_to_markdown_with_images(mdx_content, image_files, current_file):
    """Convert MDX to Markdown, preserving image references."""
    markdown_content = convert_mdx_to_gitbook(mdx_content)
    for image_path in image_files:
        relative_path = os.path.relpath(image_path, start=current_file.parent)
        markdown_content = markdown_content.replace(str(image_path), relative_path)
    return markdown_content

def generate_summary(mdx_files, output_dir):
    """Generate a summary file listing all converted files."""
    summary_lines = ["# Summary of Converted Files\n"]
    for mdx_file in mdx_files:
        converted_name = mdx_file.name.replace(".mdx", ".md")
        relative_path = os.path.relpath(mdx_file, start=output_dir)
        summary_lines.append(f"- [{converted_name}]({relative_path})")
    return "\n".join(summary_lines)

def create_output_zip(output_dir, zip_name):
    """Create a ZIP archive of the output directory."""
    zip_path = output_dir / f"{zip_name}.zip"
    zip_file_path = shutil.make_archive(str(zip_path).replace(".zip", ""), 'zip', output_dir)
    return Path(zip_file_path)

def read_file_with_fallback(file_path):
    """
    Read a file with a fallback to alternative encodings.
    Tries UTF-8 first, then falls back to common encodings.
    """
    encodings_to_try = ['utf-8', 'latin-1', 'windows-1252']
    for encoding in encodings_to_try:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # If no encoding works, raise an error
    raise ValueError(f"Could not decode the file: {file_path} with tried encodings.")

# Streamlit App
st.title("GitHub Repo MDX to Markdown Converter")

uploaded_repo = st.file_uploader("Upload your GitHub repository as a ZIP file", type="zip")
output_file_name = st.text_input("Enter a name for the output ZIP file (without extension):", "converted_repo")

if uploaded_repo and output_file_name.strip():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Save uploaded file to a temporary directory
        zip_path = Path(tmpdirname) / "uploaded_repo.zip"
        with open(zip_path, "wb") as f:
            f.write(uploaded_repo.read())

        # Validate if the file is a ZIP file
        if not is_zipfile(zip_path):
            st.error("The uploaded file is not a valid ZIP file. Please upload a valid ZIP file.")
            st.stop()

        try:
            # Extract ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)

            repo_path = Path(tmpdirname)
            st.success("Repository uploaded and extracted successfully!")

            # Find MDX and image files
            mdx_files, image_files = find_files(repo_path)

            # Prepare output directory
            output_dir = Path(tmpdirname) / "converted_repo"
            output_dir.mkdir()

            # Convert MDX files and save
            for mdx_file in mdx_files:
                try:
                    mdx_content = read_file_with_fallback(mdx_file)
                except ValueError as e:
                    st.error(f"Error reading file {mdx_file}: {str(e)}")
                    continue

                markdown_content = convert_mdx_to_markdown_with_images(mdx_content, image_files, mdx_file)
                output_file_path = output_dir / mdx_file.name.replace(".mdx", ".md")
                with open(output_file_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

            # Generate summary file
            summary_content = generate_summary(mdx_files, output_dir)
            with open(output_dir / "summary.md", "w", encoding="utf-8") as f:
                f.write(summary_content)

            # Create ZIP for download
            zip_path = create_output_zip(output_dir, output_file_name.strip())
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download Converted Repository",
                    data=f.read(),
                    file_name=f"{output_file_name.strip()}.zip",
                    mime="application/zip"
                )

            st.success(f"Converted {len(mdx_files)} files and generated summary.md!")

        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file. Please upload a valid ZIP file.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
