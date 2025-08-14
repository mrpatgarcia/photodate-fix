import cv2
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import os
import pickle
from typing import List, Dict, Tuple, Optional
from database import DatabaseManager
from PIL import Image
import hashlib

class SimilarityAnalyzer:
    def __init__(self, photos_dir: str = './photos'):
        self.photos_dir = photos_dir
        self.db = DatabaseManager()
        
        # Initialize ORB detector for feature extraction (CPU-only)
        self.orb = cv2.ORB_create(nfeatures=1000)
        
        # Color histogram parameters
        self.hist_bins = 32
        
    def extract_features(self, image_path: str) -> Optional[np.ndarray]:
        """Extract combined features from an image using ORB + color histogram"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Could not read image: {image_path}")
                return None
            
            # Resize to standard size for consistency
            image = cv2.resize(image, (256, 256))
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Extract ORB features (keypoints and descriptors)
            keypoints, descriptors = self.orb.detectAndCompute(gray, None)
            
            # Create feature vector from ORB descriptors
            if descriptors is not None:
                # Use bag of words approach - average all descriptors
                orb_features = np.mean(descriptors, axis=0)
            else:
                # No keypoints found, use zeros
                orb_features = np.zeros(32)  # ORB descriptor size
            
            # Extract color histogram features
            hist_features = self.extract_color_histogram(image)
            
            # Extract basic image statistics
            stats_features = self.extract_image_statistics(image)
            
            # Combine all features
            combined_features = np.concatenate([
                orb_features,
                hist_features,
                stats_features
            ])
            
            return combined_features
            
        except Exception as e:
            print(f"Error extracting features from {image_path}: {e}")
            return None
    
    def extract_color_histogram(self, image: np.ndarray) -> np.ndarray:
        """Extract color histogram features"""
        # Calculate histogram for each channel
        hist_b = cv2.calcHist([image], [0], None, [self.hist_bins], [0, 256])
        hist_g = cv2.calcHist([image], [1], None, [self.hist_bins], [0, 256])
        hist_r = cv2.calcHist([image], [2], None, [self.hist_bins], [0, 256])
        
        # Normalize and flatten
        hist_b = cv2.normalize(hist_b, hist_b).flatten()
        hist_g = cv2.normalize(hist_g, hist_g).flatten()
        hist_r = cv2.normalize(hist_r, hist_r).flatten()
        
        return np.concatenate([hist_b, hist_g, hist_r])
    
    def extract_image_statistics(self, image: np.ndarray) -> np.ndarray:
        """Extract basic image statistics"""
        # Convert to different color spaces
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        features = []
        
        # Statistics for each channel in BGR
        for channel in cv2.split(image):
            features.extend([
                np.mean(channel),
                np.std(channel),
                np.min(channel),
                np.max(channel)
            ])
        
        # Statistics for HSV (hue, saturation, value)
        for channel in cv2.split(hsv):
            features.extend([
                np.mean(channel),
                np.std(channel)
            ])
        
        # Edge density
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        features.append(edge_density)
        
        return np.array(features)
    
    def compute_embeddings_for_all_photos(self):
        """Compute and store embeddings for base photos only (not _a/_b variants)"""
        print("Computing embeddings for base photos only...")
        
        # Get only base photos (file_type = 'variant') that don't have embeddings yet
        # Base photos are the original scanned images, _a and _b are front/back variants
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.filepath 
            FROM photos p
            LEFT JOIN photo_embeddings pe ON p.id = pe.photo_id AND pe.embedding_type = 'combined'
            WHERE pe.photo_id IS NULL
            AND p.processed_date IS NULL
            AND p.ignored_date IS NULL
            AND p.file_type = 'variant'
        ''')
        
        photos_to_process = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(photos_to_process)} photos to process")
        
        for i, photo in enumerate(photos_to_process):
            photo_id, filepath = photo['id'], photo['filepath']
            
            if i % 10 == 0:
                print(f"Processing photo {i+1}/{len(photos_to_process)}: {os.path.basename(filepath)}")
            
            # Check if file exists before processing
            if not os.path.exists(filepath):
                print(f"Warning: Photo file not found, skipping: {filepath}")
                continue
            
            # Extract features
            features = self.extract_features(filepath)
            
            if features is not None:
                # Serialize features
                embedding_data = pickle.dumps(features)
                
                # Store in database
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO photo_embeddings (photo_id, embedding_type, embedding_data)
                    VALUES (?, ?, ?)
                ''', (photo_id, 'combined', embedding_data))
                conn.commit()
                conn.close()
        
        print("Embedding computation completed!")
    
    def find_similar_groups(self, eps: float = 0.3, min_samples: int = 2) -> List[List[str]]:
        """Find groups of similar photos using clustering"""
        print("Finding similar photo groups...")
        
        # Get all photos with embeddings
        embeddings_data = self.db.get_photo_embeddings('combined')
        
        if len(embeddings_data) < 2:
            print("Not enough photos with embeddings for clustering")
            return []
        
        # Prepare data
        filepaths = []
        embeddings = []
        
        for filepath, embedding_blob in embeddings_data:
            try:
                embedding = pickle.loads(embedding_blob)
                filepaths.append(filepath)
                embeddings.append(embedding)
            except Exception as e:
                print(f"Error loading embedding for {filepath}: {e}")
                continue
        
        if len(embeddings) < 2:
            print("Not enough valid embeddings for clustering")
            return []
        
        # Normalize features
        embeddings = np.array(embeddings)
        scaler = StandardScaler()
        embeddings_normalized = scaler.fit_transform(embeddings)
        
        # Compute cosine similarity matrix
        similarity_matrix = cosine_similarity(embeddings_normalized)
        
        # Convert similarity to distance (1 - similarity)
        # Clip to ensure non-negative values for DBSCAN
        distance_matrix = np.clip(1 - similarity_matrix, 0, 2)
        
        # Perform clustering
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='precomputed')
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Group photos by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label != -1:  # -1 means noise/outlier
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(filepaths[i])
        
        # Convert to list of groups
        groups = list(clusters.values())
        
        # Filter out groups with only one photo
        groups = [group for group in groups if len(group) > 1]
        
        print(f"Found {len(groups)} similar photo groups")
        return groups
    
    def create_photo_groups_in_database(self, groups: List[List[str]]):
        """Store discovered photo groups in the database"""
        print("Storing photo groups in database...")
        
        for i, group in enumerate(groups):
            # Calculate average similarity score for the group
            avg_similarity = self.calculate_group_similarity(group)
            
            # Create group
            group_name = f"Similar Photos Group {i+1}"
            group_description = f"Group of {len(group)} similar photos (avg similarity: {avg_similarity:.3f})"
            
            group_id = self.db.create_photo_group(
                name=group_name,
                description=group_description,
                similarity_score=avg_similarity
            )
            
            # Add photos to group
            for filepath in group:
                success = self.db.add_photo_to_group(filepath, group_id, avg_similarity)
                if not success:
                    print(f"Failed to add {filepath} to group {group_id}")
        
        print(f"Created {len(groups)} photo groups in database")
    
    def calculate_group_similarity(self, filepaths: List[str]) -> float:
        """Calculate average similarity score for a group of photos"""
        if len(filepaths) < 2:
            return 1.0
        
        embeddings = []
        for filepath in filepaths:
            embedding_data = self.db.get_photo_embeddings('combined')
            for fp, blob in embedding_data:
                if fp == filepath:
                    try:
                        embedding = pickle.loads(blob)
                        embeddings.append(embedding)
                        break
                    except:
                        continue
        
        if len(embeddings) < 2:
            return 0.0
        
        # Calculate pairwise similarities
        embeddings = np.array(embeddings)
        similarity_matrix = cosine_similarity(embeddings)
        
        # Average of upper triangle (excluding diagonal)
        n = len(embeddings)
        total_similarity = 0
        count = 0
        
        for i in range(n):
            for j in range(i+1, n):
                total_similarity += similarity_matrix[i][j]
                count += 1
        
        return total_similarity / count if count > 0 else 0.0
    
    def run_full_analysis(self):
        """Run the complete similarity analysis pipeline"""
        print("Starting full photo similarity analysis...")
        
        # Step 1: Compute embeddings for all photos
        self.compute_embeddings_for_all_photos()
        
        # Step 2: Find similar groups
        groups = self.find_similar_groups()
        
        # Step 3: Store groups in database
        if groups:
            self.create_photo_groups_in_database(groups)
        else:
            print("No similar photo groups found")
        
        print("Photo similarity analysis completed!")
        return len(groups)

if __name__ == "__main__":
    analyzer = SimilarityAnalyzer()
    analyzer.run_full_analysis()