**Synthetic Data Generation Tool for UPI Evaluation**

**Objective:**
The main goal of this project is to create a synthetic data generation tool that will produce metadata records reflective of real files. These metadata records will simulate different categories such as storage metadata, semantic metadata, and activity context metadata, adhering to the format expected by Indaleko. These records will serve as a benchmark to evaluate the effectiveness of the Unified Personal Index (UPI) system. The dataset will help us measure two key information retrieval metrics: **precision** and **recall**.

**[Precision and Recall](https://en.wikipedia.org/wiki/Precision_and_recall):**
- **Precision**: This measures how accurate our search results are. Specifically, it is the ratio of **relevant metadata records retrieved** to the **total metadata records retrieved**.
- **Recall**: This measures how well our system retrieves all relevant metadata records. It is the ratio of **relevant metadata records retrieved** to **all possible relevant metadata records**.

**Tool Workflow Overview:**

1. **Configuration Setup**:
   - The tool will start with a configuration file, which contains the following information:
     - **Target Size**: The total dataset size, including the number of metadata records and/or the total storage size (e.g., "Generate at least **30,000 metadata records** occupying approximately **30 GB**").
     - **Number of Queries**: Start with at least **5 queries** and at most **20 queries**. This gives us a variety of cases to evaluate precision and recall effectively.
     - **Matching Records per Query**: Each query should match **between 1 to 3 metadata records**. This means that for each search query, we will generate a small number of metadata records that match that query.
     - **Empty Queries**: Include at least **one query** that is expected to return no results to test the system's handling of queries without matches.

2. **Synthetic Data Generation**:
   - The tool will create output metadata records that capture the attributes describing potentially useful information. This would include:
      - Storage metadata (e.g., file name, path, size, timestamps)
      - Semantic metadata, as described in the [semantic README](../semantic/recorders/unstructured/README.md)
      - Activity context metadata, simulating various contextual attributes for each metadata record.  See the activity [README.md](../activity/README.md)

3. **Oracular Set Creation**:
   - The oracular set is constructed to evaluate how well Indaleko retrieves expected metadata records. This involves the following steps:
     - **Metadata Creation**: Generate metadata records that should match specific queries based on predetermined criteria.
     - **Inserting Metadata into Indaleko**: Insert the generated metadata into Indaleko, ensuring it adheres to the expected format.
     - **Query Execution**: Execute queries against the metadata inserted in Indaleko.
     - **Verification**: Verify that the results returned match exactly what is expected. The set is considered "oracular" if the results contain exactly the expected metadata records and no more. This ensures that both **precision** and **recall** are perfect for the generated queries.

4. **Query Execution**:
   - Queries will be executed against the generated metadata, and results will be evaluated to determine **precision** and **recall**.
   - To validate that the query and results are correct, consider the following approaches:
     - **Manual Inspection**: A UGRA or evaluator can manually inspect the retrieved metadata records to verify that they match the expected results based on the oracular set.
     - **Search Tool Explanation Requirement**: When designing the system, add an explicit requirement that the search tool must explain why each retrieved metadata record was selected. This explanation can provide insights into the matching process and help identify any discrepancies.
     - **Alternative Search Tool**: Instead of solely relying on Indaleko, consider using an external search tool to cross-validate the results. This provides an independent comparison and strengthens confidence in the measurements of **precision** and **recall**.

**Goals for UGRA**:
1. **Understand the Tool's Purpose**: This tool helps us objectively measure how well our UPI system finds metadata records by comparing it with a dataset where we **know exactly** which metadata records should match which queries.
  - Note: "know exactly" implies that the underlying tools are themselves perfect, which may not be the case. This is why it is important that the tool tells us which metadata records matched, so that we can then analyze them. Our "oracle" might not be infallible.
2. **Write the Synthetic Data Generation Logic**:
   - Build a program that takes a configuration file and generates metadata records that match specific criteria.
   - Ensure that the metadata records are compatible with Indaleko's schema and that queries can be run against them.
3. **Validate the Dataset**: Make sure that the metadata records generated have **perfect recall and precision**.
4. **Prepare the Dataset for Testing in Multiple Storage Systems**: Once the dataset is validated, it will be used for tests in a variety of environments to ensure the UPI system works effectively everywhere.

**Next Steps**:
- Start by familiarizing yourself with the configuration setup and understanding the required dataset properties.
- Work on building the metadata generation logic, ensuring it can create metadata records that are correctly formatted for Indaleko.
- We can collaborate closely during each phase—feel free to ask questions as you start implementing the steps outlined here.