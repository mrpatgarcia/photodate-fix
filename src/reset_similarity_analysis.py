#!/usr/bin/env python3
"""
Script to reset similarity analysis by clearing existing groups and embeddings,
then rerunning the analysis with the corrected logic.
"""

from database import DatabaseManager

def reset_similarity_analysis():
    """Clear all existing similarity groups and embeddings"""
    db = DatabaseManager()
    
    print("Resetting similarity analysis...")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Clear photo groups
    cursor.execute("DELETE FROM photo_groups")
    cursor.execute("DELETE FROM photo_group_members")
    
    # Clear embeddings to force recomputation
    cursor.execute("DELETE FROM photo_embeddings WHERE embedding_type = 'combined'")
    
    conn.commit()
    
    # Get counts to confirm
    cursor.execute("SELECT COUNT(*) FROM photo_groups")
    groups_count = cursor.fetchone()['COUNT(*)']
    
    cursor.execute("SELECT COUNT(*) FROM photo_group_members")
    members_count = cursor.fetchone()['COUNT(*)']
    
    cursor.execute("SELECT COUNT(*) FROM photo_embeddings WHERE embedding_type = 'combined'")
    embeddings_count = cursor.fetchone()['COUNT(*)']
    
    conn.close()
    
    print(f"Cleared:")
    print(f"  - Photo groups: {groups_count}")
    print(f"  - Photo group members: {members_count}")
    print(f"  - Combined embeddings: {embeddings_count}")
    print("\nSimilarity analysis has been reset. Run the processing script to recompute groups.")

if __name__ == '__main__':
    reset_similarity_analysis()