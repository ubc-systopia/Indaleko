# Indaleko Windows Walk-through

Note: I started preparing this on March 27, 2024

The goal of this is to show how I set up the indexing on Windows.  This is not a
complete discussion of all the ways in which this could be done, but rather to
capture how **I** did it for my data-gathering work.

## Gather hardware data

The hardware data we gather includes sensitive information, so it **must** be
collected using an elevated privilege instance of PowerShell.  The script is
called `windows-hardware-info.ps1` and in order to execute this you must have
enabled power shell script execution.  This is **not** enabled by default.

Each time you run this script it will gather the current hardware information
and store it in a file in the `config` directory.

**Note:** the config directory data is excluded from the repository via the
`.gitignore` file.  This is because we do not want you to expose confidential
information in a public repository.  You can override this and if you change the
git configuration to point to a private repository, you can certainly change
this default behavior.

In the following figure I have changed to the directory where the Indaleko
project code is located:

![Windows Hardware
Gathering](./figures/windows-hardware-gathering-2024-03-27.png)

Note there is no output.  I see my file in the config directory:

![Windows Hardware Configuration
File](./figures/windows-hardware-config-2024-03-27.png)

This file contains a JSON object that describes interesting hardware information
about the local Windows system.  Because it captures the UUID of the Windows
machine, it is considered to be sensitive information.

I normally use a shell in WSL when examining the data files, because some of
them grow to be quite large and the version of `more` on my Windows system seems
to read the entire file before it displays any information.

![Windows Configuration Data
(Partial)](./figures/windows-hardware-config-data-partial-2024-03-27.png)

## Database Management

By default, the database software runs in a Docker container (other
configurations are possible and have been used, such as a native installation of
Docker and/or a remote/WAN installation, but for this walk-through I am using
the simplest model.)

The `IndalekoDBConfig.py` script can be used to perform some level of management
of the database:

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoDBConfig.py --help
usage: IndalekoDBConfig.py [-h] [--logdir LOGDIR] [--log LOG] [--loglevel LOGLEVEL] {check,setup,reset,update,show} ...

Indaleko DB Configuration Management.

positional arguments:
  {check,setup,reset,update,show}
    check               Check the database connection.
    setup               Set up the database.
    reset               Reset the database.
    update              Update the database.
    show                Show the database configuration.

options:
  -h, --help            show this help message and exit
  --logdir LOGDIR       Log directory
  --log LOG             Log file name
  --loglevel LOGLEVEL   Log level
PS C:\Users\TonyMason\source\repos\indaleko-test>
```

My general philosophy has been to do something I consider "reasonable" when you
run the script without arguments. In this case it will execute the `check`
operation.  This determines if the database is currently executing.  If it is
not, you will get an error message:

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoDBConfig.py
Checking database connection
Could not start DB connection.  Confirm the docker image is running.
PS C:\Users\TonyMason\source\repos\indaleko-test>
```

The `show` command is quite useful because it will show you the current
configuration being used to interact with the database:

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoDBConfig.py show
Config file found: loading
Created at 20240118170759
Container name: arango-indaleko-20240118170759
Volume name: indaleko-db-1-20240118170759
Host: localhost
Port: 8529
Admin user: root
Admin password: ****************
Database name: Indaleko
User name: uiRXxRxF
User password: ****************
PS C:\Users\TonyMason\source\repos\indaleko-test>
```

Note: the passwords have been omitted.  The "root" account can be used for
administrative purposes.  The "user" account is what the scripts use for
accessing the Indaleko database.  The goal was to encourage "best practices" by
using an account with an appropriate level of authorization ("least privilege").

In this case, because my database was not running, I used the "setup" command,
which will either create the database (if it does not exist) or start it using
the existing configuration (if it does exist):

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoDBConfig.py setup
Setting up new database configuration
Initialize Docker ArangoDB
Create container arango-indaleko-20240118170759with volume indaleko-db-1-20240118170759
Created container arango-indaleko-20240118170759with volume indaleko-db-1-20240118170759
Start container arango-indaleko-20240118170759
Connect to database
```

The database is now running.

In general, the scripts will log details about their activity.  The files are
written into the `logs` directory with metadata embedded in the file name. The
size of the log file collection can become quite large. `IndalekoLogging.py` can
be used to manage these log files.  There are three command (`list`, `cleanup`,
and `purge`).  List will show you files that were created using the
IndalekoLogging package.  Cleanup will _delete_ files that were created using
the IndalekoLogging package.  Purge will remove all but the _most recent_
instance of each class of log recognized by this package.

Thus, the `IndalekoDBConfig` package writes log information out each time it is
invoked.

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoLogging.py list
Welcome to Indaleko Logging Management
List logs
        indaleko-plt=Windows-svc=IndalekoDBConfig-ts=2024_03_27T19#09#04.779763+00#00.log
        indaleko-plt=Windows-svc=IndalekoLogging-ts=2024_03_27T19#09#40.080923+00#00.log
PS C:\Users\TonyMason\source\repos\indaleko-test>
```

Note that even listing will create a log file.

## Interacting with the database

Once the database is initialized and set-up, you can interact with it, either
via a web browser (using port 8529 by default) or with the other scripts.
ArangoDB exposes a REST API that is used by the scripts.

![ArangoDB Web Interface](./figures/arangodb-via-localhost-2024-03-27.png)

The output of the `show` command can be used to provide you with the credentials
needed to log in.  In this case I have used the `root` account.

Because I had just reset the database, there are no collections created.  The
scripts will create them, as needed, once I begin loading data into the
database.

The Web interface is useful for validating that the indexing service is loading
data, as expected.

## Indexing data

Note that Windows inherits a somewhat different naming system than found in
POSIX systems, even though Windows _internally_ has a name space that is similar
to POSIX.

The tool that I use for indexing Windows local file systems is called
`IndalekoWindowsLocalIndexer.py`.  An _indexer_ in Indaleko is a component that
knows how to walk some resource and capture its meta-data.  An Indexer _does
not_ perform data operations on the file - that is for other components to do.

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoWindowsLocalIndexer.py --help
Service id 3360a328-a6e9-41d7-8168-45518f85d73e not found.
Registering service Windows Machine Configuration with id 3360a328-a6e9-41d7-8168-45518f85d73e : {'Name': 'Windows Machine Configuration', 'Description': 'T
his service provides the configuration information for a Windows machine.', 'Version': '1.0', 'Identifier': '3360a328-a6e9-41d7-8168-45518f85d73e', 'Type':
'Machine Configuration', 'Created': '2024-03-27T19:19:21.685125+00:00', 'Record': {'Data': '', 'Attributes': {}, 'Source Identifier': {'Identifier': '951724
c8-9957-4455-8132-d786b7383b47', 'Version': '1.0'}, 'Timestamp': '2024-03-27T19:19:21.685125+00:00'}, '_key': '3360a328-a6e9-41d7-8168-45518f85d73e'}.
Service id 0793b4d5-e549-4cb6-8177-020a738b66b7 not found.
Registering service Windows Local Indexer with id 0793b4d5-e549-4cb6-8177-020a738b66b7 : {'Name': 'Windows Local Indexer', 'Description': 'This service inde
xes the local filesystems of a Windows machine.', 'Version': '1.0', 'Identifier': '0793b4d5-e549-4cb6-8177-020a738b66b7', 'Type': 'Indexer', 'Created': '202
4-03-27T19:19:23.323662+00:00', 'Record': {'Data': '', 'Attributes': {}, 'Source Identifier': {'Identifier': '951724c8-9957-4455-8132-d786b7383b47', 'Versio
n': '1.0'}, 'Timestamp': '2024-03-27T19:19:23.323662+00:00'}, '_key': '0793b4d5-e549-4cb6-8177-020a738b66b7'}.
usage: IndalekoWindowsLocalIndexer.py [-h] [--configdir CONFIGDIR]
                                      [--config {windows-hardware-info-2e169bb7-0024-4dc1-93dc-18b7d2d28190-2024-03-27T18-42-58.3043468Z.json}]
                                      [--path PATH] [--datadir DATADIR] [--output OUTPUT] [--logdir LOGDIR] [--loglevel LOGLEVEL]

options:
  -h, --help            show this help message and exit
  --configdir CONFIGDIR
                        Path to the config directory
  --config {windows-hardware-info-2e169bb7-0024-4dc1-93dc-18b7d2d28190-2024-03-27T18-42-58.3043468Z.json}
  --path PATH           Path to the directory to index
  --datadir DATADIR, -d DATADIR
                        Path to the data directory
  --output OUTPUT, -o OUTPUT
                        name to assign to output directory
  --logdir LOGDIR, -l LOGDIR
                        Path to the log directory
  --loglevel LOGLEVEL   Logging level to use (lower number = more logging)
PS C:\Users\TonyMason\source\repos\indaleko-test>
```
Note that because this was the first time I had run this utility after resetting
the database, it didn't find any information in the index.  It found the machine
configuration file, parsed it, and added it to the the database.  Whereas I had
no collections _before_ running this command, _after_ running this command -
even if it was only to print out help information - it has created the necessary
files for Indaleko.

I ran it a second time and now I don't see the extra messages about how it set
things up:

```ps
PS C:\Users\TonyMason\source\repos\indaleko-test> py .\IndalekoWindowsLocalIndexer.py --help
usage: IndalekoWindowsLocalIndexer.py [-h] [--configdir CONFIGDIR]
                                      [--config {windows-hardware-info-2e169bb7-0024-4dc1-93dc-18b7d2d28190-2024-03-27T18-42-58.3043468Z.json}]
                                      [--path PATH] [--datadir DATADIR] [--output OUTPUT] [--logdir LOGDIR] [--loglevel LOGLEVEL]

options:
  -h, --help            show this help message and exit
  --configdir CONFIGDIR
                        Path to the config directory
  --config {windows-hardware-info-2e169bb7-0024-4dc1-93dc-18b7d2d28190-2024-03-27T18-42-58.3043468Z.json}
  --path PATH           Path to the directory to index
  --datadir DATADIR, -d DATADIR
                        Path to the data directory
  --output OUTPUT, -o OUTPUT
                        name to assign to output directory
  --logdir LOGDIR, -l LOGDIR
                        Path to the log directory
  --loglevel LOGLEVEL   Logging level to use (lower number = more logging)
```

By default, the indexer will use the most recent hardware configuration file (as
shown in the help command) and it will index the default path (the home
directory).  Since I want to index everything on various drives, I will invoke
this with an explicit path.

**Note:** if you do this in a normal user account, files that cannot be accessed
due to access controls _will not be indexed_.  In general, we consider this to
be acceptable **because** this is _personal_ index.  If I can't access it, then
I don't care about it.

Note that the _name_ you pass in should be a full path name.  If you use just a
drive letter, then indexing will be done relative to the current working
directory on that drive.  Each time you run this, it will generate a file with
the indexing data.  That file will include timestamp information, so that you do
not lose prior data.

**The indexer does not write any of the indexed metadata to the database**.

Indexing is a time-consuming task. It can be parallelized (e.g., you can index
multiple different paths at the same time.)  I don't recommend indexing
overlapping paths, as there is no benefit to this and it is not a scenario that
I've been testing (e.g., it probably will produce unexpected results.)

Note: the output files are only written at the end of a run currently.  These
files typically take 10-30 minutes to generate depending upon the size of your
storage and the resources of your computer.  The log file should show the amount
of time required.

I had four different drives that are accessible to my Windows system; I indexed
all four.  Here is the listing of them in the data directory:

```bash
tony@WAM-THREADRIPPER:/mnt/c/Users/TonyMason/source/repos/indaleko-test/data$ ls -l *.jsonl
-rwxrwxrwx 1 tony tony 4884885224 Mar 27 14:11 'indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=3397d97b2ca511edb2fcb40ede9a5a3c-ts=2024_03_27T19#30#34.045736+00#00.jsonl'
-rwxrwxrwx 1 tony tony 5167085961 Mar 27 13:26 'indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=414e9e8f06884c299b89b5c7064c96ae-ts=2024_03_27T19#31#38.752428+00#00.jsonl'
-rwxrwxrwx 1 tony tony 1521521859 Mar 27 12:35 'indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=c05da552927a4f6f9fdb8347598b3cd4-ts=2024_03_27T19#27#01.222096+00#00.jsonl'
-rwxrwxrwx 1 tony tony 4066285829 Mar 27 13:06 'indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=e069ddd951ad400cbccdd5433aed7ea7-ts=2024_03_27T19#31#00.451120+00#00.jsonl'
```

As you can see, the file names are structured.  For Windows, the index includes
the GUID of the machine and the GUID of the device, along with the time when the
index request was initiated.

These files are in the _JSON lines_ format (jsonl).  In addition, the log files
contain detailed information about what the script did in generating its output.
Here are the last 12 lines from the four log files that were generated:

```bash
tony@WAM-THREADRIPPER:/mnt/c/Users/TonyMason/source/repos/indaleko-test/logs$ tail --lines=12 *indexer*.jsonl
==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#27#02.841526+00#00.jsonl <==
2024-03-27 12:35:03,925 - INFO - Wrote jsonlines file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=c05da552927a4f6f9fdb8347598b3cd4-ts=2024_03_27T19#27#01.222096+00#00.jsonl.
2024-03-27 12:35:03,925 - INFO - output_count: 1585159
2024-03-27 12:35:03,925 - INFO - dir_count: 225521
2024-03-27 12:35:03,925 - INFO - file_count: 1359638
2024-03-27 12:35:03,925 - INFO - special_count: 0
2024-03-27 12:35:03,925 - INFO - error_count: 0
2024-03-27 12:35:03,925 - INFO - access_error_count: 0
2024-03-27 12:35:03,925 - INFO - encoding_count: 0
2024-03-27 12:35:03,926 - INFO - not_found_count: 8
2024-03-27 12:35:03,926 - INFO - good_symlink_count: 70
2024-03-27 12:35:03,926 - INFO - bad_symlink_count: 0
2024-03-27 12:35:03,926 - INFO - Done

==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#30#35.641806+00#00.jsonl <==
2024-03-27 14:11:24,923 - INFO - Wrote jsonlines file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=3397d97b2ca511edb2fcb40ede9a5a3c-ts=2024_03_27T19#30#34.045736+00#00.jsonl.
2024-03-27 14:11:24,923 - INFO - output_count: 5125171
2024-03-27 14:11:24,923 - INFO - dir_count: 414322
2024-03-27 14:11:24,923 - INFO - file_count: 4710849
2024-03-27 14:11:24,923 - INFO - special_count: 0
2024-03-27 14:11:24,923 - INFO - error_count: 0
2024-03-27 14:11:24,923 - INFO - access_error_count: 0
2024-03-27 14:11:24,923 - INFO - encoding_count: 0
2024-03-27 14:11:24,923 - INFO - not_found_count: 47
2024-03-27 14:11:24,923 - INFO - good_symlink_count: 0
2024-03-27 14:11:24,923 - INFO - bad_symlink_count: 0
2024-03-27 14:11:24,924 - INFO - Done

==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#31#02.061756+00#00.jsonl <==
2024-03-27 13:06:05,042 - INFO - Wrote jsonlines file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=e069ddd951ad400cbccdd5433aed7ea7-ts=2024_03_27T19#31#00.451120+00#00.jsonl.
2024-03-27 13:06:05,042 - INFO - output_count: 3878235
2024-03-27 13:06:05,042 - INFO - dir_count: 488276
2024-03-27 13:06:05,042 - INFO - file_count: 3389959
2024-03-27 13:06:05,042 - INFO - special_count: 0
2024-03-27 13:06:05,042 - INFO - error_count: 0
2024-03-27 13:06:05,042 - INFO - access_error_count: 0
2024-03-27 13:06:05,042 - INFO - encoding_count: 0
2024-03-27 13:06:05,042 - INFO - not_found_count: 54
2024-03-27 13:06:05,042 - INFO - good_symlink_count: 0
2024-03-27 13:06:05,042 - INFO - bad_symlink_count: 0
2024-03-27 13:06:05,042 - INFO - Done

==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#31#40.531098+00#00.jsonl <==
2024-03-27 13:26:07,263 - INFO - Wrote jsonlines file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=414e9e8f06884c299b89b5c7064c96ae-ts=2024_03_27T19#31#38.752428+00#00.jsonl.
2024-03-27 13:26:07,263 - INFO - output_count: 5184871
2024-03-27 13:26:07,263 - INFO - dir_count: 687902
2024-03-27 13:26:07,263 - INFO - file_count: 4496969
2024-03-27 13:26:07,263 - INFO - special_count: 0
2024-03-27 13:26:07,264 - INFO - error_count: 0
2024-03-27 13:26:07,264 - INFO - access_error_count: 0
2024-03-27 13:26:07,264 - INFO - encoding_count: 0
2024-03-27 13:26:07,264 - INFO - not_found_count: 37
2024-03-27 13:26:07,264 - INFO - good_symlink_count: 168
2024-03-27 13:26:07,264 - INFO - bad_symlink_count: 0
2024-03-27 13:26:07,264 - INFO - Done
```

The time can be computed by taking the timestamps in the log file.

```bash
tony@WAM-THREADRIPPER:/mnt/c/Users/TonyMason/source/repos/indaleko-test/logs$ head --lines 2 *.jsonl
==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#27#02.841526+00#00.jsonl <==
2024-03-27 12:27:02,842 - INFO - Indexing C:\
2024-03-27 12:27:02,842 - INFO - Output file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=c05da552927a4f6f9fdb8347598b3cd4-ts=2024_03_27T19#27#01.222096+00#00.jsonl

==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#30#35.641806+00#00.jsonl <==
2024-03-27 12:30:35,642 - INFO - Indexing D:\
2024-03-27 12:30:35,642 - INFO - Output file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=3397d97b2ca511edb2fcb40ede9a5a3c-ts=2024_03_27T19#30#34.045736+00#00.jsonl

==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#31#02.061756+00#00.jsonl <==
2024-03-27 12:31:02,061 - INFO - Indexing E:\
2024-03-27 12:31:02,062 - INFO - Output file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=e069ddd951ad400cbccdd5433aed7ea7-ts=2024_03_27T19#31#00.451120+00#00.jsonl

==> indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-ts=2024_03_27T19#31#40.531098+00#00.jsonl <==
2024-03-27 12:31:40,531 - INFO - Indexing F:\
2024-03-27 12:31:40,532 - INFO - Output file ./data\indaleko-plt=Windows-svc=fs_indexer-machine=2e169bb700244dc193dc18b7d2d28190-storage=414e9e8f06884c299b89b5c7064c96ae-ts=2024_03_27T19#31#38.752428+00#00.jsonl
```

The data in the log files can be useful in verifying that the scripts are
working as expected.

## Ingesting

Index files are interesting, but do not represent any data in the database
itself.  Index files capture raw information from the storage system.  They do
not know about the database, normalization, etc.  There is a minimal set of
requirements for an indexer:

* It must provide a URI that can be used to find the object (file/directory):
  note, that if the URI is machine specific, the indexer needs to capture
  machine information.  For user devices, this is typically a UUID that
  identifies the device.
* It must have a length
* It provides a UUID that uniquely identifies this specific object instance

Beyond that, it can have additional metadata:
* A label ("file name")
* One or more timestamps
* Ownership data
* Additional optional metadata (e.g., extended attributes)

An _ingester_ is written to take specific indexer output and extract useful
information from it, which is then inserted into the database. Each indexer
**must** have at least one ingester.

An ingester takes index information, extracts important metadata, normalizes
that metadata, and then either _inserts_ or _updates_ an entry in the database.

Typically, we build one matching ingester that knows how to take the baseline
metadata generated by the indexer and extract the metadata that is typical for
storage services.  However, that ingester (or a secondary ingester) can also do
further analysis of these index files.  This includes:

* Compute checksums
* Extract semantic content (we've been using
  [Unstructured](https://unstructured.io/) for semantic content extraction.)
* Compute file type information (MIME types, for example)
* Extract recognizable metadata (e.g., EXIF data for images.)

This list is _demonstrative_ and is not intended as being definitive.  Go to
[Hugging Face](https://huggingface.co) and look at the classifiers there.  Many
of these could be turned into specialized ingesters.





