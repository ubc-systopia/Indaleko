# Semantic Extraction Pipeline using Unstructured

## Introduction

This project is part of Indaleko, an implementation of the Unified Personal Index. It provides a source of semantic content extraction using two existing tools:

- [unstructured](https://unstrutured.io), which is a tool that takes a set of files, and for the supported files extracts semantic information, which is emitted in a structured data format.  It's primary purpose is to prepare data files for use as training data for large language models (LLMs), though the use in this project is a bit different.

- [docker](https://docker.com), which is a tool for running software (including **unstructured**) in an isolated environment.  We already use this tool for other purposes, but this use will be distinct from previous use (e.g., we expect this to be a separate container). It allows access to data outside the container, so that input and output can be external to the container.  This is important for output because the lifetime of data within the container is the lifetime of the container itself.  Thus, internal data is consider to be _ephemeral_.

### Objective

The objective of this project is to automate the extraction of metadata from files, with the output being in a format (e.g., JSONL) that can then be used by the [recorder](../../recorders/unstructured/README.md) tool for injection of this data into the database.

This tool will only be used on files that are physically present on the local system.  As much as possible, it should avoid expensive operations.  Files requiring retrieval from external storage should be skipped to avoid unnecessary delays and excessive resource consumption.

## Input Files

The input files to this tool should define the input data set with at least the following metadata information:

- A UUID that represents the instance of the file to Indaleko.
- A local path to that file.
- One or more elements of file identity:
    - A timestamp (e.g., last modified time)
    - A length
    - A checksum

The UUID should correspond to the UUID of the file in Indaleko's database.  Thus, this could either be determined by obtaining it from a local file indexer's output or from the Indaleko database directly; either approach is acceptable.

The local path to the file should be the data needed to open the file (e.g., a fully qualified path name.)

The file identity information allows the recorder to determine if the file data has changed. Note: the collector _could_ use information from the Indaleko object database to eliminate files that have already been in this pipeline and have not changed.

The data model file for the format of the input data is in [input](data_models/input.py)

## Batch Processing

While we know that Unstructured consumes a considerable amount of resources, we are not certain what the actual limits are.  Thus, from an efficiency perspective it makes sense to parameterize this and, through experimentation, determine what reasonable limits are.

Accordingly, this collector will need to process files in batches, with the batch size to be determined.

In addition, the implementation should seek to avoid copying files whenever possible.  Potential approaches to this need to be determined as part of this project.  For example, there are at least two possible strategies to try (likely others that we have not yet considered):

- Process input on a _per directory_ basis.  In this model, all the files within a given directory are processed together.  The directory can be made visible to Unstructured via a volume mount (through the container model) that maps the input directory to a location used by Unstructured for obtaining its input.
- Construct a _working directory_ and provide access to that working directory using the volume mount (through the container model.) In this case, the files in the working directory should be sybmolic links.  The goal is to avoid copying the data files, as that will incur substantial I/O overhead and is impractical.

Regardless of this technique, the pipeline should log the results:

- Batches that fail.  This will help us determine why they fail and adjust the pipeline as necessary.
- Batches that succeed.
- Files (if any) that are skipped in this process.

## File Filtering

It is quite likely that the tool will need to skip files:

- File types that are not known to Unstructured.
- Files that are "too large" (for some value we determine) that require excessive resources.
- File types that are known but we determine are expensive to process and thus to be avoided during this prototyping stage.

## Metadata Extraction

The output of of Unstructured tool is a set of data elements with a defined format.  The definition of this data, which is to be embedded in the output information, is defined in [embedded](data_models/embedded.py).

Note that the initial version of this data model was generated via a [conversation](https://chatgpt.com/share/67029bde-8640-800e-8cba-cbf8c09eecd0) via ChatGPT-4o-with-canvas.

This format is _empirically_ determined and may require revision as our experience using the tool grows.

## Final dataset:

Consistent with our approach to capturing metadata, the final dataset should:

- Capture the raw data that unstructured emitted.  This can be packed and encoded using the [encode_binary_data](../../../Indaleko.py) function.
- Capture the relevant identity information that is needed by the [recorder](../../recorders/unstructured/).  Since we control the behavior of this collector there is some flexibility about the meaning of "relevant identity information".

The normalization and injection of the data into the database is the responsibility of the _recorder_ and thus need not be defined at this stage in the pipeline.

As of the time of this writing, the data model for this is simply the base semantic data extraction data model.  See [base_data_model.py](../../data_models/base_data_model.py).

## Error handling:

The approach here should be to log errors, note that some data has been skipped, and continue processing.  This is a prototype tool, errors are likely to arise, and they should not create impediments to further processing.

## Future Scalability

As we develop the tool, it will be useful to capture information (e.g., in this document) about approaches that we might be able to take to improve scalability. This might include:

- Semantic extraction using other tools (e.g., Apache Tika).
- Increased local resources for containers.
- Parallel execution.
