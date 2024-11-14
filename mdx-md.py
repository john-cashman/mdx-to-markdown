import streamlit as st
import re
from pathlib import Path
import tempfile
import zipfile

# Helper function to convert MDX to GitBook-compatible Markdown
def convert_mdx_to_gitbook(markdown_content):
    """
    Convert MDX content to GitBook-compatible Markdown.
    This involves removing unsupported JSX elements and making formatting adjustments.
    """
    # Remove HTML-like JSX tags and JSX expressions
    cleaned_content = re.sub(r'<[^<>]+>', '', markdown_content)  # Removes HTML/JSX tags
    cleaned_content = re.sub(r'{[^{}]+}', '', cleaned_content)   # Removes JSX expressions

    # Additional replacements for GitBook compatibility
    cleaned_content = re.sub(r'^(import|export).*\n', '', cleaned_content, flags=re.MULTILINE)

    return cleaned_content

# Streamlit interface
st.title("MDX to GitBook Markdown Converter")

# User input for output file name
output_file_name = st.text_input("Enter a name for the output ZIP file (without extension):", "converted_markdown")

# Upload .mdx files
uploaded_files = st.file_uploader("Upload your MDX files", type="mdx", accept_multiple_files=True)

if uploaded_files:
    # Validate file name input
    if not output_file_name.strip():
        st.error("Please provide a valid output file name.")
    else:
        # Create a temporary directory to store the converted files
        with tempfile.TemporaryDirectory() as tmpdirname:
            converted_files = []
            
            for uploaded_file in uploaded_files:
                # Read the content of the uploaded .mdx file
                try:
                    mdx_content = uploaded_file.read().decode("utf-8")
                except UnicodeDecodeError:
                    st.error(f"Failed to decode {uploaded_file.name}. Please check the file encoding.")
                    continue
                
                # Convert the MDX content to GitBook-compatible Markdown
                gitbook_markdown = convert_mdx_to_gitbook(mdx_content)
                
                # Create the output filename by replacing the .mdx extension with .md
                output_filename = uploaded_file.name.replace(".mdx", ".md")
                converted_file_path = Path(tmpdirname) / output_filename
                
                # Write the converted content to the new .md file
                with open(converted_file_path, "w", encoding="utf-8") as f:
                    f.write(gitbook_markdown)
                
                converted_files.append(converted_file_path)
            
            # Zip all converted files with the user-specified name
            zip_output_name = f"{output_file_name.strip()}.zip"
            output_zip_path = Path(tmpdirname) / zip_output_name
            with zipfile.ZipFile(output_zip_path, "w") as zipf:
                for file_path in converted_files:
                    zipf.write(file_path, file_path.name)
            
            # Provide download button for the ZIP file
            with open(output_zip_path, "rb") as f:
                st.download_button(
                    label="Download Converted Markdown Files",
                    data=f.read(),
                    file_name=zip_output_name,
                    mime="application/zip"
                )

            st.success(f"Converted {len(converted_files)} files to GitBook-compatible Markdown!")
