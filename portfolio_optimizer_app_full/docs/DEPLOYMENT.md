# Deployment Guide

## Local use

The easiest setup is local:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Keep `data.xlsx` in the app folder.

## Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload the app folder contents.
3. Make sure these files are included:
   - `app.py`
   - `requirements.txt`
   - `data.xlsx` or `sample_data.xlsx`
   - `src/`
   - `.streamlit/config.toml`
4. Go to Streamlit Community Cloud.
5. Create a new app from the repository.
6. Set the main file path to `app.py`.
7. Deploy.

Note: if the app is deployed publicly, avoid uploading confidential portfolio data. Use a sanitized `sample_data.xlsx` and replace the file locally for private work.

## Private hosting options

For private finance work, local use is usually best. If you need a web version, consider:

- Streamlit Community Cloud with sanitized data
- A private GitHub repository and Streamlit Cloud permissions
- Internal server or VM deployment
- Docker later, if needed
