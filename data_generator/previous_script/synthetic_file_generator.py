"""
Script to generate synthetic dataset with metadata to test Indaleko
Author: Pearl Park

Two main commands:
    a) generate_dataset
        - generates a synthetic dataset using the parameters and queries specified in the dg_config.yml file
        - copies the generated dataset onto the Indaleko database 

        - receives a set of query data processed by openAI and processes data
        - feeds processed data into Indaleko 
        - 
"""
from icecream import ic

import os, shutil
from pathlib import Path
import yaml

from datetime import datetime
import time

import random
import string
from faker import Faker
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4



# class for creating synthetic dataset based on the configuration files given specifying parameters + queries
class Data_Generator:
    def __init__(self, config_path):
        self.config_path = config_path
        self.parameters = {}
        self.queries = {}
        self.queries_attributes = [] # list of attributes to avoid creating for fake and target data that is not apart of particular query

        self.parent_directory = ""
        self.file_types = []
        self.directories = {}
    
    #main function: performs data generaton
    def run_data_generator(self):
        self.parse_config_file()
    
    #parse the configuration file to extract parameter and queries 
    def parse_config_file(self):
        with open(self.config_path, 'r') as file:
            config = yaml.load(file, Loader = yaml.SafeLoader)
            self.parameters = config["dg_parameters"]
            self.queries = config["queries"]
            self.parent_directory = config["dg_parameters"]["output_dir"]
            self.file_types = config["dg_parameters"]["file_types"]

    #create a random string of words to form title
    def random_string(self, length):
        return ''.join(random.choices(string.ascii_lowercase, k = length))

    
    #using faker library to generate paragraphs using specified words 
    def generate_real_txt(self, file_path, size=100):
        fake = Faker()
        specified_words = ['apple']
        while os.stat(file_path).st_size < size:
            text_content = fake.paragraph(ext_word_list=specified_words)
            content = len(text_content)
            
            #At the last paragraph, if the size of the paragraph is too big, fill with sentence
            if os.stat(file_path).st_size + content > size:
                remaining_size = size - os.stat(file_path).st_size
                text_content = fake.sentence(nb_words=remaining_size, ext_word_list=specified_words)

            with open(file_path, 'a') as f:
                f.write(text_content + '\n')
    
    # generates the instance of a real jpg from specific query
    def generate_real_jpg(self, file_path):
        with open(file_path, 'wb') as f:
            f.write(b"\xFF\xD8\xFF\xE0")  # JPEG header bytes (placeholder)
            f.write(b"True JPEG content")


    #generates an instance of pdf that is specific to a query
    def generate_real_pdf(self, file_path):
        None
        
    #generate a dummy jpg image using image generator 
    def generate_fake_jpg(self, file_path):
        with open(file_path, 'wb') as f:
            f.write(b"\xFF\xD8\xFF\xE0")  # JPEG header bytes (placeholder)
            f.write(b"Dummy JPEG content")

    #generate a fake instance of a pdf using reportlab
    def generate_fake_pdf(self, file_path):
        fake = Faker()
        sentence = fake.sentence(nb_words=random.randint(5,10)) 
        #creates a new canvas for pdf generated using reportlab
        w, h = A4
        c = canvas.Canvas(file_path, pagesize=A4)
        text = c.beginText(50, h - 50)
        text.setFont("Times-Roman", 12)
        text.textLine(sentence)
        c.drawText(text)
        c.showPage()
        c.save()

    # fake text generator that creates file text to specified size
    def generate_fake_txt(self, file_path, size=1000):
        fake = Faker()
        while os.stat(file_path).st_size < size:
            text_content = fake.paragraph()
            content = len(text_content)
            
            #At the last paragraph, if the size of the paragraph is too big, fill with sentence
            if os.stat(file_path).st_size + content > size:
                remaining_size = size - os.stat(file_path).st_size
                ic(remaining_size)
                text_content = fake.sentence(nb_words=remaining_size, variable_nb_words = False)
                ic(text_content)

            with open(file_path, 'a') as f:
                f.write(text_content + '\n')

    #generate an instance of the real content based on the file extension
    def generate_real_content(self, file_type, file_path):
        if file_type == "jpg":
            self.generate_real_jpg(file_path)
        elif file_type == "txt":
            self.generate_real_txt(file_path)
        elif file_type == "pdf": 
            self.generate_real_pdf(file_path)

    #generate "fake" content based on the file extension
    def generate_fake_content(self, file_type, file_path):
        if file_type == "jpg":
            self.generate_fake_jpg(file_path)
        elif file_type == "txt":
            self.generate_fake_txt(file_path)
        elif file_type == "pdf":
            self.generate_fake_pdf(file_path)

    #manipulates the file metdata, access time and modification times
    def manipulate_file_metadata(self, file_path):
        #set a date for the access time/ modification time for a file
        specific_time = datetime(2024, 10, 9, 20, 0, 0)
        access_time = time.mktime(specific_time.timetuple())
        mod_time = access_time
        os.utime(file_path, (access_time, mod_time))
    
    
    # list all both parent and child directories within the output directory
    # this is used to place files in a random directory
    def list_all_directory_paths(self, parent_dir):
        list = [parent_dir]
        path = Path(parent_dir)
        list += [str(subdir) for subdir in path.rglob('*') if subdir.is_dir()]
        return list

    # Recursive function to create directories
    # derived/modified from Tony's script base.py
    def create_structure(self, base_dir, num_directories, max_depth):
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)  # Clean up the previous run if necessary
        os.makedirs(base_dir)

        directory_count = 0

        def create_dir_recursive(current_dir, current_depth):
            nonlocal directory_count
            if current_depth > max_depth or directory_count >= num_directories:
                return

            os.makedirs(current_dir, exist_ok=True)

            if num_directories - directory_count > 0:
                max_subdirs = max(1, (num_directories - directory_count) // (max_depth - current_depth + 1))
                subdirs = random.randint(1, max_subdirs)
                for _ in range(subdirs):
                    directory_count += 1
                    if directory_count >= num_directories:
                        break
                    subdir_name = self.random_string(8)
                    subdir_path = os.path.join(current_dir, subdir_name)
                    create_dir_recursive(subdir_path, current_depth + 1)
        # Start the directory creation process
        create_dir_recursive(base_dir, 1)

    #create directories for the dataset based on specified parameters in config file
    def create_files(self, total_number_files):
        path_to_all_dir = self.list_all_directory_paths(self.parent_directory)
        # For each query, create a random number of files that are considered "true" data
        for i in range(len(self.queries)):
            true_labels_number = random.randint(1,3)
            while true_labels_number > 0 and total_number_files > 0:

                random_name_len = random.randint(1, 10)
                file_type = random.choice(self.file_types) 
                file_name = self.random_string(random_name_len) + '.' + file_type

                random_dir = random.choices(path_to_all_dir)[0]
                ic(path_to_all_dir)
                file_path = os.path.join(random_dir, file_name) 
                gt_label = random.choice(["Dummy", "True"])
                ic(gt_label)

                with open(file_path, 'w') as f:
                    f.write(f"{gt_label} content for file: {file_name}\n")

                if gt_label == "True":
                    self.generate_real_content(file_type, file_path)
                    total_number_files -= 1
                else:
                    self.generate_fake_content(file_type, file_path)
                    self.manipulate_file_metadata(file_path)
                    total_number_files -= 1
                
# the main function that runs the data generator tool
def main():
    config_path = "/Users/pearl/indaleko/Indaleko_Tester/0_Input/dg_config.yml"
    data_generator = Data_Generator(config_path)
    data_generator.run_data_generator()
    data_generator.create_structure(data_generator.parent_directory, 5, 5)
    #data_generator.create_files(10)


if __name__ == '__main__':
    main()
