import os
import random
import json
import time
from datetime import datetime, timedelta

# Base configuration to add metadata and cross-linking
metadata_config = {
    'users': ['alice', 'bob', 'carol'],  # Simulated user names
    'activities': ['created', 'modified', 'accessed', 'shared'],  # Possible activities
    'discord_channels': ['project-x', 'general', 'dev-team'],  # Discord-like channels
    'email_subjects': ['Project Update', 'File Attachment', 'Report'],  # Email subject templates
    'time_range_days': 30,  # Range for random timestamps (30 days into the past)
}

# Helper to generate random timestamps within a time range
def generate_random_timestamp(days_back=30):
    start_time = datetime.now() - timedelta(days=days_back)
    random_time = start_time + timedelta(seconds=random.randint(0, days_back * 24 * 3600))
    return random_time

# Add metadata and simulate actions
def generate_metadata(base_dir, users, activities, discord_channels, email_subjects, time_range_days):
    metadata_log = []

    # Walk through the directory structure and add metadata
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_metadata = {
                'file_name': file,
                'file_path': file_path,
                'user': random.choice(users),
                'activity': random.choice(activities),
                'timestamp': generate_random_timestamp(days_back=time_range_days).strftime('%Y-%m-%d %H:%M:%S'),
                'platform': None,
                'platform_context': None
            }

            # Simulate cross-linking with Discord or email
            if file_metadata['activity'] == 'shared':
                platform = random.choice(['discord', 'email'])
                if platform == 'discord':
                    file_metadata['platform'] = 'discord'
                    file_metadata['platform_context'] = {
                        'channel': random.choice(discord_channels),
                        'message_id': random.randint(1000, 9999)
                    }
                elif platform == 'email':
                    file_metadata['platform'] = 'email'
                    file_metadata['platform_context'] = {
                        'subject': random.choice(email_subjects),
                        'recipient': random.choice(users) + "@example.com"
                    }

            metadata_log.append(file_metadata)

            # Simulate file access and modification
            access_time = generate_random_timestamp(days_back=time_range_days)
            os.utime(file_path, (time.mktime(access_time.timetuple()), time.mktime(access_time.timetuple())))

    return metadata_log

# Save metadata to JSON for logging and reproducibility
def save_metadata(base_dir, metadata):
    with open(os.path.join(base_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=4)

# Main function to call metadata generation
if __name__ == "__main__":
    base_dir = 'synthetic_dataset'
    metadata = generate_metadata(
        base_dir,
        metadata_config['users'],
        metadata_config['activities'],
        metadata_config['discord_channels'],
        metadata_config['email_subjects'],
        metadata_config['time_range_days']
    )
    save_metadata(base_dir, metadata)
    print(f"Metadata generated for files in {base_dir} and saved as metadata.json.")
