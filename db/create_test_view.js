// Create a test view with custom analyzers
print("Creating test view with custom analyzers...");

// Create unique view name
const timestamp = Date.now();
const testViewName = `TestView_${timestamp}`;

// Create the view
try {
  const viewProps = {
    links: {
      Objects: {
        includeAllFields: false,
        fields: {
          Label: {
            analyzers: ["text_en", "indaleko_camel_case", "indaleko_snake_case", "indaleko_filename"]
          },
          "Record.Attributes.URI": {
            analyzers: ["text_en"]
          },
          "Record.Attributes.Description": {
            analyzers: ["text_en"]
          },
          "Tags": {
            analyzers: ["text_en"]
          }
        }
      }
    },
    storedValues: [
      "_key",
      "Label"
    ]
  };

  const result = db._createView(testViewName, "arangosearch", viewProps);
  print(`Successfully created view '${testViewName}'`);
  print(`View properties: ${JSON.stringify(viewProps, null, 2)}`);
} catch (err) {
  print(`Failed to create view: ${err.message}`);
}

// List all views
print("\nAvailable views:");
try {
  const views = db._views();
  for (let i = 0; i < views.length; i++) {
    const view = views[i];
    print(`  - ${view.name()}`);
  }
} catch (err) {
  print(`Error listing views: ${err.message}`);
}
