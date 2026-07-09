# Deployment Guide

## Local use

The easiest setup is local:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Keep `data.xlsx` in the app folder, or use the app sidebar to upload a workbook at runtime.

## Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload the app folder contents.
3. Make sure these files are included:
   - `app.py`
   - `requirements.txt`
   - `data.xlsx` and `sample_data.xlsx`
   - `src/`
   - `.streamlit/config.toml`
4. Go to Streamlit Community Cloud.
5. Create a new app from the repository.
6. Set the main file path to `app.py`.
7. Deploy.

Note: for public sharing, keep only sanitized sample data in the repository. Users should download the Excel template and upload their own completed workbook through the app sidebar. Their uploaded workbooks are processed during the session and are not intentionally saved to the project folder.

## Private hosting options

For private finance work, local use is usually best. If you need a web version, consider:

- Streamlit Community Cloud with sanitized data
- A private GitHub repository and Streamlit Cloud permissions
- Internal server or VM deployment
- Docker later, if needed


## Public user workflow

After deployment, users can use the app without GitHub access:

1. Open the Streamlit app link.
2. Click **Download Excel template** in the sidebar.
3. Fill in price/index data and asset classifications. Expected returns are optional.
4. Select **Upload my own Excel file**.
5. Upload the completed `.xlsx` workbook.
6. Run optimization and download the output report.

This is the recommended workflow for sharing the app with classmates, colleagues, or external users.
