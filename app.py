"""
app.py

Streamlit app for dual metabolite annotation (KEGG + HMDB).
Upload CSV/Excel with metabolite names in the first column.
"""

import streamlit as st
import pandas as pd
from io import BytesIO

from annotator import annotate_metabolites

st.set_page_config(page_title="Metaborole", layout="centered")

st.title("Metaborole — Metabolite Annotator")
st.markdown(
    "Upload a **CSV** or **Excel** file with metabolite names in the **first column**.\n\n"
    "Each name is looked up in **both KEGG and HMDB** databases simultaneously."
)

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Read file
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.shape[1] < 1:
            st.error("The file must contain at least one column.")
        else:
            first_column = df.columns[0]
            names = df[first_column].dropna().astype(str).tolist()

            st.write("Preview of uploaded data:")
            st.dataframe(df.head())

            # Annotate against both databases
            with st.spinner("Annotating against KEGG and HMDB..."):
                annotations = annotate_metabolites(names)

            result_df = pd.DataFrame(annotations)

            # Summary stats
            n_total = len(result_df)
            n_kegg_found = (result_df["KEGG ID"] != "Not Found").sum()
            n_hmdb_found = (result_df["HMDB IDs"] != "Not Found").sum()
            n_both_found = (
                (result_df["KEGG ID"] != "Not Found") &
                (result_df["HMDB IDs"] != "Not Found")
            ).sum()
            n_neither = (
                (result_df["KEGG ID"] == "Not Found") &
                (result_df["HMDB IDs"] == "Not Found")
            ).sum()

            st.success("Annotation complete!")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", n_total)
            col2.metric("KEGG Found", f"{n_kegg_found} ({n_kegg_found/n_total*100:.0f}%)")
            col3.metric("HMDB Found", f"{n_hmdb_found} ({n_hmdb_found/n_total*100:.0f}%)")
            col4.metric("Both Found", f"{n_both_found} ({n_both_found/n_total*100:.0f}%)")

            if n_neither > 0:
                st.warning(f"{n_neither} metabolite(s) not found in either database.")

            st.dataframe(result_df)

            # Download as Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                result_df.to_excel(writer, index=False, sheet_name="Annotations")
            output.seek(0)

            st.download_button(
                label="Download Results as Excel",
                data=output,
                file_name="metabolite_annotations.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
