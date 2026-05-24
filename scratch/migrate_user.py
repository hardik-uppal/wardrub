import sys
from google.cloud import storage
from google.cloud import firestore
from google.oauth2 import service_account

if len(sys.argv) != 3:
    print("Usage: python migrate_user.py <OLD_UID> <NEW_UID>")
    sys.exit(1)

old_uid = sys.argv[1]
new_uid = sys.argv[2]

creds = service_account.Credentials.from_service_account_file('backend/service-account.json')
storage_client = storage.Client(project="gen-lang-client-0842206246", credentials=creds)
db = firestore.Client(project="gen-lang-client-0842206246", credentials=creds, database="wardrub")

bucket = storage_client.bucket("wardrub-assets-1")
blobs = list(bucket.list_blobs(prefix=f"users/{old_uid}/"))

print(f"Found {len(blobs)} files to migrate from {old_uid} to {new_uid} in Cloud Storage")
migrated_storage = 0
for blob in blobs:
    new_name = blob.name.replace(f"users/{old_uid}/", f"users/{new_uid}/", 1)
    new_blob = bucket.copy_blob(blob, bucket, new_name)
    # Update metadata if user_id is in it
    if new_blob.metadata and new_blob.metadata.get("user_id") == old_uid:
        new_blob.metadata["user_id"] = new_uid
        new_blob.patch()
    blob.delete()
    migrated_storage += 1

print(f"Migrated {migrated_storage} files in Cloud Storage.")

docs = db.collection("garments").where("user_id", "==", old_uid).stream()
migrated_firestore = 0
for doc in docs:
    db.collection("garments").document(doc.id).update({"user_id": new_uid})
    migrated_firestore += 1

print(f"Migrated {migrated_firestore} garments in Firestore.")
print("Done!")
