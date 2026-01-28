import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path

from annotator import annotate_metabolites

st.set_page_config(page_title="Metaborole", layout="centered")

st.title("Metaborole - Metabolite Annotator (KEGG)")
st.markdown("Upload a **CSV** or **Excel** file with metabolite names in the **first column**.")

# File uploader (accepts both CSV and Excel)
uploaded_file = st.file_uploader("📤 Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Determine file type and read accordingly
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Ensure at least one column exists
        if df.shape[1] < 1:
            st.error("❌ The file must contain at least one column.")
        else:
            # Use the first column regardless of its name
            first_column = df.columns[0]
            names = df[first_column].dropna().astype(str).tolist()

            st.write("📄 Preview of uploaded data:")
            st.dataframe(df.head())

            # Run annotation
            annotations = annotate_metabolites(names)
            result_df = pd.DataFrame(annotations)

            if result_df.empty:
                st.warning("⚠️ No matches found in the dictionary.")
            else:
                st.success("✅ Annotation complete!")
                st.write(result_df)

                # Prepare Excel for download
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    result_df.to_excel(writer, index=False, sheet_name="KEGG_Annotations")
                output.seek(0)

                # Output filename = input stem + "_kegg.xlsx"
                stem = Path(uploaded_file.name).stem
                out_name = f"{stem}_kegg.xlsx"

                # Download button
                st.download_button(
                    label="📥 Download Results as Excel",
                    data=output,
                    file_name=out_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    except Exception as e:
        st.error(f"❌ Something went wrong: {e}")
