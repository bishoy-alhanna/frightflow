import os
import hashlib
import mimetypes
from datetime import datetime
from typing import List, Optional
from werkzeug.exceptions import NotFound, BadRequest
from werkzeug.utils import secure_filename
from flask import send_file, Response

from models.booking import Document, DocumentType

class DocumentService:
    """Service for managing shipment documents"""
    
    def __init__(self, storage, db):
        self.storage = storage
        self.db = db
        self.allowed_extensions = {
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'txt'
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def upload_document(self, shipment_id: str, file, document_type: str,
                       description: str, uploaded_by: str) -> Document:
        """Upload a document for a shipment"""
        
        # Validate file
        if not file or file.filename == '':
            raise BadRequest("No file provided")
        
        # Check file extension
        if not self._allowed_file(file.filename):
            raise BadRequest(f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}")
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > self.max_file_size:
            raise BadRequest(f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB")
        
        # Validate document type
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            doc_type = DocumentType.OTHER
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1]
        filename = f"{shipment_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{original_filename}"
        
        # Calculate file checksum
        file_content = file.read()
        file.seek(0)
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Determine MIME type
        mime_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
        
        # Upload to storage
        storage_path = f"shipments/{shipment_id}/documents/{filename}"
        
        try:
            self.storage.upload_file(
                file_content,
                storage_path,
                content_type=mime_type
            )
        except Exception as e:
            raise BadRequest(f"Failed to upload file: {str(e)}")
        
        # Create document record
        document = Document(
            shipment_id=shipment_id,
            document_type=doc_type,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            storage_path=storage_path,
            checksum=checksum,
            description=description,
            uploaded_by=uploaded_by
        )
        
        # Save to database
        self._save_document(document)
        
        return document
    
    def get_documents(self, shipment_id: str, user_id: str) -> List[Document]:
        """Get all documents for a shipment"""
        
        # Check if user can access shipment
        if not self._can_access_shipment(shipment_id, user_id):
            raise NotFound("Shipment not found")
        
        # Get documents from database
        documents_data = self._query_documents(shipment_id)
        
        documents = []
        for doc_data in documents_data:
            document = self._dict_to_document(doc_data)
            documents.append(document)
        
        return documents
    
    def download_document(self, document_id: str, user_id: str) -> Response:
        """Download a document"""
        
        # Get document from database
        document = self._load_document(document_id)
        if not document:
            raise NotFound("Document not found")
        
        # Check if user can access the shipment
        if not self._can_access_shipment(document.shipment_id, user_id):
            raise NotFound("Document not found")
        
        # Download from storage
        try:
            file_content = self.storage.download_file(document.storage_path)
            
            # Verify checksum
            calculated_checksum = hashlib.sha256(file_content).hexdigest()
            if calculated_checksum != document.checksum:
                raise BadRequest("File integrity check failed")
            
            # Create response
            response = Response(
                file_content,
                mimetype=document.mime_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{document.original_filename}"',
                    'Content-Length': str(document.file_size)
                }
            )
            
            return response
            
        except Exception as e:
            raise BadRequest(f"Failed to download file: {str(e)}")
    
    def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document"""
        
        # Get document from database
        document = self._load_document(document_id)
        if not document:
            raise NotFound("Document not found")
        
        # Check if user can access the shipment
        if not self._can_access_shipment(document.shipment_id, user_id):
            raise NotFound("Document not found")
        
        # Delete from storage
        try:
            self.storage.delete_file(document.storage_path)
        except Exception as e:
            # Log error but continue with database deletion
            pass
        
        # Delete from database
        self._delete_document(document_id)
        
        return True
    
    def get_document_types(self) -> List[Dict[str, str]]:
        """Get available document types"""
        return [
            {'value': doc_type.value, 'label': doc_type.value.replace('_', ' ').title()}
            for doc_type in DocumentType
        ]
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        if not filename:
            return False
        
        extension = filename.rsplit('.', 1)[-1].lower()
        return extension in self.allowed_extensions
    
    def _can_access_shipment(self, shipment_id: str, user_id: str) -> bool:
        """Check if user can access the shipment"""
        # This would check shipment ownership or admin permissions
        # For now, return True for demo purposes
        return True
    
    # Database operations (mock implementations)
    def _save_document(self, document: Document):
        """Save document to database"""
        # Mock implementation
        pass
    
    def _load_document(self, document_id: str) -> Optional[Document]:
        """Load document from database"""
        # Mock implementation - return None for now
        return None
    
    def _query_documents(self, shipment_id: str) -> List[Dict]:
        """Query documents for a shipment"""
        # Mock implementation
        return []
    
    def _delete_document(self, document_id: str):
        """Delete document from database"""
        # Mock implementation
        pass
    
    def _dict_to_document(self, data: Dict) -> Document:
        """Convert dictionary to Document object"""
        document = Document()
        document.id = data.get('id', '')
        document.shipment_id = data.get('shipment_id', '')
        document.document_type = DocumentType(data.get('document_type', 'OTHER'))
        document.filename = data.get('filename', '')
        document.original_filename = data.get('original_filename', '')
        document.file_size = data.get('file_size', 0)
        document.mime_type = data.get('mime_type', '')
        document.description = data.get('description', '')
        document.uploaded_by = data.get('uploaded_by', '')
        return document

