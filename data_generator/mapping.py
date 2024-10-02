'''
Handles mapping between user identities.
'''
import json
import random
import os

# Configuration of users with their identities across different platforms
user_mapping = {
    'alice': {
        'email': 'alice@example.com',
        'discord': 'Alice123'
    },
    'bob': {
        'email': 'bob@example.com',
        'discord': 'BobTheGreat'
    },
    'carol': {
        'email': 'carol@example.com',
        'discord': 'CarolCoder'
    }
}

# Configuration for activities
activity_config = {
    'platforms': ['discord', 'email'],
    'actions': ['shared', 'accessed', 'modified', 'created'],
    'discord_channels': ['project-x', 'general', 'dev-team'],
    'email_subjects': ['Project Update', 'File Attachment', 'Report']
}

# Helper function to map user across platforms
def map_user_activity(user, platform):
    if platform == 'discord':
        return user_mapping[user]['discord']
    elif platform == 'email':
        return user_mapping[user]['email']

# Simulate user actions across platforms
def simulate_user_activity(metadata, activity_configuration):
    for entry in metadata:
        user = entry['user']  # User associated with the file action
        platform = random.choice(activity_configuration['platforms'])
        action = random.choice(activity_configuration['actions'])

        # Assign platform and activity details
        entry['platform'] = platform
        entry['activity'] = action

        # Map the user's identity across platforms
        entry['user_identity'] = map_user_activity(user, platform)

        # Simulate additional details based on platform
        if platform == 'discord':
            entry['platform_context'] = {
                'channel': random.choice(activity_configuration['discord_channels']),
                'message_id': random.randint(1000, 9999)
            }
        elif platform == 'email':
            entry['platform_context'] = {
                'subject': random.choice(activity_configuration['email_subjects']),
                'recipient': map_user_activity(random.choice(list(user_mapping.keys())), 'email')
            }

    return metadata

# Load previously generated metadata and add user mapping and platform actions
def apply_user_mapping(base_dir):
    metadata_path = os.path.join(base_dir, 'metadata.json')

    # Load metadata from the previous step
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Simulate user actions across platforms and update metadata
    updated_metadata = simulate_user_activity(metadata, activity_config)

    # Save the updated metadata
    with open(metadata_path, 'w') as f:
        json.dump(updated_metadata, f, indent=4)

    print(f"User mapping and platform actions applied and saved in {metadata_path}")

# Main function to run the user mapping script
if __name__ == "__main__":
    base_dir = 'synthetic_dataset'
    apply_user_mapping(base_dir)

