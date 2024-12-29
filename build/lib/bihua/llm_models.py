import json

# Function to load the models data from the JSON file
def load_models_data(file_path="models_data.json"):
    with open(file_path, "r") as f:
        return json.load(f)

# Function to get the model details from the JSON data
def get_model_info(models_data, model_id):
    for model in models_data["models"]:
        if model["model_id"] == model_id:
            return model
    return None



