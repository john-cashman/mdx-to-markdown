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
    .btn-upload {
        margin: 0.5em 0;
        background-color: #6c63ff;
        color: white;
        border: none;
        border-radius: 5px;
        font-size: 1em;
        padding: 0.6em 1.5em;
        cursor: pointer;
    }
    .btn-upload:hover {
        background-color: #5753b5;
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

if uploaded_repo and output_file_name.strip():
    # Create a progress bar
    progress_bar = st.progress(0)
    progress_bar.progress(10)

    # Start processing
    st.info("Processing your uploaded repository...")
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Save uploaded file to a temporary directory
        zip_path = Path(tmpdirname) / "uploaded_repo.zip"
        with open(zip_path, "wb") as f:
            f.write(uploaded_repo.read())
        
        progress_bar.progress(30)

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
            progress_bar.progress(50)

            # Find MDX, image, and mint.json files
            mdx_files, image_files, mint_file = find_files(repo_path)

            # Prepare output directory
            output_dir = Path(tmpdirname) / "converted_repo"
            output_dir.mkdir()

            # Convert MDX files and save
            mdx_to_md_map = {}
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

                mdx_to_md_map[str(mdx_file.name)] = str(output_file_path.name)

            # Convert mint.json to Markdown
            if mint_file:
                convert_mint_to_markdown(mint_file, output_dir, mdx_to_md_map)

            # Generate summary file
            summary_content = generate_summary(mdx_files, output_dir)
            with open(output_dir / "summary.md", "w", encoding="utf-8") as f:
                f.write(summary_content)

            progress_bar.progress(80)

            # Create ZIP for download
            zip_path = create_output_zip(output_dir, output_file_name.strip())
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download Converted Repository",
                    data=f.read(),
                    file_name=f"{output_file_name.strip()}.zip",
                    mime="application/zip",
                )
                st.balloons()  # Celebrate the successful conversion

            st.success(f"Converted {len(mdx_files)} files and mint.json!")
            progress_bar.progress(100)

        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file. Please upload a valid ZIP file.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
