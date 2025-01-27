import streamlit as st
import os
import zipfile
import tempfile
from pathlib import Path
from zipfile import is_zipfile
import shutil
import re

# Streamlit UI setup
st.markdown("<h1 style='text-align: center; color: #6c63ff;'>MDX to Markdown Converter</h1>", unsafe_allow_html=True)

uploaded_repo = st.file_uploader("Upload your GitHub repository as a ZIP file", type="zip")
output_file_name = st.text_input("Enter a name for the output ZIP file (without extension):", "converted_repo")

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
    """Convert MDX content to Markdown and fix image references."""
    def replace_image_paths(match):
        alt_text, img_path = match.groups()
        img_name = Path(img_path).name
        centralized_image_path = images_folder / img_name

        # Copy the image to the centralized folder if it exists
        source_image_path = file_path.parent / img_path
        if source_image_path.exists():
            shutil.copy(source_image_path, centralized_image_path)

        return f"![{alt_text}](./images/{img_name})"

    # Remove JSX/HTML-like tags and expressions
    content = re.sub(r'<[^<>]+>', '', content)
    content = re.sub(r'{[^{}]+}', '', content)

    # Update image references
    content = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',  # Match Markdown image syntax
        replace_image_paths,
        content,
    )

    return content

def create_output_structure(repo_path, output_dir):
    """Replicate the directory structure in the output directory."""
    for root, dirs, files in os.walk(repo_path):
        relative_path = Path(root).relative_to(repo_path)
        target_dir = output_dir / relative_path
        target_dir.mkdir(parents=True, exist_ok=True)

def process_files(all_files, repo_path, output_dir):
    """Process files by converting MDX, copying images, and other content."""
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

        # Copy other files
        elif file_path.suffix.lower() not in [".mdx"]:
            st.write(f"Copying file: {file_path}")
            shutil.copy(file_path, target_path)

def generate_summary(output_dir):
    """Generate a summary.md file grouped by folders."""
    summary_content = ["# Table of Contents\n"]

    for root, dirs, files in os.walk(output_dir):
        relative_path = Path(root).relative_to(output_dir)

        # Skip the root directory
        if relative_path == Path("."):
            continue

        # Add group (folder) to summary
        group_name = f"## {relative_path.name.capitalize()}\n"
        summary_content.append(group_name)

        # Add files as pages within the group
        for file in sorted(files):  # Sort files for consistent ordering
            if file.endswith(".md"):
                file_path = Path(root) / file
                file_relative_path = file_path.relative_to(output_dir)
                summary_content.append(f"* [{file_relative_path.stem}]({file_relative_path.as_posix()})")

        summary_content.append("")  # Add a blank line for readability

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

            # Verify that files are present in the output directory
            if not any(output_dir.iterdir()):
                st.error("The output folder is empty. Check if files were processed correctly.")
                st.stop()

            # Create a ZIP of the output directory
            st.write("Creating output ZIP...")
            zip_path = create_output_zip(output_dir, output_file_name.strip())

            # Verify the ZIP file is not empty
            if not zipfile.ZipFile(zip_path).namelist():
                st.error("The output ZIP file is empty. Something went wrong during zipping.")
                st.stop()

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
