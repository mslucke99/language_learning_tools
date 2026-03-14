"""
Legal Compliance for Immersive Reading Mode.

Handles terms of use acceptance tracking and import attestation logging.
"""

from typing import Dict, Optional
from datetime import datetime
from src.core.database import FlashcardDatabase


class LegalCompliance:
    """
    Manages legal compliance for reading mode.
    
    Responsibilities:
    - Track terms of use acceptance
    - Log import attestation
    - Verify terms acceptance before imports
    - Maintain audit trail for legal compliance
    """
    
    # Current terms version
    TERMS_VERSION = "1.0"
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize the LegalCompliance manager.
        
        Args:
            db: FlashcardDatabase instance for data persistence
        """
        self.db = db
    
    def record_terms_acceptance(
        self,
        user_id: int,
        terms_version: str = TERMS_VERSION,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Record user's terms of use acceptance.
        
        Args:
            user_id: User ID
            terms_version: Version of terms accepted
            ip_address: IP address for audit trail (optional)
            user_agent: User agent for audit trail (optional)
            
        Returns:
            ID of the acceptance record
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_terms_acceptance
            (user_id, terms_version, accepted_at, ip_address, user_agent)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
        """, (user_id, terms_version, ip_address, user_agent))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def has_accepted_terms(
        self,
        user_id: int,
        terms_version: str = TERMS_VERSION
    ) -> bool:
        """
        Check if user has accepted terms of the specified version.
        
        Args:
            user_id: User ID
            terms_version: Version to check
            
        Returns:
            True if user has accepted the specified version
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id
            FROM reading_terms_acceptance
            WHERE user_id = ? AND terms_version = ?
            ORDER BY accepted_at DESC
            LIMIT 1
        """, (user_id, terms_version))
        
        return cursor.fetchone() is not None
    
    def get_terms_acceptance_history(self, user_id: int) -> List[Dict]:
        """
        Get terms acceptance history for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of acceptance records
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, terms_version, accepted_at, ip_address, user_agent
            FROM reading_terms_acceptance
            WHERE user_id = ?
            ORDER BY accepted_at DESC
        """, (user_id,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'user_id': row[1],
                'terms_version': row[2],
                'accepted_at': row[3],
                'ip_address': row[4],
                'user_agent': row[5]
            })
        
        return history
    
    def log_import_attestation(
        self,
        session_id: int,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Log import attestation for a reading session.
        
        Creates an audit record confirming the user attested to having
        legal rights to the imported content.
        
        Args:
            session_id: Reading session ID
            user_id: User ID
            ip_address: IP address for audit trail (optional)
            user_agent: User agent for audit trail (optional)
            
        Returns:
            ID of the attestation record
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, import_ip_address, import_user_agent,
             private, shareable, created_at)
            VALUES (?, ?, ?, ?, 'user_paste', 'paste', 1, ?, ?, 1, 0, CURRENT_TIMESTAMP)
        """, (user_id, 'attestation_log', '', 'en', ip_address, user_agent))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def get_import_audit_trail(self, user_id: int) -> List[Dict]:
        """
        Get import audit trail for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of import records with audit information
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, title, content, language, source, import_method,
                   legal_attestation, import_ip_address, import_user_agent,
                   created_at
            FROM reading_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        audit_trail = []
        for row in cursor.fetchall():
            audit_trail.append({
                'id': row[0],
                'user_id': row[1],
                'title': row[2],
                'content': row[3],
                'language': row[4],
                'source': row[5],
                'import_method': row[6],
                'legal_attestation': bool(row[7]),
                'import_ip_address': row[8],
                'import_user_agent': row[9],
                'created_at': row[10]
            })
        
        return audit_trail
