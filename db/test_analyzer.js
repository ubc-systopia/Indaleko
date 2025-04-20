// Test custom analyzers with AQL
print("Testing custom analyzers with AQL queries...");

// Define test queries with different analyzers
const testQueries = [
  // Basic test
  {
    analyzer: "text_en",
    query: "Indaleko"
  },
  // CamelCase tests
  {
    analyzer: "indaleko_camel_case",
    query: "Indaleko",
    description: "CamelCase: Full word 'Indaleko'"
  },
  {
    analyzer: "indaleko_camel_case",
    query: "Object",
    description: "CamelCase: Second word in 'IndalekoObject'"
  },
  {
    analyzer: "indaleko_camel_case",
    query: "Data",
    description: "CamelCase: Middle word in 'IndalekoObjectDataModel'"
  },
  // snake_case tests
  {
    analyzer: "indaleko_snake_case",
    query: "indaleko",
    description: "snake_case: First part in 'indaleko_object'"
  },
  {
    analyzer: "indaleko_snake_case",
    query: "ed25519",
    description: "snake_case: Second part in 'indaleko_ed25519'"
  },
  // Complex filename tests
  {
    analyzer: "indaleko_filename",
    query: "data",
    description: "filename: Part after hyphen in 'indaleko-data'"
  },
  {
    analyzer: "indaleko_filename",
    query: "pub",
    description: "filename: Extension in 'indaleko_ed25519.pub'"
  }
];

// Execute each test query
for (const test of testQueries) {
  print(`\nTesting analyzer: ${test.analyzer}`);
  if (test.description) {
    print(`Description: ${test.description}`);
  }
  
  try {
    // Simple query against Objects collection
    const query = `
      FOR doc IN Objects
      FILTER ANALYZER(LIKE(doc.Label, @query), @analyzer)
      LIMIT 5
      RETURN { _key: doc._key, Label: doc.Label }
    `;
    
    const bindVars = {
      query: `%${test.query}%`,
      analyzer: test.analyzer
    };
    
    print(`Executing query: ${query}`);
    print(`Bind variables: ${JSON.stringify(bindVars)}`);
    
    const cursor = db._query(query, bindVars);
    const results = cursor.toArray();
    
    // Show results
    print(`Found ${results.length} results:`);
    for (let i = 0; i < results.length; i++) {
      print(`  ${i+1}. ${results[i].Label} (key: ${results[i]._key})`);
    }
    
    if (results.length === 0) {
      print("  No matching results found");
    }
  } catch (err) {
    print(`Error executing query: ${err.message}`);
  }
}