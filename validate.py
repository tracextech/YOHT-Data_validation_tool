# Below code is for all the pages of streamlit 
import streamlit as st
import json
import pandas as pd
from pymongo import MongoClient

# MongoDB setup
mongo_uri = st.secrets["MONGO_URI"]

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

    collection.delete_many({})

    grouped = df.groupby('BL_LR_IF')['Batch_ID'].apply(list).reset_index()

    for index, row in grouped.iterrows():
        bl_lr_if = row['BL_LR_IF']
        batch_ids = row['Batch_ID']

        document = {
            'BL_LR_IF': bl_lr_if,
            'batch_id': batch_ids,
            'geojsoncontent': None  
        }

        collection.update_one(
            {'BL_LR_IF': bl_lr_if},
            {'$set': document},
            upsert=True
        )

    message_placeholder.success(f"CSV file '{filename}' uploaded successfully!")

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
                        type="geojson",
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

# Page 3, to consolidate the geojson files and to download the file in the same page 
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
            data=json.dumps(st.session_state['merged_geojson']),
            file_name="merged.geojson",
            mime="application/json"
        )


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
                    merged_geojson['features'].extend(geojsoncontent['features'])
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
                'text': "No valid GeoJSON content was found in the database. It might have been deleted or not uploaded yet."
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

    else:
        st.session_state['messages'].append({
            'type': 'warning',
            'text': "Please upload a CSV file first."
        })



# Page 4: Data Comparison, two geojson files are compared
def page_4():
    st.title("Page 4 - Data Comparison")

    st.write("Upload two GeoJSON files to compare.")

    message_placeholder = st.empty()

    uploaded_file1 = st.file_uploader("Upload the first GeoJSON file", type="geojson", key='file1')
    uploaded_file2 = st.file_uploader("Upload the second GeoJSON file", type="geojson", key='file2')

    if uploaded_file1 is not None and uploaded_file2 is not None:
        if st.button("Compare Files"):
            try:
                file1_data = json.load(uploaded_file1)
                file2_data = json.load(uploaded_file2)
                are_files_identical = file1_data == file2_data

                if are_files_identical:
                    message_placeholder.success("The two files are identical!")
                else:
                    message_placeholder.error("The two files are different!")
            except json.JSONDecodeError:
                message_placeholder.error("One or both files are not valid GeoJSON format.")

    aligned_buttons(alignment="right")

# Page 5: GeoJSON Splitter, to split the geojson file into multiple files based on number of splits
def page_5():
    st.title("Page 5 - GeoJSON Splitter")

    uploaded_geojson = st.file_uploader("Upload a GeoJSON file", type="geojson", key='geojson_upload')

    if uploaded_geojson is not None:
        num_chunks = st.number_input("Enter the number of chunks to split the file into", min_value=1, step=1, key='num_chunks')

        if st.button("Split File"):
            try:
                geojson_data = json.load(uploaded_geojson)
                features = geojson_data.get("features", [])
                if not features:
                    st.error("No features found in the uploaded GeoJSON file.")
                    return

                split_size = len(features) // num_chunks
                split_data = []

                for i in range(num_chunks):
                    start_idx = i * split_size
                    chunk_features = features[start_idx:] if i == num_chunks - 1 else features[start_idx:start_idx + split_size]
                    split_data.append({"type": geojson_data["type"], "features": chunk_features})

                for idx, chunk in enumerate(split_data):
                    chunk_filename = f"geojson_chunk_{idx + 1}.geojson"
                    button_key = f"download_button_{idx + 1}"

                    if button_key not in st.session_state:
                        st.session_state[button_key] = False

                    if st.session_state[button_key] is False:
                        if st.download_button(
                                label=f"Download Chunk {idx + 1}",
                                data=json.dumps(chunk),
                                file_name=chunk_filename,
                                mime="application/json",
                                key=button_key
                        ):
                            st.session_state[button_key] = True
                    else:
                        st.write(f"Chunk {idx + 1} has been downloaded.")
            except json.JSONDecodeError:
                st.error("Invalid GeoJSON file. Please upload a valid file.")

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
