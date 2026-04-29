from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import numpy as np
import os

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Identify p.adj columns and calculate -log10
    padj_cols = [c for c in df.columns if c.endswith("_p.adj")]
    
    new_cols = []
    for col in padj_cols:
        new_col_name = col.replace("_p.adj", "_neg_log10_padj")
        # Handle zero or negative p-values to avoid log issues
        df[new_col_name] = -np.log10(df[col].replace(0, 1e-300))
        new_cols.append(new_col_name)

    # 2. Define suffixes and patterns to filter
    # Protein info: columns without '_vs_'
    # Fold change: columns ending in '_diff'
    # New p-values: already in new_cols
    
    cols_to_keep = []
    for col in df.columns:
        # 1. Always keep the new p-value columns
        if col in new_cols:
            cols_to_keep.append(col)
            continue
            
        # 2. Keep fold change columns
        if col.endswith("_diff"):
            cols_to_keep.append(col)
            continue
            
        # 3. Handle remaining columns
        # Exclude comparison columns (_vs_) and sample columns (starting with C_ or S_)
        # Also exclude the 'significant' column
        is_sample_or_comp = col.startswith(("C_", "S_")) or "_vs_" in col or col == "significant"
        
        if not is_sample_or_comp:
            cols_to_keep.append(col)
            
    return df[cols_to_keep]

@app.post("/convert")
async def convert_file(file: UploadFile = File(...)):
    filename = file.filename
    content = await file.read()
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel.")
            
        processed_df = process_dataframe(df)
        
        # Convert back to CSV
        output = io.StringIO()
        processed_df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=converted_{filename.split('.')[0]}.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
