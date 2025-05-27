# app.py

import streamlit as st
import pandas as pd
from annotator import annotate_metabolites
from io import BytesIO

st.set_page_config(page_title="Metaborole", layout="centered")

st.title("🧬 Metaborole - Metabolite Annotator")
st.markdown("Upload a CSV file with a column named **`name`** containing metabolite names.")

# File uploader
uploaded_file = st.file_uploader("📤 Upload CSV file", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.write("📄 Preview of uploaded data:")
        st.dataframe(df.head())

        if "name" not in df.columns:
            st.error("❌ The CSV file must contain a column named 'name'.")
        else:
            # Run annotation
            names = df["name"].dropna().tolist()
            annotations = annotate_metabolites(names)

            # Create DataFrame
            result_df = pd.DataFrame(annotations)

            st.success("✅ Annotation complete!")
            st.write(result_df)

            # Prepare Excel for download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False)
            output.seek(0)

            # Download button
            st.download_button(
                label="📥 Download Results as Excel",
                data=output,
                file_name="annotations.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
