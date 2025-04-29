// Create custom analyzers for Indaleko file name search
// Save this as create_analyzers.js and run with:
// arangosh --server.endpoint tcp://192.168.111.160:8529 --server.database Indaleko --server.username root --server.password Leto031406! --javascript.execute create_analyzers.js

var analyzers = require("@arangodb/analyzers");

// Check if analyzers already exist
var existingAnalyzers = analyzers.toArray().map(a => a.name);

// 1. CamelCase analyzer
if (!existingAnalyzers.includes("indaleko_camel_case")) {
  print("Creating CamelCase analyzer...");
  analyzers.save("indaleko_camel_case", "pipeline", {
    pipeline: [
      // Split on camelCase boundaries
      {
        type: "delimiter",
        properties: {
          delimiter: "",
          regexp: true,
          pattern: "(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
        }
      },
      // Normalize to lowercase
      {
        type: "norm",
        properties: {
          locale: "en",
          case: "lower"
        }
      }
    ]
  });
  print("Created CamelCase analyzer");
}

// 2. snake_case analyzer
if (!existingAnalyzers.includes("indaleko_snake_case")) {
  print("Creating snake_case analyzer...");
  analyzers.save("indaleko_snake_case", "pipeline", {
    pipeline: [
      // Split on underscores
      {
        type: "delimiter",
        properties: {
          delimiter: "_"
        }
      },
      // Normalize to lowercase
      {
        type: "norm",
        properties: {
          locale: "en",
          case: "lower"
        }
      }
    ]
  });
  print("Created snake_case analyzer");
}

// 3. File name analyzer (handles both extensions and multiple separator types)
if (!existingAnalyzers.includes("indaleko_filename")) {
  print("Creating filename analyzer...");
  analyzers.save("indaleko_filename", "pipeline", {
    pipeline: [
      // Extract extension first
      {
        type: "delimiter",
        properties: {
          delimiter: ".",
          reverse: true,
          max: 1
        }
      },
      // Then split on various separators (hyphens, underscores, spaces, percent-encoded chars)
      {
        type: "delimiter",
        properties: {
          delimiter: "",
          regexp: true,
          pattern: "[-_\\s%]+"
        }
      },
      // Split CamelCase
      {
        type: "delimiter",
        properties: {
          delimiter: "",
          regexp: true,
          pattern: "(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
        }
      },
      // Normalize to lowercase
      {
        type: "norm",
        properties: {
          locale: "en",
          case: "lower"
        }
      }
    ]
  });
  print("Created filename analyzer");
}

// Print all available analyzers after creation
print("\nAvailable analyzers:");
analyzers.toArray().forEach(function(analyzer) {
  print(" - " + analyzer.name + " (type: " + analyzer.type + ")");
});
