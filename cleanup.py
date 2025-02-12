import os
import glob
import json
import subprocess
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

def upload_to_kaggle(dataset_name, files):
    """Upload files to Kaggle dataset after processing"""
    try:
        # Initialize and authenticate Kaggle API
        api = KaggleApi()
        api.authenticate()
        
        if not os.path.exists('data'):
            os.makedirs('data')
        
        try:
            # Download existing dataset if it exists
            api.dataset_download_files(f"federodriguezh/{dataset_name}", path='data/existing', unzip=True)
            existing_file = 'data/existing/processed_data.json'
        except:
            existing_file = None

        # Read and combine all files
        combined_data = []
        # First read existing data if available
        if existing_file and os.path.exists(existing_file):
            with open(existing_file, 'r') as f:
                for line in f:
                    combined_data.append(json.loads(line))

        # Then add new data
        for file in files:
            with open(file, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    # Skip records with id=1 (subscription confirmation messages)
                    if data.get('id') != 1:
                        combined_data.append(data)
        
        # Remove duplicates based on entire record
        unique_data = []
        seen = set()
        for record in combined_data:
            record_str = json.dumps(record, sort_keys=True)
            if record_str not in seen:
                seen.add(record_str)
                unique_data.append(record)
                
        # Write all data to new file
        processed_file = os.path.join('data', 'processed_data.json')
        with open(processed_file, 'w') as f:
            for record in unique_data:
                json.dump(record, f)
                f.write('\n')
        
        # Create dataset-metadata.json
        metadata = {
            "title": dataset_name,
            "id": f"federodriguezh/{dataset_name}",
            "licenses": [{"name": "CC0-1.0"}],
            "isPrivate": True
        }
        
        metadata_file = os.path.join('data', 'dataset-metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

        # Upload to Kaggle without metadata parameter
        api.dataset_create_version(
            folder='data',
            version_notes=f"Auto update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Clean up files
        if os.path.exists(processed_file):
            os.remove(processed_file)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        if os.path.exists('data/existing'):
            subprocess.run(['rm', '-rf', 'data/existing'])
        
        return True
    
    except Exception as e:
        print(f"Error processing/uploading to Kaggle: {str(e)}")
        return False

def cleanup_files():
    """Clean up json files when count exceeds 10"""
    json_files = glob.glob('data/*.json')
    if len(json_files) > 10:
        # Sort files by creation time
        json_files.sort(key=os.path.getctime)
        
        # Upload to Kaggle
        if upload_to_kaggle("ethp-ob", json_files):
            try:
                # Use git rm to remove the files
                files_to_remove = ' '.join(json_files)
                subprocess.run(['git', 'rm', '-f'] + json_files, check=True)
                print(f"Successfully removed files using git rm")
                
                # Configure git
                subprocess.run(['git', 'config', '--local', 'user.email', 'github-actions[bot]@users.noreply.github.com'])
                subprocess.run(['git', 'config', '--local', 'user.name', 'github-actions[bot]'])
                
                # Commit and push changes
                subprocess.run(['git', 'commit', '-m', 'Remove processed files [skip ci]'])
                subprocess.run(['git', 'push'])
                print("Successfully committed and pushed changes")
                
            except subprocess.CalledProcessError as e:
                print(f"Error in git operations: {str(e)}")

if __name__ == "__main__":
    cleanup_files()