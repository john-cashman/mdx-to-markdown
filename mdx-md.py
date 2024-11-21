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
    """Find MDX, image files, and mint.json in the extracted repository."""
    mdx_files = []
    image_files = []
    mint_file = None

    for root, _, files in os.walk(repo_path):
        for file in files:
            full_path = Path(root) / file
            if file.endswith(".mdx"):
                mdx_files.append(full_path)
            elif file.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                image_files.append(full_path)
            elif file == "mint.json":
                mint_file = full_path

    return mdx_files, image_files, mint_file

def read_file_with_fallback(file_path):
    """Read a file and handle different encodings."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()

def convert_mdx_to_markdown_with_images(content, image_files, mdx_file_path, images_folder):
    """
    Convert MDX content to Markdown, adjusting image references to use the `images` folder.
    """
    # Placeholder: This is where actual MDX to Markdown conversion happens
    markdown_content = content

    # Adjust image references
    for image in image_files:
        if image.parent == mdx_file_path.parent:
            image_relative_path = f"./images/{image.name}"
            markdown_content = markdown_content.replace(str(image.name), image_relative_path)

    return markdown_content

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

def generate_summary(mdx_files, output_dir):
    """Generate a summary of all converted pages with .md extensions."""
    summary_content = "# Summary of Converted Pages\n\n"
    for mdx_file in mdx_files:
        md_file_name = mdx_file.name.replace(".mdx", ".md")
        summary_content += f"- {md_file_name}\n"
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

            # Find MDX, image, and mint.json files
            mdx_files, image_files, mint_file = find_files(repo_path)

            # Prepare output directory
            output_dir = Path(tmpdirname) / "converted_repo"
            output_dir.mkdir()

            # Create images folder
            images_folder = output_dir / "images"
            images_folder.mkdir()

            # Copy all images to the images folder
            for image_file in image_files:
                shutil.copy(image_file, images_folder)

            # Convert MDX files and save
            mdx_to_md_map = {}
            for mdx_file in mdx_files:
                try:
                    mdx_content = read_file_with_fallback(mdx_file)
                except ValueError as e:
                    st.error(f"Error reading file {mdx_file}: {str(e)}")
                    continue

                markdown_content = convert_mdx_to_markdown_with_images(mdx_content, image_files, mdx_file, images_folder)
                output_file_path = output_dir / mdx_file.name.replace(".mdx", ".md")
                with open(output_file_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                mdx_to_md_map[str(mdx_file.name)] = str(output_file_path.name)

            # Convert mint.json to Markdown
            if mint_file:
                convert_mint_to_markdown(mint_file, output_dir, mdx_to_md_map)

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
                    mime="application/zip",
                )

            st.success(f"Converted {len(mdx_files)} files and included {len(image_files)} images!")
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file. Please upload a valid ZIP file.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
