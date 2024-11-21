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
                st.error(f"Error reading file {file_path}: {str(e)}")
                continue

            markdown_content = convert_mdx_to_markdown_with_images(mdx_content, images_folder, target_path.parent)
            target_path = target_path.with_suffix(".md")
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            mdx_to_md_map[str(file_path.relative_to(repo_path))] = str(target_path.relative_to(output_dir))

        # Copy image files
        elif file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".svg"]:
            shutil.copy(file_path, images_folder)

        # Copy mint.json as is
        elif file_path.name == "mint.json":
            shutil.copy(file_path, target_path)

    return mdx_to_md_map

def convert_mint_to_markdown(mint_file_path, output_dir, mdx_to_md_map):
    """Convert mint.json structure to Markdown."""
    with open(mint_file_path, "r", encoding="utf-8") as f:
        mint_data = json.load(f)

    markdown_content = "# Table of Contents\n\n"
    for entry in mint_data.get("pages", []):
        page_title = entry.get("title", "Untitled")
        page_file = mdx_to_md_map.get(entry.get("file"), None)
        if page_file:
            markdown_content += f"- [{page_title}]({page_file})\n"

    with open(output_dir / "mint.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)

def generate_summary(all_files, repo_path, output_dir):
    """Generate a summary of all converted pages."""
    summary_content = "# Summary of Repository\n\n"
    for file_path in all_files:
        relative_path = file_path.relative_to(repo_path)
        if file_path.suffix == ".mdx":
            summary_content += f"- {relative_path.with_suffix('.md')}\n"
    return summary_content

def create_output_zip(output_dir, zip_name):
    """Create a ZIP file for the converted repo."""
    zip_path = Path(tempfile.gettempdir()) / f"{zip_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_path = Path(root) / file
                zipf.write(full_path, full_path.relative_to(output_dir))
    return zip_path

if uploaded_repo and output_file_name.strip():
    # Start processing
    st.info("Processing your uploaded repository...")
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

            # Prepare output directory
            output_dir = Path(tmpdirname) / "converted_repo"
            output_dir.mkdir()

            # Replicate directory structure
            create_output_structure(repo_path, output_dir)

            # Process all files
            all_files = find_files(repo_path)
            mdx_to_md_map = process_files(all_files, repo_path, output_dir)

            # Convert mint.json to Markdown if it exists
            mint_file_path = next((f for f in all_files if f.name == "mint.json"), None)
            if mint_file_path:
                convert_mint_to_markdown(mint_file_path, output_dir, mdx_to_md_map)

            # Generate summary file
            summary_content = generate_summary(all_files, repo_path, output_dir)
            with open(output_dir / "summary.md", "w", encoding="utf-8") as f:
                f.write(summary_content)

            # Create ZIP for download
            zip_path = create_output_zip(output_dir, output_file_name.strip())
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download Converted Repository",
                    data=f.read(),
                    file_name=f"{output_file_name.strip()}.zip",
                    mime="application/zip",
                )

            st.success(f"Repository processed and {len(all_files)} files handled!")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
