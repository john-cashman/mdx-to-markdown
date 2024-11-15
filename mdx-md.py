import streamlit as st
import os
import zipfile
import tempfile
from pathlib import Path

# Helper functions (place the above functions here)
# - find_files
# - convert_mdx_to_gitbook
# - convert_mdx_to_markdown_with_images
# - generate_summary
# - create_output_zip

# Streamlit UI
st.title("GitHub Repo MDX to Markdown Converter")

uploaded_repo = st.file_uploader("Upload your GitHub repository as a ZIP file", type="zip")
output_file_name = st.text_input("Enter a name for the output ZIP file (without extension):", "converted_repo")

if uploaded_repo and output_file_name.strip():
    with tempfile.TemporaryDirectory() as tmpdirname:
        zip_path = Path(tmpdirname) / "uploaded_repo.zip"
        with open(zip_path, "wb") as f:
            f.write(uploaded_repo.read())

        # Extract the ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)

        repo_path = Path(tmpdirname)
        st.success("Repository uploaded and extracted successfully!")

        # Find files
        mdx_files, image_files = find_files(repo_path)

        # Convert files and save to output directory
        output_dir = Path(tmpdirname) / "converted_repo"
        output_dir.mkdir()

        for mdx_file in mdx_files:
            with open(mdx_file, "r", encoding="utf-8") as f:
                mdx_content = f.read()

            markdown_content = convert_mdx_to_markdown_with_images(mdx_content, image_files, mdx_file)
            output_file_path = output_dir / mdx_file.name.replace(".mdx", ".md")
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

        # Generate summary
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
