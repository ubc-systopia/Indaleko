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
