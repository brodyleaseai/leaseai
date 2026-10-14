import os
from datetime import datetime

class FileUploadHandler:
    def __init__(self, supabase_client):
        self.sb = supabase_client
        self.bucket_name = "leases"
    
    def save_uploaded_file_temporarily(self, uploaded_file):
        temp_dir = os.path.join(os.getcwd(), 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        return temp_path
    
    def upload_lease_pdf(self, uploaded_file, client_id: str, property_address: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{client_id}/{timestamp}_{uploaded_file.name}"
        
        try:
            file_bytes = uploaded_file.getvalue()
            
            response = self.sb.storage.from_(self.bucket_name).upload(
                filename,
                file_bytes,
                {"content-type": "application/pdf"}
            )
            
            storage_path = filename
            storage_url = f"{self.sb.storage_url}/object/public/{self.bucket_name}/{filename}"
            
            return storage_path, storage_url
        
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")