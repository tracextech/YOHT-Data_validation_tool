# YOHT-Data_validation_tool

This is a Data Validation Tool built using Streamlit and MongoDB for performance testing. It allows you to upload, manage, and merge GeoJSON files efficiently, with the features of viewing the uploaded CSV files, processing them, and mapping them to specific BL_LR_IF values.

# Features

1. CSV Uploader: Upload CSV files with BL_LR_IF and Batch_ID and store them in MongoDB.
2. GeoJSON Mapper: Upload GeoJSON files for specific BL_LR_IF values and map them.
3. GeoJSON Merger: Merge multiple GeoJSON entries based on InBound_BL_LR_IF from CSV files.
4. GeoJSON Splitter: Split large GeoJSON files into smaller chunks.
5. Data Comparison: Compare two GeoJSON files to check if they are identical.




# Steps:

# Page 1 (CSV Uploader):

Upload a CSV file that contains BL_LR_IF and Batch_ID.
View the uploaded data and store it in MongoDB for further use.

# Page 2 (GeoJSON Mapper):
Select the BL_LR_IF from the uploaded data.
Upload the corresponding GeoJSON file and map it to the BL_LR_IF in MongoDB.

# Page 3 (Merge GeoJSON Files):
Upload a CSV file with InBound_BL_LR_IF.
The app will merge all corresponding GeoJSON files for the BL_LR_IF values.
You can download the merged GeoJSON file.

# Page 4 (Data Comparison):
Upload two GeoJSON files and compare them to see if they are identical.

# Page 5 (GeoJSON Splitter):
Upload a large GeoJSON file.
Split it into smaller chunks based on the number of splits you specify.


# Setup Instructions

# Clone the repository:
git clone https://github.com/tracextech/YOHT-Data_validation_tool.git

# Navigate to the project directory:
cd geojson-manager

# Install the required dependencies:

pip install -r requirements.txt

# run the streamlit app
streamlit run validate.py



# Requirements

Python 3.9 or later
MongoDB

