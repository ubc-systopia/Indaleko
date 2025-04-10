# Enhanced Query Support

The goal of this query support is to provide a single tool that takes, either interactively or via a scriptable API
a way to test query behavior across a range of systems, including Indaleko.

Currently, the query library is structured to contain multiple distinct components:

1. A pre-processor step.  While currently empty, this will be important in "pre-digesting" the query to determine if it can be expressed or if there are limitations.
2. A query constructor step.  This takes the pre-processed query and then converts it into an actionable query (e.g., in AQL for Indaleko.)
3. A query executor step.  This is where the actionable query is evaluated --- typically by submitting it to an external search mechanism.
4. A response analyzer.  While currently empty, this will be where the response can be further refined, possibly interactively (the "discussion mode" that I've suggested elsewhere.)
5. A query optimizer.  This is also currently empty but the idea was that it can capture information that could be beneficial in improving this query (and future queries).  This might include memoization (for example) or identification of query structure that exhibits better performance (e.g., using a specific field seems faster than using another field, possibly due to indexing that wasn't visible in the early stages.)
6. A query recorder.  This captures the entire flow of the query through the system, from originally submitted query to final optimization.  My expectation is that this will also create "activity context" information that can then be used by Indaleko for future queries.  This is consistent with the idea that humans have a tendency to perform the same search more than once, but they might focus on different aspects of the results.

## Refinement Plan

Currently (2024/10/29) this document serves as a plan for improving this query search tool.  The following sections were generated via a conversation with [ChatGPT-4o](https://chatgpt.com/share/67210fa9-5eec-800e-8ad7-1938d53b7edb) and captured here as a basis for further discussion.

Note: I have edited the original source material.

### 1. Verifying the Architecture

In this section, we identify specific additions to the architecture that might make it more extensible and robust to meet the goal of integrating multiple search backends.

- **Preprocessor Stage Enhancement**: The preprocessor can be expanded to detect and categorize the query intent.  Having the ability to classify the parts of the query that can be realized on a given search target will be useful and can help identify searches that are not viable for a given target.
- **Backend Abstraction Layer**: Ensure the abstraction layer between the LLM-based query generator and the platform-specific API call is sufficiently broad.  This layer is responsible for managing the platform-specific query languages and/or APIs.  By managing the various query languages and the constraints in the corresponding API, it will be simpler to modify existing, or add new backend targets in the future. This layer could also handle retries, batching, and rate-limiting as necessary.
- **Response Normalization**: While the existing response analyzer is a on-op, this is a good place to enhance the tool's functionality, which includes normalizing the responses in order to simplify the evaluation of the target platform(s).  This would also enable useful post-query analyses.
- **Query Optimizer Loop**: The general goal here is a good one, particularly if coupled with a feedback loop into the preprocessor.  While not necessary for achieving the project goals, it would benefit the tool overall to provide information useful in the preprocessor stage (e.g., better metadata categorization or tweaks to LLM prompt generation.)

### 2. Reasonableness of Goals

The goal of a unified tool to process and compare queries across multiple platforms is ambitious but very feasible.
- **Challenge: Query Language Differences**: Each platform has varying capabilities, and some might not be able to express the full complexity of the user's intent. This could be handled in a number of ways, such as rejecting a query that cannot be expressed, or via an adaptive fallback system that "does the best that it can" given the platform limitations.  This could also suggest ways in which additional post-processing (outside the scope of the tool) might be used to improve the results.
- **Result Evaluation**: The use of a common metric for evaluating the results will be important here. Possible metrics include: response speed, precision, and recall.  This would enable making useful comparisons between systems even when their search capabilities are significantly different.

### 3. Relevant Tools
- **LLMs**: The tool should allow LLMs to be "swapped out" easily for different use cases, or even permitting the evaluation of the performance of the LLMs themselves. It might be useful to have a modular inference step to allow experimentation with different models.
- **Query Parser and Optimizer**: Libraries like [**ANTLR**](https://www.antlr.org/) can be used to parse queries into intermediate forms, which you can then optimize for various backend APIs.
- **API Management**: Using [**OpenAPI**](https://swagger.io/specification/) specifications or a tool like [**Postman**](https://www.postman.com) can help in defining and maintaining API integration with multiple backends (Google Drive, OneDrive, Dropbox, etc.). You could write wrappers that simplify interaction with each API by using their OpenAPI descriptions.
- **Result Normalization and Analysis**: You could use data-processing tools like [**Pandas**](https://pandas.pydata.org/) in Python to build a normalized view of the results coming from different sources, which would simplify comparison and statistical analysis of the search responses.

### 4. Implementation Plan

Note: I did not edit this section.  Consider it to be "open to discussion" and it is more of a straw-person proposal than anything else.

**Phase 1: Core Infrastructure and Abstraction Layer**
- Implement an abstraction layer to manage the specifics of different query languages and API calls for Google Drive, OneDrive, Dropbox, Windows Search, Spotlight, and Linux indexing systems. Ensure this layer can handle authentication, retries, rate limiting, and API-specific parameters.
- Develop a uniform schema for translating natural language queries into platform-specific search queries. This can be based on a set of templates that map semantic components to different platforms.

**Phase 2: Modular Preprocessing and Query Generation**
- Expand the preprocessor to better classify queries by expected response type (e.g., date ranges, file types, tags) and platform capabilities.
- Refine your LLM-based query constructor to leverage prompt engineering strategies that dynamically adapt based on the target backend. Consider building a context-aware system that uses a knowledge base of each backend’s capabilities to adjust prompts.

**Phase 3: Response Normalization and Analysis**
- Develop a response normalization module that standardizes output from each platform's API into a common format that can be used for comparison.
- Expand your no-op response analyzer to include post-processing options such as result ranking, duplicate removal, and relevance scoring.

**Phase 4: Optimizer and Feedback Loop**
- Build the query optimizer, starting with a rules-based system to refine metadata selection or to suggest query splits. Over time, this could evolve to incorporate ML models to suggest optimizations based on historical data.
- Design the feedback loop for both the preprocessor and the LLM-based query generator, incorporating optimization suggestions back into the query flow.

**Phase 5: Experimentation and Evaluation**
- Develop a systematic approach to experiment with and evaluate the efficacy of each search backend, focusing on metrics like relevance, speed, and usability of results.
- Implement logging and data capture in the query recorder to generate meaningful activity data and insights about user interactions.
