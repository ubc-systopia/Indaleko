# Installation
- You need to have `Python 3.12.0` installed.
  - If you want to have multiple versions of python on your system, you can use `pyenv`.

## OneDrive Config format:
- First you need to register an application in your (portal)[https://entra.microsoft.com/].
  - Go the `Applications->App registrations-> + New registration`.
  - Go to `Authentication-> + Add a platform -> Mobile and desktop applications`. Put `http://localhost` in the **redirect url** field
  - Set **Allow public client flows** to **Yes**.
- Create a config file named `msgraph-parameters.json` inside your `data` folder. Copy the following `json` object and put it the file. Replace `[see your panel]` with your the data shown in your panel.

```json
{
    "client_id": "[see your panel]",
    "tenant_id": "[see your panel]",
    "authority": "https://login.microsoftonline.com/consumers",
    "scope": ["User.Read", "files.read.all"]
}
``````
- Run `python onedrive-ingest.py`. You need to sign in to your Mirosoft account and give permissions for reading your files on OneDrive. Follow the instructions on the terminal.

# Test Scripts

These are some test scripts I have written for the Indaleko project.  There's
nothing deep here.

* README.md - this flie
* arangodb-indaleko-reset.py - this will reset the Indaleko database inside
  ArangoDB.  Note you will need to add your own passwords.
* arangodb-insert-test.py - this is my "insert an object" test where I used a
  UUID as the contents of the node being inserted.
* arangodb-local-ingest.py - this is my "scan the file system and insert
  everything into ArangoDB" script
* docker-compose.yml - not used
* enumerate-volume.py - Used to count the number of files and directories on a
  given volume (or a tree)
* neo4j-insert-test.py - Used to insert nodes into Neo4j with a UUID as the
  creamy filling.
* neo4j-local-ingest.py - this is the script I was using to stuff data into the
  Neo4j database from my local file system.


## Notes

### 2023-10-25

I've been reconstructing my system, and while doing this I am working on fitting
the various bits and pieces I have been writing over the past 2+ years back
together.  Since it is easy for me to forget what exactly I've done, I'll
collect my contemporaneous notes here.

Yesterday my focus was on setting my machine back up for collecting the data.
I'd been in the midst of changing how I did some of this, so I thought I would
capture a description of where I'm heading at the moment.

First, my **primary goal** is to get to a point where I have an end-to-end query
chain.  What that means is I can use my GraphQL + ChatGPT interface to create
queries which can then be submitted to my database(s).  For the moment, that
means ArangoDB, which supports GraphQL, albeit indirectly.

So, what do I need to accomplish this:

1. The ability to easily set up and manage the database(s).  I did this all
   manually previously, so yesterday I automated the task into a python script
   (see [dbsetup.py](dbsetup.py)).  This assumes that I am using the dockerized
   version of ArangoDB.

2. The ability to collect existing metadata from the storage services:

    * Local file system(s) - I'm focusing on POSIX metadata initially, since
      this is easily understood and can be normalized with a minimum of fuss.
    * Cloud storage services - the metadata varies considerably here, but this
      is part of the evaluation (e.g., "how hard is it to build one of these
      things.")
      - Google Drive
      - Dropbox
      - OneDrive
      - iCloud

      Note that it is quite possible I'll omit one of these (e.g., iCloud, which
      I have not yet implemented.)  I'm keeping them all in the list because
      they each represent interesting points in the spectrum, as they differ in
      a variety of ways in how they are implemented.  For example, Google Drive
      does not store content within the structure of the local file system,
      while Dropbox and OneDrive certainly do.  iCloud has no native search
      interface, which means it relies upon keeping all the content on the local
      machine, which is different than how Dropbox and OneDrive work - they use
      a sparse file storage mechanism on Windows ("cloud filter") that means
      local indexing doesn't work reliably on them.

    * Application services that "act like" storage services.
      - Discord
      - Slack
      - Teams (which uses SharePoint/OneDrive for its storage, so probably not
        interesting.)
      - Outlook (or other e-mail clients) where attachments are present.


3. The ability to collect semantic information from the files. This one is
   intriguing because there's a variety of existing mechanisms for generating
   this and my goal is to flesh out a framework for doing so. In addition, cloud
   storage services have metadata that could be useful for this sort of semantic
   extraction.

   Tools for doing semantic extraction would include:
   * Spacy - this provides NLP for Python and could be useful for doing at least
     some basic information extraction.

   * NLTK - natural language toolkit, for python.

   * BERT - Google's NLP models that can be used to extract semantic information
     (see also "HuggingFace")

   * Word2vec and Doc2Vec

   * Semantic Scholar

    One of the challenges here is to come up with an extensible model. Most of
   the existing semantic information is about text, but there are non-text
   semantic transducers that are of interest, such as features for photos, or
   audio classification data for recordings.  I would like to be able to capture
   them.

  4. The ability to collect activity data, which in turn is used to form an
     activity context.  My mental model for this is that an activity data
     provider registers with the activity context service.  Then, using a
     pub/sub service, the activity context service can capture activity state
     each time a new activity context handle is required.  Thus, activity
     context can be thought of as a cursor into the time-series data gathered by
     the activity data generators.  It also provides a model in which activity
     data providers can be added without "breaking" prior existing activity
     context values.  This area is the least formed of the components, despite
     being the most novel part of the system.  My thinking initially is that
     activity context consists of:

     * Storage events.  Creation, access, modification of files, represent a
       stream of storage events. Less common storage events might include the
       addition or removal of a storage device (e.g., a USB stick.)  Gathering
       data about the device could be beneficial in identifying the USB stick in
       the future.
     * Relevant network events.  Even just monitoring the port 80 and 443
       accesses could be insightful since that can be related back to websites,
       which in turn could be a useful form of activity data.
     * Location.  For mobile devices, location data can be collected (it can be
       collected for non-mobile devices, it just won't be of as much interest.)
     * Calendar information.  This can be used to answer questions like "show me
       files that I accessed when I was meeting with Aki last week."
     * Communications activity.  Information, such as messages on Discord or
       Slack, could be used to identify relevant information.
     * Process/program information.  Capturing the state of running programs may
       provide additional insight useful for increasing relevancy of the
       returned operations.

    Note that there may be some cross-over for these activities.  For instance,
    a storage event might have a reference that correlates with process
    information.

The focus of this work is to try and demonstrate the ability to support a range
of queries.  The first query really should be something simple.  For example:

  * Show me files that have 2016 in their name

Subsequent queries should focus on demonstrating this index goes beyond simple
queries:

  * Find photos that have my face in them

Of course the real goal is to be able to process queries that are not
expressible in existing storage systems:

  * Find files that I saved last week from a given application
    - Web browser ("downloads")
    - E-mail program ("attachments")

So, my goal is to get these pieces built.  While building the ingestion scripts
I started with a model of directly adding content to the database.  I'm moving
away from that model to a file capture model, which permits bulk uploading and
that should be faster.

The three cloud metadata ingestion scripts generate files, the local one does
not, so my next task is to convert the local one to save to files as well.  Then
the next step is to figure out how to do bulk importing.

Once I have bulk importing working at some level, I'd like to start identifying
data that I want to normalize. Conceptually, I think of data normalization as
being distinct from the indexing, though I could implement them as part of
existing scripts.

The reason for this is that once I have indexing across silos, I can build the
query infrastructure piece: combine the schema with the GPT interface, and have
it generate GraphQL queries, which can be submitted to ArangoDB.  With those
pieces in place, I can expand this to incorporate semantic information, and
finally I can get to building the activity context service.

### 2023-10-16

Late yesterday I changed the logic of the "get local machine configuration"
powershell script so it saves it to a file that embeds the machine GUID.  My
thinking here was that this is (mostly) static information that, at least for
now, I can just capture.

The reason this is important is because I want to be able to properly address
all files, not just those that have drive letters because **I** know that drive
letters are not nearly as "baked in" to Windows as users think.  Years of
Windows file system experience.

This powershell script has to be run with administrative credentials, which is
why I want to just capture the data, at least for now.  For a real packaged
system it would be better to have it done dynamically and to do this inside a
privileged service (which I have done work on in the past.)

Now I can get back to the local ingest script.

### 2023-11-078

I have been systematically working through the local ingestion script to try
and split it out into a common core (applicable to all local environments) and
the platform specific portions.

In parallel, we're working on getting the iCloud ingestion work going as well
(Zee is looking into this.)  I'm ignoring that for the time being.

So now I seem to have a local ingest script for Windows working.  Limited
testing thus far, but it is generating a raw data file.

So, now I have a skeleton of what the _ingest_ looks like.  The next step is to
begin adding the normalizers.  Ideally, I'll end up with a model for the
normalizers that's generalizable.  At the moment, the ingest logic is not quite
where I want it to be (e.g., common framework) though there's a fair bit of
material.  Logically, I want a flow where the storage specific elements know how
to process their own data.

Thus, the question becomes: what data is _required_ (e.g., expected) and what
data is _permitted_ (e.g., useful but optional.) During this first pass, I am
focusing on the required bits, since those will become the key aspects of the
data schema.  I'll have to revisit what to do about optional data in the future.

The other aspect I need to capture here is the relationships, which I don't
think are being well-captured (yet).  I note that in the local ingest I already
am explicitly adding the full path and a URI (at least for the Windows version,
haven't massaged this to do what is needed on Linux.)  For example, I may want
to capture the inode number of the containing directory, not just its path.

This allows me to have a separate json file that contains data relationships as
well, since I think those are going to be loaded into different collections in
ArangoDB.  I don't want to lose that information, but the drive here was to make
bulk uploading as fast as possible.

### 2023-11-14

Let's start with a minimum set of fields we want for our index:

* Label - this is what corresponds to the "name" of the file
* URI - this is how we get back to the file
* Object ID - this is a UUID
* Local ID - this is an "inode number"
* Timestamps:
  - Creation Time
  - Access Time
  - Modification/Change Time
    * Note that NTFS has both, one being the _data_ and the other being the
      _metadata_.
* Size
* Source
  - UUID that identifies where we got the data
  - Version
  - Source specific metadata
* Raw Data
* Semantic attributes (key-value list)
  - Semantic Type/Identifier
  - Semantic Data


In addition, there's a relationship we want to capture, the container/contained
relationship.  I need to figure out how we describe this, since it likely goes
into a _different_ collection in ArangoDB.

Relationships I want to capture:

* Container relationship (bi-directionally)
* Causal (versioned) relationship - not needed for indexing?

### 2023-12-05

Improved the automated set-up script for the database container.  That now seems
to be basically working, though there's always more features that _could_ be
added.

Biggest point is that it now extracts the Schema from Indaleko.py and creates
the corresponding collection _with_ the Schema.  The purpose of having those
schema is because I can use them as part of the query production chain (e.g.,
use the OpenAI API + Schema + Natural Language Query and get a GraphQL query
back.) This will then provide the basis for exploring search functionality,
though I expect future work will use search to provide alternative interfaces
(e.g., the relationship graph walking model we've explored before.)

### 2023-12-06

I re-organized some code today, putting files that are from prior iterations of
work into the "old" directory.  There's still some useful work that needs to be
extracted from them.

I also added logic to the dbsetup.py script so it will _wait_ for ArangoDB to
start running before it actually tries to create the Indaleko database and the
various collections.

One of the motivations for this was that I started looking at indices again.  I
had a number of indices that I set up previously (see arangodb-local-ingest.py)
and I'm trying to extract the useful work there for setting up the indices.
That in turn led me to set up the main() method in indalekocollections.py (a new
file I added to capture some of that prior work product) so I could put test
code right there, rather than writing yet another random little script.  This,
in turn, led me to reuse the database config code (from dbsetup.py) and it
balked when it found the collections already existed.  So I modified it to just
load them up.  Then I verified that the three collections I expected _do_ in
fact exist and now I have the basis of a script for further testing.  I want to
define the indices to create for the various collections, which are then, in
turn, formed into a list of collections.  In this way I can move towards a model
where this is dynamically created from said list, as I'm increasingly convinced
we're going to need more collections.

The other motivation here is that as I was talking with Zee about building the
data ingester for Mac, I realized there is a challenge that I didn't have back
when I first added the relationship stuff: because I was inserting it
contemporaneously, I had exactly the data I needed in order to add the
relationships.  But when I bulk upload I won't have that data (e.g., the `_id`
field that ArangoDB adds to each entry and uses as part of creating the edge
relationships.)  I spent some time trying to explain sources to Zee as well and
realized I need to be more clear about this.

A _Source_ is a unique identifier that specifies what component generated the
given file.  So, for example, the Google Drive indexer should have a source
identifier and that would go into the Sources collection.  In turn, the GDrive
_ingester_ would be a source as well and have its own source identifier.

My original model was that I'd embed the raw metadata inside the object itself,
but now I'm wondering if maybe that's the wrong model.  For example, I could
have objects that go into per-indexer collections.  This sort of separation
might make sense given that the raw metadata doesn't really provide much benefit
to the core index.  Instead, I could create a causal relationship showing that
the data was ingested _from_ the raw metadata.  That would then provide us with
a model in which parallel ingesters could process that original metadata and
show their own contributions - a sort of provenance graph relationship.

Another element that I ran across yesterday and wanted to capture is likely to
be quite important once we start trying to optimize query results.

https://about.xethub.com/blog/you-dont-need-a-vector-database

Specifically, it talks about how to combine two different techniques, one is
essentially a "coarse filtering" mechanism and the second is a "fine filtering"
mechanism.

* Retrieval Augmented Generation (RAG) is a process of finding a subset of
  documents quickly using a "low precision, high recall algorithm."  This can
  reduce billions of documents to around 1,000 documents (I'm paraphrasing right
  from that blog post.)

* A vector database, with vector embeddings extracted from the document, can
  then be used to "re-rank" the original set to improve the results.

So I think this approach is solid and justifies further exploration as we begin
building exploring the query space.

### 2024-01-05

This week has been productive.  I buckled down and built a windows ingester.  It
takes the information collected by the windows _indexer_, which is written to a
file, and then it opens it, processes it:

* Extracts and normalizes specific fields
* Saves the "raw" content that was gathered by the indexer in the first place
* generates a uuid (and that becomes the _key_ to the object.)

Note the collections have a schema to enforce format of data in the document.
Most fields are _not_ required, but when present they are required to be in a
particular format.  The ingester emits six different _json lines_ files that can
be given to arangoimport.  From what I can tell, `arangoimport` is using the
HTTP bulk uploader interface.  On my machine it indicates it will be using 64
_threads_ to do its work. Overkill for my 45 file initial test sample, but it
did demonstrate that it can successfully upload the data into the database.

I'm now turning my attention to taking the "down and dirty" windows ingester and
converting it into a class library that I can use to build specialized ingesters
for the various storage engines.  This makes sense because in the end I want the
ingesters to generate the same common fields, while allowing individual
ingesters to capture metadata that we don't really know how to handle (yet).

The goal remains the same:

* Indexer to pull down the initial state of the files in the storage silo.
* Ingester to extract normalized common metadata from the storage system, while
  capturing _all_ of the metadata captured by the indexer.
* Natural Language query tool built from the GPT API and combined with the data
  schemas to generate GraphQL queries.

That is the primary goal at this stage.  Once I can get query results back I can
start looking at how to rank the returned information.  I can also measure
various performance costs, such as the time for initial ingestion, the amount of
storage used, and the CPU cycles used by the database.

General goals of portability seem to be working reasonably well, too, since I
have a linux indexer.  I expect, once the class library is done, the Linux
ingester will not be too difficult.

Having multiple storage silos indexed is important because one benefit of this
approach is that it can find "what I'm looking for" _regardless_ of where it
might be stored - an important point to help differentiate this work, since
that's not a capability of existing systems.

### 2024-01-22

I've been poking at the edges of searches now that I have a bunch of file
medatadata loaded into Arango.  While Arango allows for "full text" search, what
this means is that it will search against a list of words. File names, however,
are not nearly so neat as documents, where spaces and punctuation allow easy
tokenization of words.  Instead, we have to worry about files without spaces in
their names. After all, one of the points in the _Burrito_ paper is that people
embed metadata in file names. Indeed, I've often opined that this is a nice
demonstration of the failings of storage to permit this to be stored in a
cleaner fashion.  EAs were a great idea that's just never quite "caught on."

At any rate, let me capture a bit of what I've been learning about how searches
work in ArangoDB.

First, Arango relies upon _views_ for search.  This seems to be the "results of
a query" style output. The documentation says these views are "eventually
consistent" and that is fine for my purposes since the data sets isn't mutating
rapidly _and_ the place where Indaleko's indexing is most useful is for cold
data, not hot data.  This is an interesting observation since much of storage
focuses on efficiency for the "hot data."

Here's a simple example (from ChatGPT-4) showing how to create a view in a
python script:

```text
from arango import ArangoClient

# Initialize the ArangoDB client
client = ArangoClient(hosts='http://localhost:8529')

# Connect to "_system" database as root user
sys_db = client.db('_system', username='root', password='')

# Create a new ArangoSearch view
sys_db.create_arangosearch_view(
    name='fileSearchView',
    properties={
        'links': {
            'yourCollectionName': {
                'includeAllFields': False,
                'fields': {
                    'fileName': {
                        'analyzers': ['text_en']
                    }
                }
            }
        }
    }
)
```

Queries can then be made against that view:

```python
  # Connect to your database
  db = client.db('yourDatabaseName', username='root', password='')

  # Write an AQL query
  query = """
  FOR doc IN fileSearchView
      SEARCH doc.fileName == @fileName
      RETURN doc
  """

  # Bind parameters
  bind_vars = {'fileName': 'specificFileName'}

  # Execute the query
  result = db.aql.execute(query, bind_vars=bind_vars)

  # Print the results
  for doc in result:
      print(doc)
```

ArangoDB does allows us to have multiple views.
