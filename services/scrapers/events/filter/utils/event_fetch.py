from google.cloud import storage

def download_events_db():
    bucket_name = "blrnow-bucket"
    source_blob_name = "events.db"
    destination_file_name = "events.db"
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)