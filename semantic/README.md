# Semantic Data Extraction

## How to use Unstructured

Note: This only works on Windows (due to file path conventions that are different from UNIX ones)

1. Ensure the ArangoDB instance is running on Docker, and there are files whose semantics need to be extracted

### Collector ###

2. Run `semantic\collectors\unstructured\unstructuredd.py` with parameter `lookup`. This command does two things:
    - Creates a configuration file in the config folder. For now, we assume that all files are located 
        in the C:\ drive. If files from other drives need to be analyzed, simply change the 'HostDrive' parameter 
        in the configuration file. This tells Docker to create a bind mount to your specified drive instead of the default C:\ drive.

    - Creates the file `unstructured_inputs.jsonl` in the `data\semantic` folder. Each line specifies a file that is eligible to be
        processed with unstructured. The URI of each file is converted to a UNIX-based path relative to HostDrive, so that the Docker container
        knows where to look when trying to process a file. The ObjectIdentifier, which points to the UUID of the file stored in the Objects
        Collection on ArangoDB, is also listed to aid us in mapping the results of unstructured back to the original file in Arango.

3. If you decide that there are too many files to be processed (Due to time constraints), you can simply remove some lines in the
    `unstructured_inputs.jsonl` file.

4. Important! The next step would be to run unstructured on all the specified files. However, you can first configure the unstructured
    Docker container to allocate enough computational resources (Especially memory as that is the bottleneck). You can do this by going
    to `semantic\collectors\unstructured\retrieve.py`, scroll to the bottom where the docker container is run, and set the `mem_limit`.

5. Run `semantic\collectors\unstructured\unstructuredd.py` with parameter `retrieve`. This command simply runs unstructured on all the files
    specified in `unstructured_inputs.jsonl`, and outputs the raw, unormalized results in `unstructured_outputs.jsonl`.

### Recorder ###

6. Now that the collector stage is finished, we now normalize the outputs from unstructured. This is done by running 
    `semantic\recorders\unstructured\recorder.py`, which creates the file `unstructured_recorder.jsonl`, which contains the normalized
    entry of each file. This is the final file that will get uploaded to ArangoDB via arangoimport.

