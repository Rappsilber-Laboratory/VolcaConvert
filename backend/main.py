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

    # 2. Define suffixes to remove
    suffixes_to_remove = ["_CI.L", "_CI.R", "_p.adj", "_p.val"]
    
    # 3. Filter columns
    cols_to_keep = []
    for col in df.columns:
        # Check if it should be removed
        should_remove = any(col.endswith(sfx) for sfx in suffixes_to_remove)
        
        # Exception: keep *_diff
        if col.endswith("_diff"):
            should_remove = False
            
        if not should_remove or col in new_cols:
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
