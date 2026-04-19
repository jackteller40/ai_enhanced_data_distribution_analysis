import os
import base64
import json

image_folder = 'demo_faces'
base64_list = []

# Loop through all files in the folder
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filepath = os.path.join(image_folder, filename)
        
        with open(filepath, "rb") as image_file:
            # Read the image and encode it
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Determine the correct MIME type based on extension
            mime_type = "image/jpeg" if filename.lower().endswith(('.jpg', '.jpeg')) else "image/png"
            
            # Create the full Data URI string
            data_uri = f"data:{mime_type};base64,{encoded_string}"
            base64_list.append(data_uri)

# Save the list to a JSON file so our main script can use it
with open('faces_base64.json', 'w') as f:
    json.dump(base64_list, f)

print(f"Successfully converted {len(base64_list)} images and saved to faces_base64.json!")