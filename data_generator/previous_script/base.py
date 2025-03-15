'''
'''
import os
import random
import string
import json
import shutil

# Configuration options
config = {
    'base_dir': 'synthetic_dataset',  # Base directory for the synthetic dataset
    'num_directories': 10,            # Number of directories to generate
    'min_files_per_dir': 5,           # Minimum number of files per directory
    'max_files_per_dir': 15,          # Maximum number of files per directory
    'file_types': ['txt', 'pdf', 'jpg'],  # File types (MIME types can be expanded later)
    'max_depth': 3,                   # Maximum depth of directory tree
}

# Helper function to create a random string for filenames
def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

# Create directories and files
def create_structure(base_dir, num_directories, min_files, max_files, file_types, max_depth):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)  # Clean up the previous run if necessary
    os.makedirs(base_dir)

    directory_count = 0

    # Recursive function to create directories and files
    def create_dir_recursive(current_dir, current_depth):
        nonlocal directory_count
        if current_depth > max_depth:
            return

        os.makedirs(current_dir, exist_ok=True)

        # Create files in the current directory
        num_files = random.randint(min_files, max_files)
        for _ in range(num_files):
            file_name = random_string() + '.' + random.choice(file_types)
            file_path = os.path.join(current_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(f"Dummy content for file: {file_name}\n")

        # Create subdirectories if needed
        subdirs = random.randint(1, max(1, (num_directories - directory_count) // (max_depth - current_depth + 1)))
        for _ in range(subdirs):
            directory_count += 1
            if directory_count >= num_directories:
                break
            subdir_name = random_string()
            subdir_path = os.path.join(current_dir, subdir_name)
            create_dir_recursive(subdir_path, current_depth + 1)

    # Start the directory creation process
    create_dir_recursive(base_dir, 1)

    print(f"Created {directory_count} directories with files in {base_dir}.")

# Save configuration for reproducibility
def save_config(base_dir, config):
    with open(os.path.join(base_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=4)

# Main function
if __name__ == "__main__":
    create_structure(
        config['base_dir'],
        config['num_directories'],
        config['min_files_per_dir'],
        config['max_files_per_dir'],
        config['file_types'],
        config['max_depth']
    )
    save_config(config['base_dir'], config)
