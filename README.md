# YOHT-Data_validation_tool

This is a Data Validation Tool built using Streamlit and MongoDB for performance testing. It allows you to upload, manage, and merge GeoJSON files efficiently, with the features of viewing the uploaded CSV files, processing them, and mapping them to specific BL_LR_IF values.

Features

CSV Uploader: Upload CSV files with BL_LR_IF and Batch_ID and store them in MongoDB.
GeoJSON Mapper: Upload GeoJSON files for specific BL_LR_IF values and map them.
GeoJSON Merger: Merge multiple GeoJSON entries based on InBound_BL_LR_IF from CSV files.
GeoJSON Splitter: Split large GeoJSON files into smaller chunks.
Data Comparison: Compare two GeoJSON files to check if they are identical.
