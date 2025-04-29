# Project Indaleko

## Recent Changes

April 15, 2025

Added Fire Circle integration to implement specialized entity roles for collaborative AI analysis. The Fire Circle framework provides a standardized approach to integrating diverse AI perspectives into query analysis and knowledge pattern discovery.

Key features of the Fire Circle implementation:
- Four specialized entity roles - Storyteller, Analyst, Critic, and Synthesizer
- Adapter layer for different AI models (OpenAI, Anthropic)
- Integration with Archivist's knowledge base system
- CLI commands for multi-perspective analysis
- Pattern analysis with different viewpoints

You can enable Fire Circle features with the `--fc` flag when running the CLI.

October 18, 2024

There have been some changes around terminology, and I suspect this will lead to a consolidation around this new terminology.

In general, data gathering pipelines are divided into one component that gathers the information, a _collector_, and a second component that translates the gathered information into a normalized form that can then be inserted into the database, a _recorder_.

For example, the "indexer" for the file system metadata is logically a "collector" of the information, while the ingester is logically a _recorder_.  Sometimes these stages are combined, sometimes they are further subdivided.  For example, in the case of the local file system ingesters ("recorders") they often emit data into a file for bulk uploading.

Some of this is now reflected in the naming system (notably in the _activity_ area of the project.)

I have also removed `requirements.txt` from the project.  There is a `pyproject.toml` file instead, which captures dependencies.  I added a `setup_env.py` script as well.

The `setup_env.py` script will set up a virtual environment for you.  It will restrict you to using Python 3.12 or newer for the project, and it will download and install the "uv" utility for managing dependencies and configuring a virtual environment. Since this is new, it may not work properly in other environments.  Please let me know and I'll work with you to get it working.  So far, I've tested it on Windows and Linux.

## Introduction

Project Indaleko is about creating a _Unified Personal Index_.  The key
characteristics of the UPI model is:

* Indexing storage in a uniform fashion, regardless of _where_ or _what_ is
  being stored.  Primarily, this means that we collect information and normalize
  it for local and cloud storage devices.

* Utilizing semantic transducers to obtain information about content.  The term
  "semantic transducer" is one introduced by Gifford in the Semantic File System
  project (SFS) in the early 1990s but remains an important concept that is used
  today for indexing systems.

* Collects and associates extrinsic information about how storage objects are
  used.  We call this extrinsic information "activity context" because it
  relates to other activities that are ongoing but correlate with storage.  For
  example, the location of the computer (and hence user) when a file is created,
  the weather conditions, websites being visited contemporaneously with file
  access and/or creation, the mood of a human user creating content, and
  interactions between human users (e.g., files you accessed while you were
  interacting with another user.)

The goal of this research artifact is to demonstrate that having a unified
private index with rich semantic and activity data provides a robust base on
which to build "personal archiving tools" that enabling easier finding of
relevant information.

## Architecture

Indaleko is designed around a modular architecture.  The goals of this
architecture are to break down processing into discrete components, both for
ease of implementation as well as flexibility in supporting a variety of
devices, storage platforms, and semantic transducers.

![Indaleko Architecture](./figures/arch-diagram-solid-small.png)

Logically, the project is broken down into various components:

* A **Collector** is a component that collects useful metadata that may relate
  to storage.  The most obvious example of this is storage objects of interest.
  For example, we have collectors that look through a collection
  of local storage devices and collect basic storage information about the
  various objects stored by the storage device.  There is _no
  requirement_ that the data captured be in any particular format.  A motivation
  for this is that we have found different systems return different information,
  there are subtle distinctions in how the information is represented, and while
  there is commonality amongst the metadata, there are sufficient differences
  that building a universal indexer is a complex task.  That "complex task" is,
  ultimately, one that Indaleko provides at some level.  In our current
  implementation, collectors do not interact (or minimally interact) with the
  indexer database.

* A **Recorder** is a component that processes collector output. There is a
  many-to-one relationship between collectors and recorders.  In our model
  "recording" is the act of taking data from a collector and then extracting
  useful metadata that is recorded in the index.  While
  it might seem logical to combine the collector and recorder together - something
  we did in earlier versions - we choose to split them for similar reasons that
  we have distinct collectors.  By separating them, we allow specialized recorders
  that can process a given collector's output in a specific way.  For example,
  there is generally a collector specific recorder that understands how to
  normalize the metadata captured by the collector and then store that in the
  database.  This allows us to use a common normalized model, with the recorder
  being responsible for converting the data into that normalized form.
  Recorders can also provide additional metadata.  For example, a recorder could run
  one or more _semantic transducers_, elements that extract information _about
  the contents of the file._ Examples might include:
  * A machine learning based classifier that only processes videos and adds
    metadata to the index that identifies videos containing cats.
  * An EXIF data extractor, that only processes image files with embedded EXIF
    data.
  * A checksum calculator, that computes a family of common checksums for a
    given file. This can be useful for doing cross-storage device similarity
    analysis.  Some storage engines do not provide checksums, while others do.
    Even for those that do they may use a variety of different forms.  By having
    a collection of such checksums calculated for a file it becomes possible to
    identify duplicate files across dissimilar storage locations.

  Note that in each of these cases, the benefits of using a semantic transducer
  are primarily due to the proximity of the file data on the specific device.
  Once the data has been removed from the local device, such as in the case of
  cloud storage, it becomes resource intensive to fetch the files and extract
  additional metadata.
* The Indexer database.  This is the _Unified Personal Index_ service.  While we
  have chosen to implement it using [ArangoDB](https://www.arangodb.com,) it
  could be implemented on other database technologies, whether in tandem or as a
  replacement.
* The activity context components.  The concept of _Activity Context_ is related
  to the observation that human activities are entwined with human use of
  storage.  At the present time, storage engines do not associate related human
  activity with storage objects.  Associating human activity with storage
  objects and storage activity is one of the key goals of Indaleko.  The
  _activity context_ aspects of Indaleko break down into multiple components:
  * An _Activity Context Service_, which can be used to obtain a handle to the
    current activity state of the system. Thus, any other component can request
    a current activity context and then associate that activity context with the
    storage object.  It is also possible for this to be done after the fact by
    asking for an activity context handle relative to a given point in time.
    Thus, for example, a recorder could query for a time-relative activity
    context handle to associate with the storage event at a later time than the
    actual event.  Of course, there may not be any such context available, such
    as if the file pre-dates the activity context.
  * An _Activity Data Provider_, which is a component that provides data to the
    Activity Context Service.  These are decoupled to allow flexibility in
    capturing activity data.  Our goal is to allow these to be easily
    constructed so that we can easily test out the benefits of having various
    types of activity information.  Examples of activity data include:
    * The location of the device (and thus, by inference, the _user_ of that
      device.)
    * The ambient conditions in which the device (and again, by inference the
      _user_ of that device,) is located.
    * Computer state at a given point in time.  This might include the running
      application(s), the network connections active, etc.
    * Interactions between the user and other people.  For example, this could
      be inferred via the user's calendar, or the communications mechanisms they
      employ, such as e-mail communications, chats on commonly used services
      such as Slack, Teams, Discord, WhatsApp, etc.
    * Storage events, such as file creation, access.
    * Web usage, such as websites visited.
    * Music being played by the device.
    * The mood of the user (there's been a fair bit of work in this area.  Here
      is a [Medium
      Article](https://medium.com/analytics-vidhya/building-a-real-time-emotion-detector-towards-machine-with-e-q-c20b17f89220)
      that describes how to do this, for example.)
    * Etc.

    Indaleko does not define _what_ that activity data is, but rather provides a
    framework for capturing it and utilizing it to find human-related
    associations with storage objects.  While we know that such data is useful
    in augmenting persona data search (see [Searching Heterogeneous Personal
    Data](https://rucore.libraries.rutgers.edu/rutgers-lib/61974/PDF/1/play/)
    for example.) we do not know what the full range of such data that could be
    useful is.  Thus, this model encourages the development and evaluation of
    such activity data source providers.

## Design

The current project design is focused around evaluating the practicality and
efficacy of whether or not we can improve "finding" of relevant digital data in
a systematic fashion that works across user devices in a dynamic storage
environment that mixes local devices with cloud storage _and_ application
quasi-storage.  The architecture reflects much on the design philosophy of
modular components, with easy extensibility.

## Implementation

The current implementation consists primarily of a collection of Python scripts
that interact with an Arango database.  While in prior work we used a mixture of
languages, we chose Python for the current iteration because it provided a
robust model for constructing our prototype.

### Class model

The implementation is organized around a set of classes. As the project has evoloved,
we have increasingly relied upon the [pydantic](https://docs.pydantic.dev/latest/)
library.  Part of the motivation for this was to ease integration with LLMs, where
recent changes have allowed for "structured output" and those APIs use pydantic
(at least for Python).

The fundamental class associated with information stored in the database is the
[Record](data_modes/record.py) class, which defines a small amount of information
that should be present in everything we store in the database, which includes
original captured data (the "raw data,") attributes extracted directly or
indirectly (the "attributes,") the _source_ of the information (a UUID
identifier and a version number,) and a timestamp of when the relevant
information was captured. **Note:** we are moving away from the model of
having attributes in the record.  This helps us avoid the LLM models from
using those fields (since they are not normalized or indexed, searching
them is slow.)

The project has been substantially reorganized in the latter part of 2024,
using a hierarchical decomposition that is organized around logical functionality.
The key components are:

* **activity** - this is where the "activity context" support is maintained, which
  includes the logic for generating and using activity context as well as several
  examples of activity context data collectors and recorders.  This has been
  designed to be extensible.  When building a new activity data collector it
  is important to provide descriptions of the semantic meaning of collected
  metadata, as this allows the LLM-based search tools to "understand" the
  meaning of normalized metadata fields.

* **data_models** - this is where key (system wide) data models are stored.

* **db** - this is where the logic around managing the database resides.

* **platforms** - this is where platform-specific configuration data is collected,
  recorded, and managed.

* **query** - this is where the query support library is located. This depends on
  the main services of the index, but is logically "on top" of them.  Note that
  the current query model is using LLMs to take natural language queries and
  convert them into actionable database queries.  The query operations themselves
  do form activity data, however, since there is insight to be gained by
  understanding previous queries.

* **semantic** - this is where the semantic collector/recorder support exists.
  While semantic extraction is not really a core part of the research, the
  index itself needs to have that data as part of what it uses in query resolution.

* **storage** - this is where the storage collector/recorder support exists. This
  includes local storage for Windows, Mac, and Linux, as well as several cloud storage
  services.

This prototype system is still under active development.  It would be surprising
if it does not continue to change as the project moves forward.

Last Updated: January 6, 2025

## How to use Indaleko?

In this section, we'll talk about how to set up your system to use Indaleko.
The process is a combination of manual and automated steps.

### Install Pre-requisites

Things you should have installed:

* **Docker** this is needed because we use ArangoDB and run it in a
  containerized environment.  The _data_ is stored on the local host system.
  While it is possible to configure this to use a remote database, that step is
  not presently automated.

* **Python** this is needed to run the Indaleko scripts.  Note there are a
  number of libraries that need to be installed.  There is a `requirements.txt`
  file that captures the current configuration that we have been using, though
  it may work with other versions of the various libraries.  It is distinctly
  possible we've added some dependency and failed to capture it in the
  requirements.txt file, in which case, please open an issue and/or a pull
  request.

* **Powershell** _this is Windows Only_.  There is a powershell script that
  gathers configuration information about your Windows machine.  It requires
  elevation ("administrative privileges") and you must enable running powershell
  scripts (which is disabled by default.)  The script writes data into the
  `config` directory, where it is then parsed and extracted by the setup
  scripts.

* **ArangoDB Client Tools** In order to upload the files into Arango, you need
  to install the ArangoDB client tools on your system.  There are versions for
  Windows, MacOS X, and Linux.  **Note:** you should _not_ run the ArangoDB
  database locally.  Keep it in the container to minimize compatibility issues.
  This may require manually disabling it (this was required on Windows, for
  example.)

Note: there is a script that will set up the python environment: [setup_env.py](utils/setup_env.py).

**The setup utility for the python environment will ensure you have all the
required packages installed.  It also creates a virtual environment that you should
use.  To do so:

* **Linux** - use the command `source` with the virtual environment settings.
  By default the virtual environment is stored in a directory that begins
  with the `.venv` prefix.  For example, on one of the development machines
  it is `.venv-linux-python3.12`. Using that as the example name the following
  command will activate the virtual environment:

  ```sh
  source .venv-linux-python3.12/bin/activate
  ```

  You will need to do this before using most of the scripts, as they depend
  upon having access to the necessary libraries downloaded by the setup tool.

* **Mac** use the command `source` with the virtual environment settings.
  By default the virtual environment is stored in a directory that begins
  with the `.venv` prefix.  For example, on one of the development machines
  it is `.venv-mac-python3.13`. Using that as the example name the following
  command will activate the virtual environment:

  ```sh
  source .venv-darwin-python3.13/bin/activate
  ```

* **Windows** - execute the command "activate" with the virtual environment settings.
  By default the virtual environment is stored in a directory that begins
  with the `.venv` prefix.  For example, on one of the development machines
  it is `.venv-win32-python3.12/Scripts/activate`.  Using that as the example
  name the following  command will activate the virtual environment:

  ```sh
  .\\venv-win32-python3.12\\Scripts\activate
  ```

**Only Python 3.12 and more recent have been actively used for this project.


The following tools need to be installed manually at the present time:

* **Docker** - setup and installation of this is platform dependent.  The scripts
  in this repository will interact with docker, but do not install it.

* **Powershell** - needed on Windows (for a single machine configuration script.)

* **ArangoDB Client Tools** - the installation varies by platform.

### Set up the database

The simplest way to set up the database is to use the [dbsetup.py](db/db_setup.py) script.  It
currently supports three commands:

* check - this will verify that the database is up and running. If not, you will
  need to try and figure out what is not working. Note that this will attempt to
  start the docker container version of the database if needed.
* setup - this will set up a _new_ instance of the database (using docker). Note that if you
  already have an instance set up, it will not overwrite it - it just runs a
  check for you.
* delete - this will delete your _existing_ instance of the database. You can
  then run the script again to create a new instance.

Note that if you run the script without arguments it will choose to either check
your existing database (if it exists) or set one up (if it does not.)

As part of configuration, the script generates a config file that is stored in
the `config` directory.  **Note that this file is a sensitive
file and will not be checked into git by default (it is in `.gitignore`).  If
you lose this file, you will need to change your container to use a new
(correct) password. Your data is not encrypted at rest by the database.

This script will pull the most recent version of the ArangoDB docker image,
provision a shared volume for storing the database, create a random password for
the root account, _which is stored in the config file_. It also creates an
Indaleko account, with a separate password that only has access to the Indaleko
database.  It will create the various collections used by Indaleko, including
the various schema. Most scripts only run using the Indaleko account.

To look at the various options for this script, you can use the `--help`
command.  By default this script tries to "do the right thing" when you first
invoke it (part of our philosophy of making the tool easiest to use for new
users.)

You can confirm the database is set up and running by accessing your
[ArangoDB](http://localhost:8529) local database connection.  You can extract
the password from the `indaleko-db-config.ini` file, which is located in the
`config` directory by default.  **Do not** distribute this file.  It contains
passwords for your database.

Note: database management functionality is in [db_config.py](db/db_config.py).

```shell
usage: db_config.py [-h] [--logdir LOGDIR] [--log LOG] [--loglevel {CRITICAL,DEBUG,ERROR,FATAL,INFO,NOTSET,WARN,WARNING}] {check,setup,reset,update,show} ...

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
  --loglevel {CRITICAL,DEBUG,ERROR,FATAL,INFO,NOTSET,WARN,WARNING}
                        Log level
```

Note that the **setup** command here does not set up docker - it will connect to the local
arangoDB instance, but it does not create one if it does not already exist.

The **reset** command will delete all database content.  It is used to reset the system when
there are database schema changes (for example).

At some point, we hope to combine [db_setup.py](db/db_setup.py) with [db_config](db/db_config.py)
but it has not been a high priority task.

### Set up your machine configuration

Note that there are currently three platforms we are supporting:

* Windows - this has been used on Windows 11.
* MacOS X - this has been used on MacOS X
* Linux - this has been used on Ubuntu 22.04 and 24.04

The following sections will describe how to configure the various systems.

To install your machine configuration, you should run the correct configuration
script for your system.

* **Linux** - the script you should run is [machine_config.py](platforms/linux/machine_config.py).

  ```sh
  usage: machine_config.py [-h] [--log LOG] [--configdir CONFIGDIR] [--timestamp TIMESTAMP] {capture,add,list,delete} ...

  Indaleko Linux Machine Config

  positional arguments:
    {capture,add,list,delete}
      capture             Capture machine configuration
      add                 Add a machine config
      list                List machine configs
      delete              Delete a machine config

  options:
    -h, --help            show this help message and exit
    --log LOG             Log file name to use
    --configdir CONFIGDIR
                          Configuration directory to use
    --timestamp TIMESTAMP
                          Timestamp to use
  ```

* **Mac** - the scripts you should run are [machine_config.py](platforms/mac/machine_config.py) and
  [MacHardwareInfoGenerator.py](platforms/mac/MacHardwareInfoGenerator.py).  The latter generates
  the platform specific information, the former processes that platform specific information.

  For MacHardwareInfoGenerator:
  ```
  usage: python MacHardwareInfoGenerator.py --dir save_at_path

  options:
    -h, --help            show this help message and exit
    --save-to-dir SAVE_TO_DIR, -d SAVE_TO_DIR
                          path to the directory we want to save the directory (default=C:\Users\TonyMason\source\repos\indaleko\config)
  ```

  For machine_config:

  ```sh
  usage: machine_config.py [-h] [--version] [--delete] [--uuid UUID] [--list] [--files] [--add]

  options:
    -h, --help            show this help message and exit
    --version             show program version number and exit
    --delete, -d          Delete the machine configuration if it exists in the database.
    --uuid UUID, -u UUID  The UUID of the machine.
    --list, -l            List the machine configurations in the database.
    --files, -f           List the machine configuration files in the default directory.
    --add, -a             Add a machine configuration (from the file) to the database.
  ```

* **Windows** - the script you should run is [machine_config.py](platforms/windows/machine_config.py).
  ```sh
  usage: machine_config.py [-h] [--version] [--delete] [--uuid UUID] [--list] [--files] [--add] [--capture]

  options:
    -h, --help            show this help message and exit
    --version             show programs version number and exit
    --delete, -d          Delete the machine configuration if it exists in the database.
    --uuid UUID, -u UUID  The UUID of the machine.
    --list, -l            List the machine configurations in the database.
    --files, -f           List the machine configuration files in the default directory.
    --add, -a             Add a machine configuration (from the file) to the database.
    --capture, -c         Capture the current machine configuration.
  ```

  Note that Windows machine configuration depends upon an external powerscript shell.  Because it
  retrieves sensitive information (the UUID assigned to your machine) it must be run with admin
  privileges and thus if you use the capture option it will require "elevation" permission. This
  is **not** required for the other operations.

Machine configuration information is likely to change.  Currently we are
capturing:

* A name for the machine.
* An ID (typically a UUID) assigned by the OS to the machine.  This means it is
  really related to the _installation_ and not necessarily the hardware.
* Local storage devices, including naming information (e.g., "mount points"
  which for UNIX based systems are usually relative to a root namespace, while
  Windows allows for UNIX style mount points and/or distinct drive letters.)
  The idea is to capture information that allows us to identify the _hardware_
  since being able to find information is difficult if the hardware is portable
  (e.g, portable USB storage) or if the "mount point" changes (removable storage
  again, but also re-installation of an OS, or even mounting of an old storage
  device onto a new system.)
* Other information of interest, such as CPU information, memory information,
  network device information.

For the moment we aren't requiring any of this.  When we have volume
information, we associate it with the file via a UUID for the volume.  Note:
Windows calls them GUIDs ("Globally Unique Identifiers") but they are UUIDs
("Universally Unique Identifiers").

To add the machine configuration to the database you can run the correct script
on your machine.  Some machines may require a pre-requisite step, though we
continue to try and make this process simple.

Assuming any pre-requisite script has been run, you can load the configuration
data into the database something like the following:

  ```sh
  python3 machine_config.py --add
  ```

**Note**: use the **correct** script for your platform.  There is some support
for importing "foreign" machine configurations but that has not been extensively
tested.

#### Windows

There are multiple steps required to set up Indaleko on your Windows machine.
Assuming you have installed the database, you should be able to index and ingest
the data on your local machine.

##### Capture System Configuration

**Note**: the [machine_config.py](platforms/windows/machine_config.py) script has
been updated so you can have it run the powershell script.  That script cannot
enable running powershell scripts directly, however, so you still need to enable
running powershell scripts.  There are many resources
available for explaining this.  Here is a video [3 easy ways to run Windows
Powershell as admin on Windows 10 and
11](https://www.youtube.com/watch?v=3IKQ0PwIAdo) but it's certainly not the only
resource.

**Note:** the output is written into the `config` directory, which is **not
saved** to git (the entire directory is excluded in `.gitignore`).  While you
can override this, this is **not recommended** due to the sensitive information
captured by this script.

Once you have captured your configuration information, you can run the Python script
[machine_config.py](platforms/windows/machine_config.py).  This script will locate
and parse the file that was saved by the Powershell script and insert it into the database.

The script has various override options, but aims to "do the right thing" if you
run it without arguments.  To see the arguments, you can use the `--help` option.

##### Index Your Storage

Once your machine configuration has been saved, you can begin creating data
index files.  This is done by executing the Python script for your platform:

* **Linux** - [collector.py](storage/collectors/local/linux/collector.py)

* **Mac** - [collector.py](storage/collectors/local/mac/collector.py)

* **Windows** - [collector.py](storage/collectors/local/windows/collector.py0)

By default, this will index your home directory, which is usually something like
`C:\Users\TonyMason` (Windows), `/Users/tonymason`, or `/home/tony`.
If you want to override this you can use the `--path` option.  You can see all
of the override options by using the `--help` command.


This script will write the output index file to the `data` directory. Note that
this directory is **excluded from checkin to git** by default as it is listed in
the `.gitignore` file.  Logs (if any) will be (by default) written to the 'logs'
directory.

Without any options given, it will write the file with a structured name that
includes the platform, machine id, volume id (if available), and the timestamp of when the data
was captured.

The index data can be used in subsequent steps.

##### Process Your Storage Indexing

A _recorder_ is an agent that takes the metadata you have previously
captured and then performs additional analysis on it.  This is the step that
loads data into the database.

Local recorders are all implemented by scripts called `recorder.py`:

* Linux - [recorder.py](storage/recorders/local/linux/recorder.py)

* Mac - [recorder.py](storage/recorders/local/mac/recorder.py)

* Windows - [recorder.py](storage/recorders/local/mac/recorder.py)

For cloud services the naming is currently a bit different:

* Dropbox - [dropbox.py](storage/recorders/cloud/dropbox.py)

* Google Drive - [gdrive.py](storage/recorders/cloud/gdrive.py)

* iCloud - [icloud.py](storage/recorders/cloud/icloud.py)

* OneDrive - [onedrive.py](storage/recorders/cloud/onedrive.py)

These utilities have a common command line interface and you can
check their parameters using the `--help` operation.

By default, it will take one of the data files (ideally the most recent) and
ingest it.  The _output_ of this is a set of files that can be manually loaded
into the database. The files generated have long names, but those names capture
information about the ingested data.  Note that the timestamp of the output file
will match the timestamp of the index file unless you override it.

While the recorder script does write a small amount of data to the database, it
is writing to intermediate files in order to allow bulk uploading.  The bulk
uploader requires the `arangoimport` tool, which was installed with the ArangoDB
Client tools package.

There are two output files, one represents file and directory metadata.  This is
uploaded to the `Objects` collection, which must be specified on the command
line.

`arangoimport -c Objects <name of file with metadata>.jsonl`

We use the json lines format for these files.  Depending upon the size of your
file, this uploading process can take considerable time.

The second file represents the relationships between the objects and this is
uploaded to the `Relationships` collection, which also must be specified on the
command line.  Note that these collections should already exist inside the
Arango database.

`arangoimport -c Relationships <name of file with metadata>.jsonl`

The `arangoimport` tool will tell you how many objects were successfully
inserted.  This should show no errors or warnings.  If it does, there is an
issue and it will need to be resolved before using the rest of the Indaleko
facilities.

**Note:** we hope to automate this upload process at some point.

#### MacOS

Note: this section has not been updated since early 2024.

This section describes how to set up Indaleko on MacOS X.

##### Capture System Configuration

Run `MacHardwareInfoGenerator.py` to get the config your mac. It is saved in the `.config` directory. It saves the meta-data about your Mac including the name and size of the volumes, hardware info, etc.

```python
python MacHardwareInfoGenerator.py -d ./config
```

The output will be saved inside the `config` directory with this name pattern `macos-hardware-info-[GUID]-[TIMESTAMP].json`. The following is a sample of what you should see:

```json
{
    "MachineGuid": "74457f40-621b-444b-950b-21d8b943b28e",
    "OperatingSystem": {
        "Caption": "macOS",
        "OSArchitecture": "arm64",
        "Version": "20.6.0"
    },
    "CPU": {
        "Name": "arm",
        "Cores": 8
    },
    "VolumeInfo": [
        {
            "UniqueId": "/dev/disk3s1s1",
            "VolumeName": "disk3s1s1",
            "Size": "228.27 GB",
            "Filesystem": "apfs"
        },
        {
            "UniqueId": "/dev/disk3s6",
            "VolumeName": "disk3s6",
            "Size": "228.27 GB",
            "Filesystem": "apfs"
        }
    ]
}
```

#### Index Your Storage

Once you have captured the configuration, the first step is to index your storage.

#### Process Your Storage Indexing

This is the process we call _ingestion_, which takes the raw indexing data,
normalizes it, and captures it into files that can be bulk uploaded into the
database.  Future versions may automate more of this pipeline.

#### Linux

Note: this section has not updated since early 2024.

# Ingestion Validator

After ingesting the index data, it is necessary to ensure that what ended up in the database is what we want, especially in terms of the relationships we define. This is more important during development, while it can be ignored when using the tool.

There is a [validators](validators/) package where it contains the code and scripts for validation. The main validator code is [IndalekoIngesterValidator.py](/validators/IndalekoIngesterValidator.py). The scripts in the package are used to extract _rules_ that should be checked against the ingested data. The current validator performs the following checks:

* Validates the number of distinct file types, i.e., different `st_mode` values, to be exactly the same as what we have seen in the index file.

* Validates the `Contains` and `Contained By` relationships for each folder. The current version only validates the number of children rather than an exact string match.

Here's how we can use it:

1. Install [jq](https://jqlang.github.io/jq/). It is a powerful tool for working with `json` and `jsonl` files.
2. Run [extract_validation.sh](validators/extract_validations.sh) passing the path to the index file we ingested:

```bash
validators$ extract_validation.sh /path/to/the/index_file
```

The script creates a `validations.jsonl` file inside the `data` folder where each line is a rule to be checked. Here are three examples of these rules:

```json
{"type":"count","field":"st_mode","value":16859,"count":1}
{"type":"contains","parent_uri":"/Users/sinaee/.azuredatastudio","children_uri":["/Users/sinaee/.azuredatastudio/extensions","/Users/sinaee/.azuredatastudio/argv.json"]}
{"type":"contains","parent_uri":"/Users/sinaee/.azuredatastudio","children_uri":["/Users/sinaee/.azuredatastudio/extensions","/Users/sinaee/.azuredatastudio/argv.json"]}
{"type":"contained_by","child_uri":"/Users/sinaee/.azuredatastudio/extensions/microsoft.azuredatastudio-postgresql-0.2.7/node_modules/dashdash/package.json","parent_uris":["/Users/sinaee/.azuredatastudio/extensions/microsoft.azuredatastudio-postgresql-0.2.7/node_modules/dashdash"]}
```

3. Run [IndalekoIngesterValidator](validators/IndalekoIngesterValidator.py) passing the config file path and the validations path

```bash
validators$ python IndalekoIngesterValidator.py -c /Users/sinaee/Projects/Indaleko/config/indaleko-db-config.ini -f ./data/validations.jsonl
```

You should not see any errors; the skipping messages are fine.

# How to use Indaleko?

To view your data, navigate to `http://localhost:8529/` and log in using your
username and password. You can find these credentials in `config/indaleko-db-config.ini` under `user_name` and `user_password`.

We are actively working on query tools as well.

# License

```
    Indaleklo Project README file
    Copyright (C) 2024 Tony Mason

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

# Tooling

Note: as of October 18, 2024.  Adding this as I try to migrate towards modern tooling for the project.

## UV

This is a pip replacement package manager that I've started to use.
You can install it from the [UV](https://docs.astral.sh/uv/) website.  It also handles virtual environments.

The [setup_env.py](utils/setup_env.py) script will actually download and install `uv`.  It is then used to
maintain the python package ecosystem for the project.
