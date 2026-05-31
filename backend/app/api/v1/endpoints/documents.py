from fastapi import APIRouter

router = APIRouter()

from fastapi import UploadFile, File
from app.services.document_service import document_service

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Save file and process
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    text = document_service.process_file(file_path)
    return {"filename": file.filename, "extracted_text_snippet": text[:500]}
