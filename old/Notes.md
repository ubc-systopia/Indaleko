# Notes

The following data was collected on June 2-3, 2023

The experiment was run on my laptop.

## Hardware

The following is output from a powershell script to capture important
information about this computer:

PS C:\Users\TonyMason\source\repos\arangodb> .\windows-hardware-info.ps1
CPU:  11th Gen Intel(R) Core(TM) i7-11800H @ 2.30GHz
Cores:  8
Logical Processors:  16
Total Physical Memory (MB):  65237.5
Disk:  C:
   Size (GB):  952.807331085205
   Free Space (GB):  351.777450561523
Operating System:  Microsoft Windows 11 Enterprise
OS Architecture:  64-bit
Version:  10.0.22631
Network Adapter:  Killer(R) Wi-Fi 6E AX1675x 160MHz Wireless Network Adapter (210NGW)
   IP Address(es):  10.0.0.149 fe80::1aad:720e:f95c:d44a 2604:3d09:1c78:3e0:41a3:8d52:bd71:38a 2604:3d09:1c78:3e0:102e:6d02:c0e9:ba94 2604:3d09:1c78:3e0::f4ac
   MAC Address:  58:6C:25:FD:F2:19
Network Adapter:  VMware Virtual Ethernet Adapter for VMnet1
   IP Address(es):  192.168.70.1 fe80::a740:9819:6d0e:8aa1
   MAC Address:  00:50:56:C0:00:01
Network Adapter:  VMware Virtual Ethernet Adapter for VMnet8
   IP Address(es):  192.168.80.1 fe80::170f:cb1d:b0ce:99c3
   MAC Address:  00:50:56:C0:00:08

## Software

### Windows

![Windows 11 22H2 Build 22631.1825](win11-msi-screenshot-2023-06-03.png)


### Python

Python Version 3.11.3

```
PS C:\Users\TonyMason\source\repos\arangodb> python --version
Python 3.11.3
```

### Powershell

## Indexing

I indexed all files within my personal home directory using a single-threaded
python script. For each file and directory I collected basic information about
the file or directory.  As of this date my data objects collect basic data.
Here is a capture of the data stored for the root directory (in this case my directory).

```json
{
  "url": "file:///C:\\Users\\TonyMason",
  "timestamps": {
    "created": "2022-05-12T03:58:31.772680",
    "modified": "2023-05-20T18:07:38.113334",
    "accessed": "2023-06-02T17:59:49.184568"
  },
  "size": 24576,
  "mode": 16895,
  "posix attributes": {
    "BLK": false,
    "CHR": false,
    "DIR": true,
    "DOOR": false,
    "FIFO": false,
    "LNK": false,
    "PORT": false,
    "REG": false,
    "SOCK": false,
    "WHT": false
  },
  "dev": 3093971466,
  "inode": 23643898043695210,
  "Windows Attributes": {
    "ARCHIVE": false,
    "COMPRESSED": false,
    "DEVICE": false,
    "DIRECTORY": true,
    "ENCRYPTED": false,
    "HIDDEN": false,
    "INTEGRITY_STREAM": false,
    "NORMAL": false,
    "NOT_CONTENT_INDEXED": false,
    "NO_SCRUB_DATA": false,
    "OFFLINE": false,
    "READONLY": false,
    "REPARSE_POINT": false,
    "SPARSE_FILE": false,
    "SYSTEM": false,
    "TEMPORARY": false,
    "VIRTUAL": false
  }
}```

Here is the data for the first indexed file:

{
  "url": "file:///C:\\Users\\TonyMason\\.gitconfig",
  "timestamps": {
    "created": "2023-05-16T21:54:14.766563",
    "modified": "2023-05-16T21:54:14.766563",
    "accessed": "2023-06-02T17:58:52.732700"
  },
  "size": 175,
  "mode": 33206,
  "posix attributes": {
    "BLK": false,
    "CHR": false,
    "DIR": false,
    "DOOR": false,
    "FIFO": false,
    "LNK": false,
    "PORT": false,
    "REG": true,
    "SOCK": false,
    "WHT": false
  },
  "dev": 3093971466,
  "inode": 8444249301482995,
  "Windows Attributes": {
    "ARCHIVE": true,
    "COMPRESSED": false,
    "DEVICE": false,
    "DIRECTORY": false,
    "ENCRYPTED": false,
    "HIDDEN": false,
    "INTEGRITY_STREAM": false,
    "NORMAL": false,
    "NOT_CONTENT_INDEXED": false,
    "NO_SCRUB_DATA": false,
    "OFFLINE": false,
    "READONLY": false,
    "REPARSE_POINT": false,
    "SPARSE_FILE": false,
    "SYSTEM": false,
    "TEMPORARY": false,
    "VIRTUAL": false
  }
}
```

One of the questions that this helps me answer is "does the inode number correspond with the NTFS file ID."  The answer does appear to be yes.  The initial directory has a value that is off by 2, but NTFS uses the low order bits for versioning.  I need to review NTFS and confirm the number of bits.  The first file was a direct match.  This is useful because it means I don't have to build Windows specific code for doing this.

The python script used the recursive descent code inbuilt within Python.  I tracked the total number of objects created and tracked the elapsed time needed.  Detailed information about this can be found in the separate log file <a href='wam-msi-indexing-2023-06-02.log'>WAM MSI Indexing Log 2023-06-02</a>

The script computes the time per item indexed:

```
Added 3118276 in 15:19:36.845861 time (0.017694663930004913 seconds per entry)
```

One of the useful observations is that in preliminary testing I had observed similar performance results; this is part of the exploration that I did where I was trying to determine if it was more efficient to check for the entry explicitly and then create it or just try to create it, capture the index exception, and skip forward.

Here is a typical timing for a much smaller data set.

```
Added 106 in 0:00:01.949168 time (0.018388377358490565 seconds per entry)
```

This suggests that scaling is actually quite good with ArangoDB. Note that I was never able to get more than approximately 250,000 nodes indexed with Neo4j and that was _before_ I added indexing.

There are some issues that I need to explore with the script.  While I saw some behaviours I expected (e.g., entries that disappeared during the enumeration) there was one class of issue that suggests a bug with the script.  Here is a representative sample:

```
Processing File C:\Users\TonyMason\OneDrive -
wamason.com\swig\swig\Examples\test-suite\scilab\scilab_identifier_name_runme.sci,
exception string indices must be integers, not 'str'
```

There are a large number of such instances and I need to see if I can reproduce the issue and determine the root cause.  While it is not critical at _this_ point in my investigation, this should not be happening.

Overall, this is quite encouraging at this point.  There are multiple directions
to consider:

* How can I optimize/boost the performance of this initial indexing
information
*  I need to add information about the storage device from which the data was
collected.  Note that there is a "dev" value returned by Python and this may be
enough, though I will need to figure out how this value is derived so I can use
it in other tools/utilities perhaps.
* I need to consider other metadata to index. Notable suggestions here are:
(1) extended attributes of the flie (there is a Python mechanism for fetching
this); (2) alternate data streams.
* Checksums: I am interested in collecting checksums.  I view this as a
  background activity, not a primary scan activity and it should likely only be
  done on files that are online (to prevent expensive recalls of files from
  remote storage.)
* Indexing cloud storage.  I have multiple cloud storage services that I use:
    - Dropbox
    - Google Drive
    - OneDrive (both personal and business)
    - Sync.com
    - iCloud

  This is a pretty extensive list and being able to index these and use those
  checksums could provide insight into identifying common files.

* Adding activity information.  My earlier work focused on _storage_ events and
  I should integrate that into my graph database.  Note that this will need to
  be integrated with cloud storage as well.
* Adding schema.  These will be necessary/useful for allowing me to issue
  GraphQL queries against my data using the ArangoDB Foxx support.
* Considering a non-local version of ArangoDB.  This will become important as I
  consider the sharing of a single index between devices; even if this is not
  part of my initial work, it should not be too complicated to switch over.
  Plus the "Enterprise" version of ArangoDB has greater capabilities.
* Consider a non-container version of ArangoDB (e.g., inside a VM or on a
  separate box) for additional evaluation.
* Consider how I could build a script to take a _local_ repository and then
  upload that data into a remote repository.  This is part of the "how can I
  expand on my earlier findings about search" work. The idea here would be to
  use that for an IR paper (for example) or possibly a SIGCHI paper (remember,
  mid-September deadline for this.)

Overall, I find this encouraging.  Building on this base will be quite
interesting, especially once there are enough pieces to begin considering
inference abilities of the graph database.

One small work-item.  I ran the enumeration script over the same directory.
This shows the overhead of Python and the OS.

Here are those results:

```
PS C:\Users\TonyMason\source\repos\arangodb> python .\enumerate-volume.py
Total files: 2810075
Total directories: 330443
Enumerated 3140518 in 0:00:45.748005 time (1.4567025248701011e-05 seconds per entry)
```

Thus, the overhead is _not_ in the enumeration, it is in the processing of the
file.  I might want to consider adding the os operations (stat) again because
this will help isolate the _database_ costs against the _OS_ costs.

2023-06-04: Follow-up on the previous suggestion. I modified the
enumerate-volume.py script to perform an actual stat on each file/directory.  I
ignore any errors (e.g., transient files) and use the stat data to perform a
trivial computation.  I then re-ran said script.  As expected, this is much
slower than just enumerating the shape of the tree.

```
PS C:\Users\TonyMason\source\repos\arangodb> python .\enumerate-volume.py
Total files: 2800767
Total directories: 329120
Enumerated 3129887 in 0:05:32.352318 time (0.00010618668277800445 seconds per entry)
```
So, there is substantial overhead in extracting the metadata, but it is _not_ at
the same order of magnitude as sending it to the database.  This does suggest I
may be able to speed this up.


