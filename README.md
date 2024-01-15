# Project Indaleko

Project Indaleko is about creating a _Unified Private Index_.  The key
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

Last Updated: January 10, 2024

# How to use Indaleko?

## 1. Set up Indaleko

See `dbsetup.py` to set up the database. It creates the necessary folders, `config` and `data` directories.

## 2. Create your machine config?

### MacOS
- Run `MacHardwareInfoGenerator.py` to get the config your mac. It is saved in the `.config` directory. It saves the meta-data about your mac including the name and size of the volumes, hardware info, etc.
 
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

## 3. Index your machine

## 4. Ingest your indexed data