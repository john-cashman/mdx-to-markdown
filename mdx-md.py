import streamlit as st
import os
import zipfile
import tempfile
from pathlib import Path
from zipfile import is_zipfile
import shutil
import re
from bs4 import BeautifulSoup

# Streamlit UI setup
st.markdown("<h1 style='text-align: center; color: #6c63ff;'>GitHub Repo MDX & HTML to Markdown Converter</h1>", unsafe_allow_html=True)

uploaded_repo = st.file_uploader("Upload your GitHub repository as a ZIP file", type="zip")
output_file_name = st.text_input("Enter a name for the output ZIP file (without extension):", "converted_repo")


# Helper Functions
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


def convert_mdx_to_markdown(content, images_folder, file_path):
    """Convert MDX content to Markdown and fix image references, including JSX-like tags."""
    content = re.sub(r'<[^<>]+>', '', content)  # Remove JSX/HTML-like tags
    content = re.sub(r'{[^{}]+}', '', content)  # Remove JSX expressions

    # Replace Markdown-style image paths
    content = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        lambda match: f'![{match.group(1)}](./images/{Path(match.group(2)).name})',
        content,
    )

    # Replace <img> tags inside JSX-like tags
    content = re.sub(
        r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>',
        lambda match: f"![Image](./images/{Path(match.group(1)).name})",
        content,
    )

    return content


def convert_html_to_markdown(html_content, images_folder, file_path):
    """Convert HTML content to Markdown."""
    soup = BeautifulSoup(html_content, 'html.parser')
    markdown_content = []

    # Convert headers (h1, h2, h3, etc.)
    for header_tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(header_tag.name[1])  # Extract header level
        markdown_content.append(f"{'#' * level} {header_tag.get_text()}")

    # Convert paragraphs
    for p_tag in soup.find_all('p'):
        markdown_content.append(p_tag.get_text())

    # Convert images
    for img_tag in soup.find_all('img'):
        img_src = img_tag.get('src')
        alt_text = img_tag.get('alt', '')
        if img_src:
            img_name = Path(img_src).name
            centralized_image_path = images_folder / img_name

            # Copy the image to the centralized folder if it exists
            source_image_path = file_path.parent / img_src
            if source_image_path.exists():
                shutil.copy(source_image_path, centralized_image_path)

            markdown_content.append(f"![{alt_text}](./images/{img_name})")

    # Convert links
    for a_tag in soup.find_all('a'):
        href = a_tag.get('href')
        text = a_tag.get_text()
        if href:
            markdown_content.append(f"[{text}]({href})")

    # Join all Markdown parts
    return '\n\n'.join(markdown_content)


def create_output_structure(repo_path, output_dir):
    """Replicate the directory structure in the output directory."""
    for root, dirs, files in os.walk(repo_path):
        relative_path = Path(root).relative_to(repo_path)
        target_dir = output_dir / relative_path
        target_dir.mkdir(parents=True, exist_ok=True)


def process_files(all_files, repo_path, output_dir):
    """Process files by converting MDX, HTML, copying images, and other content."""
    images_folder = output_dir / "images"
    images_folder.mkdir(parents=True, exist_ok=True)

    for file_path in all_files:
        relative_path = file_path.relative_to(repo_path)
        target_path = output_dir / relative_path

        # Process MDX files
        if file_path.suffix == ".mdx":
            st.write(f"Processing MDX file: {file_path}")
            mdx_content = read_file_with_fallback(file_path)
            markdown_content = convert_mdx_to_markdown(mdx_content, images_folder, file_path)
            target_path = target_path.with_suffix(".md")  # Convert .mdx to .md

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

        # Process HTML files
        elif file_path.suffix == ".html":
            st.write(f"Processing HTML file: {file_path}")
            html_content = read_file_with_fallback(file_path)
            markdown_content = convert_html_to_markdown(html_content, images_folder, file_path)
            target_path = target_path.with_suffix(".md")  # Convert .html to .md

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

        # Copy other files
        else:
            st.write(f"Copying file: {file_path}")
            shutil.copy(file_path, target_path)


def generate_summary(output_dir):
    """Generate a summary.md file that represents the folder and file structure."""
    summary_content = ["# Table of contents", ""]

    for root, dirs, files in os.walk(output_dir):
        relative_path = Path(root).relative_to(output_dir)

        # Add group (folder) to summary
        if relative_path != Path("."):
            summary_content.append(f"## {relative_path.name.capitalize()}")

        # Add files as pages
        for file in sorted(files):  # Sort files for consistent ordering
            if file.endswith(".md") and file != "summary.md":
                file_path = Path(root) / file
                file_relative_path = file_path.relative_to(output_dir)
                summary_content.append(f"* [{file_relative_path.stem}]({file_relative_path})")

    # Write the summary.md file
    summary_file_path = output_dir / "summary.md"
    with open(summary_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_content))


def create_output_zip(output_dir, zip_name):
    """Create a ZIP file for the converted repo."""
    zip_path = Path(tempfile.gettempdir()) / f"{zip_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_path = Path(root) / file
                zipf.write(full_path, full_path.relative_to(output_dir))
    return zip_path


# Main Application Logic
if uploaded_repo and output_file_name.strip():
    st.info("Processing your uploaded repository...")
    with tempfile.TemporaryDirectory() as tmpdirname:
        zip_path = Path(tmpdirname) / "uploaded_repo.zip"
        with open(zip_path, "wb") as f:
            f.write(uploaded_repo.read())

        if not is_zipfile(zip_path):
            st.error("The uploaded file is not a valid ZIP file.")
            st.stop()

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                extracted_dir = Path(tmpdirname) / "uploaded_repo"
                zip_ref.extractall(extracted_dir)

            repo_path = extracted_dir
            output_dir = Path(tmpdirname) / "converted_repo"
            output_dir.mkdir()

            # Create output structure and process files
            st.write("Creating output folder structure...")
            create_output_structure(repo_path, output_dir)

            st.write("Processing files...")
            all_files = find_files(repo_path)
            process_files(all_files, repo_path, output_dir)

            st.write("Generating summary.md...")
            generate_summary(output_dir)

            # Create a ZIP of the output directory
            st.write("Creating output ZIP...")
            zip_path = create_output_zip(output_dir, output_file_name.strip())

            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download Converted Repository",
                    data=f.read(),
                    file_name=f"{output_file_name.strip()}.zip",
                    mime="application/zip",
                )

            st.success("Repository processed successfully!")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
