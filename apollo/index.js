const { ApolloServer, gql } = require('apollo-server');
const { Database } = require('arangojs');

// Connect to ArangoDB
const db = new Database({
    url: 'http://localhost:8529',
    databaseName: 'Indaleko',
    auth: { username: process.env.ARANGO_DB_USER, password: process.env.ARANGO_DB_PASS }
});

// Define GraphQL schema
const typeDefs = gql`
  type Query {
    hello: String
  }
`;

// Define resolvers
const resolvers = {
    Query: {
        hello: () => 'Hello world!'
    }
};

// Create Apollo Server
const server = new ApolloServer({ typeDefs, resolvers });

// Start the server
server.listen().then(({ url }) => {
    console.log(`🚀 Server ready at ${url}`);
});
