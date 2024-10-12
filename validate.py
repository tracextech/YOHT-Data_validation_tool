import dotenv
import os
import streamlit as st
import json
import pandas as pd
from pymongo import MongoClient
import hashlib
import io

dotenv.load_dotenv()

# MongoDB setup
mongo_uri = os.getenv('DB_URI')

client = MongoClient(mongo_uri)
db = client['geojson_db']  
collection = db['geojson_files']  

# Function to update the current page (in session state)
def set_page(page_num):
    st.session_state['current_page'] = page_num

# to delete all files from MongoDB
def delete_all_files():
    all_files = collection.find({})
    deleted_bls = []
    
    # to collect BL_LR_IF from the documents
    for file in all_files:
        bl_lr_if = file.get('BL_LR_IF', 'Unknown BL_LR_IF')
        deleted_bls.append(bl_lr_if)

    # to delete all documents
    collection.delete_many({})

    # to display success message with BL_LR_IFs
    if deleted_bls:
        st.success("The following BL_LR_IF entries were deleted from MongoDB:")
        for bl in deleted_bls:
            st.write(f"- {bl}")
    else:
        st.warning("No entries found to delete.")

def aligned_buttons(alignment="center"):
    if alignment == "left":
        col1, col2, col3 = st.columns([1, 2, 2])
    elif alignment == "right":
        col1, col2, col3 = st.columns([2, 2, 1])
    else:
        col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.button("Prev", on_click=set_page, args=(st.session_state['current_page'] - 1,))
    with col3:
        st.button("Next", on_click=set_page, args=(st.session_state['current_page'] + 1,))

def on_upload_csv(message_placeholder):
    if 'df_page1' in st.session_state and 'filename_page1' in st.session_state:
        df = st.session_state['df_page1']
        filename = st.session_state['filename_page1']
        process_and_upload_csv(df, filename, message_placeholder)
    else:
        message_placeholder.warning("Please upload a CSV file first.")

def process_and_upload_csv(df, filename, message_placeholder):
    required_columns = ['BL_LR_IF', 'Batch_ID']
    if not all(column in df.columns for column in required_columns):
        message_placeholder.error("CSV must contain BL_LR_IF and Batch_ID columns.")
        return

    grouped = df.groupby('BL_LR_IF')['Batch_ID'].apply(list).reset_index()

    for index, row in grouped.iterrows():
        bl_lr_if = row['BL_LR_IF']
        batch_ids = row['Batch_ID']

        # Check if the BL_LR_IF already exists
        existing_entry = collection.find_one({'BL_LR_IF': bl_lr_if})

        if existing_entry:
            # If BL_LR_IF exists, skip or merge new batch IDs with existing ones
            existing_batch_ids = existing_entry.get('batch_id', [])
            updated_batch_ids = list(set(existing_batch_ids + batch_ids))  # Merging batch IDs
            collection.update_one(
                {'BL_LR_IF': bl_lr_if},
                {'$set': {'batch_id': updated_batch_ids}}
            )
        else:
            # If BL_LR_IF does not exist, insert new document
            document = {
                'BL_LR_IF': bl_lr_if,
                'batch_id': batch_ids,
                'geojsoncontent': None  
            }
            collection.insert_one(document)

    message_placeholder.success(f"CSV file '{filename}' processed and uploaded successfully!")


# Page 1, CSV Uploader( Inward file is uploaded here)
def page_1():
    st.title("Page 1 - CSV Uploader")
    st.write("Upload a CSV file containing BL_LR_IF and Batch_ID.")

    uploaded_csv = st.file_uploader("Upload CSV file", type="csv", key='csv_upload_page1')

    message_placeholder = st.empty()  # Message placeholder moved to the bottom

    if uploaded_csv is not None:
        # Clear previous session state data if a new file is uploaded
        if 'df_page1' in st.session_state:
            del st.session_state['df_page1']
            del st.session_state['filename_page1']

        df = pd.read_csv(uploaded_csv)
        st.session_state['df_page1'] = df
        st.session_state['filename_page1'] = uploaded_csv.name
        st.dataframe(df.head())

        if st.button("Upload to MongoDB"):
            on_upload_csv(message_placeholder)
    else:
        if 'df_page1' in st.session_state:
            del st.session_state['df_page1']
            del st.session_state['filename_page1']

    if st.button("Delete All Files and BLs from MongoDB"):
        delete_all_files()

    aligned_buttons(alignment="center")  

    if st.button("Refresh"):
        st.rerun()

# Page 2, GeoJSON Mapper( BL is mapped to geojson file): one BL can have only one geojson
def page_2():
    st.title("Page 2 - GeoJSON Mapper")
    st.write("Select BL_LR_IF(s) and upload GeoJSON files.")

    message_placeholder = st.empty()  
    if 'upload_fields' not in st.session_state:
        st.session_state['upload_fields'] = [0]

    if 'selected_bls' not in st.session_state:
        st.session_state['selected_bls'] = []

    total_bl_count = collection.count_documents({})

    if total_bl_count == 0:
        st.info("No BL_LR_IF have been uploaded yet. Please upload data on Page 1.")
        st.button("Go to Page 1", on_click=set_page, args=(1,))
        return
    else:
        all_bl_docs = collection.find({'geojsoncontent': None}, {'BL_LR_IF': 1})
        all_bl_numbers = [doc['BL_LR_IF'] for doc in all_bl_docs]

        indices_to_remove = []
        for idx in st.session_state['upload_fields']:
            selected_bls_in_fields = [
                st.session_state.get(f'bl_select_{other_idx}')
                for other_idx in st.session_state['upload_fields']
                if other_idx != idx and st.session_state.get(f'bl_select_{other_idx}') not in [None, "Select BL number"]
            ]

            excluded_bls = st.session_state['selected_bls'] + selected_bls_in_fields
            available_bls = [bl for bl in all_bl_numbers if bl not in excluded_bls]

            if available_bls or st.session_state.get(f'bl_select_{idx}') not in [None, "Select BL number"]:
                options = ["Select BL number"] + available_bls
                current_selection = st.session_state.get(f'bl_select_{idx}', "Select BL number")
                if current_selection not in options:
                    current_selection = "Select BL number"

                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    selected_bl = st.selectbox(
                        f"Select BL_LR_IF (Upload {idx+1})",
                        options,
                        index=options.index(current_selection),
                        key=f'bl_select_{idx}'
                    )

                    uploaded_geojson = st.file_uploader(
                        f"Upload GeoJSON file (Upload {idx+1})",
                        type=["geojson","json"],
                        key=f'geojson_upload_{idx}'
                    )
                    
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.button(
                        "Delete",
                        key=f'delete_{idx}',
                        on_click=delete_upload_field,
                        args=(idx,)
                    )

                if st.button(
                    "Upload GeoJSON to MongoDB",
                    key=f'upload_button_{idx}',
                ):
                    upload_geojson_to_mongo(idx, message_placeholder)
            else:
                st.info("All BL_LR_IF have associated GeoJSON files or have been selected.")
                indices_to_remove.append(idx)

        for idx in indices_to_remove:
            if idx in st.session_state['upload_fields']:
                st.session_state['upload_fields'].remove(idx)

        st.button("Upload More Files", on_click=add_upload_field)

        aligned_buttons(alignment="right")  

def add_upload_field():
    if 'upload_fields' not in st.session_state or not st.session_state['upload_fields']:
        st.session_state['upload_fields'] = [0]
    else:
        next_index = max(st.session_state['upload_fields']) + 1 if st.session_state['upload_fields'] else 0
        st.session_state['upload_fields'].append(next_index)

def delete_upload_field(idx):
    if 'upload_fields' in st.session_state:
        selected_bl = st.session_state.get(f'bl_select_{idx}')
        st.session_state['upload_fields'].remove(idx)
        keys_to_remove = [
            f'bl_select_{idx}',
            f'geojson_upload_{idx}',
            f'upload_button_{idx}',
            f'delete_{idx}'
        ]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]

def upload_geojson_to_mongo(index, message_placeholder):
    selected_bl = st.session_state.get(f'bl_select_{index}')
    uploaded_geojson = st.session_state.get(f'geojson_upload_{index}')
    if selected_bl in [None, "Select BL number"]:
        message_placeholder.warning("Please select a BL_LR_IF.")
        return
    if uploaded_geojson is not None:
        try:
            geojson_data = json.load(uploaded_geojson)

            collection.update_one(
                {'BL_LR_IF': selected_bl},
                {'$set': {'geojsoncontent': geojson_data}}
            )

            st.session_state['selected_bls'].append(selected_bl)
            message_placeholder.success(f"GeoJSON uploaded for BL_LR_IF {selected_bl}.")
            delete_upload_field(index)

        except json.JSONDecodeError:
            message_placeholder.error("Invalid GeoJSON file.")
    else:
        message_placeholder.warning("Please upload a GeoJSON file.")

def page_3():
    st.title("Page 3 - Merge GeoJSON Files")
    st.write("Upload a CSV file to merge GeoJSON contents.")

    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    uploaded_csv = st.file_uploader("Upload CSV file", type="csv", key='csv_upload_page3')

    if uploaded_csv is not None:
        df = pd.read_csv(uploaded_csv)
        st.session_state['df_page3'] = df
        st.dataframe(df.head())

        if st.button("Merge GeoJSON Files", on_click=merge_geojson_files):
            pass
    else:
        if 'df_page3' in st.session_state:
            del st.session_state['df_page3']

    aligned_buttons(alignment="left")

    for message in st.session_state['messages']:
        message_type = message.get('type', 'info')
        text = message.get('text', '')
        if message_type == 'error':
            st.error(text)
        elif message_type == 'warning':
            st.warning(text)
        elif message_type == 'success':
            st.success(text)
        else:
            st.info(text)

    # Clear messages
    st.session_state['messages'] = []

    # Show merged BL numbers 
    if 'merged_bl_numbers' in st.session_state and st.session_state['merged_bl_numbers']:
        st.write("The following BL_LR_IF numbers were merged:")
        for bl in st.session_state['merged_bl_numbers']:
            st.write(f"- {bl}")

    if st.session_state.get('show_download_button', False):
        st.download_button(
            label="Download Merged GeoJSON",
            data=generate_formatted_geojson(st.session_state['merged_geojson']),
            file_name="merged.geojson",
            mime="application/json"
        )

# Function to generate the formatted GeoJSON string with each feature on a new line followed by a comma
def generate_formatted_geojson(geojson):
    formatted_output = '{"type": "FeatureCollection",\n'
    formatted_output += '"features": [\n'

    # Iterate through each feature and format properly
    for i, feature in enumerate(geojson['features']):
        formatted_output += json.dumps(feature)
        if i < len(geojson['features']) - 1:
            formatted_output += ",\n"  # Add comma after each feature except the last one
        else:
            formatted_output += "\n"

    # Close the GeoJSON structure
    formatted_output += "]}\n"

    return formatted_output

def merge_geojson_files():
    if 'df_page3' in st.session_state:
        df = st.session_state['df_page3']
        required_columns = ['FG_ID', 'InBound_BL_LR_IF']
        if not all(column in df.columns for column in required_columns):
            st.session_state['messages'].append({
                'type': 'error',
                'text': "CSV must contain FG_ID and InBound_BL_LR_IF columns."
            })
            return

        bl_numbers = df['InBound_BL_LR_IF'].drop_duplicates().tolist()
        merged_geojson = {"type": "FeatureCollection", "features": []}
        merged_bl_numbers = []
        processed_bl_numbers = set()

        found_data = False

        for bl_number in bl_numbers:
            if bl_number in processed_bl_numbers:
                continue

            doc = collection.find_one({'BL_LR_IF': bl_number})

            if doc and doc.get('geojsoncontent'):
                geojsoncontent = doc['geojsoncontent']
                if geojsoncontent and geojsoncontent.get('features'):
                    for feature in geojsoncontent['features']:
                        if not is_duplicate_feature(feature, merged_geojson['features']):
                            merged_geojson['features'].append(feature)
                    processed_bl_numbers.add(bl_number)
                    merged_bl_numbers.append(bl_number)
                    found_data = True  
                else:
                    st.session_state['messages'].append({
                        'type': 'warning',
                        'text': f"GeoJSON content for BL_LR_IF {bl_number} is empty or invalid."
                    })
            else:
                st.session_state['messages'].append({
                    'type': 'warning',
                    'text': f"No GeoJSON content found for BL_LR_IF {bl_number}."
                })

        if not found_data:
            st.session_state['messages'].append({
                'type': 'error',
                'text': "No valid GeoJSON content was found in the database."
            })
            return

        if merged_geojson['features']:
            st.session_state['messages'].append({
                'type': 'success',
                'text': "Merged GeoJSON created successfully."
            })

            st.session_state['merged_geojson'] = merged_geojson
            st.session_state['merged_bl_numbers'] = merged_bl_numbers
            st.session_state['show_download_button'] = True
        else:
            st.session_state['messages'].append({
                'type': 'error',
                'text': "No valid GeoJSON content was merged."
            })

def is_duplicate_feature(new_feature, merged_features):
    """Check if the new feature has duplicate coordinates in the merged features without sorting."""
    new_coords = new_feature['geometry']['coordinates']  # Get the coordinates of the new feature

    for existing_feature in merged_features:
        existing_coords = existing_feature['geometry']['coordinates']  # Get the coordinates of each existing feature

        # Direct comparison of the entire coordinate list
        if existing_coords == new_coords:
            return True  # Duplicate found
    return False  # No duplicates

# function to compare the geojson files
def page_4():
    st.title("Page 4 - GeoJSON File Comparison")
    st.write("Upload two GeoJSON files to compare individual features.")

    message_placeholder = st.empty()

    if 'comparison_done' not in st.session_state:
        st.session_state['comparison_done'] = False  # Track whether the comparison is done
        st.session_state['matched_hashes'] = []
        st.session_state['unmatched_file1'] = []
        st.session_state['unmatched_file2'] = []
    
    uploaded_file1 = st.file_uploader("Upload the first GeoJSON file", type=["geojson", "json"], key='file1')
    uploaded_file2 = st.file_uploader("Upload the second GeoJSON file", type=["geojson", "json"], key='file2')

    if uploaded_file1 is not None and uploaded_file2 is not None:
        compare_clicked = st.button("Compare Files")

        if compare_clicked:
            try:
                file1_data = json.load(uploaded_file1)
                file2_data = json.load(uploaded_file2)

                # Extract features from both files
                features_file1 = file1_data['features']
                features_file2 = file2_data['features']

                # Report basic details
                st.write(f"Total features in File 1: {len(features_file1)}")
                st.write(f"Total features in File 2: {len(features_file2)}")

                # Hash features in both files
                hash_map_file1 = {get_geo_hash(f['geometry']['coordinates'], f['geometry']['type']): f for f in features_file1}
                hash_map_file2 = {get_geo_hash(f['geometry']['coordinates'], f['geometry']['type']): f for f in features_file2}

                matched_features = 0
                unmatched_features_file1 = 0
                unmatched_features_file2 = 0

                unmatched_file1 = []
                unmatched_file2 = list(hash_map_file2.keys())
                matched_hashes = []

                for hash1, feature1 in hash_map_file1.items():
                    if hash1 in hash_map_file2:
                        matched_features += 1
                        unmatched_file2.remove(hash1)  # Remove from unmatched list
                        matched_hashes.append(hash1)
                    else:
                        unmatched_features_file1 += 1
                        unmatched_file1.append(hash1)

                unmatched_features_file2 = len(unmatched_file2)

                # Store comparison result in session state
                st.session_state['comparison_done'] = True
                st.session_state['matched_hashes'] = matched_hashes
                st.session_state['unmatched_file1'] = unmatched_file1
                st.session_state['unmatched_file2'] = unmatched_file2

                # Summary Report
                if matched_features == len(features_file1) and matched_features == len(features_file2):
                    message_placeholder.success(f"Comparison Results: The files are **identical**. All {matched_features} features matched.")
                else:
                    message_placeholder.warning(f"Comparison Results: The files are **not identical**. {unmatched_features_file1} features in File 1 and {unmatched_features_file2} features in File 2 do not match.")

                st.write(f"Matched Features: {matched_features}")
                st.write(f"Unmatched Features in File 1: {unmatched_features_file1}")
                st.write(f"Unmatched Features in File 2: {unmatched_features_file2}")

            except json.JSONDecodeError:
                message_placeholder.error("One or both files are not valid GeoJSON format.")

    # Generate the detailed report if comparison is done
    if st.session_state['comparison_done']:
        report = generate_detailed_report(
            st.session_state['matched_hashes'], 
            st.session_state['unmatched_file1'], 
            st.session_state['unmatched_file2']
        )

        # Download button for the detailed report
        st.download_button(
            label="Download Detailed Report",
            data=report,
            file_name="geojson_comparison_report.txt",
            mime="text/plain",
            key="download_report"
        )

# Function to flatten coordinates for Polygon and MultiPolygon
def flatten_coordinates(coordinates, geom_type):
    """Recursively flatten the coordinates, handling Polygon and MultiPolygon geometries."""
    flat_coords = []

    if geom_type == "Polygon":
        # For Polygon, coordinates is a list of linear rings (outer boundary, holes)
        for ring in coordinates:
            flat_coords.extend(ring)
    elif geom_type == "MultiPolygon":
        # For MultiPolygon, it's a list of polygons, each containing linear rings
        for polygon in coordinates:
            for ring in polygon:
                flat_coords.extend(ring)

    return flat_coords

# Function to hash the flattened coordinates
def get_geo_hash(coordinates, geom_type):
    """Handle both Polygon and MultiPolygon geometries and return a SHA-256 hash."""
    
    # Flatten the coordinates based on geometry type
    flat_coords = flatten_coordinates(coordinates, geom_type)
    
    # Sort coordinates by latitude and longitude
    sorted_coordinates = sorted(flat_coords, key=lambda x: (x[0], x[1]))
    
    # Flatten to a string for hashing
    flattened_coordinates = ','.join([f"{lat:.6f},{lng:.6f}" for lat, lng in sorted_coordinates])
    
    # Create the hash
    hash_object = hashlib.sha256(flattened_coordinates.encode())
    return hash_object.hexdigest()

# Generate the detailed comparison report
def generate_detailed_report(matched_hashes, unmatched_file1, unmatched_file2):
    """Generate a detailed comparison report."""
    report = io.StringIO()
    report.write("Detailed GeoJSON Comparison Report\n\n")
    report.write(f"Matched Features: {len(matched_hashes)}\n")
    report.write("Matched Hashes:\n")
    for hash_value in matched_hashes:
        report.write(f"- {hash_value}\n")

    report.write(f"\nUnmatched Features in File 1: {len(unmatched_file1)}\n")
    for hash_value in unmatched_file1:
        report.write(f"- {hash_value}\n")

    report.write(f"\nUnmatched Features in File 2: {len(unmatched_file2)}\n")
    for hash_value in unmatched_file2:
        report.write(f"- {hash_value}\n")

    return report.getvalue()


# Page 5: GeoJSON Splitter, to split the geojson file into multiple files based on number of splits
import json
import math
import zipfile
from io import BytesIO
import streamlit as st

def page_5():
    st.title("Page 5 - GeoJSON Splitter")

    uploaded_geojson = st.file_uploader("Upload a GeoJSON file", type=["geojson","json"], key='geojson_upload')

    if uploaded_geojson is not None:
        # Load the uploaded GeoJSON file
        try:
            geojson_data = json.load(uploaded_geojson)
        except json.JSONDecodeError:
            st.error("Invalid GeoJSON file. Please upload a valid file.")
            return
        
        features = geojson_data.get("features", [])
        total_features = len(features)

        if not features:
            st.error("No features found in the uploaded GeoJSON file.")
            return

        # Display total features in the original file
        st.write(f"Total features in the original file: {total_features}")

        # Input for number of chunks
        num_chunks = st.number_input("Enter the number of chunks to split the file into", min_value=1, step=1, key='num_chunks')

        if st.button("Split File"):
            # Calculate how many features per file
            features_per_file = total_features // num_chunks
            remainder = total_features % num_chunks

            # Improved message to handle the case when remainder is zero
            if remainder > 0:
                st.write(f"Each file will have {features_per_file} features, with the first {remainder} files having one additional feature.")
            else:
                st.write(f"Each file will have {features_per_file} features.")

            # Split the features into the number of chunks
            split_data = []
            for i in range(num_chunks):
                start_idx = i * features_per_file + min(i, remainder)
                end_idx = start_idx + features_per_file + (1 if i < remainder else 0)
                
                chunk_features = features[start_idx:end_idx]
                split_data.append({
                    "type": geojson_data["type"],
                    "name": geojson_data.get("name", f"Split Part {i + 1}"),
                    "crs": geojson_data.get("crs", {}),
                    "features": chunk_features
                })

                # Print how many features are in each chunk
                st.write(f"File {i+1} will contain {len(chunk_features)} features.")

            # Verify and display total features in split files
            total_split_features = sum(len(chunk["features"]) for chunk in split_data)
            st.write(f"Total features in split files: {total_split_features}")

            if total_split_features == total_features:
                st.success("No data loss occurred.")
            else:
                st.error("Data loss detected!")

            # Formatting and saving each split file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, chunk in enumerate(split_data):
                    chunk_filename = f"geojson_chunk_{idx + 1}.geojson"
                    
                    # Start the GeoJSON structure
                    formatted_output = '{"type": "FeatureCollection",\n'
                    formatted_output += f'"name": "{chunk["name"]}",\n'
                    formatted_output += '"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },\n'
                    formatted_output += '"features": [\n'

                    # Add each feature as a properly formatted JSON string
                    for i, feature in enumerate(chunk["features"]):
                        formatted_output += json.dumps(feature)  #<--- Converts dict to JSON string
                        if i < len(chunk["features"]) - 1:
                            formatted_output += ",\n"  # <---Adds a comma except for the last feature
                        else:
                            formatted_output += "\n"

                    # Close the features array and object
                    formatted_output += "]}"

                    # Save this formatted chunk in the zip
                    zip_file.writestr(chunk_filename, formatted_output)

            zip_buffer.seek(0)

            # Provide a download button for the zip file
            st.download_button(
                label="Download Split GeoJSON Files",
                data=zip_buffer,
                file_name="split_geojson_files.zip",
                mime="application/zip"
            )


# Navbar 
def navbar():
    st.sidebar.markdown("## Navigation")
    st.sidebar.button("Page 1", on_click=set_page, args=(1,))
    st.sidebar.button("Page 2", on_click=set_page, args=(2,))
    st.sidebar.button("Page 3", on_click=set_page, args=(3,))
    st.sidebar.button("Page 4", on_click=set_page, args=(4,))
    st.sidebar.button("Page 5", on_click=set_page, args=(5,))

# App entry
def main():
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1

    navbar()

    if st.session_state['current_page'] == 1:
        page_1()
    elif st.session_state['current_page'] == 2:
        page_2()
    elif st.session_state['current_page'] == 3:
        page_3()
    elif st.session_state['current_page'] == 4:
        page_4()
    elif st.session_state['current_page'] == 5:
        page_5()

if __name__ == "__main__":
    main()
